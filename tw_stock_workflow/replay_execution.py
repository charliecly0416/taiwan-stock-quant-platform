from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

import yaml

from .artifacts import ArtifactError, ArtifactRef, ArtifactResolver
from .types import ExecutionContext, WorkflowError


MODEL_A = "e4_frozen_qlib_2018_2022"
STRATEGY = "top50_exit_one_worst_sell"
WINDOW_START = "2026-01-01"
WINDOW_END = "2026-05-07"
SOURCE_CANDIDATE = Path(
    "data_tw/artifacts/readonly_replay_windows/wf2_candidate_model_a_v4/"
    "e4_frozen_qlib_2018_2022/top50_exit_one_worst_sell/20260101_20260507/"
    "wf2a_a1dd7d213f1913c9e53e90de/order_intent_replay_result/manifest.json"
)
PROTECTED_REPLAY_ROOTS = (
    Path("data_tw/artifacts/readonly_replay_windows/d6"),
    Path("data_tw/artifacts/readonly_replay_windows/d7"),
)
EXECUTION_IMPLEMENTATIONS = (
    Path("tw_stock_workflow/replay_execution.py"),
    Path("scripts/build_tw_readonly_replay_window_artifact.py"),
    Path("scripts/validate_tw_readonly_replay_window_artifact.py"),
    Path("scripts/run_tw_modular_order_intent_replay_parity.py"),
)

