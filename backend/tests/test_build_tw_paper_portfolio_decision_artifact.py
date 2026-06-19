from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_tw_paper_portfolio_decision_artifact.py"
SPEC = importlib.util.spec_from_file_location("build_tw_paper_portfolio_decision_artifact", SCRIPT_PATH)
build_tw_paper = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["build_tw_paper_portfolio_decision_artifact"] = build_tw_paper
SPEC.loader.exec_module(build_tw_paper)


def _write_signal_artifact(tmp_path: Path) -> Path:
    signal_dir = tmp_path / "signal"
    signal_dir.mkdir()
    signal_path = signal_dir / "signals.csv"
    with signal_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "date",
                "instrument",
                "model_name",
                "candidate_rank",
                "buy_score",
                "score_rank",
                "full_qlib_rank",
                "signal_asof",
                "available_at",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "date": "2026-06-17",
            "instrument": "TW1111",
            "model_name": build_tw_paper.MODEL,
            "candidate_rank": 1,
            "buy_score": 0.90,
            "score_rank": 1,
            "full_qlib_rank": 1,
            "signal_asof": "2026-06-17",
            "available_at": "2026-06-17",
        })
        writer.writerow({
            "date": "2026-06-17",
            "instrument": "TW2222",
            "model_name": build_tw_paper.MODEL,
            "candidate_rank": 2,
            "buy_score": 0.10,
            "score_rank": 2,
            "full_qlib_rank": 2,
            "signal_asof": "2026-06-17",
            "available_at": "2026-06-17",
        })
    manifest = {
        "artifact_type": "daily_model_signal",
        "schema_version": "u1.daily_model_signal.v1",
        "asof_date": "2026-06-17",
        "model_id": build_tw_paper.MODEL,
        "model_name": build_tw_paper.MODEL,
        "candidate_k": 50,
        "files": {"signals": "signals.csv"},
    }
    manifest_path = signal_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_builds_readonly_paper_decision_bundle_from_fixture(tmp_path: Path):
    signal_manifest = _write_signal_artifact(tmp_path)
    account_json = tmp_path / "paper_account.json"
    account_json.write_text(
        json.dumps({
            "account": {
                "account_uid": "tw_sim_fixture",
                "user_id": 7,
                "currency": "TWD",
                "initial_cash": 500000,
                "cash": 200000,
                "paper_account_epoch": 1,
            },
            "positions": [
                {"symbol": "9999", "quantity": 1000, "avg_cost": 50, "cost_value": 50000}
            ],
            "prices": {
                "9999": {"last_price": 80, "price_date": "2026-06-17", "source": "fixture"},
                "1111": {"last_price": 10, "price_date": "2026-06-17", "source": "fixture"},
            },
        }),
        encoding="utf-8",
    )
    account_state = build_tw_paper.load_account_state_from_json(account_json)

    result = build_tw_paper.build_artifact(
        account_state=account_state,
        signal_manifest_path=signal_manifest,
        strategy_path=Path("configs/strategy_dependencies/top50_exit_one_worst_sell.yaml"),
        out_root=tmp_path / "out",
        run_id="x1_test",
        lot_size=10,
        target_holding_count=1,
    )

    assert result["ok"] is True
    out_dir = tmp_path / "out" / "x1_test"
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((out_dir / "paper_portfolio_state.json").read_text(encoding="utf-8"))
    intent = json.loads((out_dir / "paper_order_intent.json").read_text(encoding="utf-8"))
    preview = json.loads((out_dir / "paper_apply_preview.json").read_text(encoding="utf-8"))
    forbidden = json.loads((out_dir / "forbidden_action_audit.json").read_text(encoding="utf-8"))

    assert manifest["readonly_only"] is True
    assert manifest["not_applied"] is True
    assert state["paper_account_id"] == "tw_sim_fixture"
    assert state["positions"][0]["instrument"] == "TW9999"
    assert manifest["action_counts"] == {"paper_buy_intent": 1, "paper_sell_intent": 1, "paper_skip": 0}
    actions = {item["action_type"]: item for item in intent["actions"]}
    assert actions["paper_sell_intent"]["symbol"] == "9999"
    assert actions["paper_buy_intent"]["symbol"] == "1111"
    assert actions["paper_buy_intent"]["applicability"] == "applicable"
    assert preview["readonly_preview_only"] is True
    assert preview["not_applied"] is True
    assert all(value is False for value in forbidden["actions"].values())


