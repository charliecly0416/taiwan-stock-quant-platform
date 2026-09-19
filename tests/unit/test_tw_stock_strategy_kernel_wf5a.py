from __future__ import annotations

import csv
from dataclasses import FrozenInstanceError
import importlib.util
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tw_stock_strategy import top50_exit_one_worst_sell as kernel  # noqa: E402

ACTIVE_MODEL_ID = kernel.ACTIVE_MODEL_ID
CANONICAL_CONFIG = kernel.CANONICAL_CONFIG
StrategyContractError = kernel.StrategyContractError
decide = kernel.decide


REAL_FIXTURE = ROOT / "tests/fixtures/tw_stock_strategy/wf5a_model_a_20260106.csv"
LEGACY_REPLAY = ROOT / "scripts/run_tw_modular_config_replay_matrix.py"


def load_rows() -> list[dict[str, object]]:
    with REAL_FIXTURE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in ("candidate_rank", "score_rank", "full_qlib_rank"):
            row[field] = int(row[field])
        for field in ("buy_score", "raw_score"):
            row[field] = float(row[field])
    return rows


def config(**changes: object) -> dict[str, object]:
    return {**CANONICAL_CONFIG, **changes}


def portfolio(*instruments: str, asof: str = "2026-01-05") -> list[dict[str, object]]:
    return [
        {
            "asof_date": asof,
            "instrument": instrument,
            "quantity": 100,
            "cost_basis": 50.0,
            "current_holding_flag": True,
        }
        for instrument in instruments
    ]


def load_legacy_replay():
    spec = importlib.util.spec_from_file_location("wf5a_legacy_replay", LEGACY_REPLAY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_config_and_result_are_immutable() -> None:
    with pytest.raises(TypeError):
        CANONICAL_CONFIG["candidate_k"] = 10  # type: ignore[index]
    with pytest.raises(TypeError):
        kernel._CONFIG["candidate_k"] = 10  # type: ignore[index]
    decision = decide(load_rows(), [], CANONICAL_CONFIG)
    with pytest.raises(FrozenInstanceError):
        decision.candidate_k = 10  # type: ignore[misc]
    assert decision.candidate_k == 50
    assert decision.target_holding_count == 10
    assert decision.max_buy_count == decision.max_sell_count == 1


def test_dependency_yaml_frozen_fields_match_kernel_and_migration_stays_hold() -> None:
    dependency = yaml.safe_load(
        (ROOT / "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert {field: dependency[field] for field in CANONICAL_CONFIG} == dict(
        CANONICAL_CONFIG
    )
    assert dependency["canonical_kernel"] == {
        "module": "tw_stock_strategy.top50_exit_one_worst_sell",
        "runtime_migration_status": "hold",
        "unsupported_preconditions": [
            "pending_order_state",
            "price_coupled_candidate_fallback",
            "cash_or_quantity_sizing",
        ],
    }


def test_one_worst_outside_top50_is_sold_and_top_buy_is_selected_stably() -> None:
    rows = load_rows()
    holdings = portfolio(
        "TW8021",
        "TW2408",
        "TW5351",
        "TW3260",
        "TW6139",
        "TW6443",
        "TW2327",
        "TW3264",
        "TW6510",
        "TW6770",
    )
    expected = decide(rows, holdings, CANONICAL_CONFIG)
    reversed_input = decide(list(reversed(rows)), list(reversed(holdings)), CANONICAL_CONFIG)

    assert expected == reversed_input
    assert expected.sell == ("TW2408",)
    assert expected.buy == ("TW2485",)
    assert len(expected.hold) == 9
    assert [intent.intent_action for intent in expected.intents] == [
        "sell",
        "buy",
        *("hold" for _ in range(9)),
    ]
    assert expected.intents[0].full_qlib_rank == 102
    assert expected.intents[0].buy_rank == -1


def test_buy_score_tie_breaker_is_instrument_asc() -> None:
    rows = load_rows()
    by_symbol = {row["instrument"]: row for row in rows}
    by_symbol["TW5351"]["buy_score"] = by_symbol["TW3260"]["buy_score"]

    decision = decide(rows, [], CANONICAL_CONFIG)
    assert decision.buy == ("TW3260",)


@pytest.mark.parametrize("field", ["candidate_rank", "full_qlib_rank"])
def test_duplicate_or_missing_candidate_rank_fails_closed(field: str) -> None:
    rows = load_rows()
    by_symbol = {row["instrument"]: row for row in rows}
    by_symbol["TW5351"][field] = 2
    with pytest.raises(StrategyContractError, match="rank"):
        decide(rows, [], CANONICAL_CONFIG)

    rows = load_rows()
    by_symbol = {row["instrument"]: row for row in rows}
    by_symbol["TW5351"]["candidate_rank"] = 151
    by_symbol["TW5351"]["full_qlib_rank"] = 151
    with pytest.raises(StrategyContractError, match="candidate ranks 1..50"):
        decide(rows, [], CANONICAL_CONFIG)


@pytest.mark.parametrize(
    ("held", "expected_buy"),
    [
        ((), "TW5351"),
        (("TW5351",), "TW3260"),
        (
            (
                "TW5351",
                "TW3260",
                "TW6139",
                "TW6443",
                "TW2327",
                "TW3264",
                "TW6510",
                "TW6770",
                "TW2485",
                "TW2891",
            ),
            None,
        ),
    ],
)
def test_empty_and_partial_portfolio_fill_at_most_one_slot(
    held: tuple[str, ...], expected_buy: str | None
) -> None:
    decision = decide(load_rows(), portfolio(*held), CANONICAL_CONFIG)
    assert decision.buy == (() if expected_buy is None else (expected_buy,))


def test_missing_held_symbol_rank_fails_closed() -> None:
    with pytest.raises(StrategyContractError, match="lacks same-day full-rank visibility"):
        decide(load_rows(), portfolio("TW9999"), CANONICAL_CONFIG)


def test_portfolio_over_target_count_fails_closed() -> None:
    rows = load_rows()
    held = [
        row["instrument"]
        for row in sorted(rows, key=lambda row: row["candidate_rank"])
    ][:11]
    with pytest.raises(StrategyContractError, match="exceeds target_holding_count"):
        decide(rows, portfolio(*held), CANONICAL_CONFIG)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda rows: rows.append(dict(rows[0])), "duplicate model signal instrument"),
        (lambda rows: rows[0].update(available_at="2026-01-07"), "not PIT available"),
        (lambda rows: rows[0].update(execution_price=100), "forbidden fields"),
        (lambda rows: rows[0].update(future_return_5d=0.2), "forbidden fields"),
        (lambda rows: rows[0].update(candidate_rank=True), "integer, not bool"),
    ],
)
def test_signal_contract_rejects_unsafe_rows(mutation, message: str) -> None:
    rows = load_rows()
    mutation(rows)
    with pytest.raises(StrategyContractError, match=message):
        decide(rows, [], CANONICAL_CONFIG)


