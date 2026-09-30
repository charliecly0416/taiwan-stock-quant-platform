import json
from pathlib import Path

import pytest

from scripts import deploy_clean_product as deploy
from scripts import install_clean_services as install


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
