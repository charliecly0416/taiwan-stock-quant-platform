"""Prepare an isolated release from Git + backup, then explicitly activate it."""
from pathlib import Path
import argparse
import io
import json
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import time

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from clean_product.artifacts import utc_now, write_json
from clean_product.maintenance import read_json, restore


def wait_ready(url, *, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            response = requests.get(url.rstrip('/') + '/api/ready', timeout=3)
            if response.status_code == 200 and response.json().get('ready'): return response.json()
        except (requests.RequestException, ValueError): pass
        time.sleep(1)
    raise RuntimeError('DEPLOYMENT_READINESS_TIMEOUT')


def prepare(snapshot, destination, ref, python):
    snapshot = Path(snapshot).resolve(); destination = Path(destination).resolve()
    if destination.exists(): raise ValueError('DEPLOYMENT_DESTINATION_MUST_BE_NEW')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', ref + '^{commit}'], text=True).strip()
    restored = restore(snapshot, destination)
    archive = subprocess.check_output(['git', '-C', str(ROOT), 'archive', commit])
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle: bundle.extractall(destination, filter='data')
    config = yaml.safe_load((destination / 'runtime-config.yaml').read_text())
    source_config = yaml.safe_load((destination / 'configs/product.yaml').read_text())
    for section in ('daily', 'datasets'):
        config[section] = source_config[section]
    config['datasets']['prices'].setdefault('params', {})['provider_uri'] = config['model_stages']['model_a_frozen']['provider_uri']
    # Backup credentials are intentionally absent; signing secrets are created by
    # the installer on a new host. Artifact-local Agent mode is the safe default.
    (destination / 'configs/product.yaml').write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    def local(value):
        filename = Path(value); return filename if filename.is_absolute() else destination / filename
    wheel = local(config.get('maintenance', {}).get('runtime_wheel', ''))
    if not wheel.is_file() or wheel.suffix != '.whl': raise ValueError('REGISTERED_QLIB_WHEEL_REQUIRED')
    log = destination / 'deployment.log'
    def run(command):
        with log.open('a') as stream:
            subprocess.run([str(item) for item in command], cwd=destination, stdout=stream, stderr=subprocess.STDOUT, check=True)
    run([python, '-m', 'venv', destination / '.venv'])
    interpreter = destination / '.venv/bin/python'
    run([interpreter, '-m', 'pip', '--isolated', 'install', '-c', 'backend/requirements-runtime.lock',
         '-r', 'backend/requirements.txt', '-r', 'backend/requirements-models.txt', wheel])
    run([interpreter, '-m', 'pip', 'check'])
    run(['corepack', 'pnpm', '--dir', 'frontend', 'install', '--frozen-lockfile'])
    run(['corepack', 'pnpm', '--dir', 'frontend', 'build'])
    asof = read_json(snapshot)['active_release']['asof']
    run([interpreter, 'scripts/run_product.py', 'daily', '--asof', asof, '--local-only', '--publish'])
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    with log.open('a') as stream:
        web = subprocess.Popen([str(interpreter), '-m', 'gunicorn', '--bind', f'127.0.0.1:{port}',
                                '--workers', '1', '--timeout', '180', 'backend.app:create_app()'],
                               cwd=destination, stdout=stream, stderr=subprocess.STDOUT)
        try:
            ready = wait_ready(url)
            ranking = requests.get(url + '/api/tw-stock/rankings?limit=150', timeout=30).json()
            chat = requests.post(url + '/api/tw-stock/agent/simple-chat', json={'question': '排名第一是谁？'}, timeout=30).json()
            if ranking.get('status') != 'READY' or len(ranking['rows']) != 150 or chat.get('status') != 'READY':
                raise ValueError('DEPLOYMENT_FUNCTIONAL_CHECK_FAILED')
        finally:
            web.terminate()
            try: web.wait(timeout=30)
            except subprocess.TimeoutExpired: web.kill(); web.wait(timeout=10)
    result = {'status': 'READY', 'git_commit': commit, 'root': str(destination), 'created_at': utc_now(),
              'asof': ready['asof'], 'restored_files': restored['files'], 'new_venv': True,
              'source_snapshot': str(snapshot), 'rankings': 150, 'agent': 'READY', 'activated': False}
    write_json(destination / 'deployment.json', result)
    return result


def activate(destination):
    destination = Path(destination).resolve(); report = read_json(destination / 'deployment.json')
    if not report or report.get('status') != 'READY': raise ValueError('PREPARED_DEPLOYMENT_REQUIRED')
    current = subprocess.check_output(['systemctl', '--user', 'show', 'clean-web.service', '-p', 'WorkingDirectory', '--value'], text=True).strip()
    previous = Path(current).resolve()
    if previous == destination: raise ValueError('DEPLOYMENT_ALREADY_ACTIVE')
    ready = wait_ready('http://127.0.0.1:5000')
    if ready['asof'] != report['asof']: raise ValueError('DEPLOYMENT_SNAPSHOT_OUTDATED')
    old_cfg = yaml.safe_load((previous / 'configs/product.yaml').read_text())
    new_cfg = yaml.safe_load((destination / 'configs/product.yaml').read_text())
    def resolve(root, value):
        filename = Path(value); return filename if filename.is_absolute() else root / filename
    store = resolve(previous, old_cfg['artifact_root'])
    import fcntl
    with (store / 'daily.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if wait_ready('http://127.0.0.1:5000')['asof'] != report['asof']:
            raise ValueError('DEPLOYMENT_SNAPSHOT_OUTDATED')
        subprocess.run(['systemctl', '--user', 'stop', 'clean-web.service'], check=True)
        try:
            old_db = resolve(previous, old_cfg['paper']['store']); new_db = resolve(destination, new_cfg['paper']['store'])
            if old_db.exists():
                with sqlite3.connect(old_db.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(new_db) as target:
                    source.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('DEPLOYMENT_LEDGER_COPY_FAILED')
            subprocess.run([str(destination / '.venv/bin/python'), str(destination / 'scripts/install_clean_services.py'), '--start'], check=True)
        except Exception:
            # The installer restores previous unit files if its readiness probe
            # fails. Ensure the previous listener is started after any copy error.
            subprocess.run(['systemctl', '--user', 'start', 'clean-web.service'], check=True)
            raise
    report.update(activated=True, previous_root=str(previous), activated_at=utc_now())
    write_json(destination / 'deployment.json', report)
    state = Path.home() / '.local/state/tw-stock-clean'
    write_json(state / 'current-deployment.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=['prepare', 'activate'])
    parser.add_argument('--snapshot'); parser.add_argument('--destination', required=True)
    parser.add_argument('--ref', default='HEAD'); parser.add_argument('--python', default=sys.executable)
    args = parser.parse_args()
    if args.task == 'prepare':
        if not args.snapshot: parser.error('--snapshot is required')
        result = prepare(args.snapshot, args.destination, args.ref, args.python)
    else: result = activate(args.destination)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == '__main__': raise SystemExit(main())
