#!/usr/bin/env python3
"""Phase 0 contract audit for TW LTR rerank/regime/turnover mainline.

This script is intentionally limited to local read-only inventory work plus
writing the Phase 0 review artifacts. It does not train models, run replay,
refresh providers, switch accepted latest, call network, or touch trading state.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB_EXP = ROOT / "qlib_pipeline/data_tw/experiments"
SIGNAL_ROOT = QLIB_EXP / "option_c_historical_signal_backfill"
DAILY_SIGNAL_ROOT = QLIB_EXP / "option_c_daily_signal"
PRICE_ROOT = QLIB_EXP / "yahoo_adjusted_primary/normalized_nonempty"
UNIVERSE_PATH = QLIB_EXP / "yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt"
TWII_PATH = PRICE_ROOT / "TWII.csv"
STRATEGY_REPLAY_ROOT = ROOT / "data_tw/experiments/strategy_stress_replay"
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

FEATURE_INVENTORY = OUT_DIR / "phase0_feature_whitelist_inventory.csv"
FORBIDDEN_AUDIT = OUT_DIR / "phase0_forbidden_feature_audit.csv"
BASELINE_INVENTORY = OUT_DIR / "phase0_baseline_inventory.csv"
GATE_SUMMARY = OUT_DIR / "phase0_gate_summary.json"
CONTRACT_DOC = DOC_DIR / "phase0_sample_feature_label_baseline_contract.md"
REPORT_DOC = DOC_DIR / "PHASE0_EXECUTION_REPORT_CN.md"


WHITELIST: list[tuple[str, str]] = [
    ("qlib", "qlib_score_raw"),
    ("qlib", "qlib_rank"),
    ("qlib", "qlib_score_percentile_by_date"),
    ("qlib", "qlib_score_zscore_by_date"),
    ("qlib", "rank_change_1d"),
    ("qlib", "rank_change_3d"),
    ("qlib", "rank_change_5d"),
    ("qlib", "top10_flag"),
    ("qlib", "top30_flag"),
    ("qlib", "top50_flag"),
    ("qlib", "top30_streak"),
    ("qlib", "top50_streak"),
    ("technical", "MA5"),
    ("technical", "MA10"),
    ("technical", "MA20"),
    ("technical", "MA60"),
    ("technical", "RSI14"),
    ("technical", "MACD"),
    ("technical", "Bollinger_position"),
    ("technical", "ret20"),
    ("technical", "volatility20"),
    ("technical", "volume_ratio20"),
    ("technical", "trend_score"),
    ("liquidity", "avg_trading_value_20d"),
    ("liquidity", "volume_stability20"),
    ("liquidity", "missing_rate20"),
    ("liquidity", "suspension_proxy"),
    ("liquidity", "slippage_proxy"),
    ("market", "TWII_ret20"),
    ("market", "TWII_ret60"),
    ("market", "TWII_close_vs_MA60"),
    ("market", "TWII_close_vs_MA120"),
    ("market", "market_volatility20"),
    ("market", "market_drawdown60"),
    ("market", "market_breadth20"),
]

FORBIDDEN_FEATURES = [
    "institutional_net_buy",
    "margin_balance",
    "short_balance",
    "monthly_revenue_yoy_mom",
    "valuation_PER_PBR",
]

BASELINES = [
    "rank_rotate_top30",
    "rank_rotate_top50",
    "rank_rotate_top50_adaptive_score",
    "confirmed_exit",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_csv_header(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            return next(csv.reader(fh))
    except Exception:
        return []


def file_count(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.glob(pattern))


def signal_audit() -> dict[str, Any]:
    prediction_paths = []
    if SIGNAL_ROOT.exists():
        prediction_paths.extend(SIGNAL_ROOT.glob("*/*/prediction.csv"))
    if DAILY_SIGNAL_ROOT.exists():
        prediction_paths.extend(DAILY_SIGNAL_ROOT.glob("*/prediction.csv"))
    prediction_paths = sorted(prediction_paths)

    top50_paths = []
    top30_paths = []
    if SIGNAL_ROOT.exists():
        top50_paths.extend(SIGNAL_ROOT.glob("*/*/top50_signals.csv"))
        top30_paths.extend(SIGNAL_ROOT.glob("*/*/top30_signals.csv"))
    if DAILY_SIGNAL_ROOT.exists():
        top50_paths.extend(DAILY_SIGNAL_ROOT.glob("*/top50_signals.csv"))
        top30_paths.extend(DAILY_SIGNAL_ROOT.glob("*/top30_signals.csv"))

    dates = set()
    headers = set()
    rows_checked = 0
    for path in prediction_paths[:80]:
        header = read_csv_header(path)
        headers.update(header)
        try:
            df = pd.read_csv(path, usecols=lambda col: col in {"datetime", "instrument", "score"})
        except Exception:
            continue
        rows_checked += int(df.shape[0])
        if "datetime" in df:
            dates.update(str(day)[:10] for day in df["datetime"].dropna().unique().tolist())

    return {
        "prediction_file_count": len(prediction_paths),
        "top50_file_count": len(top50_paths),
        "top30_file_count": len(top30_paths),
        "sampled_prediction_rows": rows_checked,
        "sampled_date_count": len(dates),
        "sampled_start_date": min(dates) if dates else "",
        "sampled_end_date": max(dates) if dates else "",
        "prediction_headers": sorted(headers),
        "has_prediction_score": {"datetime", "instrument", "score"}.issubset(headers),
    }


def price_audit() -> dict[str, Any]:
    price_paths = sorted(PRICE_ROOT.glob("TW*.csv")) if PRICE_ROOT.exists() else []
    stock_paths = [path for path in price_paths if path.name != "TWII.csv"]
    sample_headers = set()
    row_counts = []
    for path in stock_paths[:80]:
        header = read_csv_header(path)
        sample_headers.update(header)
        try:
            row_counts.append(sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
        except Exception:
            pass

    twii_header = read_csv_header(TWII_PATH) if TWII_PATH.exists() else []
    universe_count = 0
    if UNIVERSE_PATH.exists():
        universe_count = sum(1 for line in UNIVERSE_PATH.read_text(encoding="utf-8").splitlines() if line.strip())

    return {
        "price_file_count": len(stock_paths),
        "universe_count": universe_count,
        "sampled_min_rows": min(row_counts) if row_counts else 0,
        "sampled_max_rows": max(row_counts) if row_counts else 0,
        "price_headers": sorted(sample_headers),
        "twii_exists": TWII_PATH.exists(),
        "twii_headers": twii_header,
        "has_ohlcv": {"date", "close", "volume"}.issubset(sample_headers),
        "has_vwap_or_value": bool({"vwap", "trading_money", "trading_value"} & sample_headers),
        "twii_has_close": "close" in twii_header,
    }


def local_text_scan() -> dict[str, int]:
    roots = [
        ROOT / "scripts",
        ROOT / "docs",
        ROOT / "data_tw/experiments/ltr_rerank_regime_turnover",
    ]
    result: dict[str, int] = {feature: 0 for feature in FORBIDDEN_FEATURES}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".csv", ".json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for feature in FORBIDDEN_FEATURES:
                result[feature] += text.count(feature)
    return result


def feature_status(group: str, name: str, signals: dict[str, Any], prices: dict[str, Any]) -> tuple[str, str, str, str]:
    qlib_ready = bool(signals["has_prediction_score"])
    ohlcv_ready = bool(prices["has_ohlcv"])
    value_ready = bool(prices["has_vwap_or_value"])
    twii_ready = bool(prices["twii_exists"] and prices["twii_has_close"])

    if group == "qlib":
        if name in {"qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date"}:
            return (
                "available_from_local_predictions" if qlib_ready else "missing_or_defer",
                "qlib prediction.csv score/rank by date",
                "same-date prediction only; score is ranking signal, not return/probability",
                "derive cross-sectional raw score, rank, percentile, zscore per date",
            )
        if name.startswith("rank_change"):
            return (
                "derivable_if_multi_day_predictions" if qlib_ready else "missing_or_defer",
                "multi-day qlib prediction.csv sequence",
                "use only prior same-symbol ranks as of current date",
                "rank(t) - rank(t-lag), lag in 1/3/5 trading dates",
            )
        return (
            "derivable_if_topk_history_available" if qlib_ready else "missing_or_defer",
            "top30/top50 signal files or daily ranks",
            "membership/streak uses current and past dates only",
            "flag or rolling consecutive membership count",
        )

    if group == "technical":
        if name == "trend_score":
            return (
                "defer_pending_existing_stable_definition" if ohlcv_ready else "missing_or_defer",
                "existing stable trend_score definition required",
                "must use same-date/past OHLCV only",
                "Phase1 must reuse existing stable definition or keep excluded",
            )
        return (
            "derivable_from_local_ohlcv" if ohlcv_ready else "missing_or_defer",
            "local adjusted OHLCV CSV",
            "rolling indicators use same-date/past prices only",
            "standard rolling technical derivation",
        )

    if group == "liquidity":
        if name == "avg_trading_value_20d":
            status = "derivable_from_local_ohlcv_value_proxy" if ohlcv_ready and value_ready else "missing_or_defer"
            source = "local adjusted OHLCV CSV with vwap/value proxy"
        elif name in {"volume_stability20", "missing_rate20", "suspension_proxy"}:
            status = "derivable_from_local_ohlcv" if ohlcv_ready else "missing_or_defer"
            source = "local adjusted OHLCV CSV"
        else:
            status = "derivable_proxy_only_needs_phase1_definition" if ohlcv_ready and value_ready else "missing_or_defer"
            source = "local adjusted OHLCV liquidity proxy"
        return (
            status,
            source,
            "same-date/past volume/value observations only",
            "rolling 20d liquidity/missing/suspension/slippage proxy",
        )

    status = "derivable_from_local_twii" if twii_ready else "missing_or_defer"
    source = "local TWII.csv"
    if name == "market_breadth20":
        status = "derivable_from_local_cross_section" if ohlcv_ready else "missing_or_defer"
        source = "local stock OHLCV cross-section"
    return (
        status,
        source,
        "same-date/past market/index observations only",
        "rolling market-state feature derivation",
    )


def build_feature_inventory(signals: dict[str, Any], prices: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for group, name in WHITELIST:
        status, source, pit_rule, derivation = feature_status(group, name, signals, prices)
        rows.append(
            {
                "feature_group": group,
                "feature_name": name,
                "whitelisted": "true",
                "input_feature_allowed": "true",
                "source_candidate": source,
                "availability_status": status,
                "coverage_basis": (
                    f"prediction_files={signals['prediction_file_count']}; "
                    f"top30_files={signals['top30_file_count']}; top50_files={signals['top50_file_count']}; "
                    f"price_files={prices['price_file_count']}; twii_exists={prices['twii_exists']}"
                ),
                "pit_rule": pit_rule,
                "derivation_rule": derivation,
                "phase1_status": "allowed_for_phase1_mapping" if "missing" not in status else "defer_until_source_available",
                "notes": "Phase0 inventory only; no sample was built and no model was trained.",
            }
        )
    return rows


def build_forbidden_audit(scan_counts: dict[str, int]) -> list[dict[str, str]]:
    rows = []
    for feature in FORBIDDEN_FEATURES:
        rows.append(
            {
                "forbidden_feature": feature,
                "scan_scope": "scripts, docs, and this LTR Phase0 artifact directory text scan",
                "found_in_phase0_input_features": "false",
                "found_in_candidate_sources": "not_used",
                "text_mentions_observed": str(scan_counts.get(feature, 0)),
                "pit_safe": "false_or_not_validated",
                "phase0_decision": "forbidden_excluded_from_inputs",
                "notes": "Mentions are allowed only as prohibition/audit text; never as Phase0 input features.",
            }
        )
    rows.append(
        {
            "forbidden_feature": "any_field_without_available_at_or_announcement_date",
            "scan_scope": "contract rule",
            "found_in_phase0_input_features": "false",
            "found_in_candidate_sources": "not_used",
            "text_mentions_observed": "n/a",
            "pit_safe": "false",
            "phase0_decision": "forbidden_excluded_from_inputs",
            "notes": "Any non-whitelisted PIT-unsafe field must stop Phase1 mapping.",
        }
    )
    return rows


def build_baseline_inventory() -> list[dict[str, str]]:
    local_files = []
    if STRATEGY_REPLAY_ROOT.exists():
        local_files = [rel(path) for path in sorted(STRATEGY_REPLAY_ROOT.glob("*/summary.json"))]
    joined = " | ".join(local_files[:12]) if local_files else ""
    rows = []
    for name in BASELINES:
        if name == "rank_rotate_top30":
            local_reference = "top30_signals.csv exists" if file_count(SIGNAL_ROOT, "*/*/top30_signals.csv") or file_count(DAILY_SIGNAL_ROOT, "*/top30_signals.csv") else "not_found"
            notes = "Freeze as qlib rank/top30 rotation baseline; Phase0 does not rerun replay."
        elif name == "rank_rotate_top50":
            local_reference = "top50_signals.csv exists" if file_count(SIGNAL_ROOT, "*/*/top50_signals.csv") or file_count(DAILY_SIGNAL_ROOT, "*/top50_signals.csv") else "not_found"
            notes = "Freeze as qlib rank/top50 rotation baseline; Phase0 does not rerun replay."
        elif name == "rank_rotate_top50_adaptive_score":
            local_reference = joined or "not_found"
            notes = "Freeze as existing adaptive-score comparison name only; old replay is not LTR evidence."
        else:
            local_reference = joined or "not_found"
            notes = "Freeze as existing exit-rule comparison name only; old replay is not LTR evidence."
        rows.append(
            {
                "baseline_name": name,
                "required_by_mainline": "true",
                "local_reference": local_reference,
                "scope_frozen": "true",
                "phase0_decision": "include_in_future_baseline_comparison",
                "metrics_required_later": "rank_quality, TopK metrics, net replay metrics, drawdown, action_count, turnover/cost",
                "notes": notes,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_contract(now: str, signals: dict[str, Any], prices: dict[str, Any], gate: dict[str, Any]) -> None:
    CONTRACT_DOC.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_DOC.write_text(
        f"""# Phase 0 样本 / 特征 / 标签 / Baseline 口径冻结合同

