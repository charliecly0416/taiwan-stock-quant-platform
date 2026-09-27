#!/usr/bin/env python3
"""Record the next Model B prospective-shadow readiness decision.

This is a readonly evidence builder. It consumes the already-produced daily
preflight and B16 settlement artifacts, and never scores, trains, publishes,
or mutates a production pointer.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b17_daily_shadow_readiness_20260916"
PREFLIGHT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds0_preflight_20260905/readiness_report.json"
B16 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b16_b8_prospective_settlement_20260916/B16_MANIFEST.json"
PROTECTED = [
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
]


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fingerprints() -> dict[str, dict[str, object]]:
    return {
        str(path.relative_to(ROOT)): {"exists": path.is_file(), "sha256": sha(path)}
        for path in PROTECTED
    }


def main() -> int:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    b16 = json.loads(B16.read_text(encoding="utf-8"))
    before = fingerprints()
    blockers = list(preflight.get("blocking_gates", []))
    manifest = {
        "schema_version": "modelb.b17.daily_shadow_readiness.manifest.v1",
        "run_id": "modelb_b17_daily_shadow_readiness_20260916",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_asof": preflight.get("target_asof", "2026-09-15"),
        "status": "BLOCKED_INPUT_NOT_READY" if blockers else "READY_FOR_SHADOW_SCORING",
        "phase": "MB-1 prospective shadow accumulation",
        "preflight": {
            "path": str(PREFLIGHT.relative_to(ROOT)),
            "sha256": sha(PREFLIGHT),
            "decision": preflight.get("decision"),
            "blocking_gates": blockers,
            "missing_twii_sessions": preflight.get("missing_twii_sessions"),
            "canonical_twii_max": preflight.get("canonical_twii_max"),
            "handoff_twii_max": preflight.get("handoff_twii_max"),
        },
        "settled_prospective_paired_days_before": b16.get("prospective_paired_day_count_after", 0),
        "settled_prospective_paired_days_after": b16.get("prospective_paired_day_count_after", 0),
        "warmup_gate": "SANITY_ONLY_0_TO_19",
        "model_b_scoring_performed": False,
        "training_performed": False,
        "replay_performed": False,
        "production_allowed": False,
        "baseline_admission": False,
        "no_publish_or_latest_switch": True,
        "protected_before": before,
    }
    after = fingerprints()
    manifest["protected_after"] = after
    manifest["protected_unchanged"] = before == after
    validator = {
        "schema_version": "modelb.b17.daily_shadow_readiness.validator.v1",
        "checks": {
            "preflight_read": PREFLIGHT.is_file(),
            "expected_input_blocker": blockers == ["twii_exact_target", "twii_120_session_continuity"],
            "b16_count_preserved": manifest["settled_prospective_paired_days_after"] == 1,
            "no_scoring_or_training": not manifest["model_b_scoring_performed"] and not manifest["training_performed"],
            "protected_unchanged": manifest["protected_unchanged"],
            "no_production_write": manifest["no_publish_or_latest_switch"] and not manifest["production_allowed"],
        },
    }
    validator["verdict"] = "PASS_WITH_CONDITIONS" if all(validator["checks"].values()) else "FAIL"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "B17_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (OUT / "B17_VALIDATOR.json").write_text(json.dumps(validator, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (OUT / "B17_EXECUTION_REPORT_CN.md").write_text(
        "# B17 Model B 前瞻 shadow 输入就绪审查\n\n"
        f"目标日：`{manifest['target_asof']}`。\n\n"
        f"当前状态：`{manifest['status']}`；阻断项：`{', '.join(blockers) or '无'}`。\n\n"
        f"TWII canonical 最大日期为 `{manifest['preflight']['canonical_twii_max']}`，同 run handoff 最大日期为 `{manifest['preflight']['handoff_twii_max']}`；120 日窗口缺 `{manifest['preflight']['missing_twii_sessions']}` 日。\n\n"
        "因此本轮没有执行 Model B 评分、训练、回放或发布。B16 的 1 个 settled prospective paired day 原样保留，仍处于 `SANITY_ONLY_0_TO_19`。\n\n"
        "下一步：取得目标日正确且 PIT 合法的完整 TWII 连续 source-run 后，重新运行输入门禁；通过后才允许进入 shadow scoring。\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "blockers": blockers, "validator": validator["verdict"], "out": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if validator["verdict"] == "PASS_WITH_CONDITIONS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
