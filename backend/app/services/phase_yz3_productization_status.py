"""YZ clean E4 productization status service."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from app.services.tw_stock_artifact_registry import registry_get, registry_path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
SIGNAL_ROOT = registry_path("artifacts", "signal_root")
YZ2R_ROOT = registry_path("artifacts", "yz2r_execution_price_readiness_root")
MODEL_A = str(registry_get("models", "base_model_id"))
MODEL_B = str(registry_get("models", "treatment_model_id"))
MODEL_A_SUBDIR = str(registry_get("artifacts", "model_a_subdir", default="model_a"))
MODEL_B_PREFERRED_SUBDIR = str(registry_get("artifacts", "model_b_preferred_subdir", default="model_b_yz2"))
MODEL_B_FALLBACK_SUBDIR = str(registry_get("artifacts", "model_b_fallback_subdir", default="model_b"))
DEFAULT_STRATEGY = str(registry_get("strategies", "default_strategy_rule"))



def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _has_clean_yz_signal_artifacts(asof_dir: Path) -> bool:
    return (
        (asof_dir / MODEL_A_SUBDIR / "manifest.json").exists()
        and ((asof_dir / MODEL_B_PREFERRED_SUBDIR / "manifest.json").exists() or (asof_dir / MODEL_B_FALLBACK_SUBDIR / "manifest.json").exists())
    )


def resolve_latest_yz_signal_asof(signal_asof: str | None = None) -> str:
    explicit = str(signal_asof or "").strip()
    if explicit:
        return explicit
    if not SIGNAL_ROOT.exists():
        return ""
    candidates = [path.name for path in SIGNAL_ROOT.iterdir() if path.is_dir() and _has_clean_yz_signal_artifacts(path)]
    return sorted(candidates)[-1] if candidates else ""


def _manifest_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"exists": False}
    payload = load_json(path)
    return {
        "exists": True,
        "path": rel(path),
        "artifact_type": payload.get("artifact_type"),
        "model_id": payload.get("model_id"),
        "model_name": payload.get("model_name"),
        "model_family": payload.get("model_family"),
        "signal_asof": payload.get("signal_asof") or payload.get("asof_date"),
        "row_count": payload.get("row_count"),
        "source_model_artifact": payload.get("source_model_artifact"),
        "source_feature_artifact": payload.get("source_feature_artifact"),
        "source_model_a_manifest": payload.get("source_model_a_manifest"),
        "readonly_only": payload.get("readonly_only"),
    }


def _top_candidates(path: Path, limit: int = 8) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    manifest = load_json(path)
    files = manifest.get("files") or {}
    signal_path = path.parent / str(files.get("signals") or "signals.csv")
    if not signal_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with signal_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append({
                "instrument": row.get("instrument"),
                "candidate_rank": row.get("candidate_rank"),
                "score_rank": row.get("score_rank"),
                "full_qlib_rank": row.get("full_qlib_rank"),
                "buy_score": row.get("buy_score"),
            })
    rows.sort(key=lambda r: (int(float(r.get("score_rank") or 999999)), str(r.get("instrument") or "")))
    return rows[:limit]


def _clean_models(registry: dict[str, Any]) -> list[dict[str, Any]]:
    models = (registry.get("production_models") or {}).get("production_selectable") or {}
    clean: list[dict[str, Any]] = []
    for key, value in models.items():
        item = value or {}
        clean.append({
            "model_id": key,
            "display_name": item.get("display_name") or key,
            "frontend_selectable": bool(item.get("frontend_selectable", True)),
            "production_default": bool(item.get("production_default", False)),
        })
    return clean


def _clean_strategies(registry: dict[str, Any]) -> list[dict[str, Any]]:
    strategies = (registry.get("strategies") or {}).get("production_selectable") or {}
    clean: list[dict[str, Any]] = []
    for key, value in strategies.items():
        item = value or {}
        clean.append({
            "strategy_rule_id": key,
            "display_name": item.get("display_name") or key,
            "frontend_selectable": bool(item.get("frontend_selectable", True)),
            "production_default": bool(item.get("production_default", False)),
        })
    return clean


def load_yz3_productization_status(signal_asof: str | None = None) -> dict[str, Any]:
    registry = load_yaml(REGISTRY)
    policy = load_yaml(POLICY)
    resolved_signal_asof = resolve_latest_yz_signal_asof(signal_asof)
    model_a_manifest = SIGNAL_ROOT / resolved_signal_asof / MODEL_A_SUBDIR / "manifest.json" if resolved_signal_asof else SIGNAL_ROOT / "__missing__" / MODEL_A_SUBDIR / "manifest.json"
    model_b_manifest = _first_existing(
        SIGNAL_ROOT / resolved_signal_asof / MODEL_B_PREFERRED_SUBDIR / "manifest.json",
        SIGNAL_ROOT / resolved_signal_asof / MODEL_B_FALLBACK_SUBDIR / "manifest.json",
    ) if resolved_signal_asof else None
    clean_signal_available = bool(resolved_signal_asof and model_a_manifest.exists() and model_b_manifest and model_b_manifest.exists())
    readiness_path = YZ2R_ROOT / resolved_signal_asof / "manifest.json" if resolved_signal_asof else YZ2R_ROOT / "__missing__/manifest.json"
    readiness_exists = readiness_path.exists()
    readiness = load_json(readiness_path) if readiness_exists else {"status": "execution_price_unavailable"}
    execution_status = str(readiness.get("status") or "execution_price_unavailable")
    missing_next_open = int(readiness.get("missing_next_open_count") or 0)
    next_open_count = int(readiness.get("next_open_available_count") or 0)
    price_ready = execution_status == "pass" and next_open_count > 0 and missing_next_open == 0
    paper_apply_allowed = bool(price_ready and clean_signal_available)
    blocked_reason = "" if paper_apply_allowed else ("next_open_unavailable" if readiness_exists else "execution_price_readiness_missing")
    target_next_day = readiness.get("target_next_trading_day") or readiness.get("next_trading_day") or ""
    if paper_apply_allowed:
        message = "成交口径：次一交易日开盘价。行情已可用，可以进行模拟应用。"
    elif readiness_exists and target_next_day:
        message = f"成交口径：次一交易日开盘价。{target_next_day} 行情暂不可用，等待下一轮数据更新。策略信号已生成，模拟应用将在成交价可用后开放。"
    else:
        message = "成交口径：次一交易日开盘价。成交价可用性尚未生成，等待下一轮数据更新。"
    selected_strategy = str(policy.get("default_strategy_rule") or DEFAULT_STRATEGY)
    selected_model = MODEL_B if model_b_manifest and model_b_manifest.exists() and load_json(model_b_manifest).get("artifact_type") == "daily_model_signal" else str(policy.get("default_model_id") or MODEL_A)
    return {
        "ok": clean_signal_available,
        "schema_version": "yz3_productization_status_v1",
        "signal_asof": resolved_signal_asof,
        "models": _clean_models(registry),
        "production_strategies": _clean_strategies(registry),
        "selected_model_id": selected_model,
        "selected_strategy_rule_id": selected_strategy,
        "execution_price_mode": "next_open",
        "execution_price_status": execution_status,
        "execution_price_message": message,
        "execution_price_readiness": {
            "path": rel(readiness_path) if readiness_path.exists() else "",
            "status": execution_status,
            "target_next_trading_day": target_next_day,
            "next_open_available_count": readiness.get("next_open_available_count", 0),
            "next_close_available_count": readiness.get("next_close_available_count", 0),
            "missing_next_open_count": readiness.get("missing_next_open_count", 0),
            "missing_next_close_count": readiness.get("missing_next_close_count", 0),
            "blocked_reason": "" if price_ready else blocked_reason,
            "no_fallback_to_next_close": readiness.get("no_fallback_to_next_close") is True,
            "no_fallback_to_signal_close": readiness.get("no_fallback_to_signal_close") is True,
        },
        "paper_apply_allowed": paper_apply_allowed,
        "paper_apply_blocked_reason": blocked_reason,
        "paper_portfolio": {
            "status": "pending_execution_price" if not paper_apply_allowed else "ready_for_paper_apply",
            "apply_allowed": paper_apply_allowed,
            "apply_blocked_reason": blocked_reason,
            "writes_restricted_to_sim_account": True,
        },
        "latest_artifacts": {
            "model_a": _manifest_summary(model_a_manifest),
            "model_b": _manifest_summary(model_b_manifest),
            "execution_price_readiness": {"exists": readiness_path.exists(), "path": rel(readiness_path) if readiness_path.exists() else ""},
        },
        "strategy_preview": {
            "model_a_top_candidates": _top_candidates(model_a_manifest),
            "model_b_top_candidates": _top_candidates(model_b_manifest) if model_b_manifest else [],
            "realized_return_available": False if not price_ready else True,
            "current_signal_executable_replay_allowed": paper_apply_allowed,
        },
        "safety_flags": {
            "readonly_only": True,
            "no_broker_order": True,
            "no_quick_trade": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor_write": True,
            "no_next_close_fallback": True,
            "old_models_exposed": False,
            "old_strategies_exposed": False,
        },
    }
