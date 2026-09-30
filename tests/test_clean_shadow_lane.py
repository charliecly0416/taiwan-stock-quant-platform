import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from clean_product.artifacts import sha256, write_json
from clean_product.config import env_config
from clean_product.features import _institutional, _margin, _market, _price_features, derive_available_at, write_b19_feature_artifact
from clean_product.models import ModelBlocked, _b19r2r
from clean_product.shadow import run_shadow


def runtime(tmp_path):
    store = tmp_path / 'artifacts'; root = store / 'releases/a'
    active = {'schema_version': 'tw.clean.release.v1', 'artifact_root': str(root), 'run_id': 'A1', 'asof': '2026-09-29'}
    write_json(store / 'active.json', active)
    cfg = {'artifact_root': str(store), 'model_stages': {'b19r2r_frozen': {}}}
    target = tmp_path / 'config.yaml'; target.write_text(yaml.safe_dump(cfg))
    return cfg, target, store, active


def test_shadow_failure_retry_and_next_baseline_are_independent(tmp_path, monkeypatch):
    cfg, target, store, active = runtime(tmp_path)
    calls = []
    def execute(config, result, local_only):
        calls.append(result['run_id'])
        if len(calls) == 1: raise ModelBlocked('SOURCE_NOT_YET_AVAILABLE')
        feature = Path(result['artifact_root']) / 'features.parquet'
        feature.parent.mkdir(parents=True, exist_ok=True); feature.write_text('fixture')
        result.update(status='READY', feature_artifact={'path': str(feature), 'sha256': sha256(feature)})
    monkeypatch.setattr('clean_product.shadow._execute', execute)
    first = run_shadow(config_path=target, trigger_reason='scheduled')
    assert first['status'] == 'BLOCKED' and not first['mainline_blocking']
    second = run_shadow(config_path=target, trigger_reason='scheduled')
    assert second['status'] == 'READY' and second['latest_pointer_written']
    assert json.loads((store / 'active.json').read_text()) == active
    assert env_config(cfg)['_shadow_root'] == Path(second['artifact_root'])
    scheduled = (store / 'shadow_scheduler_status.json').read_bytes()
    run_shadow(config_path=target, trigger_reason='manual')
    assert (store / 'shadow_scheduler_status.json').read_bytes() == scheduled
    active['run_id'] = 'A2'; active['asof'] = '2026-09-30'
    write_json(store / 'active.json', active)
    assert '_shadow_root' not in env_config(cfg)


def test_baseline_changed_during_shadow_does_not_attach(tmp_path, monkeypatch):
    _, target, store, active = runtime(tmp_path)
    def execute(config, result, local_only):
        active['run_id'] = 'A2'; write_json(store / 'active.json', active)
        result['status'] = 'READY'
    monkeypatch.setattr('clean_product.shadow._execute', execute)
    result = run_shadow(config_path=target)
    assert result['reason'] == 'SHADOW_BASELINE_CHANGED_RETRY'
    assert not (store / 'shadow_active.json').exists()


def test_real_delta_is_consumed_by_b_stage_and_cannot_override_frozen_dates(tmp_path, monkeypatch):
    order = [f'f{i}' for i in range(78)]
    stage = {'feature_schema': str(tmp_path / 'schema.json'), 'historical_features': str(tmp_path / 'historical.parquet'),
             'training_manifest': str(tmp_path / 'training.json'), 'model_path': str(tmp_path / 'model.pkl'), 'exclude': ['TW7769']}
    write_json(Path(stage['feature_schema']), {'feature_order': order})
    write_json(Path(stage['training_manifest']), {'model_id': 'modelb_b19r2r_lambdarank_exact50_78f_v2'})
    pd.DataFrame([{'date': '2026-05-07', 'instrument': 'TW2330', **dict.fromkeys(order, 0.)}]).to_parquet(stage['historical_features'])
    rows = pd.DataFrame([{'date': '2026-09-29', 'instrument': f'TW{2300+i}', 'score': float(50-i), 'rank': i+1} for i in range(50)])
    frame = rows[['date', 'instrument']].copy()
    for name in order: frame[name] = np.arange(50, dtype=float)
    artifact = write_b19_feature_artifact(frame=frame, asof='2026-09-29', config={'artifact_root': tmp_path}, feature_order=order, run_id='r1')
    stage.update(feature_delta=artifact['path'], feature_delta_sha256=artifact['sha256'])
    class Model:
        booster_ = type('Booster', (), {'feature_name': lambda self: order})()
        def predict(self, numeric): return numeric.f0.to_numpy()
    monkeypatch.setattr('clean_product.models._joblib', lambda _: Model())
    result = _b19r2r(rows, asof='2026-09-29', config={}, stage=stage, fixture=False, data={})
    assert len(result) == 50 and result.iloc[0].instrument == 'TW2349'
    stage['feature_delta_sha256'] = None
    with pytest.raises(ValueError, match='CHECKSUM'): _b19r2r(rows, asof='2026-09-29', config={}, stage=stage, fixture=False, data={})
    with pytest.raises(ModelBlocked, match='ALREADY_EXISTS'):
        write_b19_feature_artifact(frame=frame, asof='2026-09-29', config={'artifact_root': tmp_path}, feature_order=order, run_id='r2')


def test_source_categories_balances_and_availability_are_not_neutral_filled():
    institutional = pd.DataFrame([{'stock_id': '2330', 'date': '2026-09-28', 'name': name, 'buy': buy, 'sell': 1}
                                  for name, buy in [('Foreign_Investor', 10), ('Foreign_Dealer_Self', 999), ('Investment_Trust', 3), ('Dealer_self', 4), ('Dealer_Hedging', 5)]])
    margin = pd.DataFrame([{'stock_id': '2330', 'date': '2026-09-28', 'MarginPurchaseTodayBalance': 30,
                           'MarginPurchaseYesterdayBalance': 25, 'ShortSaleTodayBalance': 3, 'ShortSaleYesterdayBalance': 5, 'Note': ' '}])
    data = {'prices': pd.DataFrame({'date': ['2026-09-28', '2026-09-29']}), 'institutional': institutional, 'margin': margin}
    derive_available_at(asof='2026-09-29', data=data, config={'datasets': {'institutional': {'lag_days': 1}, 'margin': {'lag_days': 1}}})
    inst = _institutional(data['institutional'], '2026-09-28', asof='2026-09-29').iloc[0]
    assert inst.foreign_net_buy == 1007 and inst.dealer_net_buy == 7 and inst.institutional_total_net_buy == 1016
    flow = _margin(data['margin'], '2026-09-28', asof='2026-09-29').iloc[0]
    assert flow.margin_balance_change == 5 and flow.short_balance_change == -2
    data['margin']['Note'] = 'OX'
    assert np.isnan(_margin(data['margin'], '2026-09-28', asof='2026-09-29').iloc[0].margin_balance)
    data['institutional'] = data['institutional'][data['institutional'].name.ne('Investment_Trust')]
    assert np.isnan(_institutional(data['institutional'], '2026-09-28', asof='2026-09-29').iloc[0].institutional_total_net_buy)


def test_index_must_cover_current_session_and_canonical_calendar():
    calendar = pd.bdate_range('2025-01-01', periods=125).strftime('%Y-%m-%d').tolist()
    frame = pd.DataFrame({'date': calendar, 'close': np.arange(125) + 100.})
    assert np.isfinite(_market(frame, calendar[-1], calendar)['TWII_close_vs_MA120'])
    with pytest.raises(ModelBlocked, match='STALE_OR_GAPPED'): _market(frame.iloc[:-1], calendar[-1], calendar)
