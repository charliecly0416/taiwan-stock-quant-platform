"""Install the three user units; requires existing Python dependencies and UI build."""
from pathlib import Path
import argparse
import os
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


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
    for name in ('clean-web.service', 'clean-daily.service', 'clean-daily.timer'):
        text = (ROOT / 'ops' / name).read_text().replace('@ROOT@', str(ROOT)).replace('@PYTHON@', sys.executable)
        (destination / name).write_text(text)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', 'clean-web.service', 'clean-daily.timer'], check=True)
    if args.start:
        subprocess.run(['systemctl', '--user', 'restart', 'clean-web.service'], check=True)
        subprocess.run(['systemctl', '--user', 'start', 'clean-daily.timer'], check=True)
    print('Installed clean-web.service and clean-daily.timer. Logs: journalctl --user -u clean-web -u clean-daily')


if __name__ == '__main__':
    main()
