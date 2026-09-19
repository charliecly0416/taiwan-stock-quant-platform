from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.services.tw_stock_paper_portfolio import STRATEGY_RULE, TWStockPaperPortfolioService, _canonical_checksum

CLEAN_MODEL_A = "e4_frozen_qlib_2018_2022"
CLEAN_MODEL_B = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
OLD_MODEL = "e4_frozen_qlib_2023_2025_ltr"


def price_ready_status(**_kwargs):
    return {
        "execution_price_mode": "next_open",
        "execution_price_status": "pass",
        "paper_apply_allowed": True,
        "execution_price_readiness": {
            "next_open_available_count": 50,
            "missing_next_open_count": 0,
            "no_fallback_to_next_close": True,
            "no_fallback_to_signal_close": True,
        },
    }


def price_pending_status(**_kwargs):
    return {
        "execution_price_mode": "next_open",
        "execution_price_status": "execution_price_unavailable",
        "paper_apply_allowed": False,
        "paper_apply_blocked_reason": "next_open_unavailable",
        "execution_price_readiness": {
            "next_open_available_count": 0,
            "missing_next_open_count": 50,
            "no_fallback_to_next_close": True,
            "no_fallback_to_signal_close": True,
            "blocked_reason": "next_open_unavailable",
        },
    }