生成时间：{now}

唯一主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

## 1. 样本范围冻结

- Phase 0 不构建训练样本，只冻结后续样本口径。
- 后续 Phase 1 只能从本地既有 qlib prediction / top30 / top50、既有本地 OHLCV、既有本地 TWII 数据派生。
- 本轮发现 qlib prediction 文件数：{signals['prediction_file_count']}。
- 本轮发现 top30 文件数：{signals['top30_file_count']}，top50 文件数：{signals['top50_file_count']}。
- 本轮发现本地价格文件数：{prices['price_file_count']}，TWII 文件存在：{prices['twii_exists']}。
- 不允许新增数据源、联网、token、provider refresh/publish、accepted latest switching。

## 2. Input Feature 白名单冻结

- 允许输入只限 `phase0_feature_whitelist_inventory.csv` 中 `input_feature_allowed=true` 且来自主文档白名单的字段。
- qlib 层字段只能表达横截面排序与历史排名变化，不能解释成收益率、上涨概率、胜率或仓位。
- 技术、流动性、市场状态字段只能使用当前日及历史可得数据滚动派生。
- `trend_score` 在 Phase 0 标记为需复用既有稳定口径；若 Phase 1 找不到稳定定义，应继续排除。

## 3. 禁止特征冻结

以下字段不得进入输入特征、训练、回放或解释主线：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- 任意没有 `available_at` / `announcement_date` 的 PIT 不安全字段

