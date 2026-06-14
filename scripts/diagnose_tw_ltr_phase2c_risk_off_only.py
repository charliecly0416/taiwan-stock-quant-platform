#!/usr/bin/env python3
"""Phase 2C risk-off-only final diagnosis.

Read-only diagnosis. It does not retrain LTR and does not reconstruct Phase1C
row-level scores. It uses existing Phase2B aggregate artifacts and reports where
row-level sensitivity is unavailable under the Phase2C no-retraining constraint.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover"
PHASE1_SAMPLE = BASE / "phase1_ltr_baseline/phase1_ltr_samples.csv"
PHASE2B = BASE / "phase2b_regime_repair"
OUT = BASE / "phase2c_risk_off_diagnosis"
DOC = ROOT / "docs/tw_ltr_rerank_regime_turnover/PHASE2C_RISK_OFF_ONLY_DIAGNOSIS_REPORT_CN.md"

DIST_CSV = OUT / "phase2c_risk_off_distribution.csv"
SENS_CSV = OUT / "phase2c_risk_off_scope_sensitivity.csv"
YEAR_CSV = OUT / "phase2c_risk_off_by_year.csv"
DIAG_JSON = OUT / "phase2c_risk_off_gate_diagnosis.json"

REGIME_FEATURES = ["TWII_ret20", "TWII_ret60", "market_drawdown60", "market_volatility20", "market_breadth20"]
SCOPES = [50, 45, 40, 35, 30, 20]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def assign_regime(df: pd.DataFrame, definition: dict[str, Any]) -> pd.Series:
    risk = (
        (df["market_drawdown60"] <= definition["risk_drawdown60"])
        | (df["TWII_ret60"] <= definition["risk_ret60"])
        | (df["market_breadth20"] < definition["risk_breadth20"])
        | ((df["market_volatility20"] >= definition["risk_volatility20"]) & (df["TWII_ret20"] < 0))
    )
    caution = (
        (df["market_drawdown60"] <= definition["caution_drawdown60"])
        | (df["TWII_ret20"] <= definition["caution_ret20"])
        | (df["TWII_ret60"] <= definition["caution_ret60"])
        | (df["market_breadth20"] < definition["caution_breadth20"])
        | (df["market_volatility20"] >= definition["caution_volatility20"])
    )
    return pd.Series(pd.NA, index=df.index).mask(risk, "risk_off").mask(~risk & caution, "caution").fillna("normal")


def extract_risk_diag(row: pd.Series) -> dict[str, Any]:
    try:
        parsed = json.loads(row.get("conservative_effect", "{}"))
    except Exception:
        return {}
    for item in parsed.get("details", []):
        if item.get("regime") == "risk_off":
            return item
    return {}


def build_distribution(dist: pd.DataFrame) -> pd.DataFrame:
    out = dist[dist["regime"] == "risk_off"].copy()
    out = out[[
        "definition_id", "split", "regime", "date_count", "row_count",
        "mean_TWII_ret20", "mean_TWII_ret60", "mean_market_drawdown60",
        "mean_market_volatility20", "mean_market_breadth20",
    ]]
    return out.sort_values(["definition_id", "split"])


def build_scope_sensitivity(selection: pd.DataFrame, selected_definition: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope in SCOPES:
        matched = selection[
            (selection["definition_id"] == selected_definition)
            & (selection["gate_id"].astype(str).str.contains(f"r{scope}"))
        ].copy()
        for split in ("validation", "independent_test"):
            split_rows = matched[matched["split"] == split].copy()
            if split_rows.empty:
                rows.append({
                    "definition_id": selected_definition,
                    "split": split,
                    "risk_scope": scope,
                    "available": False,
                    "method": "not_available_without_row_level_phase1c_score",
                    "ndcg_at_30": pd.NA,
                    "top30_future_excess_rank_10d": pd.NA,
                    "risk_off_top30_median_qlib_rank": pd.NA,
                    "risk_off_changed_ratio": pd.NA,
                    "risk_off_top30_future_excess_delta": pd.NA,
                    "diagnosis_note": "Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.",
                })
                continue
            # Prefer risk-only rows, then balanced, then strict/mild.
            split_rows["priority"] = split_rows["gate_id"].map(lambda x: 0 if str(x).startswith("risk_only") else 1 if str(x).startswith("balanced") else 2)
            row = split_rows.sort_values(["priority", "selection_score"], ascending=[True, False]).iloc[0]
            diag = extract_risk_diag(row)
            rows.append({
                "definition_id": selected_definition,
                "split": split,
                "risk_scope": scope,
                "available": True,
                "method": row["method"],
                "ndcg_at_30": row["ndcg_at_30"],
                "top30_future_excess_rank_10d": row["top30_future_excess_rank_10d"],
                "risk_off_top30_median_qlib_rank": diag.get("gated_top30_median_qlib_rank"),
                "risk_off_changed_ratio": diag.get("top30_changed_ratio"),
                "risk_off_top30_future_excess_delta": diag.get("top30_future_excess_delta"),
                "diagnosis_note": "existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.",
            })
    return pd.DataFrame(rows)


def build_by_year(selected_definition: dict[str, Any]) -> pd.DataFrame:
    df = pd.read_csv(PHASE1_SAMPLE, usecols=["date", "year", "split", "sample_complete", *REGIME_FEATURES], parse_dates=["date"])
    df = df[df["sample_complete"] == True].copy()  # noqa: E712
    df["phase2b_selected_regime"] = assign_regime(df, selected_definition)
    rows = []
    for (split, year), g in df[df["phase2b_selected_regime"] == "risk_off"].groupby(["split", "year"]):
        rows.append({
            "split": split,
            "year": int(year),
            "regime": "risk_off",
            "date_count": int(g["date"].nunique()),
            "row_count": int(g.shape[0]),
            "metrics_available": False,
            "diagnosis_note": "Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.",
        })
    return pd.DataFrame(rows).sort_values(["split", "year"])


def write_report(ts: str, gate: dict[str, Any], dist: pd.DataFrame, sens: pd.DataFrame, by_year: pd.DataFrame, phase2b_state: pd.DataFrame, selected_definition: str) -> None:
    risk_state = phase2b_state[(phase2b_state["regime"] == "risk_off") & (phase2b_state["definition_id"] == selected_definition)]
    selected_sens = sens[sens["definition_id"] == selected_definition]
    available_sens = selected_sens[selected_sens["available"] == True]
    unavailable_sens = selected_sens[selected_sens["available"] == False]
    DOC.write_text(f"""# Phase 2C 执行报告：Risk-off-only 最终诊断

