"""Small orchestration facade for the Taiwan stock data layer.

The existing acquisition, normalization, and provider writers remain the
implementations of record.  This module only gives callers one typed entry
point and keeps stage status/lineage together; it does not fetch data by
itself and therefore has no provider or latest-pointer side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .types import WorkflowError, validate_asof


class DataPipelineError(WorkflowError):
    """Raised when a data-layer stage violates the pipeline contract."""


@dataclass(frozen=True)
class DataPipelineRequest:
    """Stable request passed to every data-layer stage."""

    asof: str
    scope: str = "daily"
    symbols: tuple[str, ...] = ()
    source_profile: str = "tw-stock-default"
    decision_cutoff: str | None = None

    def __post_init__(self) -> None:
        try:
            canonical_asof = validate_asof(str(self.asof))
        except WorkflowError as exc:
            raise DataPipelineError(str(exc)) from exc
        object.__setattr__(self, "asof", canonical_asof)
        scope = str(self.scope).strip()
        profile = str(self.source_profile).strip()
        if not scope:
            raise DataPipelineError("scope is required")
        if not profile:
            raise DataPipelineError("source_profile is required")
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "source_profile", profile)
        normalized_symbols = tuple(
            symbol.strip().upper()
            for symbol in self.symbols
            if str(symbol).strip()
        )
        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise DataPipelineError("symbols must not contain duplicates")
        object.__setattr__(self, "symbols", normalized_symbols)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asof": self.asof,
            "scope": self.scope,
            "symbols": list(self.symbols),
            "source_profile": self.source_profile,
            "decision_cutoff": self.decision_cutoff,
        }


class AcquisitionStage(Protocol):
    def __call__(self, request: DataPipelineRequest) -> Mapping[str, Any]: ...


class NormalizationStage(Protocol):
    def __call__(
        self, request: DataPipelineRequest, source: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...


class StorageStage(Protocol):
    def __call__(
        self, request: DataPipelineRequest, normalized: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class DataPipelineResult:
    """The stage outputs and the point at which execution stopped."""

    request: DataPipelineRequest
    status: str
    stages: Mapping[str, Mapping[str, Any]]
    stopped_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "status": self.status,
            "stopped_at": self.stopped_at,
            "stages": {name: dict(payload) for name, payload in self.stages.items()},
        }


class DataPipeline:
    """Compose existing data stages without owning their side effects.

    The injected stages are deliberately small adapters around the current
    source, normalization, and Qlib/provider implementations.  A blocked or
    failed stage is returned as evidence and prevents downstream stages from
    running.
    """

    def __init__(
        self,
        *,
        acquire: AcquisitionStage,
        normalize: NormalizationStage,
        store: StorageStage,
    ) -> None:
        self._acquire = acquire
        self._normalize = normalize
        self._store = store

    def run(self, request: DataPipelineRequest) -> DataPipelineResult:
        if not isinstance(request, DataPipelineRequest):
            raise DataPipelineError("run() requires a DataPipelineRequest")

        stages: dict[str, Mapping[str, Any]] = {}
        source = self._stage_payload("acquisition", self._acquire(request))
        stages["acquisition"] = source
        if self._is_blocking(source):
            return DataPipelineResult(
                request=request,
                status=self._status(source),
                stages=stages,
                stopped_at="acquisition",
            )

        normalized = self._stage_payload(
            "normalization", self._normalize(request, source)
        )
        stages["normalization"] = normalized
        if self._is_blocking(normalized):
            return DataPipelineResult(
                request=request,
                status=self._status(normalized),
                stages=stages,
                stopped_at="normalization",
            )

        provider = self._stage_payload("storage", self._store(request, normalized))
        stages["storage"] = provider
        return DataPipelineResult(
            request=request,
            status=self._status(provider),
            stages=stages,
            stopped_at=None,
        )

    @staticmethod
    def _stage_payload(name: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise DataPipelineError(f"{name} stage must return a mapping")
        if not str(payload.get("status") or "").strip():
            raise DataPipelineError(f"{name} stage must return status")
        return dict(payload)

    @staticmethod
    def _status(payload: Mapping[str, Any]) -> str:
        return str(payload.get("status") or "UNKNOWN").strip().upper()

    @classmethod
    def _is_blocking(cls, payload: Mapping[str, Any]) -> bool:
        return cls._status(payload) in {"BLOCKED", "FAILED", "PENDING"}


__all__ = [
    "AcquisitionStage",
    "DataPipeline",
    "DataPipelineError",
    "DataPipelineRequest",
    "DataPipelineResult",
    "NormalizationStage",
    "StorageStage",
]