def test_main_writes_fixture_artifact_without_account_writes(tmp_path: Path):
    signal_manifest = _write_signal_artifact(tmp_path)
    account_json = tmp_path / "paper_account.json"
    account_json.write_text(
        json.dumps({
            "account": {"account_uid": "tw_sim_fixture", "user_id": 7, "currency": "TWD", "initial_cash": 100000, "cash": 100000},
            "positions": [],
            "prices": {"1111": 10},
        }),
        encoding="utf-8",
    )

    exit_code = build_tw_paper.main([
        "--paper-account-json",
        str(account_json),
        "--model-signal",
        str(signal_manifest),
        "--out-root",
        str(tmp_path / "out"),
        "--run-id",
        "x1_cli_test",
        "--target-holding-count",
        "1",
        "--json",
    ])

    assert exit_code == 0
    manifest = json.loads((tmp_path / "out" / "x1_cli_test" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["no_broker_order"] is True
    assert manifest["no_quick_trade"] is True


def _write_empty_signal_artifact(tmp_path: Path) -> Path:
    signal_dir = tmp_path / "empty_signal"
    signal_dir.mkdir()
    signal_path = signal_dir / "signals.csv"
    with signal_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "instrument", "candidate_rank", "buy_score", "score_rank", "full_qlib_rank"])
        writer.writeheader()
    manifest = {
        "artifact_type": "daily_model_signal",
        "schema_version": "u1.daily_model_signal.v1",
        "asof_date": "2026-06-17",
        "model_id": build_tw_paper.MODEL,
        "model_name": build_tw_paper.MODEL,
        "candidate_k": 50,
        "files": {"signals": "signals.csv"},
    }
    manifest_path = signal_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _build_with_account(tmp_path: Path, account_payload: dict, signal_manifest: Path | None = None):
    account_json = tmp_path / "paper_account_case.json"
    account_json.write_text(json.dumps(account_payload), encoding="utf-8")
    account_state = build_tw_paper.load_account_state_from_json(account_json)
    result = build_tw_paper.build_artifact(
        account_state=account_state,
        signal_manifest_path=signal_manifest or _write_signal_artifact(tmp_path),
        strategy_path=Path("configs/strategy_dependencies/top50_exit_one_worst_sell.yaml"),
        out_root=tmp_path / "out_case",
        run_id="case",
        lot_size=10,
        target_holding_count=1,
    )
    out_dir = tmp_path / "out_case" / "case"
    return result, {
        "manifest": json.loads((out_dir / "manifest.json").read_text(encoding="utf-8")),
        "intent": json.loads((out_dir / "paper_order_intent.json").read_text(encoding="utf-8")),
        "preview": json.loads((out_dir / "paper_apply_preview.json").read_text(encoding="utf-8")),
        "forbidden": json.loads((out_dir / "forbidden_action_audit.json").read_text(encoding="utf-8")),
    }


def test_unavailable_sell_does_not_release_slot_or_trigger_buy(tmp_path: Path):
    _, files = _build_with_account(tmp_path, {
        "account": {"account_uid": "tw_sim_fixture", "user_id": 7, "currency": "TWD", "initial_cash": 500000, "cash": 200000},
        "positions": [{"symbol": "9999", "quantity": 1000, "avg_cost": 50, "cost_value": 50000}],
        "prices": {"1111": {"last_price": 10, "price_date": "2026-06-17", "source": "fixture"}},
    })

    actions = files["intent"]["actions"]
    assert files["manifest"]["action_counts"]["paper_sell_intent"] == 1
    assert files["manifest"]["action_counts"]["paper_buy_intent"] == 0
    sell = next(item for item in actions if item["action_type"] == "paper_sell_intent")
    assert sell["applicability"] == "unavailable"
    assert files["preview"]["cash_after_preview"] == 200000.0
    assert all(value is False for value in files["forbidden"]["actions"].values())