class X2Cursor:
    def __init__(self, db):
        self.db = db
        self.row = None
        self.rows = []

    def execute(self, sql, params=None):
        compact = " ".join(str(sql).split())
        self.db.sql.append(compact)
        params = tuple(params or ())
        self.row = None
        self.rows = []
        if compact.startswith("ALTER TABLE") or compact.startswith("CREATE TABLE") or compact.startswith("CREATE UNIQUE INDEX"):
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_accounts"):
            uid, user_id = params
            row = self.db.accounts.get(uid)
            self.row = dict(row) if row and row["user_id"] == user_id and not row.get("archived") else None
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND quantity > 0"):
            uid = params[0]
            self.rows = [dict(row) for row in self.db.positions.values() if row["account_uid"] == uid and row["quantity"] > 0]
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_apply_runs WHERE user_id = ? AND paper_account_id"):
            user_id, account_id, limit = params
            self.rows = [dict(row) for row in self.db.apply_runs if row["user_id"] == user_id and row["paper_account_id"] == account_id][:limit]
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_apply_runs WHERE user_id = ? AND idempotency_key"):
            user_id, key = params
            rows = [r for r in self.db.apply_runs if r["user_id"] == user_id and r["idempotency_key"] == key]
            self.row = dict(rows[-1]) if rows else None
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_apply_runs WHERE decision_id"):
            decision_id, account_id, epoch = params
            rows = [r for r in self.db.apply_runs if r["decision_id"] == decision_id and r["paper_account_id"] == account_id and r["paper_account_epoch"] == epoch]
            self.row = dict(rows[-1]) if rows else None
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_apply_runs WHERE paper_account_id = ? AND paper_account_epoch"):
            account_id, epoch = params
            self.rows = [dict(r) for r in self.db.apply_runs if r["paper_account_id"] == account_id and r["paper_account_epoch"] == epoch]
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_reset_runs WHERE user_id"):
            user_id, key = params
            rows = [r for r in self.db.reset_runs if r["user_id"] == user_id and r["idempotency_key"] == key]
            self.row = dict(rows[-1]) if rows else None
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?"):
            uid, symbol = params
            row = self.db.positions.get((uid, symbol))
            self.row = dict(row) if row else None
            return
        if compact.startswith("UPDATE qd_tw_sim_positions SET quantity"):
            quantity, value2, value3, *rest = params
            if len(rest) == 3:
                avg_cost, cost_value, updated_at = value2, value3, rest[0]
                uid, symbol = rest[1], rest[2]
                self.db.positions[(uid, symbol)].update({"quantity": int(quantity), "avg_cost": Decimal(str(avg_cost)), "cost_value": Decimal(str(cost_value)), "updated_at": updated_at})
            else:
                cost_value, updated_at, uid, symbol = value2, value3, rest[0], rest[1]
                self.db.positions[(uid, symbol)].update({"quantity": int(quantity), "cost_value": Decimal(str(cost_value)), "updated_at": updated_at})
            return
        if compact.startswith("INSERT INTO qd_tw_sim_positions"):
            uid, symbol, qty, avg_cost, cost_value, created_at, updated_at = params
            self.db.positions[(uid, symbol)] = {"account_uid": uid, "symbol": symbol, "quantity": int(qty), "avg_cost": Decimal(str(avg_cost)), "cost_value": Decimal(str(cost_value)), "simulation_only": True, "created_at": created_at, "updated_at": updated_at}
            return
        if compact.startswith("UPDATE qd_tw_sim_accounts SET cash = ?, updated_at"):
            cash, updated_at, uid = params
            self.db.accounts[uid]["cash"] = Decimal(str(cash))
            self.db.accounts[uid]["updated_at"] = updated_at
            return
        if compact.startswith("INSERT INTO qd_tw_sim_orders"):
            self.db.orders.append({"sql": compact, "params": params, "account_uid": params[1], "symbol": params[3], "side": params[4], "quantity": params[5], "status": "filled"})
            return
        if compact.startswith("INSERT INTO qd_tw_sim_trades"):
            self.db.trades.append({"sql": compact, "params": params, "account_uid": params[2], "symbol": params[4], "side": params[5], "quantity": params[6]})
            return
        if compact.startswith("INSERT INTO qd_tw_sim_apply_runs"):
            apply_id, decision_id, account_id, user_id, epoch, key, checksum, status, request_json, result_json, created_at, applied_at = params
            self.db.apply_runs.append({"id": len(self.db.apply_runs) + 1, "apply_id": apply_id, "decision_id": decision_id, "paper_account_id": account_id, "user_id": user_id, "paper_account_epoch": epoch, "idempotency_key": key, "input_checksum": checksum, "status": status, "already_applied": False, "request_json": request_json, "result_json": result_json, "created_at": created_at, "applied_at": applied_at})
            return
        if compact.startswith("INSERT INTO qd_tw_sim_audit_log"):
            self.db.audit.append({"params": params})
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_orders WHERE account_uid"):
            uid = params[0]
            self.rows = [dict(row) for row in self.db.orders if row.get("account_uid") == uid]
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_trades WHERE account_uid"):
            uid = params[0]
            self.rows = [dict(row) for row in self.db.trades if row.get("account_uid") == uid]
            return
        if compact.startswith("DELETE FROM qd_tw_sim_positions"):
            uid = params[0]
            for key in list(self.db.positions):
                if key[0] == uid:
                    del self.db.positions[key]
            return
        if compact.startswith("UPDATE qd_tw_sim_orders SET status = 'cancelled'"):
            return
        if compact.startswith("UPDATE qd_tw_sim_accounts SET cash = ?, paper_account_epoch"):
            cash, epoch, updated_at, uid, user_id = params
            self.db.accounts[uid].update({"cash": Decimal(str(cash)), "paper_account_epoch": int(epoch), "updated_at": updated_at, "archived": False})
            return
        if compact.startswith("INSERT INTO qd_tw_sim_reset_runs"):
            reset_id, account_id, user_id, previous_epoch, new_epoch, key, checksum, archive_json, result_json, created_at, reset_at = params
            self.db.reset_runs.append({"id": len(self.db.reset_runs) + 1, "reset_id": reset_id, "paper_account_id": account_id, "user_id": user_id, "previous_epoch": previous_epoch, "new_epoch": new_epoch, "idempotency_key": key, "input_checksum": checksum, "archive_snapshot_json": archive_json, "result_json": result_json, "created_at": created_at, "reset_at": reset_at})
            return
        if compact.startswith("SELECT * FROM qd_tw_sim_apply_runs WHERE user_id = ? ORDER"):
            user_id, limit = params
            self.rows = [dict(row) for row in self.db.apply_runs if row["user_id"] == user_id][:limit]
            return
        raise AssertionError(f"Unhandled SQL: {compact}")

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class X2Db:
    def __init__(self):
        self.accounts = {}
        self.positions = {}
        self.orders = []
        self.trades = []
        self.apply_runs = []
        self.reset_runs = []
        self.audit = []
        self.sql = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return X2Cursor(self)

    def commit(self):
        self.commits += 1


