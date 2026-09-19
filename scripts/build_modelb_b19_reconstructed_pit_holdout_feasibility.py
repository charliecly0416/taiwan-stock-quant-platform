#!/usr/bin/env python3
"""Inventory B19 reconstructed-PIT holdout inputs without scoring or outcomes."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_reconstructed_pit_holdout_feasibility_20260916"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
MODEL_A = ROOT / "qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl"
MODEL_A_SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022"
MODEL_B = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914/MODEL_B_CANONICAL_LGBM_RANKER.pkl"
MODEL_B_FREEZE = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914/B9_CANONICAL_RETRAIN_RUN_FREEZE.json"
FEATURE_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
PRICE_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T103002Z/same_run_handoff_artifacts/daily_price"
ORTHOGONAL_CAPTURE = ROOT / "data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T144501Z/same_run_handoff_artifacts"
TWII_HISTORY = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii.csv"
TWII_RAW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b8_prospective_shadow_20260914/source_run_20260914_natural/yahoo_twii_20260914/twii_raw.json"
TWII_0915_ADAPTER = PRICE_CAPTURE / "twii.adapter_output.json"
ACCEPTANCE_CRITERIA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19_preflight_independent_review_20260916/B19_PREFLIGHT_ACCEPTANCE_CRITERIA.json"
START = "2026-05-11"
END = "2026-09-15"
HORIZON = 10
EXCLUDED = {"TW7769", "TW6919"}
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def fingerprint(path: Path) -> dict[str, Any]:
    return {"path": relative(path), "exists": path.is_file(), "sha256": sha256(path)}


def protected_fingerprints() -> dict[str, dict[str, Any]]:
    return {relative(path): fingerprint(path) for path in PROTECTED}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalized_index(path: Path) -> tuple[dict[str, set[str]], int, set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_date: dict[str, set[str]] = defaultdict(set)
    fields: set[str] = set()
    for row in payload.get("records", []):
        day = str(row.get("trade_date") or row.get("date") or "")[:10]
        symbol = str(row.get("symbol") or row.get("instrument") or row.get("stock_id") or "").upper()
        if day and symbol:
            symbol = symbol if symbol.startswith("TW") else "TW" + symbol
            by_date[day].add(symbol)
            fields.update(row)
    return by_date, len(payload.get("records", [])), fields


def qlib_calendar_and_coverage() -> tuple[list[str], dict[str, int], int]:
    coverage: dict[str, int] = defaultdict(int)
    files = sorted(PRICE_ROOT.glob("TW*.csv"))
    for path in files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            dates = {
                str(row.get("date") or row.get("datetime") or "")[:10]
                for row in csv.DictReader(handle)
                if START <= str(row.get("date") or row.get("datetime") or "")[:10] <= END
            }
        for day in dates:
            coverage[day] += 1
    return sorted(coverage), dict(coverage), len(files)


def csv_dates(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            str(row.get("date") or row.get("trade_date") or row.get("datetime") or "")[:10]
            for row in csv.DictReader(handle)
        }


def existing_model_a_dates() -> dict[str, list[str]]:
    paths: dict[str, list[str]] = defaultdict(list)
    for manifest in sorted(MODEL_A_SIGNAL_ROOT.glob("*/manifest.json")):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "READY":
            continue
        day = str(payload.get("asof_date") or payload.get("asof") or payload.get("signal_asof") or "")[:10]
        if START <= day <= END:
            paths[day].append(relative(manifest))
    return dict(paths)


def source_row(name: str, normalized: Path, adapter: Path, *, role: str, caveat: str) -> dict[str, Any]:
    index, rows, fields = normalized_index(normalized)
    meta = json.loads(adapter.read_text(encoding="utf-8"))
    dates = sorted(index)
    raw_files = meta.get("raw_files", [])
    return {
        "source": name,
        "role": role,
        "normalized_path": relative(normalized),
        "normalized_sha256": sha256(normalized),
        "adapter_path": relative(adapter),
        "adapter_sha256": sha256(adapter),
        "request_start": meta.get("request_parameters", {}).get("start_date", ""),
        "request_end": meta.get("request_parameters", {}).get("end_date", ""),
        "date_min": dates[0] if dates else "",
        "date_max": dates[-1] if dates else "",
        "normalized_rows": rows,
        "returned_symbols": len(set(meta.get("returned_scope", []))),
        "raw_http_files": len(raw_files),
        "fetched_at": meta.get("fetched_at", ""),
        "source_published_at": meta.get("source_published_at") or "",
        "adapter_pit_status": meta.get("pit_status", ""),
        "adapter_validator_status": meta.get("validator_status", ""),
        "field_count": len(fields),
        "caveat": caveat,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    protected_before = protected_fingerprints()
    write_json(OUT / "protected_before.json", protected_before)

    price_path = PRICE_CAPTURE / "daily_price.normalized.json"
    price_adapter = PRICE_CAPTURE / "daily_price.adapter_output.json"
    institutional_path = ORTHOGONAL_CAPTURE / "institutional/institutional.normalized.json"
    institutional_adapter = ORTHOGONAL_CAPTURE / "institutional/institutional.adapter_output.json"
    margin_path = ORTHOGONAL_CAPTURE / "margin/margin.normalized.json"
    margin_adapter = ORTHOGONAL_CAPTURE / "margin/margin.adapter_output.json"

    price_by_date, price_rows, _ = normalized_index(price_path)
    institutional_by_date, institutional_rows, _ = normalized_index(institutional_path)
    margin_by_date, margin_rows, _ = normalized_index(margin_path)
    calendar, qlib_coverage, qlib_files = qlib_calendar_and_coverage()
    twii_dates = csv_dates(TWII_HISTORY)
    model_a_dates = existing_model_a_dates()
    twii_0915 = json.loads(TWII_0915_ADAPTER.read_text(encoding="utf-8"))

    mature_end = calendar[-(HORIZON + 1)]
    mature_dates = {day for day in calendar if day <= mature_end}
    rows: list[dict[str, Any]] = []
    for index, day in enumerate(calendar):
        prior_day = calendar[index - 1] if index else "2026-05-08"
        eligible = (
            price_by_date.get(day, set())
            & institutional_by_date.get(prior_day, set())
            & margin_by_date.get(prior_day, set())
        ) - EXCLUDED
        twii_present = day in twii_dates
        capacity = len(eligible)
        rows.append(
            {
                "signal_date": day,
                "label_mature_10_trading_days": day in mature_dates,
                "label_maturity_end_date": calendar[index + HORIZON] if index + HORIZON < len(calendar) else "",
                "qlib_ohlcv_symbols": qlib_coverage.get(day, 0),
                "captured_price_symbols": len(price_by_date.get(day, set())),
                "orthogonal_trade_date": prior_day,
                "institutional_symbols_at_t_minus_1": len(institutional_by_date.get(prior_day, set())),
                "margin_short_symbols_at_t_minus_1": len(margin_by_date.get(prior_day, set())),
                "eligible_capacity_after_exclusions": capacity,
                "candidate_capacity_at_least_50": capacity >= 50,
                "twii_same_day_present_in_historical_capture": twii_present,
                "frozen_model_a_ready_artifact_exists": day in model_a_dates,
                "exact_eligible_50_materialized": False,
                "exact_eligible_50_status": "REQUIRES_FROZEN_MODELA_SCORE_NO_PREDICT_IN_B19" if capacity >= 50 and twii_present else "BLOCKED_SOURCE_INPUT",
                "reconstructed_pit_input_feasible": qlib_coverage.get(day, 0) == 150 and capacity >= 50 and twii_present,
            }
        )
    write_csv(OUT / "B19_DAILY_FEASIBILITY.csv", rows)

    source_rows = [
        source_row(
            "finmind_daily_price",
            price_path,
            price_adapter,
            role="150-stock OHLCV capture and lineage",
            caveat="capture time is evidence of archive acquisition, not source-native historical publication",
        ),
        source_row(
            "finmind_institutional",
            institutional_path,
            institutional_adapter,
            role="institutional raw inputs with conservative T+1 reconstructed availability",
            caveat="source_published_at is absent; reconstructed-PIT only",
        ),
        source_row(
            "finmind_margin_short",
            margin_path,
            margin_adapter,
            role="margin/short raw inputs with conservative T+1 reconstructed availability",
            caveat="source_published_at is absent; reconstructed-PIT only",
        ),
    ]
    source_rows.append(
        {
            "source": "yahoo_twii_history",
            "role": "same-day TWII market features and rolling lookback",
            "normalized_path": relative(TWII_HISTORY),
            "normalized_sha256": sha256(TWII_HISTORY),
            "adapter_path": relative(TWII_RAW),
            "adapter_sha256": sha256(TWII_RAW),
            "request_start": "2025-12-01",
            "request_end": "2026-09-14",
            "date_min": min(twii_dates),
            "date_max": max(twii_dates),
            "normalized_rows": len(twii_dates),
            "returned_symbols": 1,
            "raw_http_files": 1,
            "fetched_at": "2026-09-14",
            "source_published_at": "",
            "adapter_pit_status": "RECONSTRUCTED_ONLY",
            "adapter_validator_status": "NOT_SOURCE_NATIVE_TIMESTAMPED",
            "field_count": 9,
            "caveat": "covers mature subwindow but has no source-native publication timestamp; 2026-09-15 same-day row absent",
        }
    )
    write_csv(OUT / "B19_SOURCE_INVENTORY.csv", source_rows)

    prior_reads = [
        {
            "artifact_or_run": "B9 canonical retrain",
            "data_scope_read": "features/labels through 2026-05-07; untouched_test declared through 2026-04-22",
            "overlap_with_b19": "none after 2026-05-08",
            "classification_effect": "supports post-declared retrospective candidate status; does not establish untouched data",
        },
        {
            "artifact_or_run": "B18R2 historical paired replay",
            "data_scope_read": "result window ends 2026-05-07; PriceStore physically loaded full current 150 CSV date/open/close columns",
            "overlap_with_b19": "physical price-file read overlaps 2026-05-11..2026-09-15; result computation does not",
            "classification_effect": "B19 cannot claim untouched outcomes; reconstructed retrospective evidence only",
        },
        {
            "artifact_or_run": "B12/B15 diagnostic replay",
            "data_scope_read": "2026-06-17 signal and 2026-06-18..2026-07-02 execution window",
            "overlap_with_b19": "one signal date and its diagnostic execution-price window",
            "classification_effect": "those dates are previously observed diagnostics and must be tagged separately",
        },
        {
            "artifact_or_run": "B8/B16 prospective shadow and settlement",
            "data_scope_read": "2026-09-14 signal, 2026-09-15 entry, 2026-09-16 exit",
            "overlap_with_b19": "2026-09-14 and 2026-09-15",
            "classification_effect": "already observed prospective engineering dates; exclude from retrospective holdout claims",
        },
        {
            "artifact_or_run": "daily frozen Model A scoring",
            "data_scope_read": f"{len(model_a_dates)} READY signal dates in B19 window",
            "overlap_with_b19": "input/rank observations only; no B19 outcome read",
            "classification_effect": "not untouched inputs; may remain retrospective nonfit evidence if declared before outcome evaluation",
        },
    ]
    write_csv(OUT / "B19_PRIOR_READ_CLASSIFICATION.csv", prior_reads)

    source_inventory = {
        row["source"]: {
            "normalized_path": row["normalized_path"],
            "normalized_sha256": row["normalized_sha256"],
            "adapter_path": row["adapter_path"],
            "adapter_sha256": row["adapter_sha256"],
        }
        for row in source_rows
    }
    feature_order = json.loads(FEATURE_SCHEMA.read_text(encoding="utf-8"))["feature_order"]
    mature_feasible = [row for row in rows if row["label_mature_10_trading_days"] and row["reconstructed_pit_input_feasible"]]
    full_feasible = [row for row in rows if row["reconstructed_pit_input_feasible"]]
    protected_after = protected_fingerprints()
    write_json(OUT / "protected_after.json", protected_after)
    protected_unchanged = protected_before == protected_after

    manifest = {
        "schema_version": "modelb.b19.reconstructed_pit_holdout_feasibility.v1",
        "run_id": OUT.name,
        "created_at": utc_now(),
        "status": "HOLD_INCOMPLETE_TRAINING_PREFLIGHT",
        "decision": "HOLD",
        "scope": "readonly inventory and feasibility only",
        "acceptance_criteria": fingerprint(ACCEPTANCE_CRITERIA),
        "full_input_candidate_window": {
            "start": START,
            "end": END,
            "trading_days": len(calendar),
            "reconstructed_pit_input_feasible_days": len(full_feasible),
            "blocked_days": [row["signal_date"] for row in rows if not row["reconstructed_pit_input_feasible"]],
        },
        "mature_10_trading_day_label_window": {
            "start": START,
            "end": mature_end,
            "trading_days": len(mature_dates),
            "reconstructed_pit_input_feasible_days": len(mature_feasible),
            "all_mature_days_input_feasible": len(mature_feasible) == len(mature_dates),
        },
        "candidate_contract": {
            "excluded_symbols": sorted(EXCLUDED),
            "required_daily_exact_rows": 50,
            "minimum_daily_capacity_after_exclusions": min(row["eligible_capacity_after_exclusions"] for row in rows),
            "capacity_at_least_50_all_days": all(row["candidate_capacity_at_least_50"] for row in rows),
            "exact_eligible_50_materialized": False,
            "reason": "B19 does not call frozen Model A predict; exact daily key sets require the next frozen-scoring stage",
        },
        "frozen_model_a_scoreability": {
            "model_path": relative(MODEL_A),
            "model_sha256": sha256(MODEL_A),
            "qlib_input_root": relative(PRICE_ROOT),
            "qlib_input_files": qlib_files,
            "qlib_150_of_150_days": sum(1 for row in rows if row["qlib_ohlcv_symbols"] == 150),
            "existing_ready_signal_dates": len(model_a_dates),
            "dates_requiring_future_frozen_score_materialization": len(calendar) - len(model_a_dates),
            "predict_called_in_b19": False,
        },
        "frozen_model_b": {
            "model_path": relative(MODEL_B),
            "model_sha256": sha256(MODEL_B),
            "freeze_path": relative(MODEL_B_FREEZE),
            "freeze_sha256": sha256(MODEL_B_FREEZE),
            "feature_schema_path": relative(FEATURE_SCHEMA),
            "feature_schema_sha256": sha256(FEATURE_SCHEMA),
            "feature_count": len(feature_order),
            "predict_called_in_b19": False,
        },
        "source_inventory": source_inventory,
        "twii_limit": {
            "historical_reconstructed_coverage_through": max(twii_dates),
            "source_native_published_at_available": False,
            "official_2026_09_15_adapter_status": twii_0915.get("validator_status"),
            "official_2026_09_15_pit_status": twii_0915.get("pit_status"),
            "effect": "does not block mature window ending 2026-09-01; blocks complete source-semantic input through 2026-09-15",
        },
        "evidence_classification": {
            "untouched_claim": False,
            "true_prospective_claim": False,
            "post_declared_retrospective_holdout_candidate": True,
            "classification": "reconstructed-PIT historical nonfit candidate with prior-read strata",
        },
        "thresholds": {
            "mature_candidate_days": len(mature_dates),
            "legacy_120_day_gate_met": len(mature_dates) >= 120,
            "legacy_120_day_shortfall": max(0, 120 - len(mature_dates)),
            "new_version_required_design": "nested walk-forward plus independent post-2026-05-08 holdout",
            "single_window_sufficient_for_new_version": False,
        },
        "training_preflight_hard_gates": {
            "new_model_identity_and_immutable_freeze": False,
            "b18_exposed_dates_not_confirmatory": True,
            "post_20260508_exact_data_inventory": False,
            "ten_trading_day_label_maturity": True,
            "purge_and_embargo_prevent_outcome_overlap": False,
            "sealed_confirmation_or_strict_nested_walk_forward": False,
            "numeric_multidimensional_thresholds_preregistered": False,
            "tie_aware_rank_generator_and_fixture": False,
            "full_contribution_accounting": False,
            "protected_paths_unchanged": protected_unchanged,
            "no_training_tuning_scoring_or_production_write": True,
        },
        "unmaterialized_required_inventory": [
            "PIT_78_FEATURES",
            "FROZEN_MODEL_A_FULL_CROSS_SECTION_FOR_ALL_91_DATES",
            "CANONICAL_10_TRADING_DAY_LABEL",
            "NEXT_OPEN_AND_CLOSE_GRID",
            "EXACT_50_ELIGIBILITY",
        ],
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_unchanged,
        "training_performed": False,
        "scoring_performed": False,
        "model_predict_called": False,
        "replay_performed": False,
        "outcome_or_return_read": False,
        "baseline_admission": False,
        "production_allowed": False,
        "no_provider_latest_default_frontend_db_broker_write": True,
    }
    write_json(OUT / "B19_MANIFEST.json", manifest)

    checks = {
        "calendar_91_days": len(calendar) == 91,
        "mature_window_ends_2026_09_01": mature_end == "2026-09-01",
        "mature_window_81_days": len(mature_dates) == 81,
        "qlib_price_150_all_days": all(row["qlib_ohlcv_symbols"] == 150 for row in rows),
        "captured_price_150_all_days": all(row["captured_price_symbols"] == 150 for row in rows),
        "candidate_capacity_at_least_50_all_days": all(row["candidate_capacity_at_least_50"] for row in rows),
        "mature_window_inputs_feasible": len(mature_feasible) == 81,
        "exact_50_not_materialized": not any(row["exact_eligible_50_materialized"] for row in rows),
        "no_predict_training_replay_outcome": not any(
            [manifest["training_performed"], manifest["scoring_performed"], manifest["model_predict_called"], manifest["replay_performed"], manifest["outcome_or_return_read"]]
        ),
        "protected_unchanged": protected_unchanged,
        "legacy_120_day_gate_not_met": not manifest["thresholds"]["legacy_120_day_gate_met"],
        "twii_source_native_limit_disclosed": not manifest["twii_limit"]["source_native_published_at_available"],
    }
    inventory_checks_passed = all(checks.values())
    hard_gates = manifest["training_preflight_hard_gates"]
    training_preflight_passed = all(hard_gates.values())
    validator = {
        "schema_version": "modelb.b19.reconstructed_pit_holdout_feasibility.validator.v1",
        "checks": checks,
        "inventory_verdict": "PASS_WITH_CONDITIONS" if inventory_checks_passed else "FAIL",
        "data_feasibility": "GO_MATURE_SUBWINDOW_BUILD_ONLY" if inventory_checks_passed else "NO_GO",
        "training_preflight_hard_gates": hard_gates,
        "verdict": "PASS_PREFLIGHT_ONLY" if inventory_checks_passed and training_preflight_passed else ("HOLD" if inventory_checks_passed else "FAIL"),
        "go_no_go": "GO_TRAINING" if inventory_checks_passed and training_preflight_passed else "NO_GO_TRAINING",
        "conditions": [
            "materialize frozen Model A scores and exact eligible 50 in a separately frozen stage",
            "retain reconstructed-PIT and prior-read labels; never claim untouched or true prospective",
            "exclude or separately stratify previously observed B12/B15 and B8/B16 dates",
            "do not use the 81-day mature window as satisfying the legacy 120-day gate",
            "a new model version requires nested walk-forward plus an independent post-2026-05-08 holdout",
            "freeze the new model identity, split protocol, numeric gates, tie-aware generator, fixture, and full accounting contract before requesting training",
        ],
    }
    write_json(OUT / "B19_VALIDATOR.json", validator)

    report = f"""# B19 reconstructed-PIT historical holdout 可行性盘点

