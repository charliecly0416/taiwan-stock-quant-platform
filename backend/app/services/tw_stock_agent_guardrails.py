"""Deterministic guardrails for the read-only TWStock research agent."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


RESEARCH_ONLY_DISCLAIMER = "仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。"
BLOCKED_ANSWER = "该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。"

ALLOWED_INTENTS = [
    "today_top30",
    "today_top50",
    "focus_watch",
    "secondary_watch",
    "model_trend_divergence",
    "data_review_required",
    "single_symbol_metrics",
    "freshness_and_data_basis",
    "research_summary",
    "unknown_research_question",
]

BLOCKED_INTENTS = [
    "place_order",
    "auto_trade",
    "target_position",
    "portfolio_weight",
    "paper_live_trading",
    "broker_operation",
    "guaranteed_profit",
    "qlib_ops_refresh_publish",
    "qlib_retrain_or_tune",
]


@dataclass(frozen=True)
class IntentResult:
    intent: str
    blocked: bool
    reason: str = ""
    symbol: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "intent": self.intent,
            "blocked": self.blocked,
            "reason": self.reason,
            "symbol": self.symbol,
        }


class TWStockAgentGuardrails:
    """Classify user questions before any model adapter is allowed to run."""

    _symbol_pattern = re.compile(r"(?<!\d)(?:TW)?(\d{4})(?:\.TW)?(?!\d)", re.IGNORECASE)
    _blocked_patterns = [
        ("qlib_retrain_or_tune", ("retrain", "fine tune", "finetune", "训练模型", "重训", "重新训练", "调参", "調參")),
        ("qlib_ops_refresh_publish", ("刷新 qlib", "qlib refresh", "refresh qlib", "publish", "发布", "發佈", "pipeline", "provider refresh")),
        ("broker_operation", ("ibkr", "broker", "券商", "经纪商", "經紀商", "交易接口")),
        ("paper_live_trading", ("paper trading", "live trading", "实盘", "實盤", "模拟盘", "模擬盤")),
        ("auto_trade", ("自动交易", "自動交易", "auto trade", "autotrade", "自动下单", "自動下單")),
        ("target_position", ("仓位", "倉位", "target position", "target_position", "目标仓位", "目標倉位", "持仓比例", "持倉比例")),
        ("portfolio_weight", ("portfolio weight", "组合权重", "組合權重", "配置比例", "资产配置", "資產配置")),
        ("place_order", ("下单", "下單", "帮我买", "幫我買", "帮我卖", "幫我賣", "建议买入", "建議買入", "建议卖出", "建議賣出", "推荐买入", "推薦買入", "推荐卖出", "推薦賣出", "买入多少", "買入多少", "卖出多少", "賣出多少", "place order")),
        ("guaranteed_profit", ("保证收益", "保證收益", "保证上涨", "保證上漲", "稳赚", "穩賺", "胜率是多少", "勝率是多少", "score 是不是涨幅", "score 是不是漲幅")),
    ]

    @property
    def allowed_intents(self) -> List[str]:
        return list(ALLOWED_INTENTS)

    @property
    def blocked_intents(self) -> List[str]:
        return list(BLOCKED_INTENTS)

    @property
    def disclaimers(self) -> List[str]:
        return [RESEARCH_ONLY_DISCLAIMER]

    def classify(self, question: str, *, symbol: str = "") -> IntentResult:
        text = str(question or "").strip()
        lowered = text.lower()
        for intent, patterns in self._blocked_patterns:
            if any(pattern.lower() in lowered for pattern in patterns):
                return IntentResult(intent=intent, blocked=True, reason="blocked_research_boundary", symbol=self._normalize_symbol(symbol) or self._extract_symbol(text))

        detected_symbol = self._normalize_symbol(symbol) or self._extract_symbol(text)
        if detected_symbol:
            return IntentResult(intent="single_symbol_metrics", blocked=False, symbol=detected_symbol)
        if "top50" in lowered or "前50" in text or "前 50" in text:
            return IntentResult(intent="today_top50", blocked=False)
        if "top30" in lowered or "前30" in text or "前 30" in text:
            return IntentResult(intent="today_top30", blocked=False)
        if self._is_focus_watch_question(text, lowered):
            return IntentResult(intent="focus_watch", blocked=False)
        if "二级观察" in text or "二級觀察" in text or "secondary" in lowered:
            return IntentResult(intent="secondary_watch", blocked=False)
        if "分歧" in text or "divergence" in lowered or "回避" in text:
            return IntentResult(intent="model_trend_divergence", blocked=False)
        if "新鲜" in text or "新鮮" in text or "asof" in lowered or "fresh" in lowered or "口径" in text or "口徑" in text:
            return IntentResult(intent="freshness_and_data_basis", blocked=False)
        if "数据" in text or "資料" in text or "异常" in text or "異常" in text or "人工复盘" in text or "人工復盤" in text or "复核" in text or "覆核" in text or "review" in lowered:
            return IntentResult(intent="data_review_required", blocked=False)
        if "总结" in text or "總結" in text or "摘要" in text or "summary" in lowered:
            return IntentResult(intent="research_summary", blocked=False)
        return IntentResult(intent="unknown_research_question", blocked=False)


    @staticmethod
    def _is_focus_watch_question(text: str, lowered: str) -> bool:
        focus_terms = (
            "重点观察",
            "重點觀察",
            "建议关注",
            "建議關注",
            "focus",
        )
        model_terms = ("模型", "model", "qlib")
        trend_terms = ("趋势", "趨勢", "trend", "raw 趋势", "raw 趨勢")
        support_terms = ("支持", "一致", "共振", "aligned", "alignment")
        if any(term in text or term in lowered for term in focus_terms):
            return True
        has_model = any(term in text or term in lowered for term in model_terms)
        has_trend = any(term in text or term in lowered for term in trend_terms)
        has_support = any(term in text or term in lowered for term in support_terms)
        if has_model and has_trend and has_support:
            return True
        if has_trend and has_support and ("股票" in text or "哪些" in text or "哪" in text):
            return True
        return False

    @classmethod
    def _extract_symbol(cls, text: str) -> Optional[str]:
        match = cls._symbol_pattern.search(str(text or ""))
        if not match:
            return None
        return cls._normalize_symbol(match.group(1))

    @staticmethod
    def _normalize_symbol(symbol: str) -> Optional[str]:
        clean = str(symbol or "").strip().upper()
        if clean.startswith("TW"):
            clean = clean[2:]
        if "." in clean:
            clean = clean.split(".", 1)[0]
        return clean if clean.isdigit() and len(clean) == 4 else None
