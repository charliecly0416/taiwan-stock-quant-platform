"""Install the clean web, daily, health and backup units; requires existing Python dependencies and UI build."""
from pathlib import Path
import argparse
import os
import json
from uuid import uuid4
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true', help='Start the web and enable the daily timer')
    args = parser.parse_args()
    if not (ROOT / 'frontend/dist/index.html').is_file():
        parser.error('Build frontend first: corepack pnpm --dir frontend build')
    destination = Path.home() / '.config/systemd/user'
    destination.mkdir(parents=True, exist_ok=True)
    state = Path.home() / '.local/state/tw-stock-clean'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret = state / 'paper.secret'
    if not secret.exists():
        with os.fdopen(os.open(secret, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as stream:
            stream.write(secrets.token_urlsafe(48))
    previous = {}; rendered = {}
    for name in ('clean-web.service', 'clean-daily.service', 'clean-daily.timer', 'clean-shadow.service', 'clean-shadow.timer',
                 'clean-health.service', 'clean-health.timer', 'clean-backup.service', 'clean-backup.timer'):
        if (destination / name).exists(): previous[name] = (destination / name).read_text()
        rendered[name] = (ROOT / 'ops' / name).read_text().replace('@ROOT@', str(ROOT)).replace('@PYTHON@', sys.executable)
    recovery = state / 'service-installs'; recovery.mkdir(exist_ok=True)
    (recovery / (uuid4().hex + '.json')).write_text(json.dumps(previous))
    try:
        for name, content in rendered.items(): (destination / name).write_text(content)
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', 'clean-web.service', 'clean-daily.timer', 'clean-shadow.timer', 'clean-health.timer', 'clean-backup.timer'], check=True)
        if args.start:
            from scripts.deploy_clean_product import wait_ready
            subprocess.run(['systemctl', '--user', 'restart', 'clean-web.service'], check=True)
            wait_ready('http://127.0.0.1:5000')
            subprocess.run(['systemctl', '--user', 'start', 'clean-daily.timer', 'clean-shadow.timer', 'clean-health.timer', 'clean-backup.timer'], check=True)
    except Exception:
        for name, content in previous.items(): (destination / name).write_text(content)
        for name in ('clean-daily.timer', 'clean-shadow.timer', 'clean-health.timer', 'clean-backup.timer'):
            if name not in previous: subprocess.run(['systemctl', '--user', 'disable', '--now', name], check=False)
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        if args.start and 'clean-web.service' in previous:
            subprocess.run(['systemctl', '--user', 'restart', 'clean-web.service'], check=True)
        raise
    print('Installed clean web, daily, health and backup units. Logs: journalctl --user -u clean-web -u clean-daily -u clean-health -u clean-backup')


if __name__ == '__main__':
    main()
