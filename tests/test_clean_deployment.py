import json
import io
import tarfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from scripts import deploy_clean_product as deploy
from scripts import install_clean_services as install


def test_prepare_uses_release_candidate_policy_and_restored_model_paths(tmp_path, monkeypatch):
    target = tmp_path / 'release'
    snapshot = tmp_path / 'snapshot.json'
    snapshot.write_text(json.dumps({'active_release': {'asof': '2026-10-07'}}))
    stage = {'provider_uri': '/restored/provider', 'model_path': '/restored/frozen.pkl'}
    old_models = {'model_a_plus_b': {'production_allowed': False}}
    new_models = {'model_a_plus_b': {**old_models['model_a_plus_b'],
                                   'candidate_policy': 'model_a_ranked_eligible_top50'}}
    source = {'daily': {}, 'datasets': {'prices': {}}, 'models': new_models}
    bundle = io.BytesIO()
    with tarfile.open(fileobj=bundle, mode='w') as archive:
        content = yaml.safe_dump(source).encode()
        entry = tarfile.TarInfo('configs/product.yaml'); entry.size = len(content)
        archive.addfile(entry, io.BytesIO(content))

    def restore(*args):
        target.mkdir()
        (target / 'qlib.whl').touch()
        config = {**source, 'models': old_models,
                  'model_stages': {'model_a_frozen': stage},
                  'maintenance': {'runtime_wheel': 'qlib.whl'}}
        (target / 'runtime-config.yaml').write_text(yaml.safe_dump(config))
        return {'files': 1}

    monkeypatch.setattr(deploy, 'restore', restore)
    monkeypatch.setattr(deploy.subprocess, 'check_output',
                        lambda command, **kwargs: 'fixture-commit\n' if 'rev-parse' in command else bundle.getvalue())
    monkeypatch.setattr(deploy.subprocess, 'run', Mock())
    monkeypatch.setattr(deploy.subprocess, 'Popen', Mock(return_value=Mock()))
    monkeypatch.setattr(deploy, 'wait_ready', lambda *args: {'asof': '2026-10-07'})
    monkeypatch.setattr(deploy.requests, 'get', Mock(return_value=Mock(json=lambda: {'status': 'READY', 'rows': [0] * 150})))
    monkeypatch.setattr(deploy.requests, 'post', Mock(return_value=Mock(json=lambda: {'status': 'READY'})))
    deploy.prepare(snapshot, target, 'HEAD', 'python')
    config = yaml.safe_load((target / 'configs/product.yaml').read_text())
    assert config['models'] == new_models
    assert config['model_stages']['model_a_frozen'] == stage
    assert config['datasets']['prices']['params']['provider_uri'] == stage['provider_uri']


def test_old_prepared_snapshot_never_stops_active_service(tmp_path, monkeypatch):
    target = tmp_path / 'release'; target.mkdir()
    (target / 'deployment.json').write_text(json.dumps({'status': 'READY', 'asof': '2026-09-23'}))
    monkeypatch.setattr(deploy.subprocess, 'check_output', lambda *a, **k: str(tmp_path / 'current'))
    monkeypatch.setattr(deploy, 'wait_ready', lambda *a, **k: {'asof': '2026-09-24', 'ready': True})
    monkeypatch.setattr(deploy.subprocess, 'run', lambda *a, **k: pytest.fail('stale deployment mutated services'))
    with pytest.raises(ValueError, match='SNAPSHOT_OUTDATED'): deploy.activate(target)


def test_failed_install_restores_previous_units_and_restarts_old_service(tmp_path, monkeypatch):
    root = tmp_path / 'new'; (root / 'frontend/dist').mkdir(parents=True)
    (root / 'frontend/dist/index.html').write_text('fixture')
    (root / 'ops').mkdir()
    units = ['clean-web.service', 'clean-daily.service', 'clean-daily.timer', 'clean-shadow.service', 'clean-shadow.timer', 'clean-health.service',
             'clean-health.timer', 'clean-backup.service', 'clean-backup.timer']
    for name in units: (root / 'ops' / name).write_text('[Service]\nWorkingDirectory=@ROOT@\n')
    home = tmp_path / 'home'; dest = home / '.config/systemd/user'; dest.mkdir(parents=True)
    original = '[Service]\nWorkingDirectory=/previous-valid-release\n'
    (dest / 'clean-web.service').write_text(original)
    monkeypatch.setattr(install, 'ROOT', root)
    monkeypatch.setattr(Path, 'home', lambda: home)
    monkeypatch.setattr(install.sys, 'argv', ['install', '--start'])
    calls = []
    monkeypatch.setattr(install.subprocess, 'run', lambda command, **k: calls.append(command))
    monkeypatch.setattr(deploy, 'wait_ready', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('not ready')))
    with pytest.raises(RuntimeError, match='not ready'): install.main()
    assert (dest / 'clean-web.service').read_text() == original
    assert calls[-1] == ['systemctl', '--user', 'restart', 'clean-web.service']
    assert any('disable' in call and 'clean-health.timer' in call for call in calls)
    assert list((home / '.local/state/tw-stock-clean/service-installs').glob('*.json'))
