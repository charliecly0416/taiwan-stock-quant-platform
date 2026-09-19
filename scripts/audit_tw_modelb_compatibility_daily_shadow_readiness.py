#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
SIGNAL_ROOT = LATEST.parent
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
TWII = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
OPS = ROOT / "data_tw/ops/daily_auto_update"
MODEL_GATE = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905/gate_summary.json"
OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds0_preflight_20260905"

PROTECTED = [
    LATEST,
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(paths: list[Path]) -> dict[str, Any]:
    return {
        str(path.relative_to(ROOT)): {
            "exists": path.exists(),
            "sha256": sha256(path) if path.is_file() else None,
            "size": path.stat().st_size if path.exists() else None,
        }
        for path in paths
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def roc_date(raw: object) -> str | None:
    text = str(raw or "").strip()
    if len(text) != 7 or not text.isdigit():
        return None
    try:
        return date(int(text[:3]) + 1911, int(text[3:5]), int(text[5:7])).isoformat()
    except ValueError:
        return None


def handoff_twii_dates() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(OPS.glob("daily_tw_stock_auto_update_*/same_run_handoff_artifacts/**/twii.normalized.json")):
        try:
            payload = read_json(path)
        except Exception:
            continue
        for row in payload.get("records", []):
            if str(row.get("指數") or "") != "發行量加權股價指數":
                continue
            day = roc_date(row.get("日期"))
            if day:
                found[day] = str(path.relative_to(ROOT))
    return found


def load_twii_candidate(candidate_arg: str, asof: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load an isolated TWII candidate and its declared effective-session policy."""
    supplied = Path(candidate_arg).expanduser().resolve()
    if supplied.is_dir():
        lineage_path = supplied / "twii_daily_candidate_with_lineage.csv"
        plain_path = supplied / "twii_daily_candidate.csv"
        candidate_path = lineage_path if lineage_path.is_file() else plain_path
        closure_json = supplied / "effective_120_session_closure_audit.json"
        if not closure_json.is_file():
            closure_json = supplied / "effective_120_session_closure.json"
        closure_csv = supplied / "effective_120_session_closure.csv"
    else:
        candidate_path = supplied
        closure_json = supplied.parent / "effective_120_session_closure_audit.json"
        if not closure_json.is_file():
            closure_json = supplied.parent / "effective_120_session_closure.json"
        closure_csv = supplied.parent / "effective_120_session_closure.csv"
    if not candidate_path.is_file():
        raise ValueError(f"candidate file not found: {candidate_path}")
    if not closure_json.is_file():
        raise ValueError(f"effective closure JSON not found beside candidate: {closure_json}")

    candidate = pd.read_csv(candidate_path)
    required_columns = {"date", "close"}
    if not required_columns.issubset(candidate.columns):
        raise ValueError(f"candidate must contain date and close: {candidate_path}")
    candidate["date"] = candidate["date"].astype(str).str[:10]
    candidate["close"] = pd.to_numeric(candidate["close"], errors="coerce")
    duplicate_count = int(candidate["date"].duplicated().sum())
    candidate = candidate[candidate["date"] <= asof].copy()
    finite_positive_failures = int((~candidate["close"].map(pd.notna) | ~candidate["close"].map(lambda value: pd.notna(value) and float(value) > 0)).sum())
    candidate = candidate.dropna(subset=["date", "close"])
    candidate = candidate[candidate["close"] > 0].sort_values("date")

    closure = read_json(closure_json)
    closure_dates: list[str] = []
    if closure_csv.is_file():
        closure_frame = pd.read_csv(closure_csv)
        if "date" in closure_frame.columns:
            closure_dates = sorted(closure_frame["date"].astype(str).str[:10].tolist())
    window = closure.get("effective_window") or {}
    declared_exception = closure.get("excluded_exception") or closure.get("exception") or ""
    closure_policy = {
        "closure_path": str(closure_json.relative_to(ROOT)) if closure_json.is_relative_to(ROOT) else str(closure_json),
        "closure_csv_path": str(closure_csv.relative_to(ROOT)) if closure_csv.is_file() and closure_csv.is_relative_to(ROOT) else (str(closure_csv) if closure_csv.is_file() else ""),
        "declared_exception": declared_exception,
        "exception_classification": closure.get("exception_classification", "provider-calendar synthetic non-trading exception"),
        "selection_rule": closure.get("selection_rule", "declared effective closure sessions"),
        "required_sessions": int(closure.get("required_sessions", window.get("count", 0)) or 0),
        "verified_sessions": int(closure.get("verified_sessions", window.get("count", 0)) or 0),
        "closure_exact_target": bool(closure.get("exact_target", False)),
        "candidate_path": str(candidate_path.relative_to(ROOT)) if candidate_path.is_relative_to(ROOT) else str(candidate_path),
        "candidate_duplicate_dates": duplicate_count,
        "candidate_finite_positive_close_failures": finite_positive_failures,
    }
    if closure_policy["required_sessions"] != 120 or closure_policy["verified_sessions"] != 120:
        raise ValueError("effective closure must declare required_sessions=120 and verified_sessions=120")
    if not closure_dates:
        start, end = str(window.get("min") or ""), str(window.get("max") or "")
        closure_dates = sorted(candidate.loc[(candidate["date"] >= start) & (candidate["date"] <= end), "date"].unique())
    effective_dates = sorted(set(closure_dates) - {str(declared_exception)})
    if len(effective_dates) != 120:
        raise ValueError(f"effective closure dates are not 120 after exception policy: {len(effective_dates)}")
    closure_policy["effective_dates_count"] = len(effective_dates)
    closure_policy["effective_date_min"] = effective_dates[0]
    closure_policy["effective_date_max"] = effective_dates[-1]
    closure_policy["effective_dates"] = effective_dates
    return candidate, closure_policy


def main() -> int:
    parser = argparse.ArgumentParser(description="MBCDS0 Model B compatibility input readiness preflight")
    parser.add_argument("--twii-candidate", help="isolated TWII candidate directory or CSV; preserves legacy default behavior")
    args = parser.parse_args()
    before = fingerprint(PROTECTED)
    latest = read_json(LATEST)
    asof = str(latest.get("asof") or "")[:10]
    run_dir = ROOT / "qlib_pipeline" / str(latest["run_dir"])
    prediction = run_dir / "prediction.csv"
    pred = pd.read_csv(prediction, usecols=["datetime", "instrument", "score"])
    pred["date"] = pred["datetime"].astype(str).str[:10]
    target = pred[pred["date"] == asof].copy()
    target_symbols = sorted(target["instrument"].astype(str).unique())

    history_frames = []
    for path in SIGNAL_ROOT.glob("option_c_daily_signal_*/prediction.csv"):
        try:
            frame = pd.read_csv(path, usecols=["datetime", "instrument", "score"])
        except Exception:
            continue
        frame["date"] = frame["datetime"].astype(str).str[:10]
        frame = frame[frame["date"] <= asof]
        if not frame.empty:
            history_frames.append(frame[["date", "instrument", "score"]])
    history = pd.concat(history_frames, ignore_index=True) if history_frames else pd.DataFrame(columns=["date", "instrument", "score"])
    history = history.drop_duplicates(["date", "instrument"], keep="last")
    history_dates = sorted(history["date"].unique())

    price_rows = []
    for symbol in target_symbols:
        path = PRICE_ROOT / f"{symbol}.csv"
        max_date = ""
        has_target = False
        if path.exists():
            frame = pd.read_csv(path, usecols=["date"])
            dates = frame["date"].astype(str).str[:10]
            max_date = str(dates.max()) if not dates.empty else ""
            has_target = bool((dates == asof).any())
        price_rows.append({"instrument": symbol, "price_path": str(path.relative_to(ROOT)), "max_date": max_date, "has_target": has_target})

    candidate_policy: dict[str, Any] = {}
    if args.twii_candidate:
        twii_frame, candidate_policy = load_twii_candidate(args.twii_candidate, asof)
        canonical_twii_dates: set[str] = set()
        handoff: dict[str, str] = {}
        combined_twii_dates = set(twii_frame["date"])
        required_window = candidate_policy["effective_dates"]
        twii_source_mode = "explicit_isolated_candidate"
    else:
        twii_frame = pd.read_csv(TWII, usecols=["date", "close"])
        twii_frame["date"] = twii_frame["date"].astype(str).str[:10]
        canonical_twii_dates = set(twii_frame["date"])
        handoff = handoff_twii_dates()
        combined_twii_dates = canonical_twii_dates | set(handoff)
        calendar_dates = [line.strip()[:10] for line in CALENDAR.read_text(encoding="utf-8").splitlines() if line.strip() and line.strip()[:10] <= asof]
        required_window = calendar_dates[-120:]
        twii_source_mode = "canonical_plus_same_run_handoff"
    missing_twii_window = [day for day in required_window if day not in combined_twii_dates]
    candidate_checks = []
    if args.twii_candidate:
        candidate_checks = [
            {"gate": "twii_candidate_effective_closure_120", "pass": candidate_policy["required_sessions"] == 120 and candidate_policy["verified_sessions"] == 120 and len(required_window) == 120, "details": f"required={candidate_policy['required_sessions']};verified={candidate_policy['verified_sessions']};effective={len(required_window)}"},
            {"gate": "twii_candidate_duplicates_zero", "pass": candidate_policy["candidate_duplicate_dates"] == 0, "details": f"duplicates={candidate_policy['candidate_duplicate_dates']}"},
            {"gate": "twii_candidate_positive_finite_close", "pass": candidate_policy["candidate_finite_positive_close_failures"] == 0, "details": f"failures={candidate_policy['candidate_finite_positive_close_failures']}"},
            {"gate": "twii_candidate_exception_declared", "pass": bool(candidate_policy["declared_exception"]), "details": f"exception={candidate_policy['declared_exception']}"},
        ]

    model_gate = read_json(MODEL_GATE) if MODEL_GATE.exists() else {}
    checks = [
        {"gate": "accepted_latest", "pass": latest.get("status") == "accepted" and bool(asof), "details": f"status={latest.get('status')};asof={asof}"},
        {"gate": "full_qlib_cross_section", "pass": len(target_symbols) == 150 and len(target) == 150, "details": f"rows={len(target)};symbols={len(target_symbols)}"},
        {"gate": "qlib_rank_history", "pass": len(history_dates) >= 6, "details": f"dates={len(history_dates)};min={history_dates[0] if history_dates else ''};max={history_dates[-1] if history_dates else ''}"},
        {"gate": "target_adjusted_price", "pass": sum(row["has_target"] for row in price_rows) == 150, "details": f"covered={sum(row['has_target'] for row in price_rows)}/150"},
        {"gate": "exact_phase1c_model", "pass": model_gate.get("score_reproduction_pass") is True, "details": f"decision={model_gate.get('decision', 'missing')}"},
        {"gate": "twii_exact_target", "pass": asof in combined_twii_dates, "details": f"target={asof};canonical_max={max(canonical_twii_dates) if canonical_twii_dates else ''};handoff_max={max(handoff) if handoff else ''}"},
        {"gate": "twii_120_session_continuity", "pass": len(required_window) == 120 and not missing_twii_window, "details": f"required={len(required_window)};missing={len(missing_twii_window)}"},
    ]
    checks = candidate_checks + checks
    ready = all(check["pass"] for check in checks)

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(OUT / "input_gate_inventory.csv", index=False)
    pd.DataFrame(price_rows).to_csv(OUT / "target_price_coverage.csv", index=False)
    pd.DataFrame(
        [{"date": day, "source": "candidate" if args.twii_candidate else ("canonical" if day in canonical_twii_dates else "handoff"), "source_path": candidate_policy.get("candidate_path", handoff.get(day, str(TWII.relative_to(ROOT)))) if args.twii_candidate else handoff.get(day, str(TWII.relative_to(ROOT)))} for day in sorted(combined_twii_dates) if day <= asof]
    ).to_csv(OUT / "twii_source_inventory.csv", index=False)
    pd.DataFrame([{"missing_trading_date": day} for day in missing_twii_window]).to_csv(OUT / "twii_120_session_missing_dates.csv", index=False)

    after = fingerprint(PROTECTED)
    report = {
        "created_at": now(),
        "phase": "MBCDS0_CONTRACT_AND_INPUT_READINESS_PREFLIGHT_NO_SCORING",
        "target_asof": asof,
        "ready_for_shadow_scoring": ready,
        "decision": "READY_FOR_MBCDS2_LATEST_SHADOW_SCORE" if ready else "STOP_INPUT_NOT_READY",
        "blocking_gates": [check["gate"] for check in checks if not check["pass"]],
        "checks": checks,
        "canonical_twii_max": max(canonical_twii_dates) if canonical_twii_dates else "",
        "handoff_twii_unique_dates": len(handoff),
        "handoff_twii_max": max(handoff) if handoff else "",
        "twii_source_mode": twii_source_mode,
        "twii_candidate": candidate_policy,
        "required_twii_sessions": len(required_window),
        "missing_twii_sessions": len(missing_twii_window),
        "missing_twii_first": missing_twii_window[0] if missing_twii_window else "",
        "missing_twii_last": missing_twii_window[-1] if missing_twii_window else "",
        "protected_paths_unchanged": before == after,
        "no_training": True,
        "no_scoring": True,
        "no_latest_provider_cron_frontend_write": True,
        "recommended_repair": "build an immutable continuous TWII daily series through target_asof from trusted same-run/official captures, validate 120-session continuity, then rerun MBCDS0",
    }
    (OUT / "readiness_report.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (OUT / "protected_path_fingerprint_audit.json").write_text(json.dumps({"before": before, "after": after, "unchanged": before == after}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (OUT / "execution_report.md").write_text(
        "# MBCDS2 Input Preflight Execution Report\n\n"
        f"- source mode: `{twii_source_mode}`\n"
        f"- candidate: `{candidate_policy.get('candidate_path', 'legacy canonical + handoff')}`\n"
        f"- effective TWII closure: `{len(required_window)}/120`\n"
        f"- target asof: `{asof}`; exact target: `{asof in combined_twii_dates}`\n"
        f"- declared exception: `{candidate_policy.get('declared_exception', 'none')}`\n"
        f"- missing effective sessions: `{len(missing_twii_window)}`\n"
        f"- protected paths unchanged: `{before == after}`\n"
        "- Model B scoring/training: `NOT EXECUTED`\n"
        "- production/latest/provider/cron/frontend/backend mutation: `NOT AUTHORIZED`\n\n"
        f"## Decision\n`{report['decision']}`\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ready else 3


if __name__ == "__main__":
    raise SystemExit(main())
