#!/usr/bin/env python3
"""Additively freeze the sole A+B score adapter before evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
BASE = OUT / "B19R2R_COMPARATIVE_FREEZE.json"
AMENDMENT = OUT / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01.json"
REPORT = OUT / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01_CN.md"
VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_comparative_adapter_amendment.py"
BASE_SHA256 = "7283f87f640a4cb8576f1038e823b6e9fd2c07e869239bd7fe61d65ba74e8fad"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def write_once(path: Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        data = text.encode("utf-8")
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if not args.freeze:
        raise SystemExit("Select --freeze")
    if sha256(BASE) != BASE_SHA256:
        raise RuntimeError("comparative base freeze hash mismatch")
    payload = {
        "schema_version": "modelb.b19r2r.comparative_freeze_amendment.v1",
        "status": "ADDITIVE_CLOSED_BEFORE_ANY_COMPARATIVE_PREDICTION_OR_EVALUATION",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "base_freeze": {"path": rel(BASE), "sha256": BASE_SHA256},
        "implementation_bindings": {
            "builder": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__)), "bytes": Path(__file__).stat().st_size},
            "validator": {"path": rel(VALIDATOR), "sha256": sha256(VALIDATOR), "bytes": VALIDATOR.stat().st_size},
        },
        "sole_treatment_adapter": {
            "name": "outer_oof_model_b_raw_prediction_v1",
            "formula": "buy_score = 1.0 * outer_fold_oof_model_b_raw_prediction + 0.0 * model_a_raw_score",
            "model_b_weight": 1.0,
            "model_a_weight": 0.0,
            "normalization": "NONE",
            "calibration": "NONE",
            "post_result_blend_search_allowed": False,
            "alternative_adapter_candidates": 0,
            "tie_rule": "buy_score descending, instrument ascending",
        },
        "control_adapter": {
            "name": "frozen_model_a_raw_score_v1",
            "formula": "buy_score = model_a_raw_score",
        },
        "boundary_invariants": {
            "same_exact50_universe": True,
            "candidate_rank_source": "frozen Model A",
            "full_qlib_rank_source": "frozen Model A",
            "model_b_may_change_universe": False,
            "model_b_may_change_exit_boundary": False,
        },
        "safety_at_close": {
            "fit_performed": False,
            "prediction_generated": False,
            "comparison_executed": False,
            "replay_executed": False,
            "sealed_accessed": False,
            "baseline_or_production_write_performed": False,
        },
    }
    write_once(AMENDMENT, json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
    write_once(REPORT, """# B19R2R 比较协议 Adapter Amendment 01

本增补在生成任何比较预测或指标前，将唯一 treatment adapter 固定为：

`A+B buy_score = 1.0 × outer-fold OOF Model B raw prediction + 0.0 × Model A raw score`。

不允许事后搜索 blend、归一化、校准或替代 adapter。A-only 仍以冻结 Model A raw score 为 control；candidate rank、full qlib rank、exact50 universe 和退出边界始终来自 Model A。

本增补不授权 fit、predict、比较、回放、sealed access 或 baseline/production 写入。
""")
    print(json.dumps({"status": payload["status"], "amendment": rel(AMENDMENT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
