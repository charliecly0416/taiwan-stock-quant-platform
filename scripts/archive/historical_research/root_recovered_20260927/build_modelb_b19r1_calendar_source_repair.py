#!/usr/bin/env python3
"""Build the isolated B19R1 calendar/source repair without scoring or outcomes."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r1_calendar_source_repair_20260916"
B19 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_reconstructed_pit_holdout_feasibility_20260916"
REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_preflight_independent_review_20260916/B19_PREFLIGHT_FINAL_INDEPENDENT_REVIEW.json"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
PRICE_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T103002Z/same_run_handoff_artifacts/daily_price"
OTHER_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T144501Z/same_run_handoff_artifacts"
TWII = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii.csv"
TWII_RAW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii_raw.json"
START = "2026-05-11"
END = "2026-09-15"
HORIZON = 10
EXCLUDED = {"TW6919", "TW7769"}

PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)
B19_IMMUTABLE = (
    B19 / "B19_MANIFEST.json",
    B19 / "B19_VALIDATOR.json",
    B19 / "B19_DAILY_FEASIBILITY.csv",
    B19 / "B19_EXECUTION_REPORT_CN.md",
    B19 / "B19_EXECUTOR_ERRATA.json",
    B19 / "B19_EXECUTOR_ERRATA_CN.md",
    B19 / "protected_before.json",
    B19 / "protected_after.json",
)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(paths: tuple[Path, ...]) -> dict[str, dict[str, Any]]:
    return {
        relative(path): {"exists": path.is_file(), "sha256": sha256(path)}
        for path in paths
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_normalized(path: Path) -> tuple[dict[str, set[str]], dict[str, dict[str, dict[str, Any]]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_date: dict[str, set[str]] = defaultdict(set)
    records: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in payload["records"]:
        day = str(row.get("trade_date") or row.get("date") or "")[:10]
        symbol = str(row.get("symbol") or row.get("stock_id") or "").upper()
        if not day or not symbol:
            continue
        symbol = symbol if symbol.startswith("TW") else f"TW{symbol}"
        by_date[day].add(symbol)
        records[day][symbol] = row
    return dict(by_date), dict(records)


def field_present(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return True


def qlib_audit() -> tuple[dict[str, int], dict[str, Any]]:
    coverage: dict[str, int] = defaultdict(int)
    placeholder_rows = 0
    zero_volume = 0
    ohlc_equal = 0
    files = sorted(PRICE_ROOT.glob("TW*.csv"))
    for path in files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                day = str(row.get("date") or "")[:10]
                if START <= day <= END:
                    coverage[day] += 1
                if day == "2026-07-10":
                    placeholder_rows += 1
                    try:
                        zero_volume += float(row.get("volume") or 0) == 0
                    except ValueError:
                        pass
                    values = [row.get(name) for name in ("open", "high", "low", "close")]
                    ohlc_equal += bool(values[0]) and len(set(values)) == 1
    return dict(coverage), {
        "source_root": relative(PRICE_ROOT),
        "file_count": len(files),
        "date_rows_in_window": len(coverage),
        "july_10_rows": placeholder_rows,
        "july_10_zero_volume_rows": zero_volume,
        "july_10_ohlc_equal_rows": ohlc_equal,
    }


def csv_dates(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            str(row.get("date") or row.get("trade_date") or "")[:10]
            for row in csv.DictReader(handle)
        }


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing B19R1 output: {OUT}")
    OUT.mkdir(parents=True)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    protected_before = fingerprint(PROTECTED)
    b19_before = fingerprint(B19_IMMUTABLE)
    write_json(OUT / "protected_before.json", protected_before)
    write_json(OUT / "b19_immutable_before.json", b19_before)

    price_path = PRICE_CAPTURE / "daily_price.normalized.json"
    institutional_path = OTHER_CAPTURE / "institutional/institutional.normalized.json"
    margin_path = OTHER_CAPTURE / "margin/margin.normalized.json"
    price_by_date, price_records = read_normalized(price_path)
    institutional_by_date, _ = read_normalized(institutional_path)
    margin_by_date, _ = read_normalized(margin_path)
    twii_dates = csv_dates(TWII)
    qlib_coverage, placeholder = qlib_audit()

    full_actual_calendar = sorted(price_by_date)
    calendar = [day for day in full_actual_calendar if START <= day <= END]
    prior_index = {day: full_actual_calendar[index - 1] for index, day in enumerate(full_actual_calendar) if index}
    mature_dates = calendar[:-HORIZON]
    mature_set = set(mature_dates)
    tail_dates = calendar[-HORIZON:]

    calendar_rows = [
        {
            "sequence": index + 1,
            "date": day,
            "source": "finmind_daily_price_actual_record_date",
            "source_path": relative(price_path),
            "source_sha256": sha256(price_path),
        }
        for index, day in enumerate(calendar)
    ]
    write_csv(OUT / "FROZEN_ACTUAL_MARKET_CALENDAR.csv", calendar_rows)

    mapping_rows: list[dict[str, Any]] = []
    maturity_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for index, day in enumerate(calendar):
        prior = prior_index[day]
        next_day = calendar[index + 1] if index + 1 < len(calendar) else ""
        maturity_day = calendar[index + HORIZON] if index + HORIZON < len(calendar) else ""
        mapping_rows.append({
            "signal_date": day,
            "prior_actual_trading_date": prior,
            "mapping_basis": "previous_finmind_actual_price_record_date",
        })
        maturity_rows.append({
            "signal_date": day,
            "label_mature_10_actual_trading_days": day in mature_set,
            "t_plus_10_actual_trading_date": maturity_day,
            "maturity_class": "MATURE" if day in mature_set else "IMMATURE_TAIL",
        })

        eligible = (
            price_by_date.get(day, set())
            & institutional_by_date.get(prior, set())
            & margin_by_date.get(prior, set())
        ) - EXCLUDED
        next_records = price_records.get(next_day, {}) if next_day else {}
        next_open = {
            symbol for symbol, row in next_records.items() if field_present(row.get("open"))
        }
        next_close = {
            symbol for symbol, row in next_records.items() if field_present(row.get("close"))
        }
        source_rows.append({
            "signal_date": day,
            "maturity_class": "MATURE" if day in mature_set else "IMMATURE_TAIL",
            "orthogonal_trade_date": prior,
            "next_actual_trading_date": next_day,
            "qlib_ohlcv_symbols": qlib_coverage.get(day, 0),
            "finmind_price_symbols": len(price_by_date.get(day, set())),
            "institutional_symbols_at_t_minus_1": len(institutional_by_date.get(prior, set())),
            "margin_short_symbols_at_t_minus_1": len(margin_by_date.get(prior, set())),
            "twii_same_day_present": day in twii_dates,
            "next_open_field_capacity": len(next_open),
            "next_close_field_capacity": len(next_close),
            "eligible_capacity_after_exclusions": len(eligible),
            "candidate_capacity_at_least_50": len(eligible) >= 50,
            "source_capacity_closed": (
                qlib_coverage.get(day, 0) == 150
                and len(price_by_date.get(day, set())) == 150
                and len(eligible) >= 50
                and day in twii_dates
                and len(next_open) >= 50
                and len(next_close) >= 50
            ),
            "price_source_path": relative(price_path),
            "price_source_sha256": sha256(price_path),
            "institutional_source_path": relative(institutional_path),
            "institutional_source_sha256": sha256(institutional_path),
            "margin_source_path": relative(margin_path),
            "margin_source_sha256": sha256(margin_path),
            "twii_source_path": relative(TWII),
            "twii_source_sha256": sha256(TWII),
        })

    write_csv(OUT / "DAILY_T_MINUS_1_MAPPING.csv", mapping_rows)
    write_csv(OUT / "MATURITY_AUDIT.csv", maturity_rows)
    write_csv(OUT / "SOURCE_CAPACITY_AUDIT.csv", source_rows)

    calendar_sha = sha256(OUT / "FROZEN_ACTUAL_MARKET_CALENDAR.csv")
    lineage = {
        "finmind_daily_price": {
            "normalized_path": relative(price_path),
            "normalized_sha256": sha256(price_path),
            "adapter_path": relative(PRICE_CAPTURE / "daily_price.adapter_output.json"),
            "adapter_sha256": sha256(PRICE_CAPTURE / "daily_price.adapter_output.json"),
            "availability_semantics": "captured retrospectively; record dates anchor actual market calendar",
        },
        "finmind_institutional": {
            "normalized_path": relative(institutional_path),
            "normalized_sha256": sha256(institutional_path),
            "adapter_path": relative(OTHER_CAPTURE / "institutional/institutional.adapter_output.json"),
            "adapter_sha256": sha256(OTHER_CAPTURE / "institutional/institutional.adapter_output.json"),
            "availability_semantics": "reconstructed PIT; use only at next actual trading date",
        },
        "finmind_margin_short": {
            "normalized_path": relative(margin_path),
            "normalized_sha256": sha256(margin_path),
            "adapter_path": relative(OTHER_CAPTURE / "margin/margin.adapter_output.json"),
            "adapter_sha256": sha256(OTHER_CAPTURE / "margin/margin.adapter_output.json"),
            "availability_semantics": "reconstructed PIT; use only at next actual trading date",
        },
        "yahoo_twii_history": {
            "normalized_path": relative(TWII),
            "normalized_sha256": sha256(TWII),
            "raw_path": relative(TWII_RAW),
            "raw_sha256": sha256(TWII_RAW),
            "availability_semantics": "historical capture without source-native published_at",
        },
    }
    write_json(OUT / "SOURCE_LINEAGE.json", lineage)

    protected_after = fingerprint(PROTECTED)
    b19_after = fingerprint(B19_IMMUTABLE)
    write_json(OUT / "protected_after.json", protected_after)
    write_json(OUT / "b19_immutable_after.json", b19_after)
    mature_source_rows = [row for row in source_rows if row["maturity_class"] == "MATURE"]
    july_13 = next(row for row in source_rows if row["signal_date"] == "2026-07-13")
    september_15 = next(row for row in source_rows if row["signal_date"] == "2026-09-15")

    manifest = {
        "schema_version": "modelb.b19r1.calendar_source_repair.v1",
        "run_id": OUT.name,
        "created_at": created_at,
        "scope": "readonly calendar and source-capacity repair",
        "source_review": {"path": relative(REVIEW), "sha256": sha256(REVIEW)},
        "decision": "PASS_REPAIR_ONLY",
        "training_authorized": False,
        "calendar": {
            "path": relative(OUT / "FROZEN_ACTUAL_MARKET_CALENDAR.csv"),
            "sha256": calendar_sha,
            "start": calendar[0],
            "end": calendar[-1],
            "actual_market_days": len(calendar),
            "unique_strictly_increasing": calendar == sorted(set(calendar)),
            "provenance": "FinMind TaiwanStockPrice normalized record dates, cross-audited against qlib and TWII",
        },
        "placeholder_disposition": {
            **placeholder,
            "date": "2026-07-10",
            "finmind_price_present": "2026-07-10" in price_by_date,
            "twii_present": "2026-07-10" in twii_dates,
            "included_in_frozen_calendar": "2026-07-10" in calendar,
            "classification": "NON_TRADING_PLACEHOLDER_REMOVED_FROM_DATE_ARITHMETIC",
        },
        "maturity": {
            "horizon_actual_trading_days": HORIZON,
            "mature_start": mature_dates[0],
            "mature_end": mature_dates[-1],
            "mature_days": len(mature_dates),
            "immature_tail_days": len(tail_dates),
            "immature_tail_dates": tail_dates,
        },
        "july_13_closure": july_13,
        "september_15_disposition": {
            "maturity_class": september_15["maturity_class"],
            "twii_same_day_present": september_15["twii_same_day_present"],
            "included_in_mature_denominator": False,
            "classification": "IMMATURE_SOURCE_BLOCKED_TAIL",
        },
        "mature_source_capacity": {
            "days": len(mature_source_rows),
            "minimum_eligible_capacity_after_exclusions": min(row["eligible_capacity_after_exclusions"] for row in mature_source_rows),
            "minimum_next_open_field_capacity": min(row["next_open_field_capacity"] for row in mature_source_rows),
            "minimum_next_close_field_capacity": min(row["next_close_field_capacity"] for row in mature_source_rows),
            "all_source_capacity_closed": all(row["source_capacity_closed"] for row in mature_source_rows),
        },
        "candidate_contract": {
            "excluded_before_capacity_count": sorted(EXCLUDED),
            "exact_50_materialized": False,
            "capacity_only": True,
        },
        "lineage": lineage,
        "b19_immutable_before": b19_before,
        "b19_immutable_after": b19_after,
        "b19_immutable_unchanged": b19_before == b19_after,
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_before == protected_after,
        "model_a_predict_called": False,
        "model_b_predict_called": False,
        "training_performed": False,
        "tuning_performed": False,
        "replay_performed": False,
        "label_read": False,
        "outcome_or_return_value_read": False,
        "price_field_presence_only": True,
        "production_write_performed": False,
        "baseline_admission": False,
    }
    write_json(OUT / "B19R1_MANIFEST.json", manifest)

    checks = {
        "calendar_exactly_90_days": len(calendar) == 90,
        "calendar_bounds_exact": calendar[0] == START and calendar[-1] == END,
        "calendar_unique_strictly_increasing": calendar == sorted(set(calendar)),
        "july_10_absent_from_calendar": "2026-07-10" not in calendar,
        "july_10_150_qlib_zero_volume_placeholders": placeholder["july_10_rows"] == placeholder["july_10_zero_volume_rows"] == 150,
        "july_10_150_qlib_ohlc_equal_placeholders": placeholder["july_10_rows"] == placeholder["july_10_ohlc_equal_rows"] == 150,
        "july_10_absent_from_finmind_and_twii": "2026-07-10" not in price_by_date and "2026-07-10" not in twii_dates,
        "mature_exactly_80_days": len(mature_dates) == 80,
        "mature_bounds_exact": mature_dates[0] == START and mature_dates[-1] == "2026-09-01",
        "immature_tail_exactly_10_days": len(tail_dates) == 10,
        "july_13_t_minus_1_is_july_09": july_13["orthogonal_trade_date"] == "2026-07-09",
        "july_13_sources_closed": july_13["source_capacity_closed"],
        "all_80_mature_capacity_at_least_50": len(mature_source_rows) == 80 and all(row["eligible_capacity_after_exclusions"] >= 50 for row in mature_source_rows),
        "all_80_mature_twii_present": all(row["twii_same_day_present"] for row in mature_source_rows),
        "all_80_mature_next_open_close_capacity_at_least_50": all(row["next_open_field_capacity"] >= 50 and row["next_close_field_capacity"] >= 50 for row in mature_source_rows),
        "september_15_is_immature_source_blocked_tail": september_15["maturity_class"] == "IMMATURE_TAIL" and not september_15["twii_same_day_present"],
        "excluded_symbols_applied_before_capacity_only": not manifest["candidate_contract"]["exact_50_materialized"],
        "original_b19_hashes_unchanged": b19_before == b19_after,
        "protected_before_after_current_equal": protected_before == protected_after,
        "no_predict_training_tuning_replay_label_outcome_or_production_write": not any([
            manifest["model_a_predict_called"], manifest["model_b_predict_called"], manifest["training_performed"],
            manifest["tuning_performed"], manifest["replay_performed"], manifest["label_read"],
            manifest["outcome_or_return_value_read"], manifest["production_write_performed"],
        ]),
    }
    verdict = "PASS_REPAIR_ONLY" if all(checks.values()) else "FAIL"
    manifest["decision"] = verdict
    write_json(OUT / "B19R1_MANIFEST.json", manifest)
    validator = {
        "schema_version": "modelb.b19r1.calendar_source_repair.validator.v1",
        "checks": checks,
        "verdict": verdict,
        "training_go_no_go": "NO_GO_TRAINING",
        "next_action_if_pass": "independent B19R1 review, then separately frozen pretraining data materialization",
    }
    write_json(OUT / "B19R1_VALIDATOR.json", validator)

    report = f"""# B19R1 只读日历与 source repair 执行报告

