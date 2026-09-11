"""Readonly DAOV ops status adapter for Taiwan stock artifacts."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.tw_stock_daily_auto_update_status import (
    DEFAULT_OPS_ROOT,
    TWStockDailyAutoUpdateStatusService,
)
from app.services.tw_stock_qlib_option_c import DEFAULT_SIGNAL_ROOT, research_only_trading_flags

REPO_ROOT = Path(__file__).resolve().parents[3]

CONTROLLED_SIGNAL_LATEST = REPO_ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"
READONLY_SNAPSHOT_LATEST = REPO_ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
AGENT_PROMPT_LATEST = REPO_ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json"
LEGACY_OPTION_C_LATEST = REPO_ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
        warnings.append(f"{path}:json_not_object")
    except FileNotFoundError:
        warnings.append(f"{path}:missing")
    except Exception as exc:
        warnings.append(f"{path}:json_read_failed:{type(exc).__name__}")
    return {}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def _fingerprint(path: Path) -> dict[str, Any]:
    exists = path.exists()
    stat = None
    try:
        stat = path.stat() if exists else None
    except Exception:
        stat = None
    return {
        "exists": exists,
        "path": str(path),
        "size": stat.st_size if stat else None,
        "sha256": _sha256(path) if exists else None,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat() if stat else None,
    }


class TWStockReadonlyOpsStatusService:
    """Build a single readonly ops status contract from existing local evidence."""

    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        ops_root: str | Path | None = None,
        qlib_accepted_latest_path: str | Path | None = None,
        controlled_signal_latest_path: str | Path | None = None,
        readonly_snapshot_latest_path: str | Path | None = None,
        agent_prompt_latest_path: str | Path | None = None,
        legacy_option_c_latest_path: str | Path | None = None,
        daily_status_service: TWStockDailyAutoUpdateStatusService | None = None,
    ) -> None:
        root = Path(repo_root or REPO_ROOT).expanduser().resolve(strict=False)
        self.repo_root = root
        self.ops_root = Path(ops_root or os.getenv("TW_DAILY_AUTO_UPDATE_OPS_ROOT") or DEFAULT_OPS_ROOT).expanduser().resolve(strict=False)
        self.qlib_accepted_latest_path = Path(
            qlib_accepted_latest_path
            or os.getenv("QLIB_TW_OPTION_C_LATEST_PATH")
            or (Path(os.getenv("QLIB_TW_OPTION_C_ROOT") or DEFAULT_SIGNAL_ROOT) / "latest_signal.json")
        ).expanduser().resolve(strict=False)
        self.controlled_signal_latest_path = Path(controlled_signal_latest_path or root / CONTROLLED_SIGNAL_LATEST.relative_to(REPO_ROOT)).expanduser().resolve(strict=False)
        self.readonly_snapshot_latest_path = Path(readonly_snapshot_latest_path or root / READONLY_SNAPSHOT_LATEST.relative_to(REPO_ROOT)).expanduser().resolve(strict=False)
        self.agent_prompt_latest_path = Path(agent_prompt_latest_path or root / AGENT_PROMPT_LATEST.relative_to(REPO_ROOT)).expanduser().resolve(strict=False)
        self.legacy_option_c_latest_path = Path(legacy_option_c_latest_path or root / LEGACY_OPTION_C_LATEST.relative_to(REPO_ROOT)).expanduser().resolve(strict=False)
        self.daily_status_service = daily_status_service or TWStockDailyAutoUpdateStatusService(
            signal_root=self.qlib_accepted_latest_path.parent,
            ops_root=self.ops_root,
        )

    def status(self) -> dict[str, Any]:
        warnings: list[str] = []
        daily_status = self.daily_status_service.status()
        latest_job_path, latest_job = self._latest_job(warnings)
        latest_job_dir = latest_job_path.parent if latest_job_path else None
        dapr18_dir = self._latest_dapr18_dir(warnings)
        dapr18_job = self._read_from_dir(dapr18_dir, "job.json", warnings)

        daily_chain = self._daily_chain(latest_job_dir, warnings)
        if not daily_chain and dapr18_dir and dapr18_dir != latest_job_dir:
            daily_chain = self._daily_chain(dapr18_dir, warnings)

        summary = self._read_from_dir(dapr18_dir, "dapr18_controlled_latest_orchestration_summary.json", warnings)
        readiness = self._read_from_dir(dapr18_dir, "dapr18_controlled_latest_readiness.json", warnings)
        forbidden_audit = self._read_from_dir(dapr18_dir, "dapr18_forbidden_action_audit.json", warnings)
        protected_fingerprint = self._read_from_dir(dapr18_dir, "dapr18_protected_paths_fingerprint.json", warnings)

        qlib_doc = _safe_json(self.qlib_accepted_latest_path, warnings)
        controlled_doc = _safe_json(self.controlled_signal_latest_path, warnings)
        snapshot_doc = _safe_json(self.readonly_snapshot_latest_path, warnings)
        agent_doc = _safe_json(self.agent_prompt_latest_path, warnings)

        publish_state = self._dapr18_publish_state(summary, controlled_doc, snapshot_doc, agent_doc)
        evidence_binding = self._dapr18_evidence_binding(
            latest_job_path,
            latest_job,
            dapr18_dir,
            dapr18_job,
            summary,
            readiness,
        )
        natural_publish_state = dict(publish_state)
        natural_publish_state["bound_to_latest_natural_job"] = evidence_binding["bound"]
        natural_publish_state["binding_reason"] = evidence_binding["reason"]
        natural_publish_state["completed"] = bool(publish_state["completed"] and evidence_binding["bound"])
        blocker = self._blocker(
            latest_job,
            daily_chain,
            readiness if evidence_binding["bound"] else {},
            summary if evidence_binding["bound"] else {},
            natural_publish_state,
        )
        payload = {
            "ok": True,
            "schema_version": "daov1.readonly_ops_status.v1",
            "status": "readonly_status_available",
            "generated_at": _utc_now_iso(),
            "readonly_only": True,
            "provider_raw_latest": self._provider_raw_latest(latest_job, daily_chain),
            "qlib_accepted_latest": self._qlib_accepted_latest(qlib_doc, daily_status),
            "controlled_signal_latest": self._controlled_signal_latest(controlled_doc, readiness),
            "readonly_strategy_snapshot_latest": self._readonly_snapshot_latest(snapshot_doc, readiness),
            "agent_prompt_latest": self._agent_prompt_latest(agent_doc, readiness),
            "latest_natural_cron_job": self._latest_natural_cron_job(latest_job_path, latest_job, daily_chain, blocker, daily_status, natural_publish_state),
            "latest_dapr18_evidence_job": self._latest_dapr18_evidence_job(dapr18_dir, dapr18_job, summary, readiness, publish_state),
            "dapr18_controls": self._dapr18_controls(latest_job, summary, publish_state, evidence_binding),
            "protected_pointers": self._protected_pointers(protected_fingerprint),
            "forbidden_actions": self._forbidden_actions(forbidden_audit, daily_chain, summary, dapr18_dir),
            "next_action_hint": self._next_action_hint(latest_job, daily_chain, readiness, summary, daily_status, publish_state),
            "ui_wording_contract": self._ui_wording_contract(),
            "sources": {
                "daily_status": daily_status.get("sources", {}),
                "latest_job": str(latest_job_path) if latest_job_path else None,
                "latest_dapr18_job_dir": str(dapr18_dir) if dapr18_dir else None,
                "qlib_accepted_latest": str(self.qlib_accepted_latest_path),
                "controlled_signal_latest": str(self.controlled_signal_latest_path),
                "readonly_strategy_snapshot_latest": str(self.readonly_snapshot_latest_path),
                "agent_prompt_latest": str(self.agent_prompt_latest_path),
            },
            "warnings": list(dict.fromkeys(warnings + list(daily_status.get("warnings") or []))),
            "trading": research_only_trading_flags(),
        }
        payload["all_readonly_guards"] = self._all_readonly_guards(payload)
        return payload

    def _latest_job(self, warnings: list[str]) -> tuple[Path | None, dict[str, Any]]:
        paths = sorted(self.ops_root.glob("*/job.json")) if self.ops_root.exists() else []
        candidates: list[tuple[datetime, Path, dict[str, Any]]] = []
        for path in paths:
            doc = _safe_json(path, warnings)
            sort_time = _parse_dt(doc.get("finished_at") or doc.get("started_at") or doc.get("created_at"))
            if sort_time is None:
                try:
                    sort_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                except Exception:
                    sort_time = datetime.min.replace(tzinfo=timezone.utc)
            candidates.append((sort_time, path, doc))
        if not candidates:
            return None, {}
        candidates.sort(key=lambda item: item[0], reverse=True)
        _, path, doc = candidates[0]
        return path, doc

    def _latest_dapr18_dir(self, warnings: list[str]) -> Path | None:
        paths = sorted(self.ops_root.glob("*/dapr18_controlled_latest_orchestration_summary.json")) if self.ops_root.exists() else []
        if not paths:
            warnings.append("dapr18_controlled_latest_orchestration_summary.json:missing")
            return None
        candidates = []
        for path in paths:
            doc = _safe_json(path, warnings)
            sort_time = _parse_dt(doc.get("created_at"))
            if sort_time is None:
                try:
                    sort_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                except Exception:
                    sort_time = datetime.min.replace(tzinfo=timezone.utc)
            candidates.append((sort_time, path.parent))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _read_from_dir(self, directory: Path | None, name: str, warnings: list[str]) -> dict[str, Any]:
        if directory is None:
            return {}
        return _safe_json(directory / name, warnings)

    def _daily_chain(self, job_dir: Path | None, warnings: list[str]) -> dict[str, Any]:
        if job_dir is None:
            return {}
        path = job_dir / "daily_chain_status.json"
        if not path.exists():
            warnings.append(f"{path}:missing")
            return {}
        return _safe_json(path, warnings)

    def _provider_raw_latest(self, job: dict[str, Any], daily_chain: dict[str, Any]) -> dict[str, Any]:
        lineage = daily_chain.get("lineage_evidence") if isinstance(daily_chain.get("lineage_evidence"), dict) else {}
        raw_detail = lineage.get("raw_detail") if isinstance(lineage.get("raw_detail"), dict) else {}
        raw_paths = lineage.get("raw_evidence_paths") if isinstance(lineage.get("raw_evidence_paths"), list) else []
        if raw_detail:
            return {
                "source": raw_detail.get("source") or "daily_chain_status.raw_detail",
                "asof": daily_chain.get("asof") or job.get("asof"),
                "source_max_date": raw_detail.get("source_max_date"),
                "raw_status": daily_chain.get("raw_status") or "UNKNOWN",
                "evidence_path": raw_paths[0] if raw_paths else None,
                "caveat": self._provider_caveat(daily_chain),
            }
        inventory = job.get("daily_source_inventory") if isinstance(job.get("daily_source_inventory"), dict) else {}
        formal = inventory.get("stock_ohlcv_adjusted_price") if isinstance(inventory.get("stock_ohlcv_adjusted_price"), dict) else {}
        return {
            "source": formal.get("source_id") or "missing",
            "asof": job.get("asof"),
            "source_max_date": formal.get("source_max_date"),
            "raw_status": daily_chain.get("raw_status") or "MISSING_OR_DEGRADED",
            "evidence_path": formal.get("evidence_path"),
            "caveat": "raw latest evidence missing or not ready; payload uses available readonly inventory only",
        }

    def _provider_caveat(self, daily_chain: dict[str, Any]) -> str:
        formal_max = ((daily_chain.get("lineage_evidence") or {}).get("formal_calendar_max") if isinstance(daily_chain.get("lineage_evidence"), dict) else None)
        if formal_max and formal_max != daily_chain.get("asof"):
            return f"raw evidence may be newer than formal qlib provider calendar max {formal_max}"
        return "readonly raw evidence; not a provider publish or qlib refresh"

    def _qlib_accepted_latest(self, doc: dict[str, Any], daily_status: dict[str, Any]) -> dict[str, Any]:
        run_dir = str(doc.get("run_dir") or "")
        return {
            "source": str(self.qlib_accepted_latest_path),
            "asof": doc.get("asof") or daily_status.get("latest_asof"),
            "run_id": Path(run_dir).name if run_dir else daily_status.get("latest_run_id"),
            "status": doc.get("status") or daily_status.get("latest_status") or "missing",
            "stale": bool(daily_status.get("fresh_data_wait") or (daily_status.get("pending_asof") and daily_status.get("pending_asof") != (doc.get("asof") or daily_status.get("latest_asof")))),
            "freshness": {
                "pending_asof": daily_status.get("pending_asof"),
                "pending_reason": daily_status.get("pending_reason"),
                "next_retry_hint": daily_status.get("next_retry_hint"),
            },
            "evidence_path": str(self.qlib_accepted_latest_path),
            "pointer_sha256": _fingerprint(self.qlib_accepted_latest_path).get("sha256"),
            "separate_from_controlled_signal_latest": True,
        }

    def _controlled_signal_latest(self, doc: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
        readiness_item = readiness.get("controlled_signal_latest") if isinstance(readiness.get("controlled_signal_latest"), dict) else {}
        return {
            "source": str(self.controlled_signal_latest_path),
            "signal_asof": doc.get("signal_asof") or doc.get("asof") or readiness_item.get("signal_asof"),
            "run_id": doc.get("run_id") or readiness_item.get("run_id"),
            "readonly_only": bool(doc.get("readonly_only")) if doc else None,
            "production_trade_enabled": doc.get("production_trade_enabled") if doc else None,
            "provider_publish": doc.get("provider_publish") if doc else None,
            "qlib_accepted_latest_switch": doc.get("qlib_accepted_latest_switch") if doc else None,
            "pointer_sha256": _fingerprint(self.controlled_signal_latest_path).get("sha256") or ((readiness_item.get("fingerprint") or {}).get("sha256") if isinstance(readiness_item.get("fingerprint"), dict) else None),
            "evidence_path": str(self.controlled_signal_latest_path),
            "caveat": "controlled signal latest is distinct from qlib accepted latest",
        }

    def _readonly_snapshot_latest(self, doc: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
        readiness_item = readiness.get("readonly_snapshot_latest") if isinstance(readiness.get("readonly_snapshot_latest"), dict) else {}
        return {
            "source": str(self.readonly_snapshot_latest_path),
            "signal_asof": doc.get("signal_asof") or doc.get("asof") or readiness_item.get("signal_asof"),
            "target_date": doc.get("target_date") or doc.get("data_asof"),
            "checksum": doc.get("planned_manifest_payload_sha256") or doc.get("source_signal_latest_sha256"),
            "pointer_sha256": _fingerprint(self.readonly_snapshot_latest_path).get("sha256") or ((readiness_item.get("fingerprint") or {}).get("sha256") if isinstance(readiness_item.get("fingerprint"), dict) else None),
            "validation": {
                "readonly_only": doc.get("readonly_only") if doc else None,
                "candidate_only": doc.get("candidate_only") if doc else None,
                "not_provider_accepted_latest": doc.get("not_provider_accepted_latest") if doc else None,
                "not_trade_target_latest": doc.get("not_trade_target_latest") if doc else None,
                "production_trade_enabled": doc.get("production_trade_enabled") if doc else None,
            },
            "evidence_path": str(self.readonly_snapshot_latest_path),
        }

    def _agent_prompt_latest(self, doc: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
        readiness_item = readiness.get("agent_prompt_latest") if isinstance(readiness.get("agent_prompt_latest"), dict) else {}
        return {
            "source": str(self.agent_prompt_latest_path),
            "signal_asof": doc.get("signal_asof") or readiness_item.get("signal_asof"),
            "target_date": doc.get("target_date"),
            "checksum": doc.get("checksum"),
            "pointer_sha256": _fingerprint(self.agent_prompt_latest_path).get("sha256") or ((readiness_item.get("fingerprint") or {}).get("sha256") if isinstance(readiness_item.get("fingerprint"), dict) else None),
            "validation": {
                "readonly_only": doc.get("readonly_only") if doc else None,
                "production_trade_enabled": doc.get("production_trade_enabled") if doc else None,
                "manifest": doc.get("manifest") if doc else None,
            },
            "evidence_path": str(self.agent_prompt_latest_path),
        }

    def _blocker(
        self,
        job: dict[str, Any],
        daily_chain: dict[str, Any],
        readiness: dict[str, Any],
        summary: dict[str, Any],
        publish_state: dict[str, Any],
    ) -> dict[str, Any]:
        if publish_state["completed"]:
            return {
                "status": "auto_publish_chain_completed",
                "blockers": [],
                "blocked_at": "",
                "reason": "",
            }
        if (
            str(summary.get("status") or "") == "auto_publish_chain_completed"
            and not publish_state.get("controls_ok")
        ):
            return {
                "status": "BLOCKED_WITH_REASON",
                "blockers": ["dapr18_authorized_publish_controls_invalid"],
                "blocked_at": "dapr18_authorization_gate",
                "reason": "completed summary does not satisfy strict authorized publish controls",
            }
        if (
            str(summary.get("status") or "") == "auto_publish_chain_completed"
            and publish_state.get("controls_ok")
            and (
                not publish_state.get("after_matches")
                or not publish_state.get("current_matches")
            )
        ):
            return {
                "status": "BLOCKED_WITH_REASON",
                "blockers": ["dapr18_completed_product_state_mismatch"],
                "blocked_at": "dapr18_product_latest_validation",
                "reason": "completed summary does not match its post-state or current product latest pointers",
            }
        blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else summary.get("blockers")
        if not isinstance(blockers, list):
            blockers = []
        return {
            "status": daily_chain.get("state") or readiness.get("readiness_state") or summary.get("source_readiness_state") or job.get("status") or "missing",
            "blockers": blockers,
            "blocked_at": daily_chain.get("blocked_at") or daily_chain.get("daily_chain_blocked_at") or "",
            "reason": daily_chain.get("blocker_reason") or daily_chain.get("daily_chain_blocker_reason") or job.get("message") or "",
        }

    def _latest_natural_cron_job(
        self,
        job_path: Path | None,
        job: dict[str, Any],
        daily_chain: dict[str, Any],
        blocker: dict[str, Any],
        daily_status: dict[str, Any],
        publish_state: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "job_id": job.get("job_id") or (job_path.parent.name if job_path else None),
            "asof": job.get("asof") or daily_chain.get("asof"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "status": job.get("status") or "missing",
            "daily_chain_state": "auto_publish_chain_completed" if publish_state["completed"] else daily_chain.get("state") or job.get("status") or "missing",
            "blocker": blocker,
            "next_retry_hint": (
                "controlled_product_latest_published; formal_qlib_accepted_latest_remains_separate"
                if publish_state["completed"]
                else daily_chain.get("next_retry_hint") or daily_status.get("next_retry_hint")
            ),
            "evidence_path": str(job_path) if job_path else None,
        }

    def _latest_dapr18_evidence_job(
        self,
        dapr18_dir: Path | None,
        dapr18_job: dict[str, Any],
        summary: dict[str, Any],
        readiness: dict[str, Any],
        publish_state: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "job_id": dapr18_job.get("job_id") or summary.get("job_id") or readiness.get("job_id") or (dapr18_dir.name if dapr18_dir else None),
            "asof": dapr18_job.get("asof") or readiness.get("asof"),
            "job_status": dapr18_job.get("status"),
            "dapr18_status": summary.get("status") or "missing",
            "readiness_state": "PUBLISHED" if publish_state["completed"] else readiness.get("readiness_state") or summary.get("source_readiness_state") or "missing",
            "attempted": summary.get("attempted"),
            "dry_run": summary.get("dry_run"),
            "blockers": [] if publish_state["completed"] else readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else summary.get("blockers", []),
            "product_latest_publish_success": publish_state["completed"],
            "product_latest_target_asof": publish_state["target_asof"],
            "evidence_dir": str(dapr18_dir) if dapr18_dir else None,
        }

    def _dapr18_controls(
        self,
        job: dict[str, Any],
        summary: dict[str, Any],
        publish_state: dict[str, Any],
        evidence_binding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "enabled": self._pick_bool(summary.get("enabled"), job.get("dapr18_controlled_latest_orchestration_enabled")),
            "dry_run": self._pick_bool(summary.get("dry_run"), job.get("dapr18_controlled_latest_dry_run")),
            "build_candidates": self._pick_bool(summary.get("build_candidates"), job.get("dapr18_build_candidates")),
            "publish_controlled_signal_latest": self._pick_bool(summary.get("publish_controlled_signal_latest"), job.get("dapr18_publish_controlled_signal_latest")),
            "publish_readonly_snapshot_latest": self._pick_bool(summary.get("publish_readonly_snapshot_latest"), job.get("dapr18_publish_readonly_snapshot_latest")),
            "publish_agent_prompt_latest": self._pick_bool(summary.get("publish_agent_prompt_latest"), job.get("dapr18_publish_agent_prompt_latest")),
            "exact_authorization_present": self._pick_bool(summary.get("exact_authorization_present"), job.get("dapr18_exact_authorization_present")),
            "latest_pointer_write_performed": self._pick_bool(summary.get("latest_pointer_write_performed"), False),
            "product_latest_publish_success": publish_state["completed"],
            "authorized_publish_completed": publish_state["completed"],
            "product_latest_target_asof": publish_state["target_asof"],
            "evidence_bound_to_latest_natural_job": (evidence_binding or {}).get("bound"),
            "evidence_binding_reason": (evidence_binding or {}).get("reason"),
            "evidence_path": ((summary.get("evidence_paths") or {}).get("summary") if isinstance(summary.get("evidence_paths"), dict) else None),
        }

    def _dapr18_publish_state(
        self,
        summary: dict[str, Any],
        controlled_doc: dict[str, Any],
        snapshot_doc: dict[str, Any],
        agent_doc: dict[str, Any],
    ) -> dict[str, Any]:
        after = summary.get("product_latest_state_after") if isinstance(summary.get("product_latest_state_after"), dict) else {}
        target = after.get("target_asof")
        after_matches = bool(
            target
            and after.get("all_product_latest_match_target") is True
            and after.get("controlled_signal_latest_asof") == target
            and after.get("readonly_snapshot_latest_asof") == target
            and after.get("agent_prompt_latest_asof") == target
        )
        noop = summary.get("status") == "auto_publish_idempotent_noop_already_current"
        controls_ok = all(
            summary.get(key) is True
            for key in (
                "attempted",
                "exact_authorization_present",
                "publish_controlled_signal_latest",
                "publish_readonly_snapshot_latest",
                "publish_agent_prompt_latest",
            )
        ) and summary.get("dry_run") is False and (
            summary.get("latest_pointer_write_performed") is True or noop
        )
        write_keys = (
            "controlled_signal_latest_write_performed",
            "readonly_snapshot_latest_write_performed",
            "agent_prompt_latest_write_performed",
        )
        writes_ok = noop or all(summary.get(key) is True for key in write_keys if key in summary)
        current_matches = bool(
            target
            and self._pointer_dates_match(controlled_doc, ("signal_asof", "asof"), target)
            and self._pointer_dates_match(snapshot_doc, ("signal_asof", "asof", "target_date"), target)
            and self._pointer_dates_match(agent_doc, ("signal_asof", "asof", "target_date"), target)
        )
        return {
            "completed": bool(
                summary.get("ok") is True
                and summary.get("status") in {
                    "auto_publish_chain_completed",
                    "auto_publish_idempotent_noop_already_current",
                }
                and controls_ok
                and writes_ok
                and after_matches
                and current_matches
            ),
            "target_asof": target,
            "controls_ok": controls_ok,
            "after_matches": after_matches,
            "current_matches": current_matches,
        }

    @staticmethod
    def _pointer_dates_match(doc: dict[str, Any], fields: tuple[str, ...], target: Any) -> bool:
        present = [doc[field] for field in fields if field in doc]
        return bool(present) and all(value == target for value in present)

    def _dapr18_evidence_binding(
        self,
        latest_job_path: Path | None,
        latest_job: dict[str, Any],
        dapr18_dir: Path | None,
        dapr18_job: dict[str, Any],
        summary: dict[str, Any],
        readiness: dict[str, Any],
    ) -> dict[str, Any]:
        if latest_job_path is None or dapr18_dir is None:
            return {"bound": False, "reason": "missing_natural_or_dapr18_directory"}
        natural_id = latest_job.get("job_id")
        evidence_ids = [
            doc.get("job_id")
            for doc in (dapr18_job, summary, readiness)
            if isinstance(doc, dict) and doc.get("job_id")
        ]
        natural_asof = latest_job.get("asof")
        evidence_asofs = [
            doc.get("asof")
            for doc in (dapr18_job, summary, readiness)
            if isinstance(doc, dict) and doc.get("asof")
        ]
        if latest_job_path.parent == dapr18_dir:
            if (natural_id and any(value != natural_id for value in evidence_ids)) or (natural_asof and any(value != natural_asof for value in evidence_asofs)):
                return {"bound": False, "reason": "same_directory_but_job_id_or_asof_conflict"}
            return {"bound": True, "reason": "same_job_directory"}
        if natural_id and evidence_ids and all(value == natural_id for value in evidence_ids) and natural_asof and evidence_asofs and all(value == natural_asof for value in evidence_asofs):
            return {"bound": True, "reason": "matching_job_id_and_asof"}
        return {"bound": False, "reason": "detached_job_id_asof_or_directory"}

    def _pick_bool(self, *values: Any) -> bool | None:
        for value in values:
            if value is not None:
                return bool(value)
        return None

    def _protected_pointers(self, protected_fingerprint: dict[str, Any]) -> dict[str, Any]:
        current = {
            "controlled_signal_latest": _fingerprint(self.controlled_signal_latest_path),
            "readonly_snapshot_latest": _fingerprint(self.readonly_snapshot_latest_path),
            "agent_prompt_latest": _fingerprint(self.agent_prompt_latest_path),
            "provider_accepted_latest": _fingerprint(self.qlib_accepted_latest_path),
            "legacy_option_c_latest": _fingerprint(self.legacy_option_c_latest_path),
        }
        all_unchanged = protected_fingerprint.get("all_protected_paths_unchanged")
        if all_unchanged is None:
            unchanged = protected_fingerprint.get("unchanged") if isinstance(protected_fingerprint.get("unchanged"), dict) else {}
            all_unchanged = unchanged.get("all_protected_paths_unchanged")
        return {
            "all_unchanged": all_unchanged if all_unchanged is not None else "degraded_missing_dapr18_fingerprint",
            "fingerprints": current,
            "dapr18_evidence": {
                "before": protected_fingerprint.get("before", {}),
                "after": protected_fingerprint.get("after", {}),
                "unchanged": protected_fingerprint.get("unchanged", {}),
            },
        }

    def _forbidden_actions(
        self,
        forbidden_audit: dict[str, Any],
        daily_chain: dict[str, Any],
        summary: dict[str, Any],
        dapr18_dir: Path | None,
    ) -> dict[str, Any]:
        chain_forbidden = daily_chain.get("forbidden_actions") if isinstance(daily_chain.get("forbidden_actions"), dict) else {}
        all_false = forbidden_audit.get("all_false")
        if all_false is None:
            all_false = chain_forbidden.get("all_false")
        if all_false is None:
            all_false = summary.get("forbidden_actions_all_false")
        return {
            "all_false": all_false if all_false is not None else "degraded_missing_audit",
            "actions": forbidden_audit.get("actions") or chain_forbidden.get("actions") or {},
            "audit_path": str(dapr18_dir / "dapr18_forbidden_action_audit.json") if dapr18_dir else None,
            "route_scope": "GET /api/tw-stock/quant/ops/readonly-status only; no runner, refresh, publish, OpenAI, DB, monitor, broker, order, target position or target weight action",
        }

    def _next_action_hint(
        self,
        job: dict[str, Any],
        daily_chain: dict[str, Any],
        readiness: dict[str, Any],
        summary: dict[str, Any],
        daily_status: dict[str, Any],
        publish_state: dict[str, Any],
    ) -> str:
        if publish_state["completed"]:
            return (
                "授权的 DAPR18 controlled signal、readonly snapshot 与 Agent prompt latest 已发布并对齐目标日；"
                "formal qlib accepted latest 保持独立，无需人工推进 product latest。"
            )
        if job.get("status") == "today_data_window_wait":
            return "等待自然 cron 在台北盘后数据窗口重试；当前只读状态没有推进 latest。"
        if daily_chain.get("next_required_action"):
            return f"只读可见性显示阻塞在 {daily_chain.get('blocked_at') or 'daily chain'}；下一步含义是 {daily_chain.get('next_required_action')}。"
        if summary and summary.get("dry_run") and not any(
            bool(summary.get(key))
            for key in (
                "publish_controlled_signal_latest",
                "publish_readonly_snapshot_latest",
                "publish_agent_prompt_latest",
            )
        ):
            return "全自动链路已有只读 dry-run evidence，但 publish 关闭；等待明确授权前不要推进 latest。"
        if readiness.get("readiness_state") == "BLOCKED_WITH_REASON":
            return "只读 evidence 显示 DAPR18 仍被 gate 阻塞；等待自然 cron 或后续授权流程。"
        return daily_status.get("next_retry_hint") or "当前只读状态可查看；无需从本 endpoint 执行任何写入动作。"

    def _ui_wording_contract(self) -> dict[str, Any]:
        return {
            "labels": {
                "provider_raw_latest": "Provider raw/latest",
                "qlib_accepted_latest": "Qlib accepted latest",
                "controlled_signal_latest": "Controlled signal latest",
                "readonly_strategy_snapshot_latest": "Readonly strategy snapshot latest",
                "agent_prompt_latest": "Agent DailyAgentPromptArtifact latest",
                "latest_natural_cron_job": "最近自然 cron job",
                "latest_dapr18_evidence_job": "最近 DAPR18 evidence",
                "dapr18_controls": "DAPR18 controlled publish gate",
            },
            "warnings": [
                "本状态只读，不刷新 provider、不切换 accepted/latest、不发布 controlled signal/snapshot/Agent prompt。",
                "qlib score/rank 只是研究排序，不是收益率、胜率、上涨概率、买入概率或仓位建议。",
                "Agent 使用只读 DailyAgentPromptArtifact，不连接券商、不提交真实订单。",
            ],
            "forbidden_frontend_actions": [
                "provider refresh/publish",
                "accepted/latest switch",
                "monitor write/scan/alerts",
                "broker/quick-trade/order",
                "target_position/target_weight",
                "browser-side OpenAI call",
            ],
        }

    def _all_readonly_guards(self, payload: dict[str, Any]) -> bool:
        trading = payload.get("trading") or {}
        forbidden = payload.get("forbidden_actions") or {}
        actions = forbidden.get("actions") if isinstance(forbidden.get("actions"), dict) else {}
        authorized_pointer_actions = {
            "controlled_signal_latest_write",
            "readonly_snapshot_latest_write",
            "agent_prompt_latest_write",
        }
        unsafe_action_triggered = any(
            bool(value) and (name not in authorized_pointer_actions or not (payload.get("dapr18_controls") or {}).get("authorized_publish_completed"))
            for name, value in actions.items()
        )
        forbidden_audit_available = bool(actions) or forbidden.get("all_false") is True
        controlled = payload.get("controlled_signal_latest") or {}
        snapshot_validation = (payload.get("readonly_strategy_snapshot_latest") or {}).get("validation") or {}
        agent_validation = (payload.get("agent_prompt_latest") or {}).get("validation") or {}
        return bool(
            payload.get("readonly_only")
            and trading.get("orders_enabled") is False
            and trading.get("connects_to_broker") is False
            and trading.get("paper_orders_enabled") is False
            and trading.get("live_trading_enabled") is False
            and trading.get("quick_trade_enabled") is False
            and trading.get("writes_orders") is False
            and trading.get("writes_positions") is False
            and trading.get("research_signal_not_order") is True
            and forbidden_audit_available
            and not unsafe_action_triggered
            and controlled.get("readonly_only") is True
            and controlled.get("production_trade_enabled") is False
            and controlled.get("provider_publish") is False
            and controlled.get("qlib_accepted_latest_switch") is False
            and snapshot_validation.get("readonly_only") is True
            and snapshot_validation.get("candidate_only") is True
            and snapshot_validation.get("not_provider_accepted_latest") is True
            and snapshot_validation.get("not_trade_target_latest") is True
            and snapshot_validation.get("production_trade_enabled") is False
            and agent_validation.get("readonly_only") is True
            and agent_validation.get("production_trade_enabled") is False
        )
