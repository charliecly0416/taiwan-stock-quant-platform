"""Deterministic decision kernel for the active Model A strategy.

This module deliberately has no artifact, clock, dataframe, price, cash, fee,
or execution dependencies. Adapters are responsible for loading and verifying
artifacts before passing plain rows to :func:`decide`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping


ACTIVE_MODEL_ID = "e4_frozen_qlib_2018_2022"
STRATEGY_RULE = "top50_exit_one_worst_sell"

_CONFIG: Mapping[str, Any] = MappingProxyType({
    "strategy_rule": STRATEGY_RULE,
    "target_holding_count": 10,
    "candidate_k": 50,
    "max_buy_count": 1,
    "max_sell_count": 1,
    "sell_boundary": "candidate_rank_gt_candidate_k",
    "buy_order": "buy_score_desc_instrument_asc",
    "tie_breaker": "full_qlib_rank_desc_instrument_desc",
    "allow_diagnostic_rule": False,
})
CANONICAL_CONFIG: Mapping[str, Any] = _CONFIG

_SIGNAL_REQUIRED = frozenset(
    {
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
    }
)
_SIGNAL_OPTIONAL = frozenset({"source_model_artifact", "source_feature_artifact"})
_PORTFOLIO_FIELDS = frozenset(
    {"asof_date", "instrument", "quantity", "cost_basis", "current_holding_flag"}
)
_FORBIDDEN_FIELD_PATTERNS = (
    re.compile(r"^future_.*$"),
    re.compile(r"^forward_return.*$"),
    re.compile(r"^label_.*$"),
    re.compile(r"^execution_.*$"),
    re.compile(r"^next_(open|close)$"),
    re.compile(r"^(open|close|price|mark_price|last_price)$"),
    re.compile(r"^(cash|cash_after|nav|equity)$"),
    re.compile(r"^(commission|fee|tax)$"),
    re.compile(r"^(target_position|target_weight|allocation_weight)$"),
    re.compile(r"^(broker|broker_order_id|order_id|quick_trade)$"),
    re.compile(r"^(realized_pnl|realized_return|daily_return|replay_return)$"),
    re.compile(r"^(relevance_10d_top_heavy|ltr_relevance_label)$"),
)
_INSTRUMENT = re.compile(r"^TW[0-9A-Z]{4,8}$")


class StrategyContractError(ValueError):
    """Raised when a strategy input is not safe to evaluate."""


@dataclass(frozen=True, slots=True)
class StrategyIntent:
    signal_date: str
    instrument: str
    intent_action: str
    intent_reason: str
    strategy_rule: str
    model_name: str
    candidate_rank: int
    buy_rank: int
    full_qlib_rank: int
    current_holding_flag: bool


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    signal_date: str
    model_name: str
    strategy_rule: str
    candidate_k: int
    target_holding_count: int
    max_buy_count: int
    max_sell_count: int
    sell: tuple[str, ...]
    buy: tuple[str, ...]
    hold: tuple[str, ...]
    skip: tuple[str, ...]
    intents: tuple[StrategyIntent, ...]


@dataclass(frozen=True, slots=True)
class _Signal:
    instrument: str
    candidate_rank: int
    buy_score: float
    score_rank: int
    full_qlib_rank: int


def _rows(value: Iterable[Mapping[str, Any]], label: str) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes, Mapping)):
        raise StrategyContractError(f"{label} must be an iterable of row mappings")
    try:
        rows = tuple(value)
    except TypeError as exc:
        raise StrategyContractError(f"{label} must be iterable") from exc
    if any(not isinstance(row, Mapping) for row in rows):
        raise StrategyContractError(f"{label} contains a non-mapping row")
    return rows


def _strict_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value or value != value.strip():
        raise StrategyContractError(f"{field} must be a non-empty ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise StrategyContractError(f"{field} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise StrategyContractError(f"{field} must be canonical YYYY-MM-DD")
    return parsed


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise StrategyContractError(f"{field} must be a non-empty string")
    return value


def _instrument(value: Any, field: str) -> str:
    instrument = _strict_text(value, field)
    if _INSTRUMENT.fullmatch(instrument) is None:
        raise StrategyContractError(f"{field} is not a canonical TW instrument")
    return instrument


def _strict_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise StrategyContractError(f"{field} must be an integer, not bool")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and isfinite(value) and value.is_integer():
        parsed = int(value)
    else:
        raise StrategyContractError(f"{field} must be an integer")
    if parsed < minimum:
        raise StrategyContractError(f"{field} must be >= {minimum}")
    return parsed


def _strict_float(value: Any, field: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise StrategyContractError(f"{field} must be numeric, not bool")
    if not isinstance(value, (int, float)):
        raise StrategyContractError(f"{field} must be numeric")
    parsed = float(value)
    if not isfinite(parsed):
        raise StrategyContractError(f"{field} must be finite")
    if minimum is not None and parsed < minimum:
        raise StrategyContractError(f"{field} must be >= {minimum}")
    return parsed


def _reject_forbidden_fields(row: Mapping[str, Any], label: str) -> None:
    forbidden = sorted(
        str(field)
        for field in row
        if any(pattern.fullmatch(str(field)) for pattern in _FORBIDDEN_FIELD_PATTERNS)
    )
    if forbidden:
        raise StrategyContractError(f"{label} contains forbidden fields: {', '.join(forbidden)}")


def _validate_config(config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise StrategyContractError("strategy config must be a mapping")
    unknown = sorted(set(config) - set(_CONFIG))
    missing = sorted(set(_CONFIG) - set(config))
    if unknown or missing:
        details = []
        if unknown:
            details.append(f"unknown={','.join(unknown)}")
        if missing:
            details.append(f"missing={','.join(missing)}")
        raise StrategyContractError(f"strategy config fields are invalid: {'; '.join(details)}")
    for field, expected in _CONFIG.items():
        actual = config[field]
        if isinstance(expected, bool):
            matches = type(actual) is bool and actual is expected
        elif isinstance(expected, int):
            matches = type(actual) is int and actual == expected
        else:
            matches = type(actual) is str and actual == expected
        if not matches:
            raise StrategyContractError(f"strategy config {field} must equal {expected!r}")


def _parse_signals(rows: tuple[Mapping[str, Any], ...]) -> tuple[str, dict[str, _Signal]]:
    if not rows:
        raise StrategyContractError("model signal rows must not be empty")
    parsed: dict[str, _Signal] = {}
    signal_dates: set[str] = set()
    model_names: set[str] = set()
    candidate_ranks: set[int] = set()
    full_ranks: set[int] = set()
    for index, row in enumerate(rows):
        label = f"model signal row {index}"
        _reject_forbidden_fields(row, label)
        unknown = sorted(set(row) - _SIGNAL_REQUIRED - _SIGNAL_OPTIONAL)
        missing = sorted(_SIGNAL_REQUIRED - set(row))
        if unknown or missing:
            raise StrategyContractError(
                f"{label} fields are invalid: unknown={unknown}, missing={missing}"
            )
        signal_date = _strict_date(row["date"], f"{label}.date")
        signal_asof = _strict_date(row["signal_asof"], f"{label}.signal_asof")
        available_at = _strict_date(row["available_at"], f"{label}.available_at")
        if signal_asof != signal_date:
            raise StrategyContractError(f"{label} signal_asof must equal date")
        if available_at > signal_date:
            raise StrategyContractError(f"{label} is not PIT available on signal date")
        instrument = _instrument(row["instrument"], f"{label}.instrument")
        if instrument in parsed:
            raise StrategyContractError(f"duplicate model signal instrument: {instrument}")
        model_name = _strict_text(row["model_name"], f"{label}.model_name")
        if model_name != ACTIVE_MODEL_ID:
            raise StrategyContractError(f"{label} model_name is not the active Model A")
        if _strict_text(row["model_family"], f"{label}.model_family") != "qlib":
            raise StrategyContractError(f"{label} model_family must be qlib")
        _strict_text(row["source_artifact"], f"{label}.source_artifact")
        for optional in _SIGNAL_OPTIONAL & set(row):
            _strict_text(row[optional], f"{label}.{optional}")
        candidate_rank = _strict_int(row["candidate_rank"], f"{label}.candidate_rank", minimum=1)
        score_rank = _strict_int(row["score_rank"], f"{label}.score_rank", minimum=1)
        full_rank = _strict_int(row["full_qlib_rank"], f"{label}.full_qlib_rank", minimum=1)
        buy_score = _strict_float(row["buy_score"], f"{label}.buy_score")
        _strict_float(row["raw_score"], f"{label}.raw_score")
        if candidate_rank != full_rank:
            raise StrategyContractError(
                f"{label} candidate_rank must preserve Model A full_qlib_rank"
            )
        if candidate_rank in candidate_ranks or full_rank in full_ranks:
            raise StrategyContractError(f"{label} contains duplicate Model A rank")
        candidate_ranks.add(candidate_rank)
        full_ranks.add(full_rank)
        parsed[instrument] = _Signal(
            instrument=instrument,
            candidate_rank=candidate_rank,
            buy_score=buy_score,
            score_rank=score_rank,
            full_qlib_rank=full_rank,
        )
        signal_dates.add(signal_date.isoformat())
        model_names.add(model_name)
    if len(signal_dates) != 1 or len(model_names) != 1:
        raise StrategyContractError("model signal rows must have one date and one model")
    expected_candidate_ranks = set(range(1, _CONFIG["candidate_k"] + 1))
    if not expected_candidate_ranks.issubset(candidate_ranks):
        raise StrategyContractError(
            f"model signal rows must expose candidate ranks 1..{_CONFIG['candidate_k']}"
        )
    return next(iter(signal_dates)), parsed


def _parse_portfolio(
    rows: tuple[Mapping[str, Any], ...], signal_date: str, signals: Mapping[str, _Signal]
) -> tuple[str, ...]:
    seen: set[str] = set()
    held: list[str] = []
    asof_dates: set[str] = set()
    decision_date = _strict_date(signal_date, "signal_date")
    for index, row in enumerate(rows):
        label = f"portfolio state row {index}"
        _reject_forbidden_fields(row, label)
        unknown = sorted(set(row) - _PORTFOLIO_FIELDS)
        missing = sorted(_PORTFOLIO_FIELDS - set(row))
        if unknown or missing:
            raise StrategyContractError(
                f"{label} fields are invalid: unknown={unknown}, missing={missing}"
            )
        asof = _strict_date(row["asof_date"], f"{label}.asof_date")
        if asof > decision_date:
            raise StrategyContractError(f"{label} asof_date is after the signal date")
        asof_dates.add(asof.isoformat())
        instrument = _instrument(row["instrument"], f"{label}.instrument")
        if instrument in seen:
            raise StrategyContractError(f"duplicate portfolio state instrument: {instrument}")
        seen.add(instrument)
        quantity = _strict_int(row["quantity"], f"{label}.quantity")
        _strict_float(row["cost_basis"], f"{label}.cost_basis", minimum=0.0)
        holding_flag = row["current_holding_flag"]
        if type(holding_flag) is not bool:
            raise StrategyContractError(f"{label}.current_holding_flag must be bool")
        if holding_flag != (quantity > 0):
            raise StrategyContractError(
                f"{label} quantity and current_holding_flag are inconsistent"
            )
        if holding_flag:
            signal = signals.get(instrument)
            if signal is None:
                raise StrategyContractError(
                    f"held instrument lacks same-day full-rank visibility: {instrument}"
                )
            held.append(instrument)
    if len(asof_dates) > 1:
        raise StrategyContractError("portfolio state rows must have one asof_date")
    if len(held) > _CONFIG["target_holding_count"]:
        raise StrategyContractError("portfolio exceeds target_holding_count")
    return tuple(sorted(held))


def decide(
    model_signal_rows: Iterable[Mapping[str, Any]],
    portfolio_state_rows: Iterable[Mapping[str, Any]],
    strategy_config: Mapping[str, Any],
) -> StrategyDecision:
    """Return the canonical strategy decision for one signal date.

    The function selects at most one sell and one buy. It never checks whether
    an intent can execute; price availability, pending orders, cash, quantity
    sizing, and accounting belong to ReplayExecution or paper simulation.
    """

    _validate_config(strategy_config)
    signal_rows = _rows(model_signal_rows, "model signal rows")
    portfolio_rows = _rows(portfolio_state_rows, "portfolio state rows")
    signal_date, signals = _parse_signals(signal_rows)
    held = _parse_portfolio(portfolio_rows, signal_date, signals)
    candidate_set = {
        signal.instrument
        for signal in signals.values()
        if signal.candidate_rank <= _CONFIG["candidate_k"]
    }
    buy_order = sorted(
        (signal for signal in signals.values() if signal.instrument in candidate_set),
        key=lambda signal: (-signal.buy_score, signal.instrument),
    )
    buy_rank = {signal.instrument: index + 1 for index, signal in enumerate(buy_order)}

    outside = sorted(
        (signals[instrument] for instrument in held if instrument not in candidate_set),
        key=lambda signal: (signal.full_qlib_rank, signal.instrument),
        reverse=True,
    )
    sells = tuple(signal.instrument for signal in outside[: _CONFIG["max_sell_count"]])
    remaining = set(held) - set(sells)
    open_slots = max(0, _CONFIG["target_holding_count"] - len(remaining))
    buy_limit = min(_CONFIG["max_buy_count"], open_slots)
    buys = tuple(
        signal.instrument
        for signal in buy_order
        if signal.instrument not in remaining
    )[:buy_limit]
    holds = tuple(instrument for instrument in held if instrument not in sells)
    skips: tuple[str, ...] = ()

    intents: list[StrategyIntent] = []
    for action, instruments in (("sell", sells), ("buy", buys), ("hold", holds)):
        for instrument in instruments:
            signal = signals[instrument]
            intents.append(
                StrategyIntent(
                    signal_date=signal_date,
                    instrument=instrument,
                    intent_action=action,
                    intent_reason=f"{STRATEGY_RULE}_{action}",
                    strategy_rule=STRATEGY_RULE,
                    model_name=ACTIVE_MODEL_ID,
                    candidate_rank=signal.candidate_rank,
                    buy_rank=buy_rank.get(instrument, -1),
                    full_qlib_rank=signal.full_qlib_rank,
                    current_holding_flag=instrument in held,
                )
            )
    return StrategyDecision(
        signal_date=signal_date,
        model_name=ACTIVE_MODEL_ID,
        strategy_rule=STRATEGY_RULE,
        candidate_k=_CONFIG["candidate_k"],
        target_holding_count=_CONFIG["target_holding_count"],
        max_buy_count=_CONFIG["max_buy_count"],
        max_sell_count=_CONFIG["max_sell_count"],
        sell=sells,
        buy=buys,
        hold=holds,
        skip=skips,
        intents=tuple(intents),
    )