def make_service(db, *, artifact_root=None, allow_inline=True, status_loader=price_ready_status):
    return TWStockPaperPortfolioService(
        db_factory=lambda: db,
        now_fn=lambda: datetime.fromisoformat("2026-06-18T09:00:00"),
        artifact_root=artifact_root or Path("data_tw/artifacts/paper_portfolio"),
        allow_inline_intent=allow_inline,
        productization_status_loader=status_loader,
    )


def seed_account(db, epoch=1, cash="200000"):
    db.accounts["tw_sim_1"] = {"account_uid": "tw_sim_1", "user_id": 7, "currency": "TWD", "initial_cash": Decimal("500000"), "cash": Decimal(str(cash)), "paper_account_epoch": epoch, "simulation_only": True, "archived": False}
    db.positions[("tw_sim_1", "9999")] = {"account_uid": "tw_sim_1", "symbol": "9999", "quantity": 1000, "avg_cost": Decimal("50"), "cost_value": Decimal("50000"), "simulation_only": True}


def intent(decision_id="decision-1", epoch=1, actions=None, checksum="checksum-1", model_id=CLEAN_MODEL_A, strategy_rule=STRATEGY_RULE, execution_price_mode="next_open"):
    return {"artifact_type": "PaperOrderIntentArtifact", "schema_version": "phase_x.paper_order_intent.v1", "decision_id": decision_id, "model_id": model_id, "strategy_rule": strategy_rule, "paper_account_id": "tw_sim_1", "user_id": 7, "paper_account_epoch": epoch, "asof": "2026-06-18", "input_checksum": checksum, "readonly_decision_only": True, "not_real_order": True, "not_target_position": True, "not_investment_advice": True, "execution_price_mode": execution_price_mode, "actions": actions or []}


def apply_payload(decision_id="decision-1", key="idem-1", epoch=1, actions=None, checksum="checksum-1", model_id=CLEAN_MODEL_A, strategy_rule=STRATEGY_RULE):
    return {"paper_account_id": "tw_sim_1", "paper_account_epoch": epoch, "decision_id": decision_id, "idempotency_key": key, "input_checksum": checksum, "confirmed_by_user": True, "confirm_text": "确认应用到模拟账户", "paper_order_intent": intent(decision_id=decision_id, epoch=epoch, actions=actions, checksum=checksum, model_id=model_id, strategy_rule=strategy_rule)}


def sell_action(qty=1000, price=80, applicable="applicable"):
    return {"action_type": "paper_sell_intent", "symbol": "9999", "quantity": qty, "estimated_reference_price": price, "price_date": "2026-06-18", "applicability": applicable}


def buy_action(qty=10, price=100, applicable="applicable"):
    return {"action_type": "paper_buy_intent", "symbol": "1111", "quantity": qty, "estimated_reference_price": price, "price_date": "2026-06-18", "applicability": applicable}


def test_apply_happy_path_writes_paper_only_tables_and_audit():
    db = X2Db(); seed_account(db)
    service = make_service(db)
    result = service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action(), buy_action()]))
    assert result["ok"] is True
    assert result["status"] == "applied"
    assert len(result["paper_executions"]) == 2
    assert len(db.orders) == 2 and len(db.trades) == 2
    assert len(db.apply_runs) == 1 and len(db.audit) == 1
    assert json.loads(db.apply_runs[0]["request_json"])["paper_only"] is True
    assert result["paper_only"] is True
    assert db.accounts["tw_sim_1"]["paper_account_epoch"] == 1
    forbidden = " ".join(db.sql).lower()
    for item in ["quick-trade", "quick_trade", "broker", "provider_publish", "monitor/scan"]:
        assert item not in forbidden


def test_apply_duplicate_same_idempotency_returns_existing_result_and_conflict_rejected():
    db = X2Db(); seed_account(db)
    service = make_service(db)
    first = service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action()]))
    replay = service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action()]))
    conflict = service.apply_decision(user_id=7, payload=apply_payload(key="idem-1", checksum="checksum-2", actions=[sell_action()]))
    assert first["ok"] is True
    assert replay["ok"] is True and replay["already_applied"] is True
    assert conflict["ok"] is False and conflict["status"] == "idempotency_conflict"
    audit_types = [row["params"][1] for row in db.audit]
    assert audit_types == ["apply_decision", "duplicate_replay", "rejected"]
    assert len(db.trades) == 1


