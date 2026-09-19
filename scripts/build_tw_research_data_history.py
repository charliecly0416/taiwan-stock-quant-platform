#!/usr/bin/env python3
"""Build or backfill the governed daily research-data history index."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tw_research_data_history import materialize_daily_research_history


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--job-json", type=Path, required=True)
    parser.add_argument("--model-b-dir", type=Path)
    parser.add_argument("--catalog-root", type=Path)
    parser.add_argument("--canonical-history-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    job_path = args.job_json.resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    result = materialize_daily_research_history(
        repo_root=ROOT,
        asof=args.asof,
        job_id=str(job.get("job_id") or job_path.parent.name),
        job=job,
        job_dir=job_path.parent,
        catalog_root=args.catalog_root,
        canonical_history_root=args.canonical_history_root,
        model_b_dir=args.model_b_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
