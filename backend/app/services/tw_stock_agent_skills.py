"""Controlled skill registry for the TWStock research agent.

The product Agent may use these skills as backend-owned, read-only context.
It must not execute arbitrary files from user skill directories.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.tw_stock_agent_guardrails import RESEARCH_ONLY_DISCLAIMER


@dataclass(frozen=True)
class TWStockAgentSkill:
    name: str
    title: str
    description: str
    mode: str
    allowed_actions: List[str]
    forbidden_actions: List[str]

    def public_dict(self, *, status: str, reason: str, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "mode": self.mode,
            "status": status,
            "reason": reason,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "evidence": evidence or {},
        }


class TWStockAgentSkillRegistry:
    """Select safe, product-side skills and build deterministic context."""

    _skill_names = {
        "safety": "tw-stock-safety-boundary-review",
        "freshness": "tw-stock-data-freshness-diagnosis",
        "research": "tw-stock-research-context-analyst",
        "e2e": "tw-stock-readonly-e2e-acceptance",
    }

    _skill_dirs = (
        Path.home() / ".agents" / "skills",
        Path.cwd() / ".agent_skills",
    )

    def __init__(self) -> None:
        self._skills = self._load_skills()

    def select(self, *, question: str, preview: Dict[str, Any]) -> List[Dict[str, Any]]:
        intent = str(preview.get("intent") or "")
        text = str(question or "").lower()
        selected: List[Dict[str, Any]] = []

        selected.append(self._skills["safety"].public_dict(
            status="applied",
            reason="guardrails_checked_before_model",
            evidence={
                "intent": intent,
                "blocked": bool(preview.get("blocked")),
                "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            },
        ))

        if bool(preview.get("blocked")):
            return selected

        if intent == "freshness_and_data_basis" or any(term in text for term in ("fresh", "asof", "yahoo", "finmind", "自动", "自動", "retry", "重试", "重試", "口径", "口徑")):
            selected.append(self._skills["freshness"].public_dict(
                status="invoked",
                reason="freshness_or_provider_question",
                evidence=self._freshness_evidence(preview),
            ))

        research_intents = {
            "today_top30",
            "today_top50",
            "focus_watch",
            "secondary_watch",
            "model_trend_divergence",
            "data_review_required",
            "single_symbol_metrics",
            "research_summary",
            "unknown_research_question",
        }
        if intent in research_intents:
            selected.append(self._skills["research"].public_dict(
                status="invoked",
                reason="research_context_question",
                evidence=self._research_evidence(preview),
            ))

        if any(term in text for term in ("e2e", "playwright", "验收", "驗收", "全流程", "测试", "測試")):
            selected.append(self._skills["e2e"].public_dict(
                status="not_invoked_from_web_agent",
                reason="long_running_acceptance_must_run_outside_frontend_chat",
                evidence={"readonly": True, "web_agent_execution": False},
            ))

        return selected

    def context_for_model(self, *, invoked_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "selected_skills": [
                {
                    "name": item.get("name"),
                    "title": item.get("title"),
                    "mode": item.get("mode"),
                    "status": item.get("status"),
                    "reason": item.get("reason"),
                    "allowed_actions": item.get("allowed_actions") or [],
                    "forbidden_actions": item.get("forbidden_actions") or [],
                }
                for item in invoked_skills
            ],
            "skill_context": {
                str(item.get("name")): item.get("evidence") or {}
                for item in invoked_skills
                if item.get("status") in {"applied", "invoked"}
            },
            "skill_invocation_policy": {
                "frontend_direct_openai": False,
                "execute_local_skill_files": False,
                "readonly_get_context_only": True,
                "model_may_not_claim_unlisted_skill_usage": True,
            },
        }

    def _load_skills(self) -> Dict[str, TWStockAgentSkill]:
        defaults = self._default_skills()
        for key, skill in defaults.items():
            description = self._read_skill_description(skill.name) or skill.description
            defaults[key] = TWStockAgentSkill(
                name=skill.name,
                title=skill.title,
                description=description,
                mode=skill.mode,
                allowed_actions=skill.allowed_actions,
                forbidden_actions=skill.forbidden_actions,
            )
        return defaults

    def _read_skill_description(self, skill_name: str) -> str:
        for root in self._skill_dirs:
            path = root / skill_name / "SKILL.md"
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            for line in text.splitlines():
                clean = line.strip()
                if clean.lower().startswith("description:"):
                    return clean.split(":", 1)[1].strip().strip('"')
            for line in text.splitlines():
                clean = line.strip()
                if clean and not clean.startswith("#") and not clean.startswith("---"):
                    return clean[:240]
        return ""

    @classmethod
    def _default_skills(cls) -> Dict[str, TWStockAgentSkill]:
        common_forbidden = [
            "place_order",
            "broker_operation",
            "quick_trade",
            "target_position",
            "provider_refresh_or_publish",
            "accepted_latest_switch",
        ]
        return {
            "safety": TWStockAgentSkill(
                name=cls._skill_names["safety"],
                title="Safety Boundary Review",
                description="Review readonly safety boundaries for Taiwan stock Agent answers and artifacts.",
                mode="guardrail_policy",
                allowed_actions=["intent_check", "answer_boundary_check", "readonly_policy_context"],
                forbidden_actions=common_forbidden,
            ),
            "freshness": TWStockAgentSkill(
                name=cls._skill_names["freshness"],
                title="Data Freshness Diagnosis",
                description="Explain qlib accepted latest, Yahoo/FinMind freshness, pending_asof, and retry state.",
                mode="readonly_context",
                allowed_actions=["freshness_summary", "asof_explanation", "provider_status_interpretation"],
                forbidden_actions=common_forbidden,
            ),
            "research": TWStockAgentSkill(
                name=cls._skill_names["research"],
                title="Research Context Analyst",
                description="Explain top rankings, symbol context, qlib/trend alignment, and manual review watchlists.",
                mode="readonly_context",
                allowed_actions=["ranking_explanation", "symbol_context", "manual_review_context"],
                forbidden_actions=common_forbidden,
            ),
            "e2e": TWStockAgentSkill(
                name=cls._skill_names["e2e"],
                title="Readonly E2E Acceptance",
                description="Run or summarize readonly full-scenario E2E acceptance outside frontend chat.",
                mode="operator_handoff",
                allowed_actions=["acceptance_summary_reference"],
                forbidden_actions=common_forbidden + ["run_playwright_from_web_agent"],
            ),
        }

    @staticmethod
    def _freshness_evidence(preview: Dict[str, Any]) -> Dict[str, Any]:
        digest = preview.get("context_digest") or {}
        warnings = preview.get("warnings") or []
        return {
            "status": digest.get("freshness_status") or digest.get("status"),
            "qlib_asof": digest.get("qlib_asof"),
            "qlib_run_id": digest.get("qlib_run_id"),
            "target_horizon": digest.get("target_horizon"),
            "warnings": warnings if isinstance(warnings, list) else [],
            "answer_draft": preview.get("answer_draft") or "",
        }

    @staticmethod
    def _research_evidence(preview: Dict[str, Any]) -> Dict[str, Any]:
        items = preview.get("items") or []
        compact = []
        for item in items[:8] if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            compact.append({
                "symbol": item.get("symbol"),
                "qlib_rank": item.get("qlib_rank"),
                "trend_label": item.get("trend_label"),
                "cross_category": item.get("cross_category"),
                "human_action": item.get("human_action"),
            })
        return {
            "intent": preview.get("intent"),
            "item_count": len(items) if isinstance(items, list) else 0,
            "items": compact,
            "citations": preview.get("citations") or [],
        }
