"""Local operations CLI. No broker, external notifications or secret export."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from clean_product.config import load_config, env_config
from clean_product.artifacts import write_json, utc_now
from clean_product.maintenance import backup, health, restore, retention, rollback_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=['health', 'backup', 'restore', 'verify-backup', 'retention', 'rollback-release'])
    parser.add_argument('--manifest'); parser.add_argument('--out'); parser.add_argument('--release')
    parser.add_argument('--url', default='http://127.0.0.1:5000')
    args = parser.parse_args(); cfg = load_config()
    try:
        if args.task == 'health': result = health(cfg, base_url=args.url)
        elif args.task == 'backup': result = backup(cfg)
        elif args.task == 'retention': result = retention(cfg)
        elif args.task == 'rollback-release':
            if not args.release: parser.error('--release is required')
            result = rollback_release(cfg, args.release)
        else:
            if not args.manifest or (args.task == 'restore' and not args.out): parser.error('--manifest and --out are required for restore')
            result = restore(args.manifest, args.out or '.', verify_only=args.task == 'verify-backup')
    except Exception as exc:
        if args.task == 'backup':
            write_json(env_config(cfg)['_artifact_store'] / 'ops/backup.json',
                       {'status': 'BLOCKED', 'created_at': utc_now(), 'reason': type(exc).__name__})
        print(json.dumps({'status': 'BLOCKED', 'reason': type(exc).__name__})); return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['status'] in ('BLOCKED', 'CRITICAL') else 0


if __name__ == '__main__': raise SystemExit(main())