def test_duplicate_decision_returns_already_applied_and_stale_epoch_rejected():
    db = X2Db(); seed_account(db)
    service = make_service(db)
    first = service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action()]))
    dup_decision = service.apply_decision(user_id=7, payload=apply_payload(key="idem-2", actions=[sell_action()]))
    same_day = service.apply_decision(user_id=7, payload=apply_payload(decision_id="decision-2", key="idem-2b", checksum="checksum-2b", actions=[sell_action()]))
    stale = service.apply_decision(user_id=7, payload=apply_payload(decision_id="decision-old", key="idem-old", epoch=0, actions=[sell_action()]))
    assert first["ok"] is True
    assert dup_decision["ok"] is True and dup_decision["already_applied"] is True
    assert same_day["ok"] is False and same_day["status"] == "same_day_apply_rejected"
    assert stale["ok"] is False and stale["status"] == "stale_epoch"
    audit_statuses = [row["params"][10] for row in db.audit]
    assert audit_statuses == ["applied", "already_applied", "same_day_apply_rejected", "stale_epoch"]


def test_unavailable_cash_insufficient_and_oversell_actions_do_not_execute():
    db = X2Db(); seed_account(db, cash="100")
    service = make_service(db)
    result = service.apply_decision(user_id=7, payload=apply_payload(actions=[buy_action(qty=10, price=100), sell_action(qty=2000), buy_action(applicable="unavailable")]))
    assert result["ok"] is True
    assert result["paper_executions"] == []
    reasons = {item["reason"] for item in result["rejected_actions"] + result["skipped_actions"]}
    assert {"cash_insufficient", "oversell", "action_unavailable"}.issubset(reasons)
    assert db.trades == []


def test_reset_archives_previous_state_increments_epoch_and_duplicate_replays():
    db = X2Db(); seed_account(db)
    service = make_service(db)
    reset_payload = {"paper_account_id": "tw_sim_1", "current_epoch": 1, "idempotency_key": "reset-1", "input_checksum": "reset-checksum", "confirmed_by_user": True, "confirm_text": "确认重置模拟账户"}
    result = service.reset(user_id=7, payload=reset_payload)
    replay = service.reset(user_id=7, payload=reset_payload)
    assert result["ok"] is True and result["new_epoch"] == 2 and result["paper_only"] is True
    assert result["archive_snapshot"]["positions"]
    assert db.accounts["tw_sim_1"]["paper_account_epoch"] == 2
    assert db.positions == {}
    assert replay["ok"] is True and replay["already_reset"] is True
    old_apply = service.apply_decision(user_id=7, payload=apply_payload(decision_id="after-reset-old", key="idem-after-reset", epoch=1, actions=[sell_action()]))
    assert old_apply["ok"] is False and old_apply["status"] == "stale_epoch"
    audit_types = [row["params"][1] for row in db.audit]
    assert audit_types == ["reset_account", "duplicate_replay", "rejected"]


def test_state_and_apply_runs_are_user_scoped():
    db = X2Db(); seed_account(db)
    service = make_service(db)
    assert service.state(user_id=8, paper_account_id="tw_sim_1")["status"] == "not_found"
    service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action()]))
    runs = service.apply_runs(user_id=7, paper_account_id="tw_sim_1")
    assert runs["ok"] is True and runs["count"] == 1