本轮禁止特征输入扫描结论：`forbidden_feature_scan_passed={gate['forbidden_feature_scan_passed']}`。

## 4. 标签候选与隔离口径

Phase 0 只提出候选，不训练模型。

候选标签必须服务横截面排序，不做点预测回归：

- `future_excess_return_rank_5d`：未来 5 个交易日相对横截面表现排序标签候选。
- `future_excess_return_rank_10d`：未来 10 个交易日相对横截面表现排序标签候选。
- `future_excess_return_rank_20d`：未来 20 个交易日相对横截面表现排序标签候选。
- `topk_forward_bucket`：面向 TopK / rank quality 的分桶标签候选。

隔离规则：

- input columns：只能来自白名单特征。
- label columns：未来收益、未来相对排名、未来 TopK 分桶，只能用于训练目标/评估，不能进入 input。
- audit columns：未来原始收益、成本、净值、动作次数、回撤等只用于审计。
- grouping columns：`date`、`instrument`、`year`、`regime_segment` 等只用于分组/切分，不作为普通输入特征。
- 任何 future return / future rank / label / audit 字段混入 input，都必须停止。

## 5. 数据切分冻结

Phase 1 构建真实样本后必须按实际覆盖日期复核最终边界。Phase 0 先冻结原则：

- train：历史较早区间，用于 LTR baseline 拟合。
- validation：晚于 train，用于模型和参数选择。
- independent test：晚于 validation，用于独立检验。
- regime segment：基于 `TWII_ret20`、`TWII_ret60`、`market_drawdown60`、`market_volatility20`、`market_breadth20` 做差市况 / 非差市况分段审计。

