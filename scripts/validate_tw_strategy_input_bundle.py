#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_VALIDATION = ROOT / "data_tw/catalog/dng4_input_bundle_validation.json"
REPORT_PATH = ROOT / "docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_EXECUTION_REPORT_CN.md"

REQUIRED_FILES = [
    "manifest.json",
    "signals.csv",
    "current_holdings.csv",
    "price_context.csv",
    "market_context.csv",
    "calendar.csv",
    "dependency_readiness.json",
    "lineage.json",
    "validator_report.json",
]

SIGNAL_REQUIRED_FIELDS = [
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
]

HOLDING_REQUIRED_FIELDS = [
    "asof_date",
    "instrument",
    "quantity",
    "cost_basis",
    "current_holding_flag",
]

PRICE_REQUIRED_FIELDS = ["price_date", "instrument", "open", "high", "low", "close", "volume", "tradable_flag"]
MARKET_REQUIRED_FIELDS = ["date", "open", "high", "low", "close", "volume", "return_1d", "market_trend_state"]
CALENDAR_REQUIRED_FIELDS = ["date"]

FORBIDDEN_EXACT_FIELDS = {
    "target_position",
    "target_weight",
    "allocation_weight",
    "execution_price",
    "execution_quantity",
    "broker",
    "broker_order_id",
    "order_id",
    "quick_trade",
    "cash_after",
    "nav",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "replay_return",
    "performance_metric",
}
FORBIDDEN_PREFIXES = ["future_return_", "future_excess_return_", "forward_return_", "label_"]
FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_inference_triggered",
    "strategy_replay_triggered",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT.resolve()))
    except (ValueError, FileNotFoundError):
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def forbidden_columns(header: list[str]) -> list[str]:
    bad = [field for field in header if field in FORBIDDEN_EXACT_FIELDS]
    bad.extend(field for field in header if any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES))
    return sorted(set(bad))


def validate_csv(path: Path, required_fields: list[str], allow_empty: bool, errors: list[str]) -> dict[str, Any]:
    header, row_count = csv_header_and_count(path)
    missing = [field for field in required_fields if field not in header]
    if missing:
        errors.append(f"{rel(path)} missing required fields: {missing}")
    bad = forbidden_columns(header)
    if bad:
        errors.append(f"{rel(path)} contains forbidden fields: {bad}")
    if row_count <= 0 and not allow_empty:
        errors.append(f"{rel(path)} row_count must be > 0")
    return {"header": header, "row_count": row_count, "forbidden_columns": bad}


def validate_flags(payload: dict[str, Any], path: Path, errors: list[str]) -> None:
    flags = payload.get("forbidden_action_flags", {})
    for key in FORBIDDEN_ACTION_KEYS:
        if flags.get(key) is not False:
            errors.append(f"{rel(path)} forbidden_action_flags.{key} must be false")


def update_catalog(validation: dict[str, Any]) -> None:
    catalog = read_json(CATALOG_VALIDATION)
    if not catalog:
        catalog = {"schema_version": "v1.dng4.input_bundle.validation_catalog", "generated_at": utc_now()}
    catalog["generated_at"] = utc_now()
    catalog["strategy_input_bundle"] = validation
    replay = catalog.get("replay_input_bundle", {})
    catalog["ok"] = bool(validation.get("ok")) and bool(replay.get("ok", True))
    catalog["status"] = "PARTIAL_READY" if catalog["ok"] else "BLOCKED_VALIDATOR"
    catalog["forbidden_action_flags"] = {key: False for key in FORBIDDEN_ACTION_KEYS}
    write_json(CATALOG_VALIDATION, catalog)


