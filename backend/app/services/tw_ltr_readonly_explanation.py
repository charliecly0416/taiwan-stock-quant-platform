"""Readonly Phase5 LTR explanation payload presenter."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TWLTRReadonlyExplanationService:
    """Build a Phase4B product view from the frozen Phase3C payload artifact."""

    payload_path = Path("data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_readonly_explanation_payload.json")
    readonly_disclaimer = "仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。"

    role_labels = {
        "baseline": "对照参考",
        "aggressive_rerank_research": "高换手观察",
        "turnover_control_research": "少动作观察",
        "risk_review_reference": "风险复盘",
    }

    role_notes = {
        "baseline": "用来和其他研究方法比较。",
        "aggressive_rerank_research": "动作更频繁，需同时看换手和回撤。",
        "turnover_control_research": "更重视减少动作和换手。",
        "risk_review_reference": "用于观察低动作和回撤取舍。",
    }

    def __init__(self, payload_path: str | Path | None = None):
        if payload_path is not None:
            self.payload_path = Path(payload_path)

    def product_view(self) -> dict[str, Any]:
        payload = self._load_payload()
        methods = [self._method_view(item) for item in payload.get("methods", []) if isinstance(item, dict)]
        return {
            "ok": True,
            "schema_version": "phase5_product_readonly_view_v1",
            "payload_source": "phase3c_readonly_explanation_payload",
            "as_of_scope": payload.get("as_of_scope") or {},
            "data_quality": self._data_quality_view(payload.get("data_quality") or {}),
            "methods": methods,
            "readonly_disclaimer": self.readonly_disclaimer,
            "no_write_guarantees": {
                "read_only_http_method": True,
                "reads_static_payload_only": True,
                "does_not_change_runtime_state": True,
                "does_not_trigger_data_refresh": True,
                "does_not_switch_accepted_pointer": True,
                "does_not_touch_monitor_or_execution_paths": True,
            },
            "research_only": True,
        }

    def _load_payload(self) -> dict[str, Any]:
        with self.payload_path.open(encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise ValueError("Phase3C payload must be a JSON object")
        return payload

    def _data_quality_view(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "common_replay_days": data.get("common_replay_days"),
            "excluded_dates": data.get("excluded_dates") if isinstance(data.get("excluded_dates"), list) else [],
            "price_execution_audit_sample_count": data.get("price_execution_audit_sample_count"),
            "price_execution_audit_bad_count": data.get("price_execution_audit_bad_count"),
            "price_execution_max_days_to_execution": data.get("price_execution_max_days_to_execution"),
            "gross_return_policy": data.get("gross_return_policy"),
            "turnover_proxy": data.get("turnover_proxy"),
        }

    def _method_view(self, item: dict[str, Any]) -> dict[str, Any]:
        role = str(item.get("research_role") or "")
        return {
            "method_key": item.get("method_key"),
            "method_label": item.get("method_label"),
            "research_role_label": self.role_labels.get(role, "研究参考"),
            "research_role_note": self.role_notes.get(role, "仅供只读研究复盘。"),
            "why_no_action": self._why_no_action(item),
            "tradeoff_summary": self._tradeoff_summary(item),
            "readonly_disclaimer": self.readonly_disclaimer,
            "detail": self._detail_metrics(item),
            "data_quality_note": item.get("data_quality_note") or "",
        }

    def _why_no_action(self, item: dict[str, Any]) -> str:
        raw = str(item.get("why_no_action") or "")
        reason = "候选排序差距不够明显"
        mapping = [
            ("预算", "最近窗口动作预算不足"),
            ("最短持有", "仍在最短观察期内"),
            ("持有期", "仍在最短观察期内"),
            ("市况", "当前市况要求更谨慎"),
            ("数据质量", "当日数据不足以形成解释"),
            ("价格缺失", "缺少可用价格，保持只读观察"),
            ("共同日期", "当日不在共同回放日期集合内"),
            ("差距", "候选排序差距不够明显"),
        ]
        for needle, label in mapping:
            if needle in raw:
                reason = label
                break
        return f"今天不动作的主要原因：{reason}。"

    def _tradeoff_summary(self, item: dict[str, Any]) -> str:
        action = self._level_from_text(item.get("action_count_summary"), {"较少": "动作偏少", "中等": "动作适中", "较多": "动作偏多"}, "动作适中")
        turnover = self._level_from_text(item.get("turnover_summary"), {"较低": "换手压力较低", "中等": "换手压力中等", "较高": "换手压力较高"}, "换手压力中等")
        drawdown = self._level_from_text(item.get("drawdown_summary"), {"较低": "回撤较低", "中等": "回撤中等", "较高": "回撤较高"}, "回撤中等")
        return f"历史回放取舍：{action}，{turnover}，{drawdown}。"

    @staticmethod
    def _level_from_text(value: Any, mapping: dict[str, str], fallback: str) -> str:
        text = str(value or "")
        for key, label in mapping.items():
            if key in text:
                return label
        return fallback

    @staticmethod
    def _detail_metrics(item: dict[str, Any]) -> dict[str, str]:
        return {
            "net_return_summary": str(item.get("net_return_summary") or ""),
            "drawdown_summary": str(item.get("drawdown_summary") or ""),
            "action_count_summary": str(item.get("action_count_summary") or ""),
            "turnover_summary": str(item.get("turnover_summary") or ""),
            "relative_to_top50_adaptive": str(item.get("relative_to_top50_adaptive") or ""),
            "detail_disclaimer": "这些数值只用于历史回放复盘，必须和动作、换手、回撤取舍一起阅读。",
        }
