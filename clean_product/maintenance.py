"""Small, local-only operations: health, content-addressed backup and recovery."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from uuid import uuid4
import fcntl
import json
import os
import re
import shutil
import sqlite3
import tempfile

import requests
import yaml

from .artifacts import sha256, utc_now, write_json
from .config import ROOT, env_config, path

ASSET_FIELDS = ('model_path', 'training_manifest', 'prediction_archive', 'raw_prediction_archive',
                'inference_config', 'selection_prices', 'selection_universe', 'provider_uri',
                'feature_schema', 'historical_features', 'feature_delta')
PRIVATE = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_-]{24,}')


def read_json(filename):
    return json.loads(Path(filename).read_text()) if Path(filename).is_file() else None


def state_root(config):
    return Path(config.get('maintenance', {}).get('backup_root', '~/.local/state/tw-stock-clean/backups')).expanduser().resolve()


def health(config, *, base_url='http://127.0.0.1:5000', now=None, write=True, probe=None):
    config = env_config(config); store = config['_artifact_store']; alerts = []
    now = now or datetime.now(timezone.utc)
    def alert(code, severity='CRITICAL'):
        alerts.append({'code': code, 'severity': severity})
    try:
        response = (probe or requests.get)(base_url.rstrip('/') + '/api/ready', timeout=10)
        ready = response.status_code == 200 and response.json().get('ready') is True
    except (requests.RequestException, ValueError):
        ready = False
    if not ready: alert('WEB_NOT_READY')
    def record(name):
        try:
            value = read_json(store / name)
            if value is not None and not isinstance(value, dict): raise ValueError('INVALID_STATUS_RECORD')
            return value or {}
        except (ValueError, OSError):
            alert('INVALID_' + name.replace('/', '_').replace('.', '_').upper()); return {}
    scheduler = record('scheduler_status.json'); latest = record('daily_status.json') or scheduler
    backup = record('ops/backup.json')
    shadow = record('shadow_scheduler_status.json')
    if config.get('daily', {}).get('shadow_separate'):
        if shadow.get('status') == 'BLOCKED':
            alert('SCHEDULED_SHADOW_GATED' if shadow.get('execution_status') == 'COMPLETED' else 'SCHEDULED_SHADOW_FAILED', 'WARNING')
    def age(item):
        try: return (now - datetime.fromisoformat(item['created_at'])).total_seconds()
        except (KeyError, TypeError, ValueError): return float('inf')
    if latest.get('status') == 'BLOCKED': alert('LATEST_DAILY_FAILED')
    if scheduler.get('status') == 'BLOCKED': alert('SCHEDULED_DAILY_FAILED')
    if latest.get('status') == 'RUNNING' and age(latest) > 50 * 60: alert('DAILY_TIMEOUT')
    # A weekday timer must report even on a holiday; its market probe decides
    # whether a new session exists. Never equate calendar days with market days.
    local = now.astimezone(ZoneInfo('Asia/Taipei'))
    deadline = local.replace(hour=21, minute=30, second=0, microsecond=0)
    if local < deadline: deadline -= timedelta(days=1)
    while deadline.weekday() >= 5: deadline -= timedelta(days=1)
    try: scheduled_day = datetime.fromisoformat(scheduler['created_at']).astimezone(ZoneInfo('Asia/Taipei')).date()
    except (KeyError, TypeError, ValueError): scheduled_day = None
    if scheduled_day is None or scheduled_day < deadline.date(): alert('SCHEDULED_ATTEMPT_MISSING')
    if config.get('daily', {}).get('shadow_separate'):
        try: shadow_day = datetime.fromisoformat(shadow['created_at']).astimezone(ZoneInfo('Asia/Taipei')).date()
        except (KeyError, TypeError, ValueError): shadow_day = None
        if shadow_day is None or shadow_day < deadline.date(): alert('SHADOW_SCHEDULE_MISSING', 'WARNING')
        if shadow.get('status') == 'RUNNING' and age(shadow) > 45 * 60: alert('SHADOW_TIMEOUT', 'WARNING')
    expected = scheduler.get('asof'); active = config.get('_active_release', {}).get('asof')
    if expected and active and expected > active: alert('PUBLISHED_DATA_BEHIND_CHECKED_SESSION')
    free = shutil.disk_usage(store if store.exists() else ROOT).free
    if free < int(config.get('maintenance', {}).get('minimum_free_gb', 10)) * 1024**3: alert('DISK_SPACE_LOW')
    if backup.get('status') != 'READY' or age(backup) > 36 * 3600: alert('BACKUP_MISSING_OR_OLD', 'WARNING')
    status = 'CRITICAL' if any(a['severity'] == 'CRITICAL' for a in alerts) else 'WARNING' if alerts else 'OK'
    result = {'status': status, 'created_at': now.isoformat(), 'ready': ready, 'alerts': alerts,
              'active_asof': active, 'checked_market_asof': expected, 'scheduler': scheduler,
              'backup': backup, 'free_bytes': free, 'notification_mode': 'local_status_and_journal'}
    if write: write_json(store / 'ops/health.json', result)
    return result


def inventory(config, *, project_root=ROOT):
    """Only registry-selected assets. Never walk home, .env, or credentials."""
    root = Path(project_root).resolve(); cfg = env_config(config)
    targets = {root / 'configs', cfg['artifact_root'], cfg['data_root']}
    store = cfg['_artifact_store']
    targets.update(store / name for name in ('active.json', 'daily', 'scheduler_status.json', 'daily_status.json',
                                               'shadow', 'shadow_data', 'shadow_active.json', 'shadow_status.json', 'shadow_scheduler_status.json'))
    for stage in cfg.get('model_stages', {}).values():
        targets.update(path(stage[k]) for k in ASSET_FIELDS if stage.get(k))
    if cfg.get('universe_file'): targets.add(path(cfg['universe_file']))
    if cfg.get('maintenance', {}).get('runtime_wheel'): targets.add(path(cfg['maintenance']['runtime_wheel']))
    files = {}
    for target in targets:
        for item in (target.rglob('*') if target.is_dir() else (target,)):
            if not item.is_file(): continue
            resolved = item.resolve()
            if not resolved.is_relative_to(root) or item.is_symlink(): raise ValueError('BACKUP_ASSET_OUTSIDE_PROJECT')
            relative = resolved.relative_to(root)
            if any(part.startswith('.env') or part in ('paper.secret', '.git') for part in relative.parts):
                raise ValueError('BACKUP_SECRET_PATH_FORBIDDEN')
            files[str(relative)] = resolved
    return files


def _copy_object(source, pool):
    # Private artifact copies are immutable, keyed once by content and shared
    # across snapshots; unchanged model/provider bytes are not duplicated daily.
    digest = sha256(source); target = pool / digest[:2] / digest
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with Path(source).open('rb') as stream:
            tail = b''
            while chunk := stream.read(1024 * 1024):
                if PRIVATE.search(tail + chunk): raise ValueError('BACKUP_CREDENTIAL_PATTERN_DETECTED')
                tail = chunk[-128:]
        temporary = target.with_name(digest + '.' + uuid4().hex + '.tmp')
        shutil.copyfile(source, temporary); temporary.chmod(0o600)
        if sha256(temporary) != digest: raise ValueError('BACKUP_SOURCE_CHANGED_DURING_COPY')
        temporary.replace(target)
    return digest


def backup(config, *, project_root=ROOT):
    cfg = env_config(config); root = Path(project_root).resolve(); destination = state_root(cfg)
    if destination.is_relative_to(root): raise ValueError('BACKUP_MUST_BE_OUTSIDE_REPOSITORY')
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    with (destination / 'backup.lock').open('a') as lock, (cfg['_artifact_store'] / 'daily.lock').open('a') as daily_lock, (cfg['_artifact_store'] / 'shadow.lock').open('a') as shadow_lock:
        fcntl.flock(shadow_lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(daily_lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        if read_json(cfg['_artifact_store'] / 'active.json') != cfg.get('_active_release'):
            raise ValueError('BACKUP_RELEASE_CHANGED_RETRY')
        files = inventory(cfg, project_root=root); entries = []
        for name, filename in sorted(files.items()):
            entries.append({'path': name, 'sha256': _copy_object(filename, destination / 'objects'), 'bytes': filename.stat().st_size})
        database = cfg.get('paper', {}).get('store')
        if database and path(database).exists():
            dbfile = path(database).resolve()
            if not dbfile.is_relative_to(root): raise ValueError('BACKUP_DATABASE_OUTSIDE_PROJECT')
            with tempfile.TemporaryDirectory(prefix='ledger-', dir=destination) as temp:
                copied = Path(temp) / 'paper.sqlite3'
                with sqlite3.connect(dbfile.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(copied) as dst:
                    src.backup(dst)
                    if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('BACKUP_DATABASE_INVALID')
                entries.append({'path': str(dbfile.relative_to(root)), 'sha256': _copy_object(copied, destination / 'objects'), 'bytes': copied.stat().st_size})
        serial = json.loads(json.dumps(cfg, default=str))
        serial = {k:v for k,v in serial.items() if not k.startswith('_')}
        serial['artifact_root'] = str(cfg['_artifact_store'])
        serial['agent'] = {**serial.get('agent', {}), 'remote_enabled': False}
        manifest = {'schema_version': 'tw.clean.backup.v1', 'created_at': utc_now(),
                    'project_root': str(root), 'config': serial, 'files': entries,
                    'credentials_included': False, 'active_release': cfg.get('_active_release')}
        snapshot = destination / 'snapshots' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]) / 'manifest.json'
        write_json(snapshot, manifest); snapshot.chmod(0o600)
        result = {'status': 'READY', 'created_at': utc_now(), 'manifest': str(snapshot),
                  'files': len(entries), 'logical_bytes': sum(item['bytes'] for item in entries)}
        write_json(cfg['_artifact_store'] / 'ops/backup.json', result)
        return result


def restore(manifest_file, destination, *, verify_only=False):
    manifest_file = Path(manifest_file).resolve(); manifest = read_json(manifest_file)
    if manifest.get('schema_version') != 'tw.clean.backup.v1': raise ValueError('BACKUP_SCHEMA_INVALID')
    pool = manifest_file.parent.parent.parent / 'objects'; target = Path(destination).resolve()
    if not verify_only and target.exists(): raise ValueError('RESTORE_DESTINATION_MUST_BE_NEW')
    seen = set()
    for entry in manifest['files']:
        relative = Path(entry['path']); digest = entry['sha256']
        if relative.is_absolute() or '..' in relative.parts or str(relative) in seen or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('BACKUP_PATH_INVALID')
        seen.add(str(relative)); source = pool / digest[:2] / digest
        if not source.is_file() or sha256(source) != digest: raise ValueError('BACKUP_OBJECT_INVALID')
    if verify_only: return {'status': 'PASS', 'files': len(seen), 'verified_only': True}
    target.mkdir(parents=True, mode=0o700)
    for entry in manifest['files']:
        output = target / entry['path']; output.parent.mkdir(parents=True, exist_ok=True)
        digest = entry['sha256']; shutil.copyfile(pool / digest[:2] / digest, output); output.chmod(0o600)
    # Preserve original manifests byte-for-byte. A relocated install must make
    # its own local-only release, since historical lineage embeds absolute paths.
    old = manifest['project_root']
    def rebase(value):
        if isinstance(value, dict): return {k:rebase(v) for k,v in value.items()}
        if isinstance(value, list): return [rebase(v) for v in value]
        if isinstance(value, str) and (value == old or value.startswith(old + '/')): return str(target) + value[len(old):]
        return value
    config = rebase(manifest['config'])
    store = Path(config['artifact_root']); store = store if store.is_absolute() else target / store
    active = store / 'active.json'
    if active.exists(): active.rename(store / 'restored-active.json')
    (target / 'runtime-config.yaml').write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    database = config.get('paper', {}).get('store')
    if database:
        filename = Path(database); filename = filename if filename.is_absolute() else target / filename
        if filename.exists():
            with sqlite3.connect(filename.as_uri() + '?mode=ro', uri=True) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('RESTORED_DATABASE_INVALID')
    report = {'status': 'PASS', 'files': len(seen), 'destination': str(target), 'requires_local_republish': True, 'credentials_restored': False}
    write_json(manifest_file.parent / 'restore-verification.json', {**report, 'created_at': utc_now()})
    return report


def retention(config):
    cfg = env_config(config); keep_days = int(cfg.get('maintenance', {}).get('keep_days', 30))
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days); snapshots = []
    for filename in sorted(state_root(cfg).glob('snapshots/*/manifest.json'), reverse=True):
        item = read_json(filename)
        snapshots.append({'manifest': str(filename), 'created_at': item['created_at'],
                          'eligible_for_archive': len(snapshots) >= 7 and datetime.fromisoformat(item['created_at']) < cutoff,
                          'restore_verified': (filename.parent / 'restore-verification.json').exists()})
    # Deletion is deliberately separate from backup: manifests share objects;
    # operators must retain restore-tested external copies before any removal.
    return {'status': 'READY', 'keep_days': keep_days, 'minimum_snapshots': 7, 'snapshots': snapshots,
            'automatic_deletion': False, 'protected_active_release': cfg.get('_active_release')}


def rollback_release(config, release_id):
    cfg = env_config(config); store = cfg['_artifact_store']; directory = (store / 'releases' / release_id).resolve()
    if not directory.is_relative_to((store / 'releases').resolve()) or directory.name != release_id:
        raise ValueError('ROLLBACK_RELEASE_ID_INVALID')
    release = read_json(directory / 'release.json')
    if not release or Path(release['artifact_root']).resolve() != directory: raise ValueError('ROLLBACK_RELEASE_INVALID')
    candidate = {**cfg, 'artifact_root': directory, 'data_root': directory / 'data', '_active_release': release}
    candidate['agent'] = {**cfg.get('agent', {}), 'prompt_root': str(directory / 'agent_daily_prompt')}
    stage = {**cfg['model_stages']['model_a_frozen'], 'provider_uri': release['provider'],
             'selection_prices': release['selection_prices'], 'selection_universe': release['universe_file']}
    candidate['model_stages'] = {**cfg['model_stages'], 'model_a_frozen': stage}
    if release.get('shadow_feature_delta'):
        candidate['model_stages']['b19r2r_frozen'] = {
            **candidate['model_stages'].get('b19r2r_frozen', {}),
            'feature_delta': release['shadow_feature_delta'],
            'feature_delta_sha256': release.get('shadow_feature_delta_sha256'),
        }
    candidate['universe_file'] = release.get('config_universe_file', release['universe_file'])
    candidate['datasets'] = {**cfg.get('datasets', {}), 'prices': {**cfg.get('datasets', {}).get('prices', {}),
        'params': {**cfg.get('datasets', {}).get('prices', {}).get('params', {}), 'provider_uri': release['provider']}}}
    from .service import ProductService
    with (store / 'daily.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not ProductService(candidate).readiness()['ready']: raise ValueError('ROLLBACK_RELEASE_NOT_READY')
        previous = read_json(store / 'active.json')
        write_json(store / 'ops/rollbacks' / (uuid4().hex + '.json'), {'previous': previous, 'target': release, 'created_at': utc_now()})
        write_json(store / 'active.json', release)
    return {'status': 'READY', 'run_id': release_id, 'previous_run_id': (previous or {}).get('run_id')}
