#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/model_b_compatibility_baseline_reinstatement/phase1c_compatibility_20260905/direct_replay_reexecution"
REVIEW = OUT / "independent_review.json"

EXPECTED = {
    ("full", "standard_artifact_model_a_plus_b"): (0.721631, -0.050830, 405, 157661.34),
    ("full", "fresh_qlib_top50_adaptive_baseline"): (0.662457, -0.088396, 410, 155259.42),
    ("common", "standard_artifact_model_a_plus_b"): (0.641235, -0.076739, 405, 149876.44),
    ("common", "fresh_qlib_top50_adaptive_baseline"): (0.625943, -0.088431, 410, 153601.13),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    required = [
        OUT / "gate_summary.json",
        OUT / "direct_replay_metrics.csv",
        OUT / "direct_replay_daily_nav.csv",
        OUT / "direct_replay_actions.csv",
        OUT / "next_day_execution_audit.csv",
        OUT / "parity_audit.json",
        OUT / "input_consumption_audit.json",
        OUT / "protected_path_fingerprint_audit.json",
        OUT / "checksum_manifest.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    findings: list[dict[str, Any]] = []
    if missing:
        findings.append({"severity": "P0", "finding": "required evidence missing", "paths": missing})
    else:
        checksums = read_json(OUT / "checksum_manifest.json")
        checksum_failures = []
        for relative, expected_hash in checksums.items():
            path = ROOT / relative
            if not path.exists() or sha256(path) != expected_hash:
                checksum_failures.append(relative)
        if checksum_failures:
            findings.append({"severity": "P0", "finding": "checksum validation failed", "paths": checksum_failures})

        metrics = pd.read_csv(OUT / "direct_replay_metrics.csv")
        for key, expected in EXPECTED.items():
            row = metrics[(metrics["universe"] == key[0]) & (metrics["method"] == key[1])]
            if row.shape[0] != 1:
                findings.append({"severity": "P0", "finding": "expected metric row missing or duplicated", "key": key})
                continue
            actual = row.iloc[0]
            observed = (
                round(float(actual["fee_tax_adjusted_net_return"]), 6),
                round(float(actual["max_drawdown"]), 6),
                int(actual["action_count"]),
                round(float(actual["fee_and_tax"]), 2),
            )
            if observed != expected:
                findings.append({"severity": "P0", "finding": "frozen metric mismatch", "key": key, "expected": expected, "actual": observed})

        parity = read_json(OUT / "parity_audit.json")
        if not parity.get("all_exact"):
            findings.append({"severity": "P0", "finding": "standard/legacy/frozen action or NAV parity failed", "checks": parity.get("checks")})

        next_day = pd.read_csv(OUT / "next_day_execution_audit.csv")
        pass_values = next_day["pass"].astype(str).str.lower().isin({"true", "1", "yes"})
        if next_day.shape[0] != 6 or not bool(pass_values.all()):
            findings.append({"severity": "P0", "finding": "next-day execution audit failed", "rows": next_day.to_dict("records")})

        nav = pd.read_csv(OUT / "direct_replay_daily_nav.csv")
        actions = pd.read_csv(OUT / "direct_replay_actions.csv")
        if nav.shape[0] != 6 * 205:
            findings.append({"severity": "P1", "finding": "unexpected daily NAV row count", "expected": 1230, "actual": int(nav.shape[0])})
        if actions.empty:
            findings.append({"severity": "P0", "finding": "action evidence is empty"})

        input_audit = read_json(OUT / "input_consumption_audit.json")
        if input_audit.get("forbidden_signal_fields_consumed") or input_audit.get("future_or_label_fields_consumed"):
            findings.append({"severity": "P0", "finding": "forbidden or future field consumed", "audit": input_audit})
        if input_audit.get("production_allowed") is not False or input_audit.get("research_only") is not True:
            findings.append({"severity": "P0", "finding": "research-only boundary missing", "audit": input_audit})

        protected = read_json(OUT / "protected_path_fingerprint_audit.json")
        if protected.get("unchanged") is not True:
            findings.append({"severity": "P0", "finding": "protected path changed", "audit": protected})

        gate = read_json(OUT / "gate_summary.json")
        if gate.get("production_allowed") is not False or gate.get("strict_pit_oos") is not False:
            findings.append({"severity": "P0", "finding": "gate overstates production or strict PIT readiness", "gate": gate})

    verdict = "PASS" if not findings else "FAIL_NEEDS_REPAIR"
    review = {
        "created_at": now(),
        "route": "MODEL_AB_COMPATIBILITY_BASELINE_REINSTATEMENT_AB3_DIRECT_REPLAY_REVIEW",
        "verdict": verdict,
        "findings": findings,
        "reviewed_dimensions": [
            "standard artifact direct consumption",
            "full/common frozen metric reproduction",
            "standard-vs-legacy action and NAV parity",
            "full frozen action and NAV parity",
            "next-day execution and fee/tax accounting",
            "forbidden-field consumption",
            "protected production path immutability",
        ],
        "accepted_conclusion": "Model A+B is restored as a legacy-compatible research baseline" if verdict == "PASS" else "not accepted",
        "strict_pit_oos_status": "BLOCKED_UNCHANGED",
        "production_default_status": "NOT_AUTHORIZED",
        "next_step": "route closure; product/default integration requires a separate strict PIT/OOS or explicit research-mode gate",
    }
    REVIEW.write_text(json.dumps(review, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