def write_report_from_catalog() -> None:
    catalog = read_json(CATALOG_VALIDATION)
    strategy = catalog.get("strategy_input_bundle", {})
    replay = catalog.get("replay_input_bundle", {})
    text = f"""# DNG4 Input Bundle Builder 执行报告

生成日期：{utc_now()}

## 1. 输入来源

- signal：`data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a`
- price：`data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625`
- market：`data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625`
- orthogonal：`data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625`

## 2. StrategyInputBundle 状态

- root：`{strategy.get('bundle_root', '')}`
- status：`{strategy.get('status', '')}`
- ok：`{strategy.get('ok', '')}`
- partial reason：`missing_current_holdings_or_order_intents; model_signal_asof_lags_price_market_asof; can_continue_to_model_b_ltr=false`

## 3. ReplayInputBundle 状态

- root：`{replay.get('bundle_root', '')}`
- status：`{replay.get('status', 'NOT_RUN')}`
- ok：`{replay.get('ok', 'NOT_RUN')}`
- partial reason：`empty_order_intents placeholder; no ReplayResult/NAV generated; next-day execution remains blocked for 2026-06-25`

## 4. Validator 输出

```json
{json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True)}
```

## 5. Forbidden Action Audit

本轮只读取本地既有 artifact 并生成 bundle/validator/report。未执行真实抓数、provider refresh/publish、accepted latest switch、readonly/Agent publish、模型训练、模型推理、模型 score 生成、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、target_position 或 target_weight。

## 6. DNG5 建议

建议进入 DNG5 route dependency contract，但仅限 contract/gate 设计。不得进入 Model B LTR、order intent 生成、replay execution、shadow execution 或 publish，直到 current holdings/order intents、2026-06-25 ModelSignalArtifact、DNG3 blockers 与 next-day execution availability 被修复并重新验证。
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG4 StrategyInputBundle.")
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = (ROOT / args.bundle_root).resolve() if not Path(args.bundle_root).is_absolute() else Path(args.bundle_root)

    errors: list[str] = []
    warnings: list[str] = []
    required_paths = {}
    for name in REQUIRED_FILES:
        path = root / name
        required_paths[name] = rel(path)
        if not path.exists():
            errors.append(f"missing required file: {rel(path)}")

    manifest = read_json(root / "manifest.json")
    dependency = read_json(root / "dependency_readiness.json")
    lineage = read_json(root / "lineage.json")

    if manifest.get("artifact_type") != "strategy_input_bundle":
        errors.append("manifest artifact_type must be strategy_input_bundle")
    for key in ["readonly_only", "no_order", "no_target_position", "no_target_weight"]:
        if manifest.get(key) is not True:
            errors.append(f"manifest {key} must be true")
    if manifest.get("model_b_ltr_ready") is not False:
        errors.append("manifest model_b_ltr_ready must be false")
    if manifest.get("status") == "PARTIAL_READY" and not manifest.get("partial_reason"):
        errors.append("partial strategy bundle must include partial_reason")
    validate_flags(manifest, root / "manifest.json", errors)

    if dependency.get("can_continue_to_replay") is not False:
        errors.append("dependency_readiness can_continue_to_replay must be false for DNG4 partial bundle")
    if dependency.get("model_b_ltr_ready") is not False:
        errors.append("dependency_readiness model_b_ltr_ready must be false")
    validate_flags(dependency, root / "dependency_readiness.json", errors)

    if lineage.get("lineage_type") != "local_artifact_bundle_no_fetch_no_score_no_order":
        errors.append("lineage lineage_type must be local_artifact_bundle_no_fetch_no_score_no_order")
    validate_flags(lineage, root / "lineage.json", errors)

    csv_results = {
        "signals": validate_csv(root / "signals.csv", SIGNAL_REQUIRED_FIELDS, False, errors),
        "current_holdings": validate_csv(root / "current_holdings.csv", HOLDING_REQUIRED_FIELDS, True, errors),
        "price_context": validate_csv(root / "price_context.csv", PRICE_REQUIRED_FIELDS, False, errors),
        "market_context": validate_csv(root / "market_context.csv", MARKET_REQUIRED_FIELDS, False, errors),
        "calendar": validate_csv(root / "calendar.csv", CALENDAR_REQUIRED_FIELDS, False, errors),
    }

    if csv_results["current_holdings"]["row_count"] == 0:
        warnings.append("current_holdings.csv is empty; acceptable only because bundle is PARTIAL_READY")

    status = "BLOCKED_VALIDATOR" if errors else manifest.get("status", "PARTIAL_READY")
    validation = {
        "schema_version": "v1.dng4.strategy_input_bundle.validation",
        "generated_at": utc_now(),
        "ok": not errors,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "bundle_root": rel(root),
        "bundle_id": manifest.get("bundle_id"),
        "run_id": manifest.get("run_id"),
        "asof": manifest.get("asof"),
        "required_paths": required_paths,
        "row_counts": {name: result["row_count"] for name, result in csv_results.items()},
        "model_b_ltr_ready": manifest.get("model_b_ltr_ready"),
        "fallback_allowed": manifest.get("fallback_allowed"),
        "partial_reason": manifest.get("partial_reason"),
        "forbidden_action_flags": {key: False for key in FORBIDDEN_ACTION_KEYS},
    }
    write_json(root / "validator_report.json", validation)
    update_catalog(validation)
    write_report_from_catalog()

    if args.json:
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok={validation['ok']} status={status} errors={len(errors)} warnings={len(warnings)}")
    return 0 if validation["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
