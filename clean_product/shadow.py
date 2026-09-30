"""Independent, retryable research lane bound to an immutable Model A release."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import fcntl
import json
import shutil

import pandas as pd

from .artifacts import sha256, utc_now, write_json
from .config import CONFIG_PATH, datasets, env_config, load_config, path, trading_days
from .data import DataCatalog, DataError
from .models import ModelBlocked, ModelRunner
from .orchestrator import _prepare_shadow_features
from .service import ProductService
from .validation import validate_signal_rows, verify_file


def _history(config, current, cache):
    """Continue the frozen candidate history with persisted baseline inference."""
    stage = config['model_stages']['b19r2r_frozen']
    frozen = pd.read_parquet(path(stage['historical_features']), columns=['date', 'instrument'])
    end = frozen.date.astype(str).str[:10].max()
    filename = cache / 'model_a_history.parquet'
    history = pd.read_parquet(filename) if filename.exists() else pd.DataFrame(columns=['date', 'instrument', 'score', 'rank'])
    asof = str(current.date.iloc[0])
    days = [day for day in config['_shadow_calendar'] if end < day < asof]
    # Preserve rankings already published by A. Recompute only dates for which
    # no immutable daily signal exists (the one-time historical gap).
    published = []
    for manifest_path in sorted(config['_artifact_store'].glob('releases/*/signals/model_a/*/manifest.json')):
        metadata = json.loads(manifest_path.read_text())
        day = metadata.get('asof')
        if day not in days or metadata.get('status') != 'READY':
            continue
        if metadata.get('canonical_id') != config['models']['model_a']['canonical_id']:
            continue
        filename = manifest_path.parent / 'signals.csv'
        verify_file(filename, metadata['files']['signals']['sha256'])
        rows = pd.read_csv(filename)
        validate_signal_rows(rows, day)
        published.append(rows[['date', 'instrument', 'score', 'rank']])
    if published:
        history = pd.concat([history, *published], ignore_index=True).drop_duplicates(['date', 'instrument'], keep='last')
    missing = sorted(set(days) - set(history.date))
    if missing:
        data = {}
        ModelRunner(config).precompute(missing, data=data)
        frames = []
        for day in missing:
            rows = data['__model_a_signals'].get(day)
            if rows is None or len(rows) != 150:
                raise ModelBlocked('B19R2R_MODELA_HISTORY_INCOMPLETE', day)
            frames.append(rows[['date', 'instrument', 'score', 'rank']])
        history = pd.concat([history, *frames], ignore_index=True)
    history = pd.concat([history, current[['date', 'instrument', 'score', 'rank']]], ignore_index=True)
    history = history.drop_duplicates(['date', 'instrument'], keep='last').sort_values(['date', 'rank'])
    temporary = filename.with_suffix('.tmp.parquet')
    history.to_parquet(temporary, index=False); temporary.replace(filename)
    config['_shadow_history'] = str(filename)
    return set(frozen.instrument)


def _execute(config, result, local_only):
    service = ProductService(config)
    if not service.readiness()['ready']:
        raise ModelBlocked('SHADOW_BASELINE_NOT_READY')
    asof = result['asof']
    baseline = service._stored_signal('model_a', asof)
    if baseline is None or baseline.status != 'READY' or len(baseline.rows) != 150:
        raise ModelBlocked('SHADOW_BASELINE_SIGNAL_MISSING')
    model_a = baseline.rows.sort_values('rank').copy()
    model_a.attrs['full_qlib_ranks'] = baseline.full_ranks
    cache = config['_artifact_store'] / 'shadow_data'
    cache.mkdir(parents=True, exist_ok=True)
    stage = config['model_stages']['b19r2r_frozen']
    stage.pop('feature_delta', None); stage.pop('feature_delta_sha256', None)
    config.pop('_shadow_root', None)
    config['artifact_root'] = Path(result['artifact_root'])
    config['data_root'] = cache
    # Acquisition uses only the exact Top50 minus the frozen exclusion, never
    # the provider's 1,964-symbol screening universe.
    exact = model_a.head(50)
    symbols = exact[~exact.instrument.isin(stage.get('exclude', []))].instrument.tolist()
    fetch_config = {**config, 'universe': symbols, 'universe_file': None}
    catalog = DataCatalog(fetch_config)
    calendar_file = cache / 'market_calendar.csv'
    if not local_only:
        from .provider_refresh import _fetch
        calendar_frame = _fetch('TWII', '2021-01-04', asof,
                                str(config.get('provider_refresh', {}).get('proxy', '')))
        if calendar_frame.empty or str(calendar_frame.date.max()) != asof:
            raise ModelBlocked('SHADOW_MARKET_CALENDAR_UNAVAILABLE')
        calendar_frame[['date']].to_csv(calendar_file, index=False)
    calendar = pd.read_csv(calendar_file).date.astype(str).tolist()
    if not calendar or calendar[-1] != asof:
        raise ModelBlocked('SHADOW_MARKET_CALENDAR_STALE')
    config['_shadow_calendar'] = calendar
    result['market_calendar'] = {'path': str(calendar_file), 'sha256': sha256(calendar_file),
                                 'source': 'Yahoo ^TWII', 'asof': asof}
    data = {'__calendar': calendar}
    for name in ('institutional', 'margin', 'twii'):
        if not local_only:
            result['datasets'].append(catalog.fetch(datasets(config)[name], asof))
        data[name] = catalog.query(name, end=asof)
    breadth_symbols = _history(config, model_a, cache)
    start = '2021-01-04'  # Frozen transform's canonical price-calendar start (MACD warmup).
    data['prices'] = catalog.query_local_source('prices', start, asof,
                                               symbols=sorted(breadth_symbols | set(model_a.instrument)))
    sources = {}
    source_root = config['artifact_root'] / 'source_inputs'; source_root.mkdir(parents=True, exist_ok=True)
    for filename in ('market_calendar.csv', 'institutional.csv', 'margin.csv', 'twii.csv', 'model_a_history.parquet'):
        target = source_root / filename
        shutil.copyfile(cache / filename, target)
        sources[filename] = {'path': str(target), 'sha256': sha256(target)}
    config['_shadow_history'] = sources['model_a_history.parquet']['path']
    config['_shadow_sources'] = sources
    result['source_inputs'] = sources
    result['market_calendar']['path'] = sources['market_calendar.csv']['path']
    artifact = _prepare_shadow_features(config=config, data=data, asof=asof,
                                        run_id=result['run_id'], model_a=model_a)
    result['feature_artifact'] = artifact
    signal = ModelRunner(config).run('model_a_plus_b', asof, data={'__model_a_signals': {asof: model_a}})
    if signal.status != 'READY':
        raise ModelBlocked('SHADOW_SIGNAL_BLOCKED', signal.reason or '')
    if set(signal.rows.instrument) != set(symbols):
        raise ModelBlocked('SHADOW_EXACT50_MISMATCH')
    # Validate the persisted artifact through the same consumer as the API.
    config['_shadow_root'] = config['artifact_root']
    stored = ProductService(config)._stored_signal('model_a_plus_b', asof)
    if stored is None or stored.status != 'READY':
        raise ModelBlocked('SHADOW_STORED_SIGNAL_INVALID')
    result.update(status='READY', signal_rows=len(signal.rows), top1=str(signal.rows.iloc[0].instrument))


def run_shadow(*, config_path=CONFIG_PATH, trigger_reason='manual', local_only=False):
    if trigger_reason not in ('manual', 'scheduled'):
        raise ValueError('INVALID_TRIGGER_REASON')
    config = env_config(load_config(config_path)); store = config['_artifact_store']
    store.mkdir(parents=True, exist_ok=True)
    with (store / 'shadow.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'BLOCKED', 'reason': 'SHADOW_ALREADY_RUNNING', 'mainline_blocking': False}
        active = config.get('_active_release', {})
        run_id = uuid4().hex
        root = store / 'shadow' / run_id
        result = {'schema_version': 'tw.clean.shadow.v1', 'status': 'RUNNING', 'asof': active.get('asof'),
                  'source_run_id': active.get('run_id'), 'run_id': run_id, 'created_at': utc_now(),
                  'started_at': utc_now(), 'trigger_reason': trigger_reason, 'local_only': local_only,
                  'artifact_root': str(root), 'datasets': [], 'mainline_blocking': False,
                  'production_allowed': False, 'no_apply': True, 'latest_pointer_written': False}
        def record():
            write_json(root / 'run.json', result)
            write_json(store / 'shadow_status.json', result)
            if trigger_reason == 'scheduled':
                write_json(store / 'shadow_scheduler_status.json', result)
        record()
        try:
            if not active:
                raise ModelBlocked('SHADOW_ACTIVE_BASELINE_REQUIRED')
            _execute(deepcopy(config), result, local_only)
            # A can publish while shadow is fetching. Never attach old B to new A.
            with (store / 'daily.lock').open('a') as daily_lock:
                fcntl.flock(daily_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if json.loads((store / 'active.json').read_text()) != active:
                    raise ModelBlocked('SHADOW_BASELINE_CHANGED_RETRY')
                write_json(store / 'shadow_active.json', result)
                result['latest_pointer_written'] = True
        except (ModelBlocked, DataError) as exc:
            result.update(status='BLOCKED', reason=str(exc))
        except Exception as exc:
            # Provider exceptions may contain credential-bearing request URLs.
            result.update(status='BLOCKED', reason=f'SHADOW_EXECUTION_FAILED: {type(exc).__name__}')
        result['created_at'] = utc_now(); record()
        return result