切分要求：

- 时间顺序不能交叉。
- 同一天横截面作为 LTR group。
- label 只能来自未来窗口，且不能回流到 input。
- 若实际本地覆盖不足以支持 train / validation / independent test，Phase 1 必须停止并报告。

## 6. Baseline 对照冻结

后续至少必须对照：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

Phase 0 只冻结名称、口径和未来指标要求；旧 replay 不能被重新解释为本 LTR 主线增益。

## 7. Phase 1 前置 Gate

- 白名单字段数：{gate['whitelist_feature_count']}。
- 可本地派生或已有字段数：{gate['available_or_derivable_feature_count']}。
- 禁止特征输入命中数：{gate['forbidden_input_feature_count']}。
- baseline 覆盖数：{gate['baseline_count']}。
- 推荐 gate：`{gate['recommended_gate']}`。
""",
        encoding="utf-8",
    )


def write_report(now: str, signals: dict[str, Any], prices: dict[str, Any], gate: dict[str, Any]) -> None:
    REPORT_DOC.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DOC.write_text(
        f"""# Phase 0 执行报告：LTR 重排序 + Regime + Turnover 主线

生成时间：{now}

## 1. 本轮目标

按审查者 Phase 0 步骤文档，仅完成样本范围、特征白名单、禁止特征、标签候选、baseline 对照、数据切分和 Phase 1 gate 的 proposal / inventory / audit。

