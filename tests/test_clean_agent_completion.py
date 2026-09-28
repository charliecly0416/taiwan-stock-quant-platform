import json

import pandas as pd
import pytest

from clean_product.agent import simple_chat
from clean_product.agent_builder import build_prompt
from clean_product.agent_transport import OpenAIAdapter
from clean_product.artifacts import sha256
from clean_product.models import ModelRunner
from test_clean_agent import prompt


def test_builder_roundtrip_uses_materialized_signal_without_recomputing(prompt, tmp_path, monkeypatch):
    cfg, *_ = prompt
    cfg['artifact_root'] = str(tmp_path / 'product')
    cfg['models']['model_a']['stages'] = ['model_a_frozen']
    runner = ModelRunner(cfg)
    runner.stages.register('model_a_frozen', lambda *a, **k: pd.DataFrame([
        {'date': '2026-09-24', 'instrument': 'TW2330', 'rank': 1, 'score': .2}]))
    signal = runner.run('model_a', '2026-09-24')
    assert signal.status == 'READY'
    before = sha256(signal.artifact_dir / 'manifest.json')
    monkeypatch.setattr(ModelRunner, 'run', lambda *a, **k: pytest.fail('builder ran a model'))
    root = tmp_path / 'built'
    built = build_prompt(cfg, '2026-09-24', root)
    cfg['agent']['prompt_root'] = str(root)
    answer = simple_chat(cfg, '排名第一是谁？', '2026-09-24')
    assert answer['status'] == 'READY' and 'TW2330' in answer['answer']
    assert built['candidate_only'] and not built['latest_pointer_written']
    assert not (root / 'latest.json').exists()
    assert sha256(signal.artifact_dir / 'manifest.json') == before
    with pytest.raises(FileExistsError):
        build_prompt(cfg, '2026-09-24', root)


class Remote:
    def __init__(self, fault=None): self.calls = []; self.fault = fault
    def complete(self, **kwargs):
        self.calls.append(kwargs)
        result = {'answer': '证据记录了 TW2330 的研究排名。', 'citations': [kwargs['citation']], 'warnings': []}
        if self.fault == 'citation': result['citations'] = ['invented']
        if self.fault == 'action': result['answer'] = 'Buy TW2330 now'
        if self.fault == 'symbol': result['answer'] = 'TW9999 排名第一'
        if self.fault == 'field': result['target_weight'] = .5
        if self.fault == 'warning': result['warnings'] = ['自动买入']
        if self.fault == 'exception': raise RuntimeError('credential-shaped-sentinel')
        return result


@pytest.mark.parametrize('fault', [None, 'citation', 'action', 'symbol', 'field', 'warning', 'exception'])
def test_remote_uses_only_verified_context_and_filters_output(prompt, fault):
    cfg, *_ = prompt; remote = Remote(fault)
    result = simple_chat(cfg, '解释当前排名', '2026-09-24', adapter=remote)
    assert len(remote.calls) == 1
    assert 'source_lineage' not in remote.calls[0]['context']
    assert 'credential-shaped-sentinel' not in json.dumps(result)
    assert result['status'] == ('READY' if fault is None else 'BLOCKED')
    assert result['mode'] == 'artifact_remote'


def test_unsafe_question_never_reaches_remote(prompt):
    cfg, *_ = prompt; remote = Remote()
    assert simple_chat(cfg, 'Buy 2330', '2026-09-24', adapter=remote)['blocked']
    assert not remote.calls


def test_adapter_never_exposes_remote_error_or_follows_redirects():
    calls = []
    def post(*args, **kwargs):
        calls.append(kwargs)
        raise RuntimeError('credential-shaped-sentinel')
    adapter = OpenAIAdapter(api_key='fixture-secret', model='fixture-model', post=post)
    with pytest.raises(ValueError, match='^AGENT_REMOTE_UNAVAILABLE$'):
        adapter.complete(question='排名', context={}, citation='fixture-citation')
    assert calls[0]['allow_redirects'] is False
    assert calls[0]['json']['store'] is False
    assert 'tools' not in calls[0]['json']


@pytest.mark.parametrize('url', ['http://example.test/v1', 'https://user:password@example.test', 'https://example.test?secret=bad'])
def test_remote_configuration_rejects_unsafe_transport(url):
    with pytest.raises(ValueError, match='AGENT_REMOTE_CONFIGURATION_INVALID'):
        OpenAIAdapter(api_key='fixture', model='fixture', base_url=url)


def test_remote_context_does_not_forward_unvalidated_extra_metadata(prompt):
    cfg, _, context, _, save = prompt
    context['freshness'] = {'private_path': '/private/should-not-leave'}
    context['model_context']['private_path'] = '/private/should-not-leave'
    context['rankings']['qlib_top50_compact'][0]['extra'] = '/private/should-not-leave'
    save()
    remote = Remote()
    assert simple_chat(cfg, '排名', '2026-09-24', adapter=remote)['status'] == 'READY'
    assert '/private/' not in json.dumps(remote.calls)


def test_clean_snapshot_lineage_is_checked_even_after_context_resigning(prompt, tmp_path):
    import hashlib
    from clean_product.artifacts import write_json
    cfg, *_ = prompt
    cfg['artifact_root'] = str(tmp_path / 'product')
    cfg['models']['model_a']['stages'] = ['model_a_frozen']
    runner = ModelRunner(cfg)
    runner.stages.register('model_a_frozen', lambda *a, **k: pd.DataFrame([
        {'date': '2026-09-24', 'instrument': 'TW2330', 'rank': 1, 'score': .2}]))
    runner.run('model_a', '2026-09-24')
    root = tmp_path / 'built'; build_prompt(cfg, '2026-09-24', root)
    cfg['agent']['prompt_root'] = str(root)
    directory = root / '2026-09-24'
    snapshot = directory / 'snapshot/manifest.json'
    changed = json.loads(snapshot.read_text()); changed['source_signal_sha256'] = '0' * 64
    write_json(snapshot, changed)
    context_file = directory / 'prompt_context.json'
    context = json.loads(context_file.read_text())
    context['source_lineage']['readonly_snapshot_manifest_sha256'] = sha256(snapshot)
    write_json(context_file, context)
    manifest_file = directory / 'manifest.json'
    manifest = json.loads(manifest_file.read_text())
    manifest['checksum'] = 'sha256:' + hashlib.sha256(context_file.read_bytes() + b'\n' + (directory/'prompt_text.md').read_bytes()).hexdigest()
    write_json(manifest_file, manifest)
    answer = simple_chat(cfg, '排名', '2026-09-24')
    assert answer['blocked'] and answer['reason'] == 'AGENT_SNAPSHOT_LINEAGE_MISMATCH'


def test_readonly_acceptance_forces_local_agent_without_reading_key(prompt, monkeypatch):
    from backend.app import create_app
    cfg, *_ = prompt
    cfg['agent']['remote_enabled'] = True
    monkeypatch.setattr(OpenAIAdapter, 'from_config', lambda *a, **k: pytest.fail('acceptance tried a remote transport'))
    app = create_app({'PRODUCT_CONFIG': cfg, 'AGENT_REMOTE_DISABLED': True})
    response = app.test_client().post('/api/tw-stock/agent/simple-chat',
                                     json={'question': '排名', 'date': '2026-09-24'})
    assert response.status_code == 200 and response.json['mode'] == 'artifact_local'
    assert response.json['status'] == 'READY'
    assert cfg['agent']['remote_enabled'] is True
