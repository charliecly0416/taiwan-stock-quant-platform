"""Simple TWStock research chat over validated DailyAgentPromptArtifact."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.tw_stock_agent_daily_prompt import TWStockAgentDailyPromptError, TWStockAgentDailyPromptLoader
from app.services.tw_stock_agent_guardrails import BLOCKED_ANSWER, RESEARCH_ONLY_DISCLAIMER
from app.services.tw_stock_agent_openai import TWStockAgentOpenAIAdapter
from scripts.validate_tw_agent_daily_prompt_artifact import FORBIDDEN_PATTERNS


SAFE_REFUSAL_WARNING = "unsafe_model_output_overridden"


@dataclass(frozen=True)
class SimpleIntent:
    intent: str
    blocked: bool = False
    reason: str = ""
    symbol: Optional[str] = None


class TWStockAgentSimpleChatService:
    """Classify, load artifact, optionally call OpenAI, and validate output."""

    _symbol_pattern = re.compile(r"(?<!\d)(?:TW)?(\d{4})(?:\.TW)?(?!\d)", re.IGNORECASE)
    _blocked_patterns = [
        ("qlib_retrain_or_tune", ("retrain", "fine tune", "finetune", "训练模型", "重训", "重新训练", "调参", "調參")),
        ("qlib_ops_refresh_publish", ("刷新 qlib", "qlib refresh", "refresh qlib", "publish", "发布", "發佈", "provider refresh", "provider publish")),
        ("monitor_write", ("monitor scan", "monitor alerts", "monitor config", "保存监控配置", "触发 monitor", "写 monitor")),
        ("broker_operation", ("ibkr", "broker", "券商", "经纪商", "經紀商", "交易接口", "quick trade", "quick-trade", "quick_trade")),
        ("auto_trade", ("自动交易", "自動交易", "auto trade", "autotrade", "auto buy", "auto sell", "自动下单", "自動下單")),
        ("target_position", ("仓位", "倉位", "target position", "target_position", "target-position", "target weight", "target_weight", "target-weight", "目标仓位", "目標倉位", "持仓比例", "持倉比例", "open position", "close position")),
        ("portfolio_weight", ("portfolio weight", "组合权重", "組合權重", "配置比例", "资产配置", "資產配置")),
        ("place_order", ("下单", "下單", "帮我买", "幫我買", "帮我卖", "幫我賣", "建议买入", "建議買入", "建议卖出", "建議賣出", "推荐买入", "推薦買入", "推荐卖出", "推薦賣出", "place order", "submit order", "execute order", "order execution", "buy now", "sell now", "market order", "limit order")),
        ("guaranteed_profit", ("保证收益", "保證收益", "保证上涨", "保證上漲", "稳赚", "穩賺", "胜率是多少", "勝率是多少", "上涨概率", "上漲概率")),
    ]
    _unsafe_answer_terms = (
        "下单", "下單", "自动交易", "自動交易", "目标仓位", "目標倉位", "提交订单", "提交訂單",
        "连接券商", "連接券商", "broker", "quick-trade", "monitor scan", "monitor alerts", "monitor config",
        "provider publish", "accepted latest", "qlib refresh", "retrain", "调参", "調參", "保证收益", "保證收益",
        "保证上涨", "保證上漲", "胜率承诺", "勝率承諾", "上涨概率", "上漲概率",
        "order", "orders", "place order", "place orders", "submit order", "target_position", "target-position",
        "target weight", "target_weight",
    )

    def __init__(self, *, loader: Optional[TWStockAgentDailyPromptLoader] = None, openai_adapter: Optional[Any] = None) -> None:
        self.loader = loader or TWStockAgentDailyPromptLoader()
        self.openai_adapter = openai_adapter or TWStockAgentOpenAIAdapter()

    def chat(self, *, question: str, symbol: str = "", max_items: int = 8, artifact_dir: Optional[str] = None) -> Dict[str, Any]:
        intent = self.classify(question, symbol=symbol)
        if intent.blocked:
            return self._blocked_response(intent=intent, warnings=[intent.reason or "blocked_research_boundary"])
        try:
            artifact = self.loader.load(artifact_dir=artifact_dir)
        except TWStockAgentDailyPromptError as exc:
            return self._artifact_error_response(intent=intent, error=str(exc))

        fallback = self._fallback_answer(intent=intent, artifact=artifact, max_items=max_items)
        status = self.openai_adapter.status()
        if not status.get("enabled"):
            fallback["mode"] = "disabled"
            fallback["warnings"] = self._merge_warnings(fallback.get("warnings"), [str(status.get("reason") or "openai_disabled")])
            return fallback

        controlled_context = self._controlled_context(question=question, intent=intent, artifact=artifact, max_items=max_items)
        result = self.openai_adapter.complete(controlled_context=controlled_context)
        if not result.get("ok"):
            fallback["mode"] = str(result.get("mode") or status.get("mode") or "fallback")
            fallback["warnings"] = self._merge_warnings(fallback.get("warnings"), [str(result.get("status") or "openai_error")])
            return fallback

        validated = self._validate_model_content(
            content=str(result.get("content") or ""),
            intent=intent,
            artifact=artifact,
            mode=str(result.get("mode") or status.get("mode") or "openai"),
            fallback=fallback,
        )
        if validated is not None:
            return validated
        fallback["mode"] = str(result.get("mode") or status.get("mode") or "fallback")
        fallback["warnings"] = self._merge_warnings(fallback.get("warnings"), ["model_output_invalid_fallback"])
        return fallback

    def classify(self, question: str, *, symbol: str = "") -> SimpleIntent:
        text = str(question or "").strip()
        lowered = text.lower()
        for intent, patterns in self._blocked_patterns:
            if any(pattern.lower() in lowered for pattern in patterns):
                return SimpleIntent(intent=intent, blocked=True, reason="blocked_research_boundary", symbol=self._normalize_symbol(symbol) or self._extract_symbol(text))
        detected_symbol = self._normalize_symbol(symbol) or self._extract_symbol(text)
        if detected_symbol:
            return SimpleIntent(intent="single_symbol_status", symbol=detected_symbol)
        if "排名第一" in text or "第一" in text or "top ranked" in lowered:
            return SimpleIntent(intent="top_ranked_stock")
        if "前十" in text or "前 10" in text or "top10" in lowered or "top 10" in lowered:
            return SimpleIntent(intent="top_n_rankings")
        if "明天" in text or "tomorrow" in lowered or "候选" in text or "候選" in text:
            return SimpleIntent(intent="tomorrow_candidates")
        if "调入" in text or "調入" in text or "调出" in text or "調出" in text or "买卖" in text or "買賣" in text:
            return SimpleIntent(intent="strategy_buy_sell_observation")
        if "模拟账户" in text or "模擬帳戶" in text or "应用" in text or "應用" in text or "apply" in lowered:
            return SimpleIntent(intent="paper_apply_status")
        if "为什么不能" in text or "為什麼不能" in text or "execution" in lowered or "next_open" in lowered:
            return SimpleIntent(intent="execution_price_pending")
        if "新鲜" in text or "新鮮" in text or "fresh" in lowered or "asof" in lowered or "数据" in text or "資料" in text:
            return SimpleIntent(intent="data_freshness")
        if "回放" in text or "回測" in text or "replay" in lowered:
            return SimpleIntent(intent="replay_summary")
        return SimpleIntent(intent="today_strategy")

    def _controlled_context(self, *, question: str, intent: SimpleIntent, artifact: Any, max_items: int) -> Dict[str, Any]:
        return {
            "prompt_text": artifact.prompt_text,
            "prompt_context": self._compact_context(artifact.prompt_context, max_items=max_items),
            "question": str(question or "")[:500],
            "intent": intent.intent,
            "symbol": intent.symbol,
            "allowed_citations": artifact.allowed_citations,
            "context_digest": artifact.context_digest,
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
        }

    @staticmethod
    def _compact_context(context: Dict[str, Any], *, max_items: int) -> Dict[str, Any]:
        compact = dict(context)
        rankings = dict(compact.get("rankings") or {})
        strategy = dict(compact.get("strategy") or {})
        for key in ("qlib_top10", "qlib_top50", "ltr_top10", "ltr_top50_compact"):
            if isinstance(rankings.get(key), list):
                rankings[key] = rankings[key][:max_items]
        for key in ("top_candidates", "exit_candidates", "skipped_or_blocked"):
            if isinstance(strategy.get(key), list):
                strategy[key] = strategy[key][:max_items]
        compact["rankings"] = rankings
        compact["strategy"] = strategy
        external = dict(compact.get("external_research") or {})
        tradingagents = dict(external.get("tradingagents_readonly") or {})
        if isinstance(tradingagents.get("symbols"), list):
            tradingagents["symbols"] = [
                dict(item) for item in tradingagents["symbols"][:max_items] if isinstance(item, dict)
            ]
        if tradingagents:
            external["tradingagents_readonly"] = tradingagents
            compact["external_research"] = external
        return compact

    def _validate_model_content(self, *, content: str, intent: SimpleIntent, artifact: Any, mode: str, fallback: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(content)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        answer = parsed.get("answer")
        citations = parsed.get("citations")
        warnings = parsed.get("warnings")
        disclaimer = parsed.get("research_only_disclaimer")
        model_intent = parsed.get("intent")
        if not isinstance(answer, str) or not answer.strip():
            return None
        if model_intent != intent.intent:
            return None
        if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
            return None
        if not citations or any(item not in artifact.allowed_citations for item in citations):
            return None
        if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
            return None
        if not isinstance(disclaimer, str) or "不构成交易建议" not in disclaimer:
            return None
        if self._is_unsafe_answer(answer):
            blocked = self._blocked_response(intent=SimpleIntent(intent.intent, blocked=True), warnings=self._merge_warnings(fallback.get("warnings"), [SAFE_REFUSAL_WARNING]))
            blocked["mode"] = mode
            blocked["context_digest"] = artifact.context_digest
            return blocked
        return {
            "ok": True,
            "mode": mode,
            "intent": intent.intent,
            "blocked": False,
            "answer": answer.strip(),
            "items": fallback.get("items") or [],
            "citations": citations,
            "warnings": self._merge_warnings(fallback.get("warnings"), warnings),
            "research_only_disclaimer": disclaimer,
            "context_digest": artifact.context_digest,
        }

    def _fallback_answer(self, *, intent: SimpleIntent, artifact: Any, max_items: int) -> Dict[str, Any]:
        context = artifact.prompt_context
        items = self._items_for_intent(intent=intent, context=context, max_items=max_items)
        digest = artifact.context_digest
        answer = self._answer_for_intent(intent=intent, context=context, items=items)
        return {
            "ok": True,
            "mode": "fallback",
            "intent": intent.intent,
            "blocked": False,
            "answer": answer,
            "items": items,
            "citations": artifact.allowed_citations[:1],
            "warnings": list((context.get("freshness") or {}).get("warnings") or []),
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            "context_digest": digest,
        }

    def _answer_for_intent(self, *, intent: SimpleIntent, context: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
        date_context = context.get("date_context") or {}
        strategy = context.get("strategy") or {}
        paper = context.get("paper_portfolio") or {}
        freshness = context.get("freshness") or {}
        replay = context.get("replay_summary") or {}
        symbols = ", ".join(str(item.get("symbol")) for item in items if item.get("symbol")) or "无"
        if intent.intent == "paper_apply_status":
            return f"模拟账户 apply_allowed={paper.get('apply_allowed')}，blocked_reason={paper.get('blocked_reason')}。这只是只读状态，不是交易指令。"
        if intent.intent == "execution_price_pending":
            return f"当前执行价状态为 {date_context.get('execution_price_status')}，执行价口径为 next_open；pending 时只能等待数据齐备或人工复盘。"
        if intent.intent == "data_freshness":
            return f"当前 freshness={freshness.get('status')}，warnings={freshness.get('warnings') or []}。"
        if intent.intent == "replay_summary":
            return f"只读回放窗口为 {replay.get('window')}，metrics={replay.get('metrics') or {}}，不代表未来收益。"
        if intent.intent == "top_ranked_stock":
            return f"当前 Model A（E4 Qlib）排名第一观察标的是 {symbols}；score 仅用于候选排序，不是涨幅、胜率或收益承诺。"
        if intent.intent in {"top_n_rankings", "tomorrow_candidates"}:
            return f"当前只读排序观察包括：{symbols}。"
        if intent.intent == "strategy_buy_sell_observation":
            return f"当前只读策略观察包括：{symbols}。这些是拟调入/拟调出观察，不是订单或仓位建议。"
        if intent.intent == "single_symbol_status":
            return f"{intent.symbol} 的当前只读状态需结合排名、策略候选和 freshness 人工复盘。"
        return f"今日只读策略为 {strategy.get('strategy_rule')}，signal_asof={date_context.get('signal_asof')}，target_date={date_context.get('target_date')}，观察标的包括：{symbols}。"

    @staticmethod
    def _items_for_intent(*, intent: SimpleIntent, context: Dict[str, Any], max_items: int) -> List[Dict[str, Any]]:
        rankings = context.get("rankings") or {}
        strategy = context.get("strategy") or {}
        qlib_items = list(rankings.get("qlib_top10") or rankings.get("qlib_top50") or [])
        ltr_items = list(rankings.get("ltr_top10") or [])
        if intent.intent == "top_ranked_stock":
            return (qlib_items or ltr_items)[:1]
        if intent.intent in {"top_n_rankings", "tomorrow_candidates"}:
            return (qlib_items or ltr_items)[:max_items]
        if intent.intent == "strategy_buy_sell_observation":
            return (list(strategy.get("top_candidates") or []) + list(strategy.get("exit_candidates") or []))[:max_items]
        if intent.intent == "single_symbol_status" and intent.symbol:
            candidates = qlib_items + list(rankings.get("ltr_top50_compact") or []) + ltr_items + list(strategy.get("top_candidates") or [])
            return [item for item in candidates if str(item.get("symbol")) == intent.symbol][:max_items]
        return list(strategy.get("top_candidates") or [])[:max_items]

    @staticmethod
    def _artifact_error_response(*, intent: SimpleIntent, error: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "mode": "artifact_missing" if "missing" in error else "fallback",
            "intent": intent.intent,
            "blocked": False,
            "answer": f"当前 DailyAgentPromptArtifact 不可用：{error}。",
            "items": [],
            "citations": [],
            "warnings": [error],
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            "context_digest": {},
        }

    @staticmethod
    def _blocked_response(*, intent: SimpleIntent, warnings: List[str]) -> Dict[str, Any]:
        return {
            "ok": True,
            "mode": "blocked",
            "intent": intent.intent,
            "blocked": True,
            "answer": BLOCKED_ANSWER,
            "items": [],
            "citations": [],
            "warnings": warnings,
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            "context_digest": {},
        }

    @classmethod
    def _is_unsafe_answer(cls, answer: str) -> bool:
        lowered = str(answer or "").lower()
        if any(term.lower() in lowered for term in cls._unsafe_answer_terms):
            return True
        return any(pattern.search(str(answer or "")) for _, pattern in FORBIDDEN_PATTERNS)

    @staticmethod
    def _merge_warnings(base: Any, extra: Any) -> List[str]:
        merged: List[str] = []
        for group in (base or [], extra or []):
            values = [group] if isinstance(group, str) else list(group) if isinstance(group, list) else []
            for value in values:
                clean = str(value or "").strip()
                if clean and clean not in merged:
                    merged.append(clean)
        return merged

    @classmethod
    def _extract_symbol(cls, text: str) -> Optional[str]:
        match = cls._symbol_pattern.search(str(text or ""))
        return cls._normalize_symbol(match.group(1)) if match else None

    @staticmethod
    def _normalize_symbol(symbol: str) -> Optional[str]:
        clean = str(symbol or "").strip().upper()
        if clean.startswith("TW"):
            clean = clean[2:]
        if "." in clean:
            clean = clean.split(".", 1)[0]
        return clean if clean.isdigit() and len(clean) == 4 else None
