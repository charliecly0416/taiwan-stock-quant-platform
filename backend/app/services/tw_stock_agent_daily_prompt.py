"""Loader for validated TW Agent DailyAgentPromptArtifact."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.validate_tw_agent_daily_prompt_artifact import validate_artifact


DEFAULT_LATEST_PATH = "data_tw/artifacts/agent_daily_prompt/latest.json"


class TWStockAgentDailyPromptError(RuntimeError):
    pass


@dataclass(frozen=True)
class TWStockAgentDailyPromptArtifact:
    artifact_dir: Path
    manifest: Dict[str, Any]
    prompt_context: Dict[str, Any]
    prompt_text: str
    context_digest: Dict[str, Any]
    allowed_citations: list[str]


class TWStockAgentDailyPromptLoader:
    """Load and validate a DailyAgentPromptArtifact from latest pointer or explicit dir."""

    def __init__(self, *, latest_path: str | Path = DEFAULT_LATEST_PATH) -> None:
        self.latest_path = Path(latest_path)

    def load(self, *, artifact_dir: Optional[str | Path] = None) -> TWStockAgentDailyPromptArtifact:
        latest_payload = None if artifact_dir else self._read_latest()
        resolved_dir = Path(artifact_dir) if artifact_dir else Path(str(latest_payload.get("artifact_dir")))
        if not resolved_dir.exists():
            raise TWStockAgentDailyPromptError(f"artifact_dir_missing:{resolved_dir}")
        validation = validate_artifact(resolved_dir)
        if not validation.ok:
            raise TWStockAgentDailyPromptError("artifact_validation_failed:" + ";".join(validation.errors))

        manifest = self._read_json(resolved_dir / "manifest.json")
        if latest_payload is not None:
            self._check_latest_pointer(latest_payload, resolved_dir=resolved_dir, manifest=manifest)
        prompt_context = self._read_json(resolved_dir / "prompt_context.json")
        prompt_text = (resolved_dir / "prompt_text.md").read_text(encoding="utf-8")
        self._check_readonly_flags(manifest)
        digest = self._context_digest(resolved_dir=resolved_dir, manifest=manifest, prompt_context=prompt_context)
        return TWStockAgentDailyPromptArtifact(
            artifact_dir=resolved_dir,
            manifest=manifest,
            prompt_context=prompt_context,
            prompt_text=prompt_text,
            context_digest=digest,
            allowed_citations=self._allowed_citations(digest),
        )

    def _read_latest(self) -> Dict[str, Any]:
        if not self.latest_path.exists():
            raise TWStockAgentDailyPromptError(f"latest_missing:{self.latest_path}")
        latest = self._read_json(self.latest_path)
        if latest.get("artifact_type") != "tw_agent_daily_prompt_latest":
            raise TWStockAgentDailyPromptError("latest_invalid_artifact_type")
        artifact_dir = latest.get("artifact_dir")
        if not isinstance(artifact_dir, str) or not artifact_dir:
            raise TWStockAgentDailyPromptError("latest_missing_artifact_dir")
        return latest

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TWStockAgentDailyPromptError(f"json_read_failed:{path}:{exc}") from exc
        if not isinstance(payload, dict):
            raise TWStockAgentDailyPromptError(f"json_not_object:{path}")
        return payload


    @staticmethod
    def _check_latest_pointer(latest: Dict[str, Any], *, resolved_dir: Path, manifest: Dict[str, Any]) -> None:
        manifest_path = resolved_dir / "manifest.json"
        latest_manifest = latest.get("manifest")
        if latest_manifest and Path(str(latest_manifest)) != manifest_path:
            raise TWStockAgentDailyPromptError("latest_manifest_path_mismatch")
        if latest.get("checksum") and latest.get("checksum") != manifest.get("checksum"):
            raise TWStockAgentDailyPromptError("latest_checksum_mismatch")
        if latest.get("signal_asof") and latest.get("signal_asof") != manifest.get("signal_asof"):
            raise TWStockAgentDailyPromptError("latest_signal_asof_mismatch")

    @staticmethod
    def _check_readonly_flags(manifest: Dict[str, Any]) -> None:
        checks = {
            "readonly_only": True,
            "not_order": True,
            "not_target_position": True,
            "production_trade_enabled": False,
        }
        for field, expected in checks.items():
            if manifest.get(field) is not expected:
                raise TWStockAgentDailyPromptError(f"manifest_{field}_invalid")

    @staticmethod
    def _context_digest(*, resolved_dir: Path, manifest: Dict[str, Any], prompt_context: Dict[str, Any]) -> Dict[str, Any]:
        date_context = prompt_context.get("date_context") or {}
        freshness = prompt_context.get("freshness") or {}
        return {
            "signal_asof": manifest.get("signal_asof"),
            "target_date": manifest.get("target_date"),
            "prompt_artifact": str(resolved_dir / "manifest.json"),
            "checksum": manifest.get("checksum"),
            "execution_price_status": date_context.get("execution_price_status"),
            "freshness_status": freshness.get("status"),
        }

    @staticmethod
    def _allowed_citations(digest: Dict[str, Any]) -> list[str]:
        signal_asof = digest.get("signal_asof")
        checksum = digest.get("checksum")
        citations = [f"agent_prompt:{signal_asof}:{checksum}"]
        citations.append(str(digest.get("prompt_artifact") or ""))
        return [item for item in citations if item]