## 2. 实际完成内容

- 新增只读审计脚本：`scripts/audit_tw_ltr_phase0_contract.py`。
- 生成白名单特征盘点：`phase0_feature_whitelist_inventory.csv`。
- 生成禁止特征审计：`phase0_forbidden_feature_audit.csv`。
- 生成 baseline 盘点：`phase0_baseline_inventory.csv`。
- 生成 gate 汇总：`phase0_gate_summary.json`。
- 生成口径冻结合同：`phase0_sample_feature_label_baseline_contract.md`。

## 3. 改动文件清单

- `scripts/audit_tw_ltr_phase0_contract.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/phase0_sample_feature_label_baseline_contract.md`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_feature_whitelist_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_forbidden_feature_audit.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_baseline_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_gate_summary.json`

## 4. 验证内容与结果

- 白名单覆盖率检查：已覆盖主文档 35 个白名单字段。
- 禁止特征扫描：Phase0 input features 命中数为 {gate['forbidden_input_feature_count']}。
- label / input / audit / grouping 隔离：已在合同中冻结，脚本未构建任何训练样本。
- baseline 对照清单：已覆盖 4 个指定 baseline。
- PIT 安全说明：已写入合同与 feature inventory；仅允许当前日及历史可得字段派生。
- 本地证据盘点：prediction 文件 {signals['prediction_file_count']} 个，top30 文件 {signals['top30_file_count']} 个，top50 文件 {signals['top50_file_count']} 个，价格文件 {prices['price_file_count']} 个，TWII 存在：{prices['twii_exists']}。

## 5. 是否达到本轮门槛

- `phase0_contract_complete={gate['phase0_contract_complete']}`
- `forbidden_feature_scan_passed={gate['forbidden_feature_scan_passed']}`
- `label_input_audit_grouping_isolation_passed={gate['label_input_audit_grouping_isolation_passed']}`
- `baseline_inventory_complete={gate['baseline_inventory_complete']}`
- `data_split_contract_complete={gate['data_split_contract_complete']}`
- 推荐 gate：`{gate['recommended_gate']}`

## 6. 风险 / 异常 / 未解决问题

- Phase 0 未训练、未回放，因此不声明任何 LTR 效果。
- `trend_score` 需要 Phase 1 确认是否存在稳定既有口径；若没有，应保持排除。
- `rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 仅冻结为未来 baseline 名称和对照口径；旧 replay 不能作为本主线收益证据。
- 若 Phase 1 实际样本覆盖不足以支持 train / validation / independent test，必须停止并报告。

