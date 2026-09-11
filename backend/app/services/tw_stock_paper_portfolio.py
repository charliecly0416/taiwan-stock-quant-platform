"""Paper portfolio apply/reset service for Taiwan stock simulation accounts.

This service writes only to qd_tw_sim_* paper/simulation tables. It does not
call broker, quick-trade, real order, provider, monitor, Agent, or training
paths.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from app.services.phase_yz3_productization_status import load_yz3_productization_status
from app.services.tw_stock_artifact_registry import registry_get
from scripts.tw_daily_runtime_stages import runtime_truth
from app.services.tw_stock_sim_account import sim_trading_flags
from app.utils.db import get_db_connection

MONEY = Decimal("0.01")
PRICE = Decimal("0.0001")
FEE_RATE = Decimal("0.001425")
SELL_TAX_RATE = Decimal("0.003")
LOT_SIZE = 10
_RUNTIME_TRUTH = runtime_truth()
STRATEGY_RULE = _RUNTIME_TRUTH.strategy_rule
EXECUTION_PRICE_MODE = _RUNTIME_TRUTH.execution_price_mode
ARTIFACT_ROOT = Path(__file__).resolve().parents[3] / "data_tw" / "artifacts" / "paper_portfolio"
REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "configs" / "tw_modular_registry.yaml"
POLICY_PATH = REPO_ROOT / "configs" / "tw_replay_window_policy.yaml"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dec(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _money(value: Any) -> Decimal:
    return _dec(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _price(value: Any) -> Decimal:
    return _dec(value).quantize(PRICE, rounding=ROUND_HALF_UP)


def _float(value: Any) -> float:
    return float(_dec(value))


def _row(row: Any) -> Dict[str, Any]:
    return dict(row or {})


def _rows(rows: Any) -> List[Dict[str, Any]]:
    return [dict(item) for item in (rows or [])]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _canonical_checksum(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _loads(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if ":" in text:
        text = text.split(":", 1)[1]
    if text.startswith("TW"):
        text = text[2:]
    if "." in text:
        text = text.split(".", 1)[0]
    return text


class TWStockPaperPortfolioService:
    """Apply readonly paper decisions to simulation-only TWStock accounts."""

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any] = get_db_connection,
        now_fn: Callable[[], datetime] = _utc_now,
        artifact_root: Path | str = ARTIFACT_ROOT,
        allow_inline_intent: bool = False,
        productization_status_loader: Callable[..., Dict[str, Any]] = load_yz3_productization_status,
    ) -> None:
        self.db_factory = db_factory
        self.now_fn = now_fn
        self.artifact_root = Path(artifact_root)
        self.allow_inline_intent = bool(allow_inline_intent)
        self.productization_status_loader = productization_status_loader
        self._schema_ready = False
        self._policy_cache: Optional[Dict[str, set[str]]] = None

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with self.db_factory() as conn:
            cur = conn.cursor()
            cur.execute("ALTER TABLE qd_tw_sim_accounts ADD COLUMN IF NOT EXISTS paper_account_epoch INTEGER NOT NULL DEFAULT 1")
            cur.execute("ALTER TABLE qd_tw_sim_accounts ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_apply_runs (
                    id BIGSERIAL PRIMARY KEY,
                    apply_id VARCHAR(80) NOT NULL UNIQUE,
                    decision_id VARCHAR(120) NOT NULL,
                    paper_account_id VARCHAR(64) NOT NULL,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    paper_account_epoch INTEGER NOT NULL DEFAULT 1,
                    idempotency_key VARCHAR(160) NOT NULL,
                    input_checksum VARCHAR(160) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    already_applied BOOLEAN NOT NULL DEFAULT FALSE,
                    request_json TEXT NOT NULL DEFAULT '',
                    result_json TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW(),
                    applied_at TIMESTAMP
                )
                """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tw_sim_apply_decision_epoch ON qd_tw_sim_apply_runs(decision_id, paper_account_id, paper_account_epoch)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tw_sim_apply_idem ON qd_tw_sim_apply_runs(user_id, idempotency_key)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_reset_runs (
                    id BIGSERIAL PRIMARY KEY,
                    reset_id VARCHAR(80) NOT NULL UNIQUE,
                    paper_account_id VARCHAR(64) NOT NULL,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    previous_epoch INTEGER NOT NULL,
                    new_epoch INTEGER NOT NULL,
                    idempotency_key VARCHAR(160) NOT NULL,
                    input_checksum VARCHAR(160) NOT NULL,
                    archive_snapshot_json TEXT NOT NULL DEFAULT '',
                    result_json TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW(),
                    reset_at TIMESTAMP
                )
                """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tw_sim_reset_idem ON qd_tw_sim_reset_runs(user_id, idempotency_key)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS qd_tw_sim_audit_log (
                    id BIGSERIAL PRIMARY KEY,
                    event_id VARCHAR(80) NOT NULL UNIQUE,
                    event_type VARCHAR(40) NOT NULL,
                    paper_account_id VARCHAR(64) NOT NULL,
                    paper_account_epoch INTEGER NOT NULL DEFAULT 1,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    decision_id VARCHAR(120),
                    apply_id VARCHAR(80),
                    reset_id VARCHAR(80),
                    idempotency_key VARCHAR(160),
                    input_checksum VARCHAR(160),
                    result_status VARCHAR(40) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cur.close()
            conn.commit()
        self._schema_ready = True

    def state(self, *, user_id: int, paper_account_id: str) -> Dict[str, Any]:
        self.ensure_schema()
        with self.db_factory() as conn:
            cur = conn.cursor()
            account = self._account(cur, user_id=user_id, paper_account_id=paper_account_id)
            if not account:
                cur.close()
                return self._reject("not_found", "paper simulation account not found")
            positions = self._positions(cur, paper_account_id=paper_account_id)
            cur.close()
        return {"ok": True, "status": "ok", "paper_account": self._account_payload(account), "positions": positions, "simulation_only": True, "trading": sim_trading_flags()}

    def apply_runs(self, *, user_id: int, paper_account_id: str = "", limit: int = 100) -> Dict[str, Any]:
        self.ensure_schema()
        with self.db_factory() as conn:
            cur = conn.cursor()
            safe_limit = max(1, min(int(limit or 100), 500))
            if paper_account_id:
                cur.execute("SELECT * FROM qd_tw_sim_apply_runs WHERE user_id = ? AND paper_account_id = ? ORDER BY created_at DESC LIMIT ?", (int(user_id), paper_account_id, safe_limit))
            else:
                cur.execute("SELECT * FROM qd_tw_sim_apply_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (int(user_id), safe_limit))
            rows = _rows(cur.fetchall())
            cur.close()
        return {"ok": True, "status": "ok", "items": [self._apply_run_payload(row) for row in rows], "count": len(rows), "simulation_only": True, "trading": sim_trading_flags()}

    def latest_decision(self, *, user_id: int, paper_account_id: str = "") -> Dict[str, Any]:
        root = self.artifact_root.resolve()
        if not root.exists():
            return self._reject("no_decision", "paper decision artifact root not found", warnings=[str(root)])
        candidates: List[Dict[str, Any]] = []
        warnings: List[str] = []
        for manifest_path in root.rglob("manifest.json"):
            try:
                resolved = manifest_path.resolve()
                if root != resolved and root not in resolved.parents:
                    continue
                manifest = json.loads(resolved.read_text(encoding="utf-8"))
                if manifest.get("artifact_type") != "PaperDecisionBundleArtifact":
                    continue
                if not self._manifest_is_clean_decision(manifest):
                    warnings.append(f"skip non-clean paper decision manifest {resolved}")
                    continue
                if int(manifest.get("user_id") or -1) != int(user_id):
                    continue
                if paper_account_id and str(manifest.get("paper_account_id") or "") != paper_account_id:
                    continue
                candidates.append({"manifest_path": resolved, "manifest": manifest, "mtime": resolved.stat().st_mtime})
            except Exception as exc:
                warnings.append(f"skip invalid manifest {manifest_path}: {exc}")
        if not candidates:
            return self._reject("no_clean_decision", "no clean paper decision artifact found", warnings=warnings)
        candidates.sort(key=lambda item: (str(item["manifest"].get("created_at") or ""), item["mtime"]), reverse=True)
        selected = candidates[0]
        manifest_path = selected["manifest_path"]
        manifest = selected["manifest"]
        files = manifest.get("files") or {}
        intent_rel = files.get("paper_order_intent") or "paper_order_intent.json"
        preview_rel = files.get("paper_apply_preview") or "paper_apply_preview.json"
        intent_path = manifest_path.parent / intent_rel
        preview_path = manifest_path.parent / preview_rel
        try:
            intent_resolved = intent_path.resolve()
            if manifest_path.parent.resolve() != intent_resolved.parent:
                return self._reject("invalid_artifact", "paper_order_intent must stay beside manifest")
            intent = json.loads(intent_resolved.read_text(encoding="utf-8"))
            preview = json.loads(preview_path.resolve().read_text(encoding="utf-8")) if preview_path.exists() else {}
        except Exception as exc:
            return self._reject("invalid_artifact", f"failed to read paper decision artifact: {exc}")
        checksum, checksum_error = self._recompute_intent_input_checksum(intent, path=intent_resolved)
        if checksum_error:
            return checksum_error
        if str(intent.get("input_checksum") or "") != checksum:
            return self._reject("invalid_artifact", "paper decision checksum mismatch")
        artifact_error = self._validate_intent(
            intent,
            paper_account_id=str(intent.get("paper_account_id") or manifest.get("paper_account_id") or ""),
            decision_id=str(intent.get("decision_id") or manifest.get("decision_id") or ""),
            input_checksum=checksum,
        )
        if artifact_error:
            return self._reject("no_clean_decision", "latest paper decision artifact is not clean selectable", warnings=warnings + [artifact_error.get("message", "")])
        account_id = str(intent.get("paper_account_id") or manifest.get("paper_account_id") or "")
        with self.db_factory() as conn:
            cur = conn.cursor()
            account = self._account(cur, user_id=user_id, paper_account_id=account_id) if account_id else {}
            cur.close()
        if not account:
            return self._reject("no_account", "paper simulation account not found for latest decision", paper_account_id=account_id, warnings=warnings)
        artifact_path = str(intent_resolved.relative_to(root))
        return {
            "ok": True,
            "status": "ok",
            "asof": intent.get("asof") or manifest.get("asof"),
            "model_id": intent.get("model_id") or manifest.get("model_id"),
            "strategy_rule": intent.get("strategy_rule") or manifest.get("strategy_rule"),
            "decision_id": intent.get("decision_id") or manifest.get("decision_id"),
            "paper_account_id": account_id,
            "paper_account_epoch": int(intent.get("paper_account_epoch") or manifest.get("paper_account_epoch") or 0),
            "input_checksum": checksum,
            "paper_order_intent_artifact_path": artifact_path,
            "manifest_path": str(manifest_path.relative_to(root)),
            "preview": preview,
            "intent": intent,
            "warnings": warnings,
            "simulation_only": True,
            "trading": sim_trading_flags(),
        }

    def apply_decision(self, *, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        paper_account_id = str(payload.get("paper_account_id") or payload.get("paperAccountId") or "")
        idempotency_key = str(payload.get("idempotency_key") or payload.get("idempotencyKey") or "")
        input_checksum = str(payload.get("input_checksum") or payload.get("inputChecksum") or "")
        intent_result, artifact_error = self._authoritative_intent(payload)
        if artifact_error:
            return artifact_error
        intent = intent_result["intent"]
        server_checksum = str(intent_result["input_checksum"])
        decision_id = str(payload.get("decision_id") or payload.get("decisionId") or intent.get("decision_id") or "")
        requested_epoch = int(payload.get("paper_account_epoch") or payload.get("paperAccountEpoch") or intent.get("paper_account_epoch") or 0)
        if not paper_account_id or not decision_id or not idempotency_key or not input_checksum:
            return self._reject("invalid_request", "paper_account_id, decision_id, idempotency_key and input_checksum are required")
        if payload.get("confirmed_by_user") is not True:
            return self._reject("invalid_confirmation", "confirmed_by_user must be true")
        if "模拟" not in str(payload.get("confirm_text") or payload.get("confirmText") or ""):
            return self._reject("invalid_confirmation", "confirm_text must include 模拟")
        if input_checksum != server_checksum:
            return self._reject("invalid_artifact", "input_checksum mismatch with server artifact checksum")
        artifact_error = self._validate_intent(intent, paper_account_id=paper_account_id, decision_id=decision_id, input_checksum=input_checksum)
        if artifact_error:
            return artifact_error
        gate_error = self._execution_price_gate(intent)
        if gate_error:
            return gate_error
        if requested_epoch != int(intent.get("paper_account_epoch") or 0):
            return self._reject("invalid_artifact", "paper_account_epoch mismatch")

        self.ensure_schema()
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            account = self._account(cur, user_id=user_id, paper_account_id=paper_account_id)
            if not account:
                cur.close()
                return self._reject("not_found", "paper simulation account not found")
            current_epoch = int(account.get("paper_account_epoch") or 1)
            if requested_epoch != current_epoch:
                self._audit(cur, event_type="rejected", paper_account_id=paper_account_id, epoch=current_epoch, user_id=user_id, decision_id=decision_id, apply_id=None, reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="stale_epoch", created_at=now)
                cur.close()
                conn.commit()
                return self._reject("stale_epoch", "paper_account_epoch does not match current account epoch")
            existing_idem = self._find_apply_by_idempotency(cur, user_id=user_id, idempotency_key=idempotency_key)
            if existing_idem:
                existing_result = _loads(existing_idem.get("result_json"))
                if str(existing_idem.get("input_checksum") or "") != input_checksum:
                    self._audit(cur, event_type="rejected", paper_account_id=paper_account_id, epoch=current_epoch, user_id=user_id, decision_id=decision_id, apply_id=None, reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="idempotency_conflict", created_at=now)
                    cur.close()
                    conn.commit()
                    return self._reject("idempotency_conflict", "same idempotency_key used with different input_checksum")
                self._audit(cur, event_type="duplicate_replay", paper_account_id=paper_account_id, epoch=current_epoch, user_id=user_id, decision_id=decision_id, apply_id=existing_idem.get("apply_id"), reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="already_applied", created_at=now)
                existing_result["already_applied"] = True
                existing_result["status"] = existing_result.get("status") or "already_applied"
                cur.close()
                conn.commit()
                return self._ok(existing_result)
            existing_decision = self._find_apply_by_decision(cur, decision_id=decision_id, paper_account_id=paper_account_id, epoch=current_epoch)
            if existing_decision:
                existing_result = _loads(existing_decision.get("result_json"))
                self._audit(cur, event_type="duplicate_replay", paper_account_id=paper_account_id, epoch=current_epoch, user_id=user_id, decision_id=decision_id, apply_id=existing_decision.get("apply_id"), reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="already_applied", created_at=now)
                existing_result["already_applied"] = True
                existing_result["status"] = existing_result.get("status") or "already_applied"
                cur.close()
                conn.commit()
                return self._ok(existing_result)
            asof = str(intent.get("asof") or payload.get("asof") or "")
            same_day = self._find_same_day_apply(cur, paper_account_id=paper_account_id, epoch=current_epoch, asof=asof) if asof else {}
            if same_day:
                self._audit(cur, event_type="rejected", paper_account_id=paper_account_id, epoch=current_epoch, user_id=user_id, decision_id=decision_id, apply_id=None, reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="same_day_apply_rejected", created_at=now)
                cur.close()
                conn.commit()
                return self._reject("same_day_apply_rejected", "same-day apply already exists for this paper account epoch")

            apply_id = f"paper_apply_{uuid.uuid4().hex}"
            request_json = _json({k: v for k, v in payload.items() if k not in {"paper_order_intent", "paperOrderIntent"}})
            cash_before = _money(account.get("cash"))
            positions_before = self._positions(cur, paper_account_id=paper_account_id)
            executions: List[Dict[str, Any]] = []
            skipped: List[Dict[str, Any]] = []
            rejected: List[Dict[str, Any]] = []
            cash = cash_before
            for action in intent.get("actions") or []:
                result = self._apply_action(cur, account=account, action=action, user_id=user_id, apply_id=apply_id)
                if result.get("status") == "executed":
                    cash = _money(result.get("cash_after"))
                    account["cash"] = cash
                    executions.append(result)
                elif result.get("status") == "skipped":
                    skipped.append(result)
                else:
                    rejected.append(result)
            positions_after = self._positions(cur, paper_account_id=paper_account_id)
            status = "applied" if executions or skipped or rejected else "no_actions"
            result_payload = {
                "artifact_type": "PaperApplyResultArtifact",
                "schema_version": "phase_x.paper_apply_result.v1",
                "apply_id": apply_id,
                "decision_id": decision_id,
                "idempotency_key": idempotency_key,
                "input_checksum": input_checksum,
                "paper_account_id": paper_account_id,
                "paper_account_epoch": current_epoch,
                "asof": str(intent.get("asof") or payload.get("asof") or ""),
                "already_applied": False,
                "status": status,
                "paper_executions": executions,
                "skipped_actions": skipped,
                "rejected_actions": rejected,
                "cash_before": _float(cash_before),
                "cash_after": _float(cash),
                "positions_before": positions_before,
                "positions_after": positions_after,
                "created_at": str(now),
                "applied_at": str(now),
                "simulation_only": True,
                "trading": sim_trading_flags(),
            }
            cur.execute(
                """
                INSERT INTO qd_tw_sim_apply_runs
                  (apply_id, decision_id, paper_account_id, user_id, paper_account_epoch, idempotency_key,
                   input_checksum, status, already_applied, request_json, result_json, created_at, applied_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, FALSE, ?, ?, ?, ?)
                """,
                (apply_id, decision_id, paper_account_id, int(user_id), current_epoch, idempotency_key, input_checksum, status, request_json, _json(result_payload), now, now),
            )
            self._audit(cur, event_type="apply_decision", paper_account_id=paper_account_id, epoch=current_epoch, user_id=user_id, decision_id=decision_id, apply_id=apply_id, reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status=status, created_at=now)
            cur.close()
            conn.commit()
        return self._ok(result_payload)

    def reset(self, *, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_schema()
        paper_account_id = str(payload.get("paper_account_id") or payload.get("paperAccountId") or "")
        idempotency_key = str(payload.get("idempotency_key") or payload.get("idempotencyKey") or "")
        current_epoch = int(payload.get("current_epoch") or payload.get("currentEpoch") or 0)
        if not paper_account_id or not idempotency_key:
            return self._reject("invalid_request", "paper_account_id and idempotency_key are required")
        if payload.get("confirmed_by_user") is not True:
            return self._reject("invalid_confirmation", "confirmed_by_user must be true")
        if "重置模拟账户" not in str(payload.get("confirm_text") or payload.get("confirmText") or ""):
            return self._reject("invalid_confirmation", "confirm_text must include 重置模拟账户")
        input_checksum = str(payload.get("input_checksum") or payload.get("inputChecksum") or f"reset:{paper_account_id}:{current_epoch}:{idempotency_key}")
        now = self.now_fn()
        with self.db_factory() as conn:
            cur = conn.cursor()
            existing = self._find_reset_by_idempotency(cur, user_id=user_id, idempotency_key=idempotency_key)
            if existing:
                result = _loads(existing.get("result_json"))
                previous_epoch = int(existing.get("previous_epoch") or 0)
                new_epoch = int(existing.get("new_epoch") or previous_epoch)
                if str(existing.get("input_checksum") or "") != input_checksum:
                    self._audit(cur, event_type="rejected", paper_account_id=str(existing.get("paper_account_id") or paper_account_id), epoch=new_epoch, user_id=user_id, decision_id=None, apply_id=None, reset_id=existing.get("reset_id"), idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="idempotency_conflict", created_at=now)
                    cur.close()
                    conn.commit()
                    return self._reject("idempotency_conflict", "same idempotency_key used with different input_checksum")
                self._audit(cur, event_type="duplicate_replay", paper_account_id=str(existing.get("paper_account_id") or paper_account_id), epoch=new_epoch, user_id=user_id, decision_id=None, apply_id=None, reset_id=existing.get("reset_id"), idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="already_reset", created_at=now)
                result["already_reset"] = True
                cur.close()
                conn.commit()
                return self._ok(result)
            account = self._account(cur, user_id=user_id, paper_account_id=paper_account_id)
            if not account:
                cur.close()
                return self._reject("not_found", "paper simulation account not found")
            previous_epoch = int(account.get("paper_account_epoch") or 1)
            if current_epoch != previous_epoch:
                self._audit(cur, event_type="rejected", paper_account_id=paper_account_id, epoch=previous_epoch, user_id=user_id, decision_id=None, apply_id=None, reset_id=None, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="stale_epoch", created_at=now)
                cur.close()
                conn.commit()
                return self._reject("stale_epoch", "current_epoch does not match current account epoch")
            archive_snapshot = self._archive_snapshot(cur, account=account)
            reset_id = f"paper_reset_{uuid.uuid4().hex}"
            new_epoch = previous_epoch + 1
            reset_cash = _money(payload.get("reset_initial_cash") or payload.get("resetInitialCash") or account.get("initial_cash"))
            cur.execute("DELETE FROM qd_tw_sim_positions WHERE account_uid = ?", (paper_account_id,))
            cur.execute("UPDATE qd_tw_sim_orders SET status = 'cancelled', updated_at = ? WHERE account_uid = ? AND status = 'draft'", (now, paper_account_id))
            cur.execute("UPDATE qd_tw_sim_accounts SET cash = ?, paper_account_epoch = ?, updated_at = ?, archived = FALSE WHERE account_uid = ? AND user_id = ?", (reset_cash, new_epoch, now, paper_account_id, int(user_id)))
            result_payload = {
                "artifact_type": "PaperAccountResetArtifact",
                "schema_version": "phase_x.paper_account_reset.v1",
                "reset_id": reset_id,
                "paper_account_id": paper_account_id,
                "previous_epoch": previous_epoch,
                "new_epoch": new_epoch,
                "archive_snapshot": archive_snapshot,
                "initial_cash": _float(reset_cash),
                "idempotency_key": idempotency_key,
                "confirmed_by_user": True,
                "status": "reset",
                "already_reset": False,
                "created_at": str(now),
                "simulation_only": True,
                "trading": sim_trading_flags(),
            }
            cur.execute(
                """
                INSERT INTO qd_tw_sim_reset_runs
                  (reset_id, paper_account_id, user_id, previous_epoch, new_epoch, idempotency_key,
                   input_checksum, archive_snapshot_json, result_json, created_at, reset_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (reset_id, paper_account_id, int(user_id), previous_epoch, new_epoch, idempotency_key, input_checksum, _json(archive_snapshot), _json(result_payload), now, now),
            )
            self._audit(cur, event_type="reset_account", paper_account_id=paper_account_id, epoch=new_epoch, user_id=user_id, decision_id=None, apply_id=None, reset_id=reset_id, idempotency_key=idempotency_key, input_checksum=input_checksum, result_status="reset", created_at=now)
            cur.close()
            conn.commit()
        return self._ok(result_payload)

    def _authoritative_intent(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        artifact_path = str(
            payload.get("paper_order_intent_artifact_path")
            or payload.get("paperOrderIntentArtifactPath")
            or payload.get("artifact_path")
            or payload.get("artifactPath")
            or ""
        ).strip()
        artifact_id = str(payload.get("decision_artifact_id") or payload.get("decisionArtifactId") or "").strip()
        if artifact_path or artifact_id:
            path, error = self._resolve_artifact_path(artifact_path=artifact_path, artifact_id=artifact_id)
            if error:
                return {}, error
            try:
                intent = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                return {}, self._reject("invalid_artifact", f"failed to read paper_order_intent artifact: {exc}")
            if not isinstance(intent, dict):
                return {}, self._reject("invalid_artifact", "paper_order_intent artifact must be an object")
            checksum, checksum_error = self._recompute_intent_input_checksum(intent, path=path)
            if checksum_error:
                return {}, checksum_error
            if str(intent.get("input_checksum") or "") != checksum:
                return {}, self._reject("invalid_artifact", "artifact input_checksum does not match server recomputed checksum")
            return {"intent": intent, "input_checksum": checksum, "artifact_path": str(path)}, None

        if not self.allow_inline_intent:
            return {}, self._reject("invalid_artifact", "paper_order_intent_artifact_path or decision_artifact_id is required")
        intent = payload.get("paper_order_intent") or payload.get("paperOrderIntent") or {}
        if not isinstance(intent, dict):
            return {}, self._reject("invalid_artifact", "paper_order_intent must be an object")
        checksum = str(intent.get("input_checksum") or "")
        return {"intent": intent, "input_checksum": checksum, "artifact_path": "inline_test_payload"}, None

    def _resolve_artifact_path(self, *, artifact_path: str, artifact_id: str) -> Tuple[Path, Optional[Dict[str, Any]]]:
        root = self.artifact_root.resolve()
        if artifact_id:
            if "/" in artifact_id or "\\" in artifact_id or ".." in Path(artifact_id).parts:
                return Path(), self._reject("invalid_artifact", "decision_artifact_id is invalid")
            candidate = self.artifact_root / artifact_id / "paper_order_intent.json"
        else:
            raw = Path(artifact_path)
            if raw.is_absolute() or ".." in raw.parts:
                return Path(), self._reject("invalid_artifact", "paper_order_intent_artifact_path escapes artifact root")
            if raw.parts[:4] == ("data_tw", "artifacts", "paper_portfolio"):
                raw = Path(*raw.parts[4:])
            candidate = self.artifact_root / raw
            if candidate.is_dir() or candidate.suffix == "":
                candidate = candidate / "paper_order_intent.json"
        try:
            resolved = candidate.resolve()
        except Exception:
            return Path(), self._reject("invalid_artifact", "paper_order_intent_artifact_path is invalid")
        if root != resolved and root not in resolved.parents:
            return Path(), self._reject("invalid_artifact", "paper_order_intent_artifact_path escapes artifact root")
        if resolved.name != "paper_order_intent.json":
            return Path(), self._reject("invalid_artifact", "artifact path must point to paper_order_intent.json")
        if not resolved.exists() or not resolved.is_file():
            return Path(), self._reject("invalid_artifact", "paper_order_intent artifact not found")
        return resolved, None

    def _recompute_intent_input_checksum(self, intent: Dict[str, Any], *, path: Path) -> Tuple[str, Optional[Dict[str, Any]]]:
        if intent.get("artifact_type") != "PaperOrderIntentArtifact":
            return "", self._reject("invalid_artifact", "artifact_type must be PaperOrderIntentArtifact")
        state_ref = str(intent.get("source_portfolio_state_artifact") or "paper_portfolio_state.json")
        state_path = path.parent / state_ref
        try:
            resolved_state = state_path.resolve()
            if path.parent.resolve() != resolved_state.parent:
                return "", self._reject("invalid_artifact", "source_portfolio_state_artifact must stay beside paper_order_intent")
            state = json.loads(resolved_state.read_text(encoding="utf-8"))
        except Exception as exc:
            return "", self._reject("invalid_artifact", f"failed to read source portfolio state artifact: {exc}")
        portfolio_state_checksum = str(state.get("checksum") or "")
        if not portfolio_state_checksum:
            return "", self._reject("invalid_artifact", "source portfolio state checksum is required")
        input_payload = {
            "portfolio_state_checksum": portfolio_state_checksum,
            "source_model_signal_artifact": intent.get("source_model_signal_artifact"),
            "strategy_rule": intent.get("strategy_rule"),
            "asof": intent.get("asof"),
            "actions": intent.get("actions") or [],
        }
        return _canonical_checksum(input_payload), None

    def _validate_intent(self, intent: Dict[str, Any], *, paper_account_id: str, decision_id: str, input_checksum: str) -> Optional[Dict[str, Any]]:
        required_true = ["readonly_decision_only", "not_real_order", "not_target_position", "not_investment_advice"]
        for field in required_true:
            if intent.get(field) is not True:
                return self._reject("invalid_artifact", f"{field} must be true")
        model_id = str(intent.get("model_id") or "")
        strategy_rule = str(intent.get("strategy_rule") or "")
        execution_price_mode = str(intent.get("execution_price_mode") or EXECUTION_PRICE_MODE)
        clean = self._clean_policy()
        if model_id not in clean["models"]:
            return self._reject("invalid_artifact", "model_id is not production selectable")
        if strategy_rule not in clean["strategies"]:
            return self._reject("invalid_artifact", "strategy_rule is not production selectable")
        if execution_price_mode != "next_open":
            return self._reject("invalid_artifact", "execution_price_mode must be next_open")
        if str(intent.get("paper_account_id") or "") != paper_account_id:
            return self._reject("invalid_artifact", "paper_account_id mismatch")
        if str(intent.get("decision_id") or "") != decision_id:
            return self._reject("invalid_artifact", "decision_id mismatch")
        if str(intent.get("input_checksum") or "") != input_checksum:
            return self._reject("invalid_artifact", "input_checksum mismatch")
        return None

    def _clean_policy(self) -> Dict[str, set[str]]:
        if self._policy_cache is not None:
            return self._policy_cache
        registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
        registry_models = set(((registry.get("production_models") or {}).get("production_selectable") or {}).keys())
        policy_models = {key for key, value in (policy.get("models") or {}).items() if (value or {}).get("production_selectable") is True}
        strategies = set(((registry.get("strategies") or {}).get("production_selectable") or {}).keys())
        self._policy_cache = {"models": registry_models & policy_models, "strategies": strategies}
        return self._policy_cache

    def _manifest_is_clean_decision(self, manifest: Dict[str, Any]) -> bool:
        clean = self._clean_policy()
        return (
            str(manifest.get("model_id") or "") in clean["models"]
            and str(manifest.get("strategy_rule") or "") in clean["strategies"]
            and str(manifest.get("execution_price_mode") or EXECUTION_PRICE_MODE) == EXECUTION_PRICE_MODE
        )

    def _execution_price_gate(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        status = self.productization_status_loader(signal_asof=str(intent.get("asof") or "") or None)
        readiness = status.get("execution_price_readiness") or {}
        checks = {
            "execution_price_mode": str(status.get("execution_price_mode") or "") == "next_open",
            "execution_price_status": str(status.get("execution_price_status") or "") == "pass",
            "paper_apply_allowed": status.get("paper_apply_allowed") is True,
            "next_open_available_count": int(readiness.get("next_open_available_count") or 0) > 0,
            "missing_next_open_count": int(readiness.get("missing_next_open_count") or 0) == 0,
            "no_fallback_to_next_close": readiness.get("no_fallback_to_next_close") is True,
            "no_fallback_to_signal_close": readiness.get("no_fallback_to_signal_close") is True,
        }
        if all(checks.values()):
            return None
        return self._reject(
            "execution_price_unavailable",
            "execution price readiness is not pass; paper apply is blocked before simulation writes",
            execution_price_status=status.get("execution_price_status") or "execution_price_unavailable",
            paper_apply_allowed=status.get("paper_apply_allowed") is True,
            paper_apply_blocked_reason=status.get("paper_apply_blocked_reason") or readiness.get("blocked_reason") or "next_open_unavailable",
            execution_price_readiness=readiness,
            gate_checks=checks,
        )

    def _apply_action(self, cur: Any, *, account: Dict[str, Any], action: Dict[str, Any], user_id: int, apply_id: str) -> Dict[str, Any]:
        action_type = str(action.get("action_type") or "")
        if action_type == "paper_skip":
            return {"status": "skipped", "reason": "paper_skip", "instrument": action.get("instrument"), "symbol": _symbol(action.get("symbol") or action.get("instrument"))}
        if action_type not in {"paper_buy_intent", "paper_sell_intent"}:
            return {"status": "skipped", "reason": "unsupported_action_type", "action_type": action_type}
        if str(action.get("applicability") or "") != "applicable":
            return {"status": "skipped", "reason": "action_unavailable", "action_type": action_type, "symbol": _symbol(action.get("symbol") or action.get("instrument"))}
        side = "buy" if action_type == "paper_buy_intent" else "sell"
        symbol = _symbol(action.get("symbol") or action.get("instrument"))
        qty = int(action.get("quantity") or 0)
        price = _price(action.get("estimated_reference_price"))
        if not symbol or qty <= 0 or price <= 0:
            return {"status": "rejected", "reason": "invalid_action_values", "action_type": action_type, "symbol": symbol}
        paper_account_id = str(account.get("account_uid"))
        cur.execute("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?", (paper_account_id, symbol))
        pos = _row(cur.fetchone())
        cash_before = _money(account.get("cash"))
        gross = _money(Decimal(qty) * price)
        fee = _money(gross * FEE_RATE)
        tax = _money(gross * SELL_TAX_RATE) if side == "sell" else Decimal("0.00")
        if side == "buy":
            cash_required = _money(gross + fee)
            if cash_before < cash_required:
                return {"status": "rejected", "reason": "cash_insufficient", "action_type": action_type, "symbol": symbol}
            new_cash = _money(cash_before - cash_required)
            self._apply_buy(cur, paper_account_id=paper_account_id, symbol=symbol, qty=qty, gross=gross, fee=fee)
            net_cash_effect = -cash_required
        else:
            current_qty = int(pos.get("quantity") or 0) if pos else 0
            if qty > current_qty:
                return {"status": "rejected", "reason": "oversell", "action_type": action_type, "symbol": symbol, "current_quantity": current_qty}
            cash_credit = _money(gross - fee - tax)
            new_cash = _money(cash_before + cash_credit)
            self._apply_sell(cur, paper_account_id=paper_account_id, symbol=symbol, qty=qty, pos=pos)
            net_cash_effect = cash_credit
        now = self.now_fn()
        cur.execute("UPDATE qd_tw_sim_accounts SET cash = ?, updated_at = ? WHERE account_uid = ?", (new_cash, now, paper_account_id))
        order_uid = f"paper_order_{uuid.uuid4().hex}"
        trade_uid = f"paper_trade_{uuid.uuid4().hex}"
        source_context = {"apply_id": apply_id, "decision_id": action.get("decision_id"), "paper_action_type": action_type}
        cur.execute(
            """
            INSERT INTO qd_tw_sim_orders
              (sim_order_uid, account_uid, user_id, symbol, side, quantity, status, source_type, source_context_json,
               reference_price, price_source, price_date, gross_amount, fee, tax, net_cash_effect, message, warnings,
               simulation_only, created_at, updated_at, filled_at)
            VALUES (?, ?, ?, ?, ?, ?, 'filled', 'paper_strategy', ?, ?, ?, ?, ?, ?, ?, ?, 'paper_strategy_apply', '', TRUE, ?, ?, ?)
            """,
            (order_uid, paper_account_id, int(user_id), symbol, side, qty, _json(source_context), price, action.get("price_source") or "artifact_reference_price", action.get("price_date") or None, gross, fee, tax, net_cash_effect, now, now, now),
        )
        cur.execute(
            """
            INSERT INTO qd_tw_sim_trades
              (sim_trade_uid, sim_order_uid, account_uid, user_id, symbol, side, quantity, price, price_source,
               price_date, gross_amount, fee, tax, net_cash_effect, source_type, source_context_json, simulation_only, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'paper_strategy', ?, TRUE, ?)
            """,
            (trade_uid, order_uid, paper_account_id, int(user_id), symbol, side, qty, price, action.get("price_source") or "artifact_reference_price", action.get("price_date") or None, gross, fee, tax, net_cash_effect, _json(source_context), now),
        )
        return {"status": "executed", "paper_execution_id": trade_uid, "paper_order_id": order_uid, "action_type": action_type, "symbol": symbol, "side": side, "quantity": qty, "price": _float(price), "gross_amount": _float(gross), "fee": _float(fee), "tax": _float(tax), "net_cash_effect": _float(net_cash_effect), "cash_after": _float(new_cash)}

    def _apply_buy(self, cur: Any, *, paper_account_id: str, symbol: str, qty: int, gross: Decimal, fee: Decimal) -> None:
        now = self.now_fn()
        cur.execute("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND symbol = ?", (paper_account_id, symbol))
        pos = _row(cur.fetchone())
        add_cost = _money(gross + fee)
        if pos:
            old_qty = int(pos.get("quantity") or 0)
            old_cost = _money(pos.get("cost_value"))
            new_qty = old_qty + qty
            new_cost = _money(old_cost + add_cost)
            avg_cost = _price(new_cost / Decimal(new_qty)) if new_qty else Decimal("0")
            cur.execute("UPDATE qd_tw_sim_positions SET quantity = ?, avg_cost = ?, cost_value = ?, updated_at = ? WHERE account_uid = ? AND symbol = ?", (new_qty, avg_cost, new_cost, now, paper_account_id, symbol))
        else:
            avg_cost = _price(add_cost / Decimal(qty))
            cur.execute("INSERT INTO qd_tw_sim_positions (account_uid, symbol, quantity, avg_cost, cost_value, simulation_only, created_at, updated_at) VALUES (?, ?, ?, ?, ?, TRUE, ?, ?)", (paper_account_id, symbol, qty, avg_cost, add_cost, now, now))

    def _apply_sell(self, cur: Any, *, paper_account_id: str, symbol: str, qty: int, pos: Dict[str, Any]) -> None:
        now = self.now_fn()
        old_qty = int(pos.get("quantity") or 0)
        avg_cost = _price(pos.get("avg_cost"))
        new_qty = old_qty - qty
        new_cost = _money(avg_cost * Decimal(new_qty)) if new_qty > 0 else Decimal("0.00")
        cur.execute("UPDATE qd_tw_sim_positions SET quantity = ?, cost_value = ?, updated_at = ? WHERE account_uid = ? AND symbol = ?", (new_qty, new_cost, now, paper_account_id, symbol))

    def _account(self, cur: Any, *, user_id: int, paper_account_id: str) -> Dict[str, Any]:
        cur.execute("SELECT * FROM qd_tw_sim_accounts WHERE account_uid = ? AND user_id = ? AND simulation_only = TRUE AND COALESCE(archived, FALSE) = FALSE", (paper_account_id, int(user_id)))
        return _row(cur.fetchone())

    def _positions(self, cur: Any, *, paper_account_id: str) -> List[Dict[str, Any]]:
        cur.execute("SELECT * FROM qd_tw_sim_positions WHERE account_uid = ? AND quantity > 0 ORDER BY symbol ASC", (paper_account_id,))
        return _rows(cur.fetchall())

    def _archive_snapshot(self, cur: Any, *, account: Dict[str, Any]) -> Dict[str, Any]:
        paper_account_id = str(account.get("account_uid"))
        positions = self._positions(cur, paper_account_id=paper_account_id)
        cur.execute("SELECT * FROM qd_tw_sim_orders WHERE account_uid = ? ORDER BY created_at DESC", (paper_account_id,))
        orders = _rows(cur.fetchall())
        cur.execute("SELECT * FROM qd_tw_sim_trades WHERE account_uid = ? ORDER BY created_at DESC", (paper_account_id,))
        trades = _rows(cur.fetchall())
        return {"account": self._account_payload(account), "positions": positions, "orders": orders, "trades": trades, "created_at": str(self.now_fn())}

    def _find_apply_by_idempotency(self, cur: Any, *, user_id: int, idempotency_key: str) -> Dict[str, Any]:
        cur.execute("SELECT * FROM qd_tw_sim_apply_runs WHERE user_id = ? AND idempotency_key = ? ORDER BY id DESC LIMIT 1", (int(user_id), idempotency_key))
        return _row(cur.fetchone())

    def _find_apply_by_decision(self, cur: Any, *, decision_id: str, paper_account_id: str, epoch: int) -> Dict[str, Any]:
        cur.execute("SELECT * FROM qd_tw_sim_apply_runs WHERE decision_id = ? AND paper_account_id = ? AND paper_account_epoch = ? ORDER BY id DESC LIMIT 1", (decision_id, paper_account_id, int(epoch)))
        return _row(cur.fetchone())

    def _find_reset_by_idempotency(self, cur: Any, *, user_id: int, idempotency_key: str) -> Dict[str, Any]:
        cur.execute("SELECT * FROM qd_tw_sim_reset_runs WHERE user_id = ? AND idempotency_key = ? ORDER BY id DESC LIMIT 1", (int(user_id), idempotency_key))
        return _row(cur.fetchone())

    def _find_same_day_apply(self, cur: Any, *, paper_account_id: str, epoch: int, asof: str) -> Dict[str, Any]:
        cur.execute("SELECT * FROM qd_tw_sim_apply_runs WHERE paper_account_id = ? AND paper_account_epoch = ? ORDER BY id DESC", (paper_account_id, int(epoch)))
        for row in _rows(cur.fetchall()):
            result = _loads(row.get("result_json"))
            if str(result.get("asof") or "") == asof:
                return row
        return {}

    def _audit(self, cur: Any, *, event_type: str, paper_account_id: str, epoch: int, user_id: int, decision_id: Optional[str], apply_id: Optional[str], reset_id: Optional[str], idempotency_key: str, input_checksum: str, result_status: str, created_at: datetime) -> None:
        cur.execute(
            """
            INSERT INTO qd_tw_sim_audit_log
              (event_id, event_type, paper_account_id, paper_account_epoch, user_id, decision_id, apply_id,
               reset_id, idempotency_key, input_checksum, result_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"paper_audit_{uuid.uuid4().hex}", event_type, paper_account_id, int(epoch), int(user_id), decision_id, apply_id, reset_id, idempotency_key, input_checksum, result_status, created_at),
        )

    def _account_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {"account_uid": row.get("account_uid"), "user_id": int(row.get("user_id") or 0), "currency": row.get("currency") or "TWD", "initial_cash": _float(row.get("initial_cash")), "cash": _float(row.get("cash")), "paper_account_epoch": int(row.get("paper_account_epoch") or 1), "simulation_only": True}

    def _apply_run_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {"apply_id": row.get("apply_id"), "decision_id": row.get("decision_id"), "paper_account_id": row.get("paper_account_id"), "paper_account_epoch": int(row.get("paper_account_epoch") or 0), "idempotency_key": row.get("idempotency_key"), "input_checksum": row.get("input_checksum"), "status": row.get("status"), "already_applied": bool(row.get("already_applied")), "result": _loads(row.get("result_json")), "created_at": str(row.get("created_at") or ""), "applied_at": str(row.get("applied_at") or "")}

    def _ok(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload.setdefault("ok", True)
        payload.setdefault("simulation_only", True)
        payload.setdefault("trading", sim_trading_flags())
        return payload

    def _reject(self, status: str, message: str, **extra: Any) -> Dict[str, Any]:
        payload = {"ok": False, "status": status, "message": message, "simulation_only": True, "trading": sim_trading_flags()}
        payload.update(extra)
        return payload
