"""Discover persisted signals only inside the product's published artifact store."""
from pathlib import Path
import json


def published_roots(config, model):
    store = config['_artifact_store'].resolve()
    roots = []
    patterns = ('daily/*/*/run.json', 'shadow/*/run.json', 'history/*/run.json')
    for pattern in patterns:
        for filename in store.glob(pattern):
            try:
                run = json.loads(filename.read_text())
                if not isinstance(run, dict):
                    continue
                imported = run.get('schema_version') == 'tw.clean.history.v1'
                if run.get('status') != 'READY' or (not imported and not run.get('latest_pointer_written')):
                    continue
                root = Path(run['artifact_root']).resolve()
                if not root.is_relative_to(store):
                    continue
                source = run.get('source_run_id') or run.get('run_id')
                roots.append((run.get('created_at', ''), root, source))
            except (ValueError, OSError, KeyError, TypeError):
                continue
    preferred = (config.get('_shadow_root', config['artifact_root'])
                 if config['models'][model].get('role') == 'shadow' else config['artifact_root'])
    active = config.get('_active_release', {})
    ordered = [(Path(preferred), active.get('run_id'))] if preferred else []
    ordered += [(root, source) for _, root, source in sorted(roots, key=lambda row: (row[0], str(row[1])), reverse=True)]
    unique, seen = [], set()
    for root, source in ordered:
        if root not in seen:
            seen.add(root)
            unique.append((root, source))
    return unique


def locate_signal(config, roots, model, asof, source_run_id=None):
    active = config.get('_active_release', {})
    for root, source in roots:
        if source_run_id and source != source_run_id:
            continue
        # Same-date retries must never attach a previous A batch's B signal.
        if (config['models'][model].get('role') == 'shadow' and asof == active.get('asof')
                and source != active.get('run_id')):
            continue
        directory = root / 'signals' / model / asof
        if directory.exists():
            return directory, source
    return None
