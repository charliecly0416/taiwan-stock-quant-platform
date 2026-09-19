from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


class WorkflowError(RuntimeError):
    """Base error for workflow contract violations."""


def validate_asof(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise WorkflowError(f"invalid canonical asof: {value}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise WorkflowError(f"invalid canonical asof: {value}") from exc
    if parsed.isoformat() != value:
        raise WorkflowError(f"invalid canonical asof: {value}")
    return value


def canonical_datetime(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise WorkflowError("decision_cutoff is required")
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowError(f"invalid decision_cutoff: {value}") from exc
    if parsed.tzinfo is None:
        raise WorkflowError("decision_cutoff must include a timezone")
    return parsed.isoformat()


@dataclass(frozen=True)
class ExecutionContext:
    mode: str
    asof: str
    decision_cutoff: str
    workspace: Path
    permissions: frozenset[str]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_.-]*", self.mode):
            raise WorkflowError(f"invalid execution mode: {self.mode}")
        object.__setattr__(self, "asof", validate_asof(self.asof))
        object.__setattr__(
            self, "decision_cutoff", canonical_datetime(self.decision_cutoff)
        )
        object.__setattr__(self, "workspace", Path(self.workspace).resolve())
        permissions = frozenset(self.permissions)
        if any(not re.fullmatch(r"[a-z][a-z0-9_.-]*", item) for item in permissions):
            raise WorkflowError("permissions must be non-empty canonical identifiers")
        object.__setattr__(self, "permissions", permissions)

    def identity_payload(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "asof": self.asof,
            "decision_cutoff": self.decision_cutoff,
            "workspace": str(self.workspace),
            "permissions": sorted(self.permissions),
        }
