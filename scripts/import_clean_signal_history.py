"""Import an already validated historical reconstruction into the product store.

Only adds an immutable history bundle. Never writes active/shadow/scheduler
pointers, refreshes providers, trains models, or touches paper accounts.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import shutil
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import pandas as pd
from clean_product.artifacts import sha256, utc_now, write_json
from clean_product.config import CONFIG_PATH, env_config, load_config
from clean_product.service import ProductService
from clean_product.validation import pipeline_context, pipeline_fingerprint, read_signal_artifact, verify_file


def import_history(config, source):
    source = Path(source).resolve()
    summary = json.loads((source / 'summary.json').read_text())
    verification = json.loads((source / 'verification.json').read_text())
    if (summary.get('status') != 'READY' or verification.get('status') != 'PASS'
            or summary.get('evidence_kind') != 'historical_reconstruction'):
        raise ValueError('VALIDATED_RECONSTRUCTION_REQUIRED')
    cfg = env_config(config); store = cfg['_artifact_store']
    if summary['source_run_id'] != cfg.get('_active_release', {}).get('run_id'):
        raise ValueError('IMPORT_BASELINE_RELEASE_MISMATCH')
    batch = 'reconstruction-' + uuid4().hex
    target = store / 'history' / batch
    target.mkdir(parents=True, exist_ok=False)
    run = {'schema_version': 'tw.clean.history.v1', 'status': 'BUILDING', 'run_id': batch,
           'artifact_root': str(target), 'source_run_id': summary['source_run_id'],
           'evidence_kind': 'historical_reconstruction', 'created_at': utc_now(),
           'no_apply': True, 'production_allowed': False, 'source_summary_sha256': sha256(source / 'summary.json')}
    write_json(target / 'run.json', run)
    sources = {}
    allowed = {'market_calendar.csv', 'institutional.csv', 'margin.csv', 'twii.csv', 'model_a_history.parquet'}
    for name, item in summary['sources'].items():
        filename = Path(item['path']).resolve()
        if name not in allowed or not filename.is_relative_to(source):
            raise ValueError('HISTORY_SOURCE_OUTSIDE_BUNDLE')
        verify_file(filename, item['sha256'])
        destination = target / 'source_inputs' / name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(filename, destination)
        sources[name] = {'path': str(destination), 'sha256': sha256(destination)}
    original_a = pd.read_parquet(source / 'model_a_signals.parquet')
    service = ProductService(cfg)
    for item in summary['days']:
        day = item['asof']
        baseline = service._stored_signal('model_a', day)
        if baseline is None or baseline.status != 'READY':
            raise ValueError('HISTORY_BASELINE_UNAVAILABLE')
        expected = original_a[original_a.date.eq(day)].reset_index(drop=True)
        pd.testing.assert_frame_equal(baseline.rows.reset_index(drop=True), expected, check_exact=False, atol=1e-14, rtol=1e-14)
        old_feature = Path(item['feature_artifact']['path']).resolve()
        if not old_feature.is_relative_to(source): raise ValueError('HISTORY_FEATURE_OUTSIDE_BUNDLE')
        verify_file(old_feature, item['feature_artifact']['sha256'])
        feature_dir = target / 'shadow_features' / day
        feature_dir.mkdir(parents=True)
        feature = feature_dir / old_feature.name
        shutil.copyfile(old_feature, feature)
        feature_manifest = json.loads(Path(item['feature_artifact']['manifest']).read_text())
        feature_manifest['files']['features']['path'] = str(feature)
        feature_manifest['source_inputs'] = sources
        write_json(feature_dir / 'manifest.json', feature_manifest)
        for model in ('model_a', 'model_a_plus_b'):
            work = deepcopy(cfg)
            if model == 'model_a_plus_b':
                work['model_stages']['b19r2r_frozen'].update(feature_delta=str(feature), feature_delta_sha256=sha256(feature))
            origin = baseline.artifact_dir if model == 'model_a' else source / 'artifacts/signals' / model / day
            destination = target / 'signals' / model / day
            destination.mkdir(parents=True)
            payload = json.loads((origin / 'manifest.json').read_text())
            verify_file(origin / 'signals.csv', payload['files']['signals']['sha256'])
            shutil.copyfile(origin / 'signals.csv', destination / 'signals.csv')
            payload['files']['signals']['path'] = str(destination / 'signals.csv')
            payload.update(pipeline_context=pipeline_context(work, model), pipeline_fingerprint=pipeline_fingerprint(work, model),
                           evidence_kind='historical_reconstruction', source_run_id=summary['source_run_id'],
                           origin_manifest_sha256=sha256(origin / 'manifest.json'), no_apply=True)
            write_json(destination / 'manifest.json', payload)
            read_signal_artifact(destination, work, model, day)
    if json.loads((store / 'active.json').read_text()) != cfg['_active_release']:
        raise ValueError('IMPORT_BASELINE_CHANGED_RETRY')
    run.update(status='READY', sessions=summary['sessions'], models=['model_a', 'model_a_plus_b'])
    write_json(target / 'run.json', run)
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--config', type=Path, default=CONFIG_PATH)
    parser.add_argument('--store', type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    config['artifact_root'] = str(args.store.resolve())
    print(json.dumps(import_history(config, args.source), ensure_ascii=False, indent=2))
