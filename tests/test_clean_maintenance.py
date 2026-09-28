import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from clean_product.artifacts import write_json
from clean_product.maintenance import backup, health, restore, retention, rollback_release
from clean_product.paper import PaperStore
from test_clean_release import release_config


@pytest.fixture
def operations(tmp_path):
    root = tmp_path / 'project'; root.mkdir(); (root / 'configs').mkdir()
    (root / 'configs/product.yaml').write_text('product: fixture\n')
    store = root / 'artifacts'; store.mkdir()
    model = root / 'model.pkl'; model.write_bytes(b'frozen-model')
    cfg = {'artifact_root': str(store), 'data_root': str(root / 'data'),
           'maintenance': {'backup_root': str(tmp_path / 'backups'), 'minimum_free_gb': 0},
           'model_stages': {'model_a_frozen': {'model_path': str(model)}},
           'paper': {'store': str(root / 'paper.sqlite3')}}
    PaperStore(cfg['paper']['store']).create('fixture', name='fixture', initial_cash=1000, key='create_fixture')
    return cfg, root, store


def test_backup_restores_independent_files_and_consistent_ledger(operations, tmp_path):
    cfg, root, store = operations
    (root / '.env').write_text('must-not-be-copied')
    result = backup(cfg, project_root=root)
    manifest = json.loads(Path(result['manifest']).read_text())
    assert all('.env' not in item['path'] for item in manifest['files'])
    assert not manifest['credentials_included']
    second = backup(cfg, project_root=root)
    assert result['manifest'] != second['manifest']
    destination = tmp_path / 'restored'
    restored = restore(result['manifest'], destination)
    assert restored['status'] == 'PASS'
    assert (destination / 'model.pkl').read_bytes() == b'frozen-model'
    assert len(PaperStore(destination / 'paper.sqlite3').accounts('fixture')) == 1
    assert not (destination / '.env').exists()
    assert retention(cfg)['automatic_deletion'] is False
    assert restore(result['manifest'], '.', verify_only=True)['status'] == 'PASS'


def test_restore_rejects_tampering_and_never_overwrites_destination(operations, tmp_path):
    cfg, root, _ = operations; result = backup(cfg, project_root=root)
    with pytest.raises(ValueError, match='DESTINATION_MUST_BE_NEW'): restore(result['manifest'], root)
    manifest = json.loads(Path(result['manifest']).read_text()); digest = manifest['files'][0]['sha256']
    obj = tmp_path / 'backups/objects' / digest[:2] / digest; obj.write_text('tampered')
    with pytest.raises(ValueError, match='BACKUP_OBJECT_INVALID'): restore(result['manifest'], tmp_path / 'new')
    assert not (tmp_path / 'new').exists()


def test_backup_rejects_credential_patterns(operations):
    cfg, root, _ = operations
    (root / 'configs/accidental.yaml').write_text('token: ' + 'ghp_' + 'x' * 40)
    with pytest.raises(ValueError, match='CREDENTIAL_PATTERN'): backup(cfg, project_root=root)


class Ready:
    status_code = 200
    def json(self): return {'ready': True}


def test_health_checks_timer_execution_without_inventing_market_sessions(operations):
    cfg, _, store = operations
    now = datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc)
    write_json(store / 'scheduler_status.json', {'status': 'READY', 'asof': '2026-09-24',
               'reason': 'NO_NEW_MARKET_SESSION', 'created_at': '2026-09-28T12:30:00+00:00'})
    write_json(store / 'ops/backup.json', {'status': 'READY', 'created_at': now.isoformat()})
    result = health(cfg, now=now, probe=lambda *a, **k: Ready())
    assert result['status'] == 'OK'
    write_json(store / 'daily_status.json', {'status': 'BLOCKED', 'created_at': now.isoformat()})
    result = health(cfg, now=now, probe=lambda *a, **k: Ready())
    assert result['ready'] and result['status'] == 'CRITICAL'
    assert 'LATEST_DAILY_FAILED' in {a['code'] for a in result['alerts']}


def test_health_detects_missed_timer_and_backup(operations):
    cfg, _, _ = operations
    result = health(cfg, now=datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc), probe=lambda *a, **k: Ready())
    assert {'SCHEDULED_ATTEMPT_MISSING', 'BACKUP_MISSING_OR_OLD'}.issubset({a['code'] for a in result['alerts']})


def test_release_rollback_checks_target_before_switching(release_config):
    from clean_product.orchestrator import run_daily
    from clean_product.config import load_config
    cfg, target = release_config
    first = run_daily('2026-09-24', config_path=target, publish=True, local_only=True)
    second = run_daily('2026-09-24', config_path=target, publish=True, local_only=True)
    result = rollback_release(load_config(target), first['run_id'])
    assert result['previous_run_id'] == second['run_id']
    assert json.loads((Path(cfg['artifact_root']) / 'active.json').read_text())['run_id'] == first['run_id']
    with pytest.raises(ValueError): rollback_release(cfg, '../escape')


def test_health_reports_malformed_status_instead_of_crashing(operations):
    cfg, _, store = operations
    write_json(store / 'scheduler_status.json', [])
    result = health(cfg, now=datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc), probe=lambda *a, **k: Ready())
    assert result['status'] == 'CRITICAL'
    assert 'INVALID_SCHEDULER_STATUS_JSON' in {a['code'] for a in result['alerts']}