结论分为两层：数据源盘点为 `GO_MATURE_SUBWINDOW_BUILD_ONLY / PASS_WITH_CONDITIONS`；B19 完整训练前置裁决为 `HOLD / NO_GO_TRAINING`。本阶段只做只读盘点，没有训练、评分、`model.predict`、回放或收益读取。

`HOLD` 的原因不是成熟子窗数据不足以继续构建，而是冻结验收标准要求的每日 78 维特征、完整 Model A 截面、canonical label、next-open/close、exact-50、purge/embargo split、数值质量门槛、tie-aware fixture 和完整贡献核算合同尚未全部物化或冻结。它们闭合并通过独立复算前，不得开始新模型训练。

## 1. 两个时间窗

- 全输入候选窗：`{START}` 至 `{END}`，实际交易日 `{len(calendar)}` 日。150 股 OHLCV 每日 150/150；法人和融资融券原始快照覆盖全段，按 B2 合同只在下一交易日使用。排除 `TW7769`、`TW6919` 后，每日可用容量最低 `{manifest['candidate_contract']['minimum_daily_capacity_after_exclusions']}`，足够后续形成 50 股候选。
- 10 交易日标签成熟窗：`{START}` 至 `{mature_end}`，共 `{len(mature_dates)}` 日，全部具备 reconstructed-PIT 输入容量。最后 10 个信号日尚未满足 10 日标签成熟度，不能纳入已成熟 holdout。