def _write_authoritative_artifact(root: Path, *, run_id="run1", decision_id="decision-artifact-1", account_id="tw_sim_1", user_id=7, epoch=1, asof="2026-06-18", actions=None, state_checksum="sha256:portfolio-state", model_id=CLEAN_MODEL_A, strategy_rule=STRATEGY_RULE, execution_price_mode="next_open"):
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {"artifact_type": "PaperPortfolioStateArtifact", "checksum": state_checksum, "paper_account_id": account_id, "paper_account_epoch": epoch}
    actions = actions if actions is not None else [sell_action()]
    input_payload = {
        "portfolio_state_checksum": state_checksum,
        "source_model_signal_artifact": "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json",
        "strategy_rule": STRATEGY_RULE,
        "asof": asof,
        "actions": actions,
    }
    checksum = _canonical_checksum(input_payload)
    intent_payload = {
        "artifact_type": "PaperOrderIntentArtifact",
        "schema_version": "phase_x.paper_order_intent.v1",
        "decision_id": decision_id,
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "paper_account_id": account_id,
        "user_id": user_id,
        "paper_account_epoch": epoch,
        "asof": asof,
        "source_portfolio_state_artifact": "paper_portfolio_state.json",
        "source_model_signal_artifact": input_payload["source_model_signal_artifact"],
        "input_checksum": checksum,
        "readonly_decision_only": True,
        "not_real_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "execution_price_mode": execution_price_mode,
        "actions": actions,
    }
    preview_payload = {
        "artifact_type": "PaperApplyPreviewArtifact",
        "decision_id": decision_id,
        "paper_account_id": account_id,
        "paper_account_epoch": epoch,
        "asof": asof,
        "cash_before": 200000,
        "cash_after_preview": 279657.0,
        "preview_rows": actions,
        "readonly_preview_only": True,
        "not_applied": True,
        "not_real_order": True,
    }
    manifest = {
        "artifact_type": "PaperDecisionBundleArtifact",
        "schema_version": "phase_x.paper_decision_bundle.v1",
        "run_id": run_id,
        "created_at": "2026-06-18T09:00:00+00:00",
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "paper_account_id": account_id,
        "user_id": user_id,
        "paper_account_epoch": epoch,
        "asof": asof,
        "input_checksum": checksum,
        "execution_price_mode": execution_price_mode,
        "decision_id": decision_id,
        "files": {
            "paper_portfolio_state": "paper_portfolio_state.json",
            "paper_order_intent": "paper_order_intent.json",
            "paper_apply_preview": "paper_apply_preview.json",
        },
    }
    (run_dir / "paper_portfolio_state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    (run_dir / "paper_order_intent.json").write_text(json.dumps(intent_payload, ensure_ascii=False), encoding="utf-8")
    (run_dir / "paper_apply_preview.json").write_text(json.dumps(preview_payload, ensure_ascii=False), encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return intent_payload, f"{run_id}/paper_order_intent.json"


def _artifact_apply_payload(intent_payload, artifact_path, *, key="artifact-idem"):
    return {
        "paper_account_id": intent_payload["paper_account_id"],
        "paper_account_epoch": intent_payload["paper_account_epoch"],
        "decision_id": intent_payload["decision_id"],
        "idempotency_key": key,
        "input_checksum": intent_payload["input_checksum"],
        "paper_order_intent_artifact_path": artifact_path,
        "confirmed_by_user": True,
        "confirm_text": "确认应用到模拟账户",
    }


def test_inline_paper_order_intent_rejected_by_default(tmp_path: Path):
    db = X2Db(); seed_account(db)
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    result = service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action()]))
    assert result["ok"] is False
    assert result["status"] == "invalid_artifact"
    assert "artifact" in result["message"]


def test_authoritative_artifact_apply_success_and_checksum_mismatch(tmp_path: Path):
    db = X2Db(); seed_account(db)
    intent_payload, artifact_path = _write_authoritative_artifact(tmp_path, actions=[sell_action()])
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    result = service.apply_decision(user_id=7, payload=_artifact_apply_payload(intent_payload, artifact_path))
    mismatch = _artifact_apply_payload(intent_payload, artifact_path, key="artifact-idem-2")
    mismatch["input_checksum"] = "sha256:not-the-server-checksum"
    rejected = service.apply_decision(user_id=7, payload=mismatch)
    assert result["ok"] is True and result["status"] == "applied"
    assert rejected["ok"] is False and rejected["status"] == "invalid_artifact"


def test_authoritative_artifact_path_traversal_rejected(tmp_path: Path):
    db = X2Db(); seed_account(db)
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    payload = {"paper_account_id": "tw_sim_1", "paper_account_epoch": 1, "decision_id": "x", "idempotency_key": "k", "input_checksum": "sha256:x", "paper_order_intent_artifact_path": "../paper_order_intent.json", "confirmed_by_user": True, "confirm_text": "确认应用到模拟账户"}
    result = service.apply_decision(user_id=7, payload=payload)
    assert result["ok"] is False
    assert result["status"] == "invalid_artifact"