结论：`{verdict}`。这只表示 B19 的日历和逐日 source capacity 已修复，不授权训练、评分、回放或 baseline 纳入；训练仍为 `NO_GO`。

## 日历修复

冻结日历以 FinMind 实际价格 record date 为锚，和 qlib、TWII 交叉审计。`{START}..{END}` 共 `{len(calendar)}` 个真实市场日，日期唯一且严格递增。`2026-07-10` 已从日期运算移除：qlib 150 股当天全部 volume=0 且各股 OHLC 四值相同，FinMind 与 TWII 都没有该日，因此它是 non-trading placeholder。

10 个真实交易日 horizon 下，成熟信号日为 `{mature_dates[0]}..{mature_dates[-1]}` 共 `{len(mature_dates)}` 日；最后 `{len(tail_dates)}` 日为未成熟 tail。`2026-09-15` 的 TWII 仍缺失，但它只保留为 immature/source-blocked tail，不进入成熟窗通过率。

## 7 月 13 日与逐日容量

`2026-07-13` 保留在日历，t-1 已按真实交易日修为 `{july_13['orthogonal_trade_date']}`。该日 qlib/FinMind price 分别为 {july_13['qlib_ohlcv_symbols']}/{july_13['finmind_price_symbols']} 股，t-1 institutional/margin 为 {july_13['institutional_symbols_at_t_minus_1']}/{july_13['margin_short_symbols_at_t_minus_1']} 股，TWII 存在，排除 `TW6919`、`TW7769` 后容量为 {july_13['eligible_capacity_after_exclusions']}。

80 个成熟日的最小 eligible capacity 为 {manifest['mature_source_capacity']['minimum_eligible_capacity_after_exclusions']}；next-open 和 next-close 字段最小容量分别为 {manifest['mature_source_capacity']['minimum_next_open_field_capacity']} 和 {manifest['mature_source_capacity']['minimum_next_close_field_capacity']}。这里只读取字段是否存在，不保存数值、不计算标签或收益，也没有物化 exact-50。

## 安全边界

原 B19/errata hashes 前后一致，protected latest 指纹前后一致。没有调用 Model A/B predict，没有训练、调参、回放、标签或收益读取，也没有 baseline/latest/provider/frontend/DB/broker 写入。
"""
    (OUT / "B19R1_EXECUTION_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(json.dumps({"verdict": verdict, "actual_days": len(calendar), "mature_days": len(mature_dates), "july_13_t_minus_1": july_13["orthogonal_trade_date"]}, ensure_ascii=False))
    return 0 if verdict == "PASS_REPAIR_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