def test_portfolio_contract_rejects_strict_bool_and_future_asof() -> None:
    state = portfolio("TW5351")
    state[0]["current_holding_flag"] = 1
    with pytest.raises(StrategyContractError, match="must be bool"):
        decide(load_rows(), state, CANONICAL_CONFIG)

    with pytest.raises(StrategyContractError, match="after the signal date"):
        decide(load_rows(), portfolio("TW5351", asof="2026-01-07"), CANONICAL_CONFIG)


@pytest.mark.parametrize(
    "bad_config, message",
    [
        (config(strategy_rule="unknown"), "strategy_rule"),
        (config(candidate_k=49), "candidate_k"),
        (config(allow_diagnostic_rule=0), "allow_diagnostic_rule"),
        ({**config(), "unknown": True}, "unknown=unknown"),
    ],
)
def test_unknown_or_noncanonical_config_fails_closed(bad_config, message: str) -> None:
    with pytest.raises(StrategyContractError, match=message):
        decide(load_rows(), [], bad_config)


def test_real_fixture_matches_legacy_pre_execution_choice_without_pending_state() -> None:
    rows = load_rows()
    holdings = portfolio("TW8021", "TW2408")
    decision = decide(rows, holdings, CANONICAL_CONFIG)
    legacy = load_legacy_replay()

    candidate_rows = [row for row in rows if int(row["candidate_rank"]) <= 50]
    legacy_state = {
        "candidate_set": {row["instrument"] for row in candidate_rows},
        "target_top10": {
            row["instrument"]
            for row in sorted(
                candidate_rows,
                key=lambda row: (-float(row["buy_score"]), row["instrument"]),
            )[:10]
        },
        "buy_rank": {
            row["instrument"]: index + 1
            for index, row in enumerate(
                sorted(
                    candidate_rows,
                    key=lambda row: (-float(row["buy_score"]), row["instrument"]),
                )
            )
        },
        "full_rank": {
            row["instrument"]: int(row["full_qlib_rank"]) for row in rows
        },
    }
    legacy_sell = legacy.choose_sells(
        "top50_exit_one_worst_sell",
        {row["instrument"]: row["quantity"] for row in holdings},
        legacy_state,
    )
    legacy_buy = next(
        symbol
        for symbol, _ in sorted(legacy_state["buy_rank"].items(), key=lambda item: item[1])
        if symbol not in {row["instrument"] for row in holdings} - set(legacy_sell)
    )

    assert decision.sell == tuple(legacy_sell) == ("TW2408",)
    assert decision.buy == (legacy_buy,) == ("TW5351",)
    assert decision.model_name == ACTIVE_MODEL_ID


def test_kernel_has_no_runtime_or_dataframe_dependencies() -> None:
    source = (ROOT / "tw_stock_strategy/top50_exit_one_worst_sell.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("pandas", "pathlib", "datetime.now", "price_store", "pending_order")
    assert all(token not in source for token in forbidden)