def test_same_day_rejects_after_previous_no_actions_run(tmp_path: Path):
    db = X2Db(); seed_account(db)
    first_intent, first_path = _write_authoritative_artifact(tmp_path, run_id="empty", decision_id="decision-empty", actions=[])
    second_intent, second_path = _write_authoritative_artifact(tmp_path, run_id="different", decision_id="decision-different", actions=[sell_action()], state_checksum="sha256:portfolio-state-2")
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    first = service.apply_decision(user_id=7, payload=_artifact_apply_payload(first_intent, first_path, key="idem-empty"))
    second = service.apply_decision(user_id=7, payload=_artifact_apply_payload(second_intent, second_path, key="idem-different"))
    assert first["ok"] is True and first["status"] == "no_actions"
    assert second["ok"] is False and second["status"] == "same_day_apply_rejected"


def test_user_scoping_blocks_other_users_authoritative_artifact(tmp_path: Path):
    db = X2Db(); seed_account(db)
    intent_payload, artifact_path = _write_authoritative_artifact(tmp_path, account_id="tw_sim_1", user_id=7, actions=[sell_action()])
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    result = service.apply_decision(user_id=8, payload=_artifact_apply_payload(intent_payload, artifact_path))
    assert result["ok"] is False
    assert result["status"] == "not_found"


def test_latest_decision_reads_manifest_preview_and_requires_user_account(tmp_path: Path):
    db = X2Db(); seed_account(db)
    intent_payload, artifact_path = _write_authoritative_artifact(tmp_path, run_id="latest", actions=[sell_action()])
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    result = service.latest_decision(user_id=7)
    assert result["ok"] is True
    assert result["decision_id"] == intent_payload["decision_id"]
    assert result["paper_order_intent_artifact_path"] == artifact_path
    assert result["preview"]["readonly_preview_only"] is True
    assert result["trading"]["real_orders_enabled"] is False
    assert service.latest_decision(user_id=8)["status"] == "no_clean_decision"


def test_validate_intent_accepts_model_a_and_rejects_shadow_or_legacy_models_and_bad_strategy():
    db = X2Db(); seed_account(db)
    service = make_service(db)
    accepted = intent(model_id=CLEAN_MODEL_A)
    assert service._validate_intent(accepted, paper_account_id="tw_sim_1", decision_id="decision-1", input_checksum="checksum-1") is None
    for model in [CLEAN_MODEL_B, OLD_MODEL]:
        rejected = intent(model_id=model)
        assert service._validate_intent(rejected, paper_account_id="tw_sim_1", decision_id="decision-1", input_checksum="checksum-1")["status"] == "invalid_artifact"
    research = intent(strategy_rule="one_sell_one_buy_buggy_e8r")
    assert service._validate_intent(research, paper_account_id="tw_sim_1", decision_id="decision-1", input_checksum="checksum-1")["status"] == "invalid_artifact"
    deprecated = intent(strategy_rule="original")
    assert service._validate_intent(deprecated, paper_account_id="tw_sim_1", decision_id="decision-1", input_checksum="checksum-1")["status"] == "invalid_artifact"


def test_apply_pending_execution_price_rejected_before_schema_and_writes():
    db = X2Db(); seed_account(db)
    service = make_service(db, status_loader=price_pending_status)
    result = service.apply_decision(user_id=7, payload=apply_payload(actions=[sell_action()]))
    assert result["ok"] is False
    assert result["status"] == "execution_price_unavailable"
    assert result["paper_apply_allowed"] is False
    assert db.apply_runs == []
    assert db.orders == []
    assert db.trades == []
    assert db.audit == []
    assert not any(sql.startswith("CREATE TABLE") or sql.startswith("ALTER TABLE") for sql in db.sql)


def test_latest_decision_filters_old_model_artifact(tmp_path: Path):
    db = X2Db(); seed_account(db)
    _write_authoritative_artifact(tmp_path, run_id="old", model_id=OLD_MODEL)
    service = make_service(db, artifact_root=tmp_path, allow_inline=False)
    result = service.latest_decision(user_id=7)
    assert result["ok"] is False
    assert result["status"] == "no_clean_decision"


def test_paper_portfolio_service_source_has_no_old_model_constant():
    source = Path("backend/app/services/tw_stock_paper_portfolio.py").read_text(encoding="utf-8")
    assert "MODEL_ID" not in source
    assert "e4_frozen_qlib_2023_2025_ltr" not in source
