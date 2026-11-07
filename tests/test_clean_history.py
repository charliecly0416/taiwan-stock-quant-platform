from copy import deepcopy
from pathlib import Path
import json

import pandas as pd
import pytest

from clean_product.artifacts import write_json
from clean_product.config import env_config
from clean_product.models import ModelRunner
from clean_product.service import ProductService


@pytest.fixture
def config(tmp_path):
    store = tmp_path / 'artifacts'
    root = store / 'releases/current'
    provider = tmp_path / 'provider'
    (provider / 'calendars').mkdir(parents=True)
    (provider / 'calendars/day.txt').write_text('2026-09-23\n2026-09-24\n2026-09-25\n')
    write_json(store / 'active.json', {'schema_version': 'tw.clean.release.v1', 'artifact_root': str(root),
                                       'run_id': 'A2', 'asof': '2026-09-25'})
    return env_config({'artifact_root': str(store), 'data_root': str(tmp_path / 'data'),
                       'model_stages': {'test_stage': {}, 'model_a_frozen': {'provider_uri': str(provider)}},
                       'models': {'model_a': {'role': 'baseline', 'stages': ['test_stage']},
                                  'model_a_plus_b': {'role': 'shadow', 'stages': ['test_stage'], 'production_allowed': False}},
                       'datasets': {}, 'strategy': 'top50_exit_one_worst_sell', 'execution': 'next_open',
                       'simulation': {'initial_cash': 1000, 'max_positions': 1, 'buy_cost_rate': 0, 'sell_cost_rate': 0, 'min_cost': 0}})


def store_signal(config, root, model, day, score=.9):
    work = deepcopy(config); work['artifact_root'] = root
    runner = ModelRunner(work)
    runner.stages.register('test_stage', lambda *args, **kwargs: pd.DataFrame(
        [{'date': day, 'instrument': 'TW2330', 'score': score, 'rank': 1}]))
    result = runner.run(model, day)
    assert result.status == 'READY'
    return result


def bundle(config, name='restored', source='A1', created='2026-09-25T00:00:00+00:00'):
    root = config['_artifact_store'] / 'history' / name
    write_json(root / 'run.json', {'schema_version': 'tw.clean.history.v1', 'status': 'READY',
                                   'artifact_root': str(root), 'source_run_id': source, 'created_at': created})
    return root


def test_old_signals_survive_new_provider_and_latest_shadow(config):
    root = bundle(config)
    old = deepcopy(config); old['datasets'] = {'prices': {'params': {'provider_uri': 'old-provider'}}}
    for day in ('2026-09-23', '2026-09-24'):
        store_signal(old, root, 'model_a_plus_b', day)
    service = ProductService(config)
    service.runner.run = lambda *args, **kwargs: pytest.fail('stored history was recomputed')
    result = service.rankings('model_a_plus_b', '2026-09-23')
    assert result['status'] == 'READY' and result['rows'][0]['score'] == .9
    assert result['provenance']['source_run_id'] == 'A1'
    assert service.history('model_a_plus_b')['dates'] == ['2026-09-23', '2026-09-24']


@pytest.mark.parametrize('fault', ['csv', 'model_identity', 'fingerprint', 'context_type', 'stage_type', 'manifest_type'])
def test_invalid_history_is_blocked_without_recompute_or_older_fallback(config, fault):
    older = bundle(config, 'older', created='2026-09-24')
    root = bundle(config, 'newer', created='2026-09-25')
    store_signal(config, older, 'model_a_plus_b', '2026-09-23', .5)
    result = store_signal(config, root, 'model_a_plus_b', '2026-09-23')
    manifest = result.artifact_dir / 'manifest.json'
    payload = json.loads(manifest.read_text())
    if fault == 'csv':
        (result.artifact_dir / 'signals.csv').write_text('corrupt')
    elif fault == 'model_identity':
        payload['pipeline_context']['model_stages']['test_stage']['model_path'] = 'another-model'
    elif fault == 'context_type':
        payload['pipeline_context']['model_stages'] = ['test_stage']
    elif fault == 'stage_type':
        payload['pipeline_context']['model_stages']['test_stage'] = 1
    elif fault == 'manifest_type':
        payload = []
    else:
        payload['pipeline_fingerprint'] = 'wrong'
    write_json(manifest, payload)
    service = ProductService(config)
    service.runner.run = lambda *args, **kwargs: pytest.fail('invalid signal bypassed')
    assert service.signal('model_a_plus_b', '2026-09-23').status == 'BLOCKED'
    assert service.history('model_a_plus_b')['dates'] == []


def test_unpublished_and_wrong_same_day_batch_are_not_history(config):
    root = config['_artifact_store'] / 'shadow/unpublished'
    store_signal(config, root, 'model_a_plus_b', '2026-09-23')
    write_json(root / 'run.json', {'status': 'READY', 'artifact_root': str(root), 'latest_pointer_written': False})
    write_json(config['_artifact_store'] / 'history/corrupt/run.json', [])
    old = bundle(config)
    store_signal(config, old, 'model_a_plus_b', '2026-09-25')
    assert ProductService(config).history('model_a_plus_b')['dates'] == []


def test_published_scheduled_shadow_is_discovered_automatically(config):
    root = config['_artifact_store'] / 'shadow/scheduled'
    store_signal(config, root, 'model_a_plus_b', '2026-09-25')
    write_json(root / 'run.json', {'status': 'READY', 'artifact_root': str(root), 'latest_pointer_written': True,
                                  'source_run_id': 'A2', 'created_at': '2026-09-25'})
    assert ProductService(config).history('model_a_plus_b')['dates'] == ['2026-09-25']


def test_comparison_uses_baseline_from_shadow_source_release(config):
    root = bundle(config)
    store_signal(config, root, 'model_a', '2026-09-24', .7)
    store_signal(config, root, 'model_a_plus_b', '2026-09-24', .8)
    store_signal(config, config['artifact_root'], 'model_a', '2026-09-24', .9)
    result = ProductService(config).compare('model_a', 'model_a_plus_b', '2026-09-24')
    assert result['status'] == 'READY' and result['rows'][0]['left_score'] == .7


def test_history_replay_reads_each_saved_day_and_next_open(config, monkeypatch):
    root = bundle(config)
    for day in ('2026-09-23', '2026-09-24'):
        store_signal(config, root, 'model_a_plus_b', day)
    service = ProductService(config)
    monkeypatch.setattr(service, '_model_data', lambda *args: {'prices': pd.DataFrame([
        {'stock_id': '2330', 'date': '2026-09-23', 'open': 10., 'close': 10.},
        {'stock_id': '2330', 'date': '2026-09-24', 'open': 10., 'close': 9.},
        {'stock_id': '2330', 'date': '2026-09-25', 'open': 9., 'close': 8.}])})
    monkeypatch.setattr(ModelRunner, 'precompute', lambda *args, **kwargs: pytest.fail('historical artifacts bypassed'))
    service.runner.run = lambda *args, **kwargs: pytest.fail('historical inference bypassed')
    result = service.run_replay('model_a_plus_b', '2026-09-23', '2026-09-25')
    assert result['status'] == 'READY' and result['final_nav'] == 800
    assert result['trades'][0]['execute_date'] == '2026-09-24'
    assert not (config['_artifact_store'] / 'shadow_active.json').exists()