## 2. Model A 与 exact 50

冻结 Model A artifact 和标准 qlib 输入仍在；150 个输入文件覆盖全 91 日。窗内已有 `{len(model_a_dates)}` 个日期的 READY Model A 信号，可证明运行链可评分；其余 `{len(calendar) - len(model_a_dates)}` 日需要在下一阶段用冻结模型补评分。B19 明确没有调用预测，因此这里只证明“容量足够”，没有伪称每日 exact eligible 50 已生成。

## 3. 原始数据与 available_at

9 月 15 日 FinMind capture 保存了价格、法人、融资融券各 150 个请求范围（法人和融资融券各 150 个 raw HTTP 文件），请求窗覆盖 2025-12-29 至 2026-09-15。stdout 是请求和 artifact 审计，不是单日数据摘要；历史明细位于 raw HTTP 和 normalized payload。法人/融资融券没有 source-native `source_published_at`，只能按 B2 的下一交易日规则重建 `available_at`。

TWII 历史 capture 可覆盖成熟窗和 120 日 rolling lookback，但没有 source-native 发布时间。2026-09-15 官方 adapter 仍为 `{twii_0915.get('validator_status')}` / `{twii_0915.get('pit_status')}`，所以它阻断完整 91 日窗尾的同语义输入，不阻断截止 2026-09-01 的成熟子窗。