def test_missing_buy_price_outputs_unavailable_buy_preview(tmp_path: Path):
    _, files = _build_with_account(tmp_path, {
        "account": {"account_uid": "tw_sim_fixture", "user_id": 7, "currency": "TWD", "initial_cash": 500000, "cash": 200000},
        "positions": [{"symbol": "9999", "quantity": 1000, "avg_cost": 50, "cost_value": 50000}],
        "prices": {"9999": {"last_price": 80, "price_date": "2026-06-17", "source": "fixture"}},
    })

    actions = {item["action_type"]: item for item in files["intent"]["actions"]}
    assert files["manifest"]["action_counts"]["paper_sell_intent"] == 1
    assert files["manifest"]["action_counts"]["paper_buy_intent"] == 1
    assert actions["paper_sell_intent"]["applicability"] == "applicable"
    assert actions["paper_buy_intent"]["applicability"] == "unavailable"
    assert actions["paper_buy_intent"]["reason"] == "missing_reference_price"


def test_empty_signal_rows_keep_sell_only_semantics(tmp_path: Path):
    _, files = _build_with_account(tmp_path, {
        "account": {"account_uid": "tw_sim_fixture", "user_id": 7, "currency": "TWD", "initial_cash": 500000, "cash": 200000},
        "positions": [{"symbol": "9999", "quantity": 1000, "avg_cost": 50, "cost_value": 50000}],
        "prices": {"9999": {"last_price": 80, "price_date": "2026-06-17", "source": "fixture"}},
    }, signal_manifest=_write_empty_signal_artifact(tmp_path))

    assert files["manifest"]["action_counts"] == {"paper_buy_intent": 0, "paper_sell_intent": 1, "paper_skip": 0}
    assert files["intent"]["actions"][0]["action_type"] == "paper_sell_intent"
    assert files["intent"]["actions"][0]["applicability"] == "applicable"


def test_db_loader_and_price_fill_execute_select_only(monkeypatch):
    sys.path.insert(0, str(build_tw_paper.ROOT / "backend"))
    import app.utils.db as db_mod

    executed_verbs = []

    class Cursor:
        def __init__(self):
            self.row = None
            self.rows = []

        def execute(self, sql, params=None):
            verb = str(sql).strip().split()[0].upper()
            executed_verbs.append(verb)
            assert verb == "SELECT"
            if "FROM qd_tw_sim_accounts" in sql:
                self.row = {"account_uid": "tw_sim_db", "user_id": 7, "currency": "TWD", "initial_cash": 100000, "cash": 90000}
                self.rows = []
            elif "FROM qd_tw_sim_positions" in sql:
                self.row = None
                self.rows = [{"symbol": "9999", "quantity": 10, "avg_cost": 50, "cost_value": 500}]
            elif "FROM qd_tw_stock_daily_bars" in sql:
                symbol = (params or [""])[0]
                self.row = {"symbol": symbol, "trade_date": "2026-06-17", "close": 80, "source": "mock"}
                self.rows = []
            else:
                raise AssertionError(f"unexpected SQL: {sql}")

        def fetchone(self):
            return self.row

        def fetchall(self):
            return self.rows

        def close(self):
            pass

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(db_mod, "get_db_connection", lambda: Conn())

    state = build_tw_paper.load_account_state_from_db(account_uid="tw_sim_db", user_id=7)
    prices = build_tw_paper.fill_missing_prices_from_db(state["prices"], ["TW1111"])

    assert state["account"]["account_uid"] == "tw_sim_db"
    assert prices["1111"]["last_price"] == 80.0
    assert executed_verbs
    assert set(executed_verbs) == {"SELECT"}
