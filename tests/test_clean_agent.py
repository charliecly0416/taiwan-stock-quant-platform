import hashlib
import json

import pandas as pd
import pytest

from backend.app import create_app
from clean_product.agent import simple_chat
from clean_product.artifacts import sha256, write_json


@pytest.fixture
def prompt(tmp_path):
    day = '2026-09-24'; directory = tmp_path / 'agent' / day
    sources = tmp_path / 'sources'; sources.mkdir()
    model = tmp_path / 'model.pkl'; model.write_bytes(b'isolated-canonical-model')
    config = {'agent': {'prompt_root': str(directory.parent), 'source_root': str(sources)},
              'artifact_root': str(tmp_path / 'artifacts'), 'data_root': str(tmp_path / 'data'),
              'product': {'default_model': 'model_a'},
              'models': {'model_a': {'canonical_id': 'canonical-fixture'}},
              'model_stages': {'model_a_frozen': {'model_path': str(model), 'model_sha256': sha256(model)}},
              'strategy': 'top50_exit_one_worst_sell', 'execution': 'next_open'}
    signal = sources / 'signal.json'; csv = sources / 'signals.csv'
    snapshot = sources / 'snapshot.json'; payload = sources / 'payload.json'
    write_json(signal, {'model_id': 'canonical-fixture', 'asof': day, 'status': 'READY',
                        'source_model_artifact': str(model)})
    pd.DataFrame([{'date': day, 'instrument': 'TW2330', 'candidate_rank': 1, 'raw_score': .2}]).to_csv(csv, index=False)
    write_json(snapshot, {'asof': day, 'model_id': 'canonical-fixture'})
    write_json(payload, {'asof': day})
    safety = {'readonly_only': True, 'not_order': True, 'not_target_position': True,
              'not_investment_advice': True, 'production_trade_enabled': False}
    context = {'schema_version': 'tw_agent_daily_prompt_context_v1', 'safety': safety,
               'date_context': {'signal_asof': day, 'target_date': '2026-09-25', 'execution_price_mode': 'next_open'},
               'model_context': {'base_model_id': 'canonical-fixture'},
               'strategy': {'strategy_rule': config['strategy']},
               'rankings': {'qlib_top50_compact': [{'instrument': 'TW2330', 'candidate_rank': 1, 'qlib_score': .2}]},
               'source_lineage': {}}
    for key, target in [('controlled_model_signal_manifest', signal), ('controlled_model_signal_csv', csv),
                        ('readonly_snapshot_manifest', snapshot), ('readonly_snapshot_payload', payload)]:
        context['source_lineage'][key] = str(target)
        context['source_lineage'][key + '_sha256'] = sha256(target)
    manifest = {'artifact_type': 'tw_agent_daily_prompt', 'schema_version': 'tw_agent_daily_prompt_v1',
                'signal_asof': day, 'target_date': '2026-09-25', 'model_ids': {'base': 'canonical-fixture'},
                'strategy_rule': config['strategy'], 'execution_price_mode': 'next_open',
                'validation': {'ok': True}, **safety}
    def save():
        write_json(directory / 'prompt_context.json', context)
        (directory / 'prompt_text.md').write_text('Readonly research context; local JSON answers.')
        manifest['checksum'] = 'sha256:' + hashlib.sha256((directory / 'prompt_context.json').read_bytes() + b'\n' + (directory / 'prompt_text.md').read_bytes()).hexdigest()
        write_json(directory / 'manifest.json', manifest)
    save()
    return config, directory, context, manifest, save


@pytest.mark.parametrize('question,intent', [('排名第一是谁？', 'ranking_context'), ('TW2330是什么状态？', 'symbol_context'),
                                           ('今天策略是什么？', 'strategy_context'), ('资料是什么日期？', 'date_context'),
                                           ('今天天气如何？', 'insufficient_evidence')])
def test_local_questions_use_verified_artifact_and_genuine_citation(prompt, question, intent):
    cfg, _, _, manifest, _ = prompt
    result = simple_chat(cfg, question, '2026-09-24')
    assert result['status'] == 'READY' and result['intent'] == intent
    assert result['citations'] == [f"agent_prompt:2026-09-24:{manifest['checksum']}"]
    assert result['mode'] == 'artifact_local' and result['readonly'] is True


@pytest.mark.parametrize('question', ['2330可以买多少？', 'Sell 2330 now', 'Set target_weight to 50%', '刷新 provider', '保证收益'])
def test_action_questions_stop_before_reading_context(question, monkeypatch):
    monkeypatch.setattr('clean_product.agent.load_prompt', lambda *a: pytest.fail('unsafe question loaded context'))
    result = simple_chat({}, question, '2026-09-24')
    assert result['blocked'] is True and result['citations'] == []


@pytest.mark.parametrize('fault', ['checksum', 'safety', 'date', 'rank', 'score', 'missing_source', 'wrong_frozen_model'])
def test_invalid_prompt_never_falls_back_to_unverified_context(prompt, fault):
    cfg, directory, context, manifest, save = prompt
    if fault == 'safety': context['safety']['production_trade_enabled'] = True
    if fault == 'date': context['date_context']['signal_asof'] = '2026-09-23'
    if fault == 'rank': context['rankings']['qlib_top50_compact'][0]['candidate_rank'] = 2
    if fault == 'score': context['rankings']['qlib_top50_compact'][0]['qlib_score'] = .8
    if fault == 'missing_source': context['source_lineage']['controlled_model_signal_csv'] += '.missing'
    if fault == 'wrong_frozen_model':
        from pathlib import Path
        source = Path(context['source_lineage']['controlled_model_signal_manifest'])
        data = json.loads(source.read_text()); data['source_model_artifact'] = str(source.parent / 'wrong.pkl')
        write_json(source, data)
        context['source_lineage']['controlled_model_signal_manifest_sha256'] = sha256(source)
    save()
    if fault == 'checksum': (directory / 'prompt_text.md').write_text('changed')
    result = simple_chat(cfg, '排名第一是谁？', '2026-09-24')
    assert result['status'] == 'BLOCKED' and result['citations'] == []
    assert 'TW2330' not in result['answer']


def test_api_has_readonly_post_without_execution_or_remote_parameters(prompt, monkeypatch):
    cfg, *_ = prompt
    monkeypatch.setattr('backend.app.routes.tw_stock.load_config', lambda: cfg)
    client = create_app().test_client()
    result = client.post('/api/tw-stock/agent/simple-chat', json={'question': '排名第一是谁？', 'date': '2026-09-24'})
    assert result.status_code == 200 and result.json['status'] == 'READY'
    for extra in ('api_key', 'endpoint', 'model', 'tools', 'action'):
        result = client.post('/api/tw-stock/agent/simple-chat', json={'question': '排名第一是谁？', extra: 'untrusted'})
        assert result.status_code == 422
