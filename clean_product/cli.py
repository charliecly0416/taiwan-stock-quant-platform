from __future__ import annotations

import argparse
import json

from .config import CONFIG_PATH, load_config
from .data import DataCatalog, DataError
from .orchestrator import run_daily
from .replay import replay


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean Taiwan stock research product")
    parser.add_argument("task", choices=["shadow", "daily", "replay", "candidate", "paper-token", "paper-import", "paper-export"]); parser.add_argument("--asof"); parser.add_argument("--model", default="model_a")
    parser.add_argument("--start"); parser.add_argument("--end"); parser.add_argument("--dry-run", action="store_true")
    parser.add_argument('--publish', action='store_true', help='Atomically activate a complete daily release')
    parser.add_argument('--local-only', action='store_true', help='Use existing local data without fetching')
    parser.add_argument('--trigger-reason', choices=['manual', 'scheduled'], default='manual')
    parser.add_argument('--out'); parser.add_argument('--owner'); parser.add_argument('--snapshot'); parser.add_argument('--checksum')
    args = parser.parse_args()
    if args.task == 'paper-export':
        from pathlib import Path
        from .paper import PaperStore, checksum
        from .config import path
        if not args.owner or not args.out: parser.error('--owner --out are required')
        cfg = load_config()
        if not isinstance(cfg.get('paper'), dict) or not cfg['paper'].get('store'):
            parser.error('paper export requires an explicitly configured paper.store')
        snapshot = PaperStore(path(cfg['paper']['store'])).export_snapshot(args.owner)
        with Path(args.out).open('x', encoding='utf-8') as stream:
            json.dump(snapshot, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'EXPORTED', 'accounts': len(snapshot['accounts']), 'checksum': checksum(snapshot)})); return 0
    if args.task == 'paper-token':
        from .paper import issue_token, auth_secret
        if not args.owner: parser.error('--owner is required')
        print(issue_token(auth_secret(), args.owner)); return 0
    if args.task == 'paper-import':
        from pathlib import Path
        from .paper import PaperStore
        if not all((args.owner, args.snapshot, args.checksum, args.out)): parser.error('--owner --snapshot --checksum --out are required')
        output = Path(args.out).resolve()
        if output.exists(): parser.error('import output must be a new isolated database')
        payload = PaperStore(output).import_snapshot(args.owner, json.loads(Path(args.snapshot).read_text()), args.checksum)
        print(json.dumps(payload, ensure_ascii=False)); return 0
    if args.task == 'candidate':
        from pathlib import Path
        from copy import deepcopy
        from .artifacts import write_json
        from .config import env_config
        import tempfile
        import yaml
        if not args.asof or not args.out: parser.error('candidate requires --asof --out')
        output = Path(args.out).resolve()
        if output.exists(): parser.error('candidate output must not already exist')
        config = deepcopy(load_config(CONFIG_PATH)); config['artifact_root'] = str(output)
        config.setdefault('agent', {})['build_daily_prompt'] = True
        if env_config(config)['artifact_root'].resolve() != output: parser.error('runtime artifact override conflicts with isolated output')
        with tempfile.TemporaryDirectory(prefix='clean-candidate-config-') as directory:
            filename = Path(directory) / 'product.yaml'; filename.write_text(yaml.safe_dump(config))
            payload = run_daily(args.asof, config_path=filename, local_only=True)
        payload.update(scope='isolated_local_candidate', latest_pointer_written=False)
        write_json(output / 'candidate_result.json', payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0 if payload['status'] == 'READY' else 1
    if args.task == "shadow":
        if args.dry_run or args.asof or args.publish:
            parser.error('shadow binds the active baseline; use --local-only for offline execution')
        from .shadow import run_shadow
        payload = run_shadow(trigger_reason=args.trigger_reason, local_only=args.local_only)
    elif args.task == "daily":
        payload = run_daily(args.asof, dry_run=args.dry_run, local_only=args.local_only,
                            publish=args.publish, trigger_reason=args.trigger_reason)
    else:
        if not args.start or not args.end: parser.error("replay requires --start and --end")
        config = load_config(CONFIG_PATH); catalog = DataCatalog(config)
        try:
            prices = catalog.query("prices", args.start, args.end, allow_fixture=True) if args.dry_run else catalog.query_local_source("prices", args.start, args.end)
            payload = replay(config, {"prices": prices}, args.model, args.start, args.end, fixture=args.dry_run)
        except (DataError, ValueError) as exc:
            payload = {"status": "BLOCKED", "model": args.model, "start": args.start, "end": args.end, "reason": str(exc), "readonly": True, "simulation_only": True, "fixture": args.dry_run}
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=str)); return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if payload.get("status") == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