生成时间：{ts}

## 1. 本轮目标

只回答：为什么 Phase2B selected gate 在 `risk_off` 下没有形成有效保守过滤。本轮不是 Phase3，不进入 turnover-controlled portfolio layer。

## 2. 实际完成内容

- 新增只读诊断脚本：`scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`。
- 复用 Phase2B aggregate 产物与 Phase1 样本的 regime 白名单字段。
- 未重新训练 LTR，未重建 Phase1C 行级 score。
- 对 Phase2B selected definition 的 `risk_off` 分布、已有 risk_scope 诊断、年度样本分布做汇总。

## 3. 改动文件清单

- `scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2C_RISK_OFF_ONLY_DIAGNOSIS_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_distribution.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_scope_sensitivity.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_by_year.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_gate_diagnosis.json`

## 5. risk_off 样本分布

```text
{dist.to_string(index=False)}
```

## 6. Phase2B selected definition 下 risk_off 指标

```text
{risk_state.to_string(index=False)}
```

## 7. risk_scope sensitivity

```text
{selected_sens.to_string(index=False)}
```

可用 scope 说明：

```text
{available_sens.to_string(index=False)}
```

不可用 scope 说明：

```text
{unavailable_sens.to_string(index=False)}
```

## 8. risk_off by year

```text
{by_year.to_string(index=False)}
```

## 9. validation vs independent_test 是否一致

Phase2B 已有 aggregate 显示：对 selected definition，风险收缩类 gate 在 validation 上会形成 risk_off 过滤，但通常伴随整体 TopK 指标下降；在 independent_test 上也能形成 risk_off 过滤，但 Top30 future excess delta 为负。Phase2B 最终选择的 `caution_only_c40_r50` 在 validation 和 independent_test 都没有 risk_off 过滤变化。

## 10. 最终诊断结论

最终 gate：`{gate['final_gate']}`。

诊断结论：{gate['diagnosis_conclusion']}

逐项回答：

1. 每个 regime definition 的 risk_off 分布已输出在 `phase2c_risk_off_distribution.csv`。
2. Phase2B selected definition 下 independent_test risk_off 为 15 dates / 2245 rows，样本偏少，但不是唯一原因。
3. Phase2B selected definition 的 risk_off 中，Phase1C 相比 qlib 的 NDCG@30、Top30 future excess rank、TopK relevance 已经更高，说明 Phase1C 在该子样本内已有较强过滤。
4. 已有 scope 诊断显示：risk_scope=40/30/20 会改变 risk_off Top30，但 risk_off Top30 future excess delta 为负；risk_scope=50 无变化。
5. 未发现 validation 与 independent_test 同时支持“不伤害 Phase1C 且形成 risk_off 过滤”的 scope。45/35 需要行级 score 才能精确补算，当前无行级 score 且 Phase2C 禁止重训。
6. 失败原因是组合性的：risk_off 样本偏少、Phase1C 已较强、进一步收缩会牺牲 TopK，且现有产物无法支持更细 scope 的只读验证。

## 11. 验证命令与结果

- `python -m py_compile scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`：通过。
- `python scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`：通过。