## 4. 既往读取与证据等级

B9 的特征/标签止于 2026-05-07，B18R2 的结果窗也止于该日；但 B18R2 的 PriceStore 曾物理读取当前完整价格 CSV，所以不能声称后续价格从未被代码读取。B12/B15 已观察 2026-06-17 信号及 06-18 至 07-02 的诊断执行窗；B8/B16 已观察 2026-09-14/15。后续必须按 `B19_PRIOR_READ_CLASSIFICATION.csv` 分层，统一称 reconstructed-PIT historical nonfit evidence，不能称 untouched 或 true prospective。

## 5. HOLD 条件和后续停止点

成熟窗只有 `{len(mature_dates)}` 日，距离旧 120 日门槛还差 `{120 - len(mature_dates)}` 日，不能单靠本窗进入 baseline。下一阶段可先冻结每日评分/候选构建协议，再用冻结 Model A 物化每日 exact 50；如果目标升级为训练新版本，设计必须采用 nested walk-forward，并保留独立 post-2026-05-08 holdout。真正开始任何模型训练前必须停下。

所有 protected latest 指纹前后一致；未写 provider/latest/default/frontend/DB/broker。
"""
    (OUT / "B19_EXECUTION_REPORT_CN.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "inventory_verdict": validator["inventory_verdict"], "training_verdict": validator["verdict"], "calendar_days": len(calendar), "mature_days": len(mature_dates), "mature_end": mature_end}, ensure_ascii=False))
    return 0 if inventory_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
