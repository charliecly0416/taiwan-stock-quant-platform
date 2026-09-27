from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import CONFIG_PATH, load_config
from .data import DataCatalog
from .orchestrator import run_daily
from .replay import replay


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean Taiwan stock research product")
    parser.add_argument("task", choices=["daily", "replay"])
    parser.add_argument("--asof")
    parser.add_argument("--model", default="model_a")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.task == "daily":
        payload = run_daily(args.asof, dry_run=args.dry_run)
    else:
        config = load_config(CONFIG_PATH)
        data = DataCatalog(config).query("prices", args.start, args.end, allow_fixture=True)
        payload = replay(config, data, args.model, args.start, args.end)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