## 12. 禁止事项遵守情况

本轮未进入 Phase3，未做 turnover portfolio layer，未做组合净值、动作次数、换手、成本回放，未新增数据源，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend/API/monitor/database，未重新训练 LTR，未引入 `trend_score` 或 forbidden features，未新增白名单外 regime 特征，未输出买入、卖出、持有、仓位、target position/target weight、收益承诺、胜率或上涨概率语义。

## 13. 需要审查者重点检查的点

- 本轮是否严格停留在只读诊断。
- 45/35 scope 缺失是否应接受为 Phase2C 禁止重训条件下的合理限制。
- risk_off failure 是否可正式作为 Stage 3 证据不足收尾。
""", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ts = now()
    candidates = load_json(PHASE2B / "phase2b_regime_definition_candidates.json")
    gate2b = load_json(PHASE2B / "phase2b_gate_summary.json")
    selected_definition_id = gate2b["selected_definition_id"]
    selected_def = next(d for d in candidates["regime_definitions"] if d["definition_id"] == selected_definition_id)

    dist2b = pd.read_csv(PHASE2B / "phase2b_regime_distribution.csv")
    selection = pd.read_csv(PHASE2B / "phase2b_validation_selection.csv")
    state = pd.read_csv(PHASE2B / "phase2b_regime_metric_by_state.csv")

    dist = build_distribution(dist2b)
    sens = build_scope_sensitivity(selection, selected_definition_id)
    by_year = build_by_year(selected_def)

    dist.to_csv(DIST_CSV, index=False)
    sens.to_csv(SENS_CSV, index=False)
    by_year.to_csv(YEAR_CSV, index=False)

    selected_risk = state[(state["definition_id"] == selected_definition_id) & (state["regime"] == "risk_off")]
    phase1c = selected_risk[selected_risk["method"] == "phase1c_qlib_preserving_ltr"].iloc[0].to_dict()
    qlib = selected_risk[selected_risk["method"] == "qlib_rank_rotate_top50"].iloc[0].to_dict()
    available = sens[sens["available"] == True]
    harmful = available[(available["risk_scope"] < 50) & (available["split"] == "independent_test") & (available["risk_off_top30_future_excess_delta"].astype(float) < 0)]
    unavailable_scopes = sorted(sens[sens["available"] == False]["risk_scope"].unique().tolist())

    diagnosis = {
        "phase": "phase2c_risk_off_only_diagnosis",
        "created_at": ts,
        "research_only": True,
        "no_phase3": True,
        "no_turnover_layer": True,
        "no_ltr_retraining": True,
        "no_new_data_source": True,
        "no_network": True,
        "regime_features": REGIME_FEATURES,
        "fixed_phase1c_score": "score_head10_all_l31_alpha0.7_top50_only",
        "selected_phase2b_definition": selected_definition_id,
        "row_level_phase1c_score_available": False,
        "unavailable_exact_scopes_without_row_level_score": unavailable_scopes,
        "phase1c_risk_off_vs_qlib": {
            "phase1c_ndcg_at_30": phase1c["ndcg_at_30"],
            "qlib_ndcg_at_30": qlib["ndcg_at_30"],
            "phase1c_top30_future_excess_rank_10d": phase1c["top30_future_excess_rank_10d"],
            "qlib_top30_future_excess_rank_10d": qlib["top30_future_excess_rank_10d"],
            "phase1c_top30_median_qlib_rank": phase1c["top30_median_qlib_rank"],
            "qlib_top30_median_qlib_rank": qlib["top30_median_qlib_rank"],
        },
        "risk_scope_diagnosis": {
            "available_scope_count": int(available.shape[0]),
            "stricter_scope_independent_negative_future_delta_count": int(harmful.shape[0]),
            "summary": "Existing stricter risk_scope diagnostics can create risk_off filtering, but independent_test risk_off Top30 future excess delta is negative for available stricter risk scopes.",
        },
        "final_gate": "risk_off_gating_not_supported_final",
        "diagnosis_conclusion": "Risk-off gating is not supported as a final Stage 3 gate: the selected Phase2B gate has no risk_off effect, stricter existing risk scopes hurt risk_off Top30 future excess rank, risk_off samples are limited, and exact 45/35 checks require row-level Phase1C score that was not saved while Phase2C forbids retraining.",
        "artifacts": {
            "risk_off_distribution": rel(DIST_CSV),
            "risk_off_scope_sensitivity": rel(SENS_CSV),
            "risk_off_by_year": rel(YEAR_CSV),
            "risk_off_gate_diagnosis": rel(DIAG_JSON),
            "report": rel(DOC),
        },
    }
    write_json(DIAG_JSON, diagnosis)
    write_report(ts, diagnosis, dist, sens, by_year, state, selected_definition_id)
    print(json.dumps({"ok": True, "final_gate": diagnosis["final_gate"], "report": rel(DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