ValidationFunction = Callable[[Path], dict[str, Any]]
BuilderFunction = Callable[..., dict[str, Any]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _execution_implementation_digest(files: Any) -> str:
    if not isinstance(files, list) or not files:
        raise WorkflowError("replay candidate execution implementation is missing")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "bytes"}:
            raise WorkflowError("replay candidate execution implementation is invalid")
        path = item["path"]
        digest = item["sha256"]
        size = item["bytes"]
        if (
            not isinstance(path, str)
            or not path
            or path in seen
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or type(size) is not int
            or size < 0
        ):
            raise WorkflowError("replay candidate execution implementation is invalid")
        seen.add(path)
        normalized.append({"path": path, "sha256": digest, "bytes": size})
    payload = json.dumps(
        sorted(normalized, key=lambda item: item["path"]),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_script(repo_root: Path, relative: str, module_name: str) -> Any:
    path = (repo_root / relative).resolve()
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise WorkflowError(f"unable to load workflow dependency: {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_validator(repo_root: Path) -> ValidationFunction:
    module = _load_script(
        repo_root,
        "scripts/validate_tw_readonly_replay_window_artifact.py",
        "tw_workflow_wf2b_replay_validator",
    )
    return module.validate_artifact


def _default_builder(repo_root: Path) -> BuilderFunction:
    module = _load_script(
        repo_root,
        "scripts/build_tw_readonly_replay_window_artifact.py",
        "tw_workflow_wf2b_replay_builder",
    )
    return module.build_artifact


class ReplayCandidateInputAdapter:
    adapter_id = "replay_candidate_input.wf2b.v1"

    def __init__(
        self,
        repo_root: Path,
        *,
        source_manifest_path: Path | None = None,
        validator: ValidationFunction | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._resolver = ArtifactResolver(self.repo_root)
        self.source_manifest_path = self._contained(
            source_manifest_path or SOURCE_CANDIDATE
        )
        allowed_root = (
            self.repo_root
            / "data_tw/artifacts/readonly_replay_windows/wf2_candidate_model_a_v4"
        ).resolve()
        try:
            self.source_manifest_path.relative_to(allowed_root)
        except ValueError as exc:
            raise ArtifactError(
                "WF-2B input must be the isolated WF-2A candidate"
            ) from exc
        self.validator = validator

    def _contained(self, raw_path: str | Path) -> Path:
        return self._resolver.resolve_path(str(raw_path))

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.repo_root))

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid WF-2B JSON input: {path}") from exc
        if not isinstance(value, dict):
            raise ArtifactError(f"WF-2B JSON input must be an object: {path}")
        return value

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ArtifactError(f"invalid WF-2B YAML input: {path}") from exc
        if not isinstance(value, dict):
            raise ArtifactError(f"WF-2B YAML input must be an object: {path}")
        return value

    def _required_binding_paths(self, manifest: dict[str, Any]) -> set[Path]:
        def required_ref(value: Any, label: str) -> Path:
            if not isinstance(value, str) or not value:
                raise ArtifactError(f"WF-2B required input reference missing: {label}")
            return self._contained(value)

        paths = {
            self.source_manifest_path,
            required_ref(manifest.get("baseline_manifest"), "baseline_manifest"),
            required_ref(manifest.get("replay_window_policy"), "replay_window_policy"),
            required_ref(manifest.get("model_registry"), "model_registry"),
            required_ref(manifest.get("baseline_descriptor"), "baseline_descriptor"),
            required_ref(
                manifest.get("canonical_price_store_manifest"),
                "canonical_price_store_manifest",
            ),
        }
        validation = manifest.get("replay_window_policy_validation") or {}
        paths.add(
            required_ref(
                validation.get("source_training_report"), "source_training_report"
            )
        )
        identity = manifest.get("model_source_identity") or {}
        for field in (
            "canonical_training_manifest",
            "canonical_model_artifact",
            "raw_oos_score",
            "signal_manifest",
            "full_rank_manifest",
        ):
            paths.add(required_ref(identity.get(field), field))
        artifacts = manifest.get("artifacts") or {}
        paths.add(
            required_ref(
                artifacts.get("source_identity_audit"), "source_identity_audit"
            )
        )

        price_manifest = self._load_json(
            required_ref(
                manifest.get("canonical_price_store_manifest"),
                "canonical_price_store_manifest",
            )
        )
        paths.add(required_ref(price_manifest.get("prices_path"), "prices_path"))
        for field in ("signal_manifest", "full_rank_manifest"):
            lineage = self._load_json(required_ref(identity.get(field), field))
            outputs = lineage.get("output_files") or {}
            if not isinstance(outputs, dict) or not outputs:
                raise ArtifactError(f"WF-2B lineage outputs missing: {field}")
            for name, value in outputs.items():
                paths.add(required_ref(value, f"{field}.output_files.{name}"))
        return paths

    def resolve(self) -> ArtifactRef:
        if not self.source_manifest_path.is_file():
            raise ArtifactError("WF-2A source candidate manifest is missing")
        validator = self.validator or _default_validator(self.repo_root)
        validation = validator(self.source_manifest_path)
        if not isinstance(validation, dict) or validation.get("ok") is not True:
            raise ArtifactError("WF-2A source candidate failed the complete validator")
        manifest = self._load_json(self.source_manifest_path)
        expected = {
            "artifact_type": "replay_result",
            "schema_version": "readonly_replay_result_wf2a_v1",
            "model_id": MODEL_A,
            "strategy_rule": STRATEGY,
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
            "asof": WINDOW_END,
            "status": "CANDIDATE_HOLD",
            "execution_price_mode": "next_open",
            "product_index_admission": False,
        }
        for field, value in expected.items():
            actual = manifest.get(field)
            if isinstance(value, bool):
                matches = type(actual) is bool and actual is value
            else:
                matches = actual == value
            if not matches:
                raise ArtifactError(f"WF-2B source identity mismatch: {field}")
        run_id = manifest.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("wf2a_"):
            raise ArtifactError("WF-2B source candidate run_id is invalid")

        checksum_path = self._contained(manifest.get("checksum_manifest"))
        checksum = self._load_json(checksum_path)
        files = checksum.get("files")
        if not isinstance(files, list) or not files:
            raise ArtifactError("WF-2B source checksum closure is empty")
        bound_files: list[dict[str, Any]] = []
        declared_paths: set[Path] = set()
        for item in files:
            if not isinstance(item, dict):
                raise ArtifactError("WF-2B source checksum entry is invalid")
            path = self._contained(item.get("path"))
            if path in declared_paths:
                raise ArtifactError("WF-2B source checksum path is duplicated")
            declared_paths.add(path)
            if (
                not path.is_file()
                or item.get("sha256") != _sha256(path)
                or type(item.get("bytes")) is not int
                or item["bytes"] != path.stat().st_size
            ):
                raise ArtifactError(f"WF-2B bound input checksum mismatch: {path}")
            bound_files.append(
                {
                    "path": self._relative(path),
                    "sha256": item["sha256"],
                    "bytes": item["bytes"],
                }
            )
        required_paths = self._required_binding_paths(manifest)
        missing = sorted(
            self._relative(path) for path in required_paths - declared_paths
        )
        if missing:
            raise ArtifactError(
                f"WF-2B input checksum closure is incomplete: {', '.join(missing)}"
            )
        builder_inputs = {
            field: manifest[field]
            for field in (
                "baseline_manifest",
                "replay_window_policy",
                "model_registry",
                "baseline_descriptor",
                "canonical_price_store_manifest",
            )
        }
        implementation_files = []
        for relative in EXECUTION_IMPLEMENTATIONS:
            path = self._contained(relative)
            if not path.is_file():
                raise ArtifactError(
                    f"WF-2B execution implementation is missing: {relative}"
                )
            implementation_files.append(
                {
                    "path": self._relative(path),
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
        implementation_files.sort(key=lambda item: item["path"])
        implementation_digest = _execution_implementation_digest(implementation_files)
        return ArtifactRef(
            adapter_id=self.adapter_id,
            artifact_type="replay_result",
            model_id=MODEL_A,
            asof=WINDOW_END,
            status="CANDIDATE_HOLD",
            run_id=run_id,
            path=self._relative(self.source_manifest_path.parent),
            manifest_path=self._relative(self.source_manifest_path),
            manifest_sha256=_sha256(self.source_manifest_path),
            metadata={
                "binding_kind": "WF2A_COMPLETE_REPLAY_INPUT_CLOSURE",
                "strategy_rule": STRATEGY,
                "window_start": WINDOW_START,
                "window_end": WINDOW_END,
                "input_identity_sha256": manifest.get("identity_sha256"),
                "builder_inputs": builder_inputs,
                "checksum_manifest": self._relative(checksum_path),
                "checksum_manifest_sha256": _sha256(checksum_path),
                "bound_files": sorted(bound_files, key=lambda item: item["path"]),
                "execution_implementation_files": implementation_files,
                "execution_implementation_sha256": implementation_digest,
            },
        )


class ReplayCandidateExecution:
    module_id = "replay_candidate.build_validate"
    required_permissions = frozenset({"artifact.read", "replay.candidate.write"})

    def __init__(
        self,
        repo_root: Path,
        *,
        input_adapter: ReplayCandidateInputAdapter | None = None,
        builder: BuilderFunction | None = None,
        validator: ValidationFunction | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.input_adapter = input_adapter or ReplayCandidateInputAdapter(
            self.repo_root
        )
        self.builder = builder
        self.validator = validator

    @staticmethod
    def _validate_config(context: ExecutionContext, config: dict[str, Any]) -> None:
        required = {
            "model_id": MODEL_A,
            "strategy_rule": STRATEGY,
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
        }
        unknown = sorted(set(config) - set(required))
        if unknown:
            raise WorkflowError(
                f"unknown replay candidate config fields: {', '.join(unknown)}"
            )
        for field, expected in required.items():
            if config.get(field) != expected:
                raise WorkflowError(
                    f"replay candidate {field} must be fixed to {expected}"
                )
        if context.mode != "replay":
            raise WorkflowError("replay candidate execution requires replay mode")
        if context.asof != WINDOW_END:
            raise WorkflowError(f"replay candidate asof must be {WINDOW_END}")

    def _candidate_root(self, context: ExecutionContext) -> Path:
        workspace = context.workspace.resolve()
        try:
            workspace.relative_to(self.repo_root)
        except ValueError:
            pass
        else:
            raise WorkflowError("replay candidate workspace must be outside repository")
        for relative in PROTECTED_REPLAY_ROOTS:
            protected = (self.repo_root / relative).resolve()
            if workspace == protected or protected in workspace.parents:
                raise WorkflowError(
                    "replay candidate workspace is a protected product path"
                )
        candidate_root = (
            workspace / "artifacts/wf2b_model_a_replay_candidate"
        ).resolve()
        try:
            candidate_root.relative_to(workspace)
        except ValueError as exc:
            raise WorkflowError("replay candidate output escapes workspace") from exc
        return candidate_root

    def _implementation_root(
        self, source_ref: ArtifactRef, candidate_root: Path
    ) -> tuple[Path, str]:
        files = source_ref.metadata.get("execution_implementation_files")
        digest = _execution_implementation_digest(files)
        if source_ref.metadata.get("execution_implementation_sha256") != digest:
            raise WorkflowError(
                "replay candidate execution implementation digest mismatch"
            )
        implementation_root = (candidate_root / f"implementation_{digest}").resolve()
        self._require_candidate_path(implementation_root, candidate_root)
        return implementation_root, digest

    def resolve_artifact_inputs(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        resolver: ArtifactResolver,
    ) -> list[ArtifactRef]:
        self._validate_config(context, config)
        self._candidate_root(context)
        return [self.input_adapter.resolve()]

    def _validate_output(
        self, manifest_path: Path, source_ref: ArtifactRef, candidate_root: Path
    ) -> dict[str, Any]:
        resolved = manifest_path.resolve()
        try:
            resolved.relative_to(candidate_root.resolve())
        except ValueError as exc:
            raise WorkflowError("replay candidate manifest escaped workspace") from exc
        validator = self.validator or _default_validator(self.repo_root)
        result = validator(resolved)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise WorkflowError("replay candidate failed the complete validator")
        try:
            manifest = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowError("replay candidate manifest is invalid") from exc
        if (
            manifest.get("run_id") != source_ref.run_id
            or manifest.get("identity_sha256")
            != source_ref.metadata.get("input_identity_sha256")
            or manifest.get("status") != "CANDIDATE_HOLD"
            or manifest.get("product_index_admission") is not False
            or manifest.get("model_id") != MODEL_A
            or manifest.get("strategy_rule") != STRATEGY
            or manifest.get("window_start") != WINDOW_START
            or manifest.get("window_end") != WINDOW_END
        ):
            raise WorkflowError("replay candidate output identity is invalid")
        return manifest

    @staticmethod
    def _require_candidate_path(path: Path, candidate_root: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(candidate_root.resolve())
        except ValueError as exc:
            raise WorkflowError("replay candidate output escapes workspace") from exc
        return resolved

    def execute(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        inputs: dict[str, dict[str, Any]],
        resolver: ArtifactResolver,
    ) -> dict[str, Any]:
        self._validate_config(context, config)
        candidate_root = self._candidate_root(context)
        source_ref = self.input_adapter.resolve()
        implementation_root, implementation_digest = self._implementation_root(
            source_ref, candidate_root
        )
        window_key = f"{WINDOW_START}_{WINDOW_END}".replace("-", "")
        expected_manifest = (
            implementation_root
            / MODEL_A
            / STRATEGY
            / window_key
            / source_ref.run_id
            / "order_intent_replay_result/manifest.json"
        )
        expected_manifest = self._require_candidate_path(
            expected_manifest, candidate_root
        )
        reused_candidate = expected_manifest.is_file()
        if not reused_candidate:
            builder_inputs = source_ref.metadata.get("builder_inputs") or {}
            builder = self.builder or _default_builder(self.repo_root)
            result = builder(
                model_id=MODEL_A,
                strategy_rule=STRATEGY,
                start=WINDOW_START,
                end=WINDOW_END,
                out_root=implementation_root,
                baseline_manifest=self.repo_root / builder_inputs["baseline_manifest"],
                policy_path=self.repo_root / builder_inputs["replay_window_policy"],
                registry_path=self.repo_root / builder_inputs["model_registry"],
                baseline_descriptor_path=self.repo_root
                / builder_inputs["baseline_descriptor"],
                price_store_manifest_path=self.repo_root
                / builder_inputs["canonical_price_store_manifest"],
            )
            raw_manifest = result.get("manifest") if isinstance(result, dict) else None
            if not isinstance(raw_manifest, str) or not raw_manifest:
                raise WorkflowError("replay candidate builder returned no manifest")
            built_manifest = Path(raw_manifest)
            expected_manifest = (
                built_manifest
                if built_manifest.is_absolute()
                else (self.repo_root / built_manifest)
            )
        manifest = self._validate_output(expected_manifest, source_ref, candidate_root)
        relative_manifest = str(
            expected_manifest.resolve().relative_to(context.workspace)
        )
        return {
            "artifact_type": "ReplayResultArtifactCandidate",
            "status": "CANDIDATE_HOLD",
            "product_index_admission": False,
            "model_id": MODEL_A,
            "strategy_rule": STRATEGY,
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
            "run_id": manifest["run_id"],
            "manifest": relative_manifest,
            "manifest_sha256": _sha256(expected_manifest),
            "execution_implementation_sha256": implementation_digest,
            "workspace": str(context.workspace),
            "reused_candidate": reused_candidate,
        }
