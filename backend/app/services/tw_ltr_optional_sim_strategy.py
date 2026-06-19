"""Readonly LTR baseline product-closure payload presenter."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class TWLTROptionalSimStrategyService:
    """Build a minimal readonly product view from Phase B1/B1B artifacts with split-aware wording."""

    out_dir = Path("data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay")
    period_comparison_path = out_dir / "phaseb1_period_comparison.csv"
    method_summary_path = out_dir / "phaseb1_method_summary.csv"
    gate_path = out_dir / "phaseb1_gate_summary.json"
    boundary_text = "仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。"

    strategy_labels = {
        "phase1c_ltr_simple_daily": "LTR simple 默认主策略",
        "rank_rotate_top50_adaptive_score": "Top50 自适应规则参考",
        "phase1c_ltr_conservative_top30_2day_confirm_daily": "LTR Top30 连续确认",
        "phase1c_ltr_conservative_top20_entry_2day_exit_daily": "LTR Top20 严格入选",
    }

    strategy_roles = {
        "phase1c_ltr_simple_daily": "default_main_strategy",
        "rank_rotate_top50_adaptive_score": "rule_based_reference",
        "phase1c_ltr_conservative_top30_2day_confirm_daily": "conservative_reference",
        "phase1c_ltr_conservative_top20_entry_2day_exit_daily": "conservative_reference",
    }

    strategy_status_labels = {
        "phase1c_ltr_simple_daily": "默认 / 独立测试较强 / 动作较多",
        "rank_rotate_top50_adaptive_score": "规则简单 / 换手略低",
        "phase1c_ltr_conservative_top30_2day_confirm_daily": "保守 / 低动作 / 低换手",
        "phase1c_ltr_conservative_top20_entry_2day_exit_daily": "更严格入选 / 低动作",
    }

    strategy_notes = {
        "phase1c_ltr_simple_daily": "在固定候选的独立测试区间表现较强，动作和换手略高；历史混合区间只作复盘参考。",
        "rank_rotate_top50_adaptive_score": "规则更容易理解；独立测试区间表现低于默认 LTR，但动作和换手略低。",
        "phase1c_ltr_conservative_top30_2day_confirm_daily": "连续确认后才动作；独立测试区间表现低于默认 LTR，但动作明显更少。",
        "phase1c_ltr_conservative_top20_entry_2day_exit_daily": "入选更严格，动作明显更少，作为低频参考；历史混合区间不代表未来收益。",
    }

    def __init__(self, out_dir: str | Path | None = None):
        if out_dir is not None:
            self.out_dir = Path(out_dir)
            self.period_comparison_path = self.out_dir / "phaseb1_period_comparison.csv"
            self.method_summary_path = self.out_dir / "phaseb1_method_summary.csv"
            self.gate_path = self.out_dir / "phaseb1_gate_summary.json"

    def product_view(self) -> dict[str, Any]:
        missing = [
            str(path)
            for path in (self.period_comparison_path, self.method_summary_path, self.gate_path)
            if not path.exists()
        ]
        if missing:
            return self._missing_artifact_view(missing)
        period_rows = self._read_csv(self.period_comparison_path)
        summary_rows = self._read_csv(self.method_summary_path)
        gate = self._read_json(self.gate_path)
        methods = [
            "phase1c_ltr_simple_daily",
            "rank_rotate_top50_adaptive_score",
            "phase1c_ltr_conservative_top30_2day_confirm_daily",
            "phase1c_ltr_conservative_top20_entry_2day_exit_daily",
        ]
        return {
            "ok": True,
            "schema_version": "phaseb2_ltr_simple_default_readonly_product_view_v1",
            "payload_source": "phaseb1_conservative_replay_artifacts",
            "default_method_key": "phase1c_ltr_simple_daily",
            "boundary_text": self.boundary_text,
            "selection_policy": {
                "default_selected": True,
                "ltr_auto_enabled": False,
                "ltr_simple_default": True,
                "top50_adaptive_reference_only": True,
                "readonly_only": True,
            },
            "strategies": [self._strategy_view(method, period_rows, summary_rows) for method in methods],
            "caveats": [
                "默认展示主要依据 phase1c_independent_test_range 的固定候选同口径比较，不代表未来表现。",
                "common full range 包含 train / validation / independent_test，只能作为历史复盘明细，不能作为样本外泛化证据。",
                "LTR simple 在独立测试区间表现较强，但动作和换手略高，页面必须同时展示频率标签。",
                "independent_test 已用于产品默认决策，因此不能再作为未触碰的最终检验集或未来保证。",
                "Top50 adaptive 是规则型参考，不再表述为量化效果更优。",
                "两个保守候选只作为低动作、低换手参考。",
            ],
            "no_write_guarantees": {
                "read_only_http_method": True,
                "reads_static_artifacts_only": True,
                "does_not_change_runtime_state": True,
                "does_not_trigger_data_refresh": True,
                "does_not_switch_accepted_pointer": True,
                "does_not_touch_monitor_or_execution_paths": True,
                "does_not_touch_broker_or_orders": True,
            },
            "phaseb1_gate": gate.get("recommended_gate"),
            "phaseb2_gate_basis": "phaseb1b_repaired_request_phaseb2_ltr_simple_default_design",
            "research_only": True,
        }

    def _missing_artifact_view(self, missing_paths: list[str]) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "artifact_missing",
            "schema_version": "phaseb2_ltr_simple_default_readonly_product_view_v1",
            "payload_source": "phaseb1_conservative_replay_artifacts",
            "default_method_key": "phase1c_ltr_simple_daily",
            "boundary_text": self.boundary_text,
            "selection_policy": {
                "default_selected": False,
                "ltr_auto_enabled": False,
                "ltr_simple_default": False,
                "top50_adaptive_reference_only": True,
                "readonly_only": True,
            },
            "strategies": [],
            "caveats": [
                "历史可选模拟策略产物未找到；页面保持只读空态，不触发任何数据刷新或写入。",
            ],
            "missing_artifacts": missing_paths,
            "no_write_guarantees": {
                "read_only_http_method": True,
                "reads_static_artifacts_only": True,
                "does_not_change_runtime_state": True,
                "does_not_trigger_data_refresh": True,
                "does_not_switch_accepted_pointer": True,
                "does_not_touch_monitor_or_execution_paths": True,
                "does_not_touch_broker_or_orders": True,
            },
            "phaseb1_gate": None,
            "phaseb2_gate_basis": "artifact_missing_readonly_empty_state",
            "research_only": True,
        }

    def _strategy_view(self, method: str, period_rows: list[dict[str, str]], summary_rows: list[dict[str, str]]) -> dict[str, Any]:
        periods = [row for row in period_rows if row.get("method") == method]
        summary = next((row for row in summary_rows if row.get("method") == method), {})
        primary = next((row for row in periods if row.get("period") == "phase1c_independent_test_range"), periods[0] if periods else {})
        full_range = next((row for row in periods if row.get("period") == "common_full_range_shared_by_all_compared_methods"), {})
        is_default = method == "phase1c_ltr_simple_daily"
        return {
            "method_key": method,
            "display_name": self.strategy_labels.get(method, method),
            "role": self.strategy_roles.get(method, "readonly_reference"),
            "status_label": self.strategy_status_labels.get(method, "只读参考"),
            "is_default_baseline": is_default,
            "is_default_main_strategy": is_default,
            "is_optional_ltr": method != "rank_rotate_top50_adaptive_score",
            "note": self.strategy_notes.get(method, "只读历史模拟候选。"),
            "sample_scope": self._sample_scope(primary),
            "oos_interpretation_allowed": any(row.get("period") == "phase1c_independent_test_range" for row in periods),
            "metrics": self._compact_result(primary),
            "primary_evidence_period": "phase1c_independent_test_range",
            "full_range_metrics": self._compact_result(full_range) if full_range else None,
            "split_purity_note": "首屏主指标使用独立测试区间；common full range 为 train/validation/independent_test 混合历史复盘，不作为样本外泛化证明。",
            "method_summary": self._method_summary(summary),
            "period_results": [self._compact_result(row) for row in periods],
            "walk_forward": [self._compact_result(row) for row in periods],
            "rolling_summary": {**self._method_summary(summary), "detail_layer_only": True},
            "boundary_text": self.boundary_text,
        }

    def _compact_result(self, row: dict[str, str]) -> dict[str, Any]:
        return {
            "fold_id": row.get("period"),
            "period": row.get("period"),
            "test_period": self._sample_scope(row),
            "walk_forward_mode": "phaseb1_fixed_candidate_replay",
            "fee_tax_adjusted_net_return": self._number(row.get("fee_tax_adjusted_net_return")),
            "max_drawdown": self._number(row.get("max_drawdown")),
            "action_count": self._int(row.get("action_count")),
            "turnover_proxy_by_notional_over_avg_equity": self._number(row.get("turnover_proxy_by_notional_over_avg_equity")),
            "relative_return_vs_top50_adaptive": self._number(row.get("relative_return_vs_top50_adaptive")),
            "relative_drawdown_vs_top50_adaptive": self._number(row.get("relative_drawdown_vs_top50_adaptive")),
            "relative_actions_vs_top50_adaptive": self._int(row.get("relative_actions_vs_top50_adaptive")),
            "sample_status": row.get("sample_status"),
            "trading_days_used": self._int(row.get("trading_days_used")),
            "oos_interpretation_allowed": row.get("period") == "phase1c_independent_test_range",
        }

    def _method_summary(self, row: dict[str, str]) -> dict[str, Any]:
        return {
            "period_count": self._int(row.get("period_count")),
            "positive_period_count": self._int(row.get("positive_period_count")),
            "avg_fee_tax_adjusted_net_return": self._number(row.get("avg_fee_tax_adjusted_net_return")),
            "min_fee_tax_adjusted_net_return": self._number(row.get("min_fee_tax_adjusted_net_return")),
            "avg_max_drawdown": self._number(row.get("avg_max_drawdown")),
            "worst_max_drawdown": self._number(row.get("worst_max_drawdown")),
            "avg_action_count": self._number(row.get("avg_action_count")),
            "avg_turnover_proxy": self._number(row.get("avg_turnover_proxy")),
        }

    @staticmethod
    def _sample_scope(row: dict[str, str]) -> str:
        period = row.get("period") or "-"
        start = row.get("start_date") or "-"
        end = row.get("end_date") or "-"
        return f"{period}：{start} 至 {end}"

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _number(raw: Any) -> float | None:
        try:
            return float(raw)
        except Exception:
            return None

    @staticmethod
    def _int(raw: Any) -> int | None:
        try:
            return int(float(raw))
        except Exception:
            return None