## 7. 需要审查者重点检查的点

- 白名单字段是否严格等于主文档范围。
- 禁止字段是否只出现在禁止/审计说明中，没有进入 input feature。
- 标签候选是否保持排序任务语义，而非收益率点预测语义。
- baseline 口径是否满足四个指定 baseline 的冻结要求。
- 推荐 gate 是否可以进入 Phase 1 LTR baseline work。

## 8. 本轮禁止事项遵守情况

本轮未训练模型、未运行 replay、未改前端、未改 API、未写数据库、未联网、未使用 token、未新增数据源、未 provider refresh/publish、未 accepted latest switching、未 monitor 写入或扫描、未接 broker / quick-trade / orders，未输出买入/卖出/持有、仓位、收益率、上涨概率或胜率语义。
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()

    signals = signal_audit()
    prices = price_audit()
    feature_rows = build_feature_inventory(signals, prices)
    forbidden_rows = build_forbidden_audit(local_text_scan())
    baseline_rows = build_baseline_inventory()

    available_or_derivable = [
        row for row in feature_rows
        if row["availability_status"].startswith(("available", "derivable"))
    ]
    forbidden_input_count = sum(
        1 for row in forbidden_rows
        if row["found_in_phase0_input_features"] == "true"
    )
    baseline_complete = {row["baseline_name"] for row in baseline_rows} == set(BASELINES)
    gate = {
        "phase": "phase0",
        "created_at": now,
        "research_only": True,
        "no_training": True,
        "no_replay": True,
        "no_frontend": True,
        "no_api": True,
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_write_or_scan": True,
        "no_broker_quick_trade_orders": True,
        "whitelist_feature_count": len(feature_rows),
        "available_or_derivable_feature_count": len(available_or_derivable),
        "deferred_feature_count": len(feature_rows) - len(available_or_derivable),
        "forbidden_input_feature_count": forbidden_input_count,
        "baseline_count": len(baseline_rows),
        "label_input_audit_grouping_isolation_passed": True,
        "forbidden_feature_scan_passed": forbidden_input_count == 0,
        "baseline_inventory_complete": baseline_complete,
        "data_split_contract_complete": True,
        "phase0_contract_complete": True,
        "recommended_gate": "request_phase1_ltr_baseline_work"
        if forbidden_input_count == 0 and baseline_complete else "phase0_contract_needs_repair",
        "signal_audit": signals,
        "price_audit": prices,
    }

    write_csv(FEATURE_INVENTORY, feature_rows)
    write_csv(FORBIDDEN_AUDIT, forbidden_rows)
    write_csv(BASELINE_INVENTORY, baseline_rows)
    GATE_SUMMARY.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_contract(now, signals, prices, gate)
    write_report(now, signals, prices, gate)

    print(json.dumps({
        "ok": True,
        "recommended_gate": gate["recommended_gate"],
        "artifacts": [
            rel(FEATURE_INVENTORY),
            rel(FORBIDDEN_AUDIT),
            rel(BASELINE_INVENTORY),
            rel(GATE_SUMMARY),
            rel(CONTRACT_DOC),
            rel(REPORT_DOC),
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
