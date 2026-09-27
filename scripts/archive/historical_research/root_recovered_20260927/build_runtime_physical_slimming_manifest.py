#!/usr/bin/env python3
"""Build a no-move, path-level runtime dependency manifest.

The output is evidence only.  It never changes a runtime path and deliberately
marks every discovered path as non-movable.
"""
from __future__ import annotations

import argparse
import ast
from collections import deque
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


SCHEMA_VERSION = "runtime_physical_slimming_manifest.v1"
DAPR_TARGETS = [
    "scripts/build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py",
    "scripts/build_tw_dapr10_actual_controlled_signal_latest_publish.py",
    "scripts/build_tw_dapr11_downstream_readonly_snapshot_agent_preflight_or_stop.py",
    "scripts/build_tw_dapr12_candidate_only_readonly_snapshot_dry_run_no_publish.py",
    "scripts/build_tw_dapr13_actual_readonly_snapshot_publish.py",
    "scripts/build_tw_dapr14_agent_prompt_latest_preflight_or_stop.py",
    "scripts/build_tw_dapr15_candidate_only_agent_prompt_dry_run_no_publish.py",
    "scripts/build_tw_dapr16_controlled_agent_prompt_publish_preflight_or_stop.py",
    "scripts/build_tw_dapr17_actual_controlled_agent_prompt_publish.py",
]
ACTIVE_ROOTS = [
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
    "scripts/ensure_tw_stock_services.sh",
    "scripts/watch_tw_stock_services.sh",
    "scripts/run_daily_env.sh",
    "scripts/serve_frontend_static_proxy.py",
    "scripts/tw_stock_ops_backup.py",
    "scripts/verify_tw_stock_readonly_deployment.py",
    "scripts/run_tw_stock_product_fixture_acceptance.sh",
    "scripts/generate-secret-key.sh",
    "scripts/run_daily_tw_stock_auto_update.py",
    "scripts/finmind_logical_acquisition.py",
    "scripts/build_tw_model_b_hsa8_isolated_handoff_wiring.py",
    "scripts/tw_daily_runtime_stages.py",
    "backend/gunicorn_config.py",
    "backend/docker-entrypoint.sh",
    "backend/Dockerfile",
    "backend/run.py",
    "backend/app/__init__.py",
    "backend/app/routes/__init__.py",
    "backend/app/routes/tw_stock.py",
    "backend/app/routes/readonly_strategy_snapshot.py",
    "backend/app/routes/readonly_replay_window.py",
    "backend/app/routes/readonly_replay_window_index.py",
    "backend/app/services/tw_stock_current_strategy_context.py",
    "frontend/src/config/router.config.js",
    "frontend/src/views/tw-stock-monitor/index.vue",
    "frontend/Dockerfile",
    "frontend/package.json",
    ".github/workflows/backend-tw-stock-research.yml",
    "docs/ops/STABLE_OPERATIONS_RUNBOOK_CN.md",
]
CONFIG_ROOTS = [
    "configs/active_baseline_descriptor.yaml",
    "configs/tw_product_artifact_registry.yaml",
    "configs/tw_modular_registry.yaml",
    "configs/tw_replay_window_policy.yaml",
]
PROTECTED_PATHS = [
    "configs/active_baseline_descriptor.yaml",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "data_tw/artifacts/agent_daily_prompt/latest.json",
    "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]
SCAN_SUFFIXES = {".py", ".sh", ".js", ".ts", ".vue", ".yaml", ".yml", ".json"}
IGNORED_PARTS = {"node_modules", "dist", "__pycache__", ".git", ".pytest_cache", ".pnpm-store", "coverage"}
LITERAL_PATH = re.compile(r"(?<![A-Za-z0-9_./-])((?:scripts|backend|frontend|configs|data_tw|qlib_pipeline)/[A-Za-z0-9_./-]+)")
ROOTED_LITERAL_PATH = re.compile(
    r"\$(?:ROOT|\{ROOT\})/((?:scripts|backend|frontend|configs|data_tw|qlib_pipeline)/[A-Za-z0-9_./-]+)"
)
DYNAMIC_TOKENS = ("importlib", ".glob(", ".rglob(", "os.getenv", "os.environ", "Path(", "resolve(")
CONTROL_PATHS = [
    "scripts/build_runtime_physical_slimming_manifest.py",
    "scripts/validate_runtime_physical_slimming_manifest.py",
    "schemas/runtime_physical_slimming_manifest.schema.json",
]
TEST_ROOTS = ("tests", "backend/tests", "frontend/tests")


def sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve(strict=False).relative_to(root.resolve(strict=False)))
    except ValueError:
        return str(path.resolve(strict=False))


def under_root(root: Path, path: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def git_states(root: Path) -> tuple[bool, dict[str, str], list[dict[str, str]]]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"], cwd=root, check=True, capture_output=True
    )
    states: dict[str, str] = {}
    entries: list[dict[str, str]] = []
    for raw in completed.stdout.decode("utf-8", errors="replace").split("\0"):
        if not raw:
            continue
        state, path = raw[:2], raw[3:]
        states[path] = state
        entries.append({"path": path, "state": state})
    return bool(entries), states, sorted(entries, key=lambda item: item["path"])


def cron_commands(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if "run_daily_tw_stock_auto_update.py" in line]


def record(
    *, root: Path, git: dict[str, str], source_kind: str, source_path: str,
    target_path: str, reference_type: str, runtime_scope: str,
    classification: str = "active_keep", evidence: dict[str, Any] | None = None,
    dynamic_exception: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = root / target_path if target_path else None
    exists = bool(target and target.is_file() and under_root(root, target))
    resolved_path = rel(root, target.resolve(strict=False)) if target and under_root(root, target) else ""
    return {
        "source_kind": source_kind,
        "source_path": source_path,
        "target_path": target_path,
        "resolved_path": resolved_path,
        "reference_type": reference_type,
        "runtime_scope": runtime_scope,
        "classification": classification,
        "exists": exists,
        "sha256": sha256(target) if target else "",
        "git_state": git.get(target_path, "clean"),
        "move_eligible": False,
        "evidence": evidence or {},
        "dynamic_exception": dynamic_exception,
    }


def test_source_files(root: Path) -> Iterable[Path]:
    for relative in TEST_ROOTS:
        base = root / relative
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            relative_parts = set(path.relative_to(root).parts)
            if not relative_parts.intersection(IGNORED_PARTS) and path.is_file() and path.suffix.lower() in SCAN_SUFFIXES:
                yield path


def _existing_module_target(root: Path, candidates: Iterable[Path]) -> str | None:
    for candidate in candidates:
        if set(candidate.parts).intersection(IGNORED_PARTS):
            continue
        if candidate.is_file() and under_root(root, candidate):
            return rel(root, candidate)
        package_init = candidate / "__init__.py"
        if package_init.is_file() and under_root(root, package_init):
            return rel(root, package_init)
    return None


def _python_module_target(root: Path, source: Path, module: str, level: int = 0) -> str | None:
    module_parts = [part for part in module.split(".") if part]
    candidates: list[Path] = []
    if level:
        package_dir = source.parent
        for _ in range(max(0, level - 1)):
            package_dir = package_dir.parent
        base = package_dir.joinpath(*module_parts) if module_parts else package_dir
        candidates.extend((base.with_suffix(".py"), base))
    elif module.startswith("scripts."):
        base = root.joinpath(*module_parts)
        candidates.extend((base.with_suffix(".py"), base))
    elif module.startswith("app.") or module == "app":
        base = root / "backend" / Path(*module_parts)
        candidates.extend((base.with_suffix(".py"), base))
    elif module.startswith("backend."):
        base = root.joinpath(*module_parts)
        candidates.extend((base.with_suffix(".py"), base))
    elif "." not in module:
        candidates.extend((source.parent / f"{module}.py", root / "scripts" / f"{module}.py"))
    return _existing_module_target(root, candidates)


def local_python_imports(root: Path, path: Path) -> tuple[list[str], list[str]]:
    if path.suffix != ".py":
        return [], []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return [], ["unparseable_python_source"]
    targets: set[str] = set()
    unresolved: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                target = _python_module_target(root, path, item.name)
                (targets if target else unresolved).add(target or item.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            target = _python_module_target(root, path, module, node.level)
            if target:
                targets.add(target)
            resolved_member = False
            for item in node.names:
                if item.name == "*":
                    continue
                member_module = ".".join(part for part in (module, item.name) if part)
                member_target = _python_module_target(root, path, member_module, node.level)
                if member_target:
                    targets.add(member_target)
                    resolved_member = True
            if not target and not resolved_member:
                unresolved.add(("." * node.level) + module or ".")
    return sorted(targets), sorted(unresolved)


def _frontend_candidate(root: Path, path: Path, value: str) -> str | None:
    if value.startswith("@/"):
        base = root / "frontend/src" / value[2:]
    elif value.startswith("./") or value.startswith("../"):
        base = path.parent / value
    else:
        return None
    candidates = [base]
    if not base.suffix:
        candidates.extend(base.with_suffix(suffix) for suffix in (".js", ".ts", ".vue"))
        candidates.extend(base / f"index{suffix}" for suffix in (".js", ".ts", ".vue"))
    return _existing_module_target(root, candidates)


def frontend_targets(root: Path, path: Path) -> tuple[list[str], list[str]]:
    if path.suffix not in {".js", ".ts", ".vue"}:
        return [], []
    text = path.read_text(encoding="utf-8", errors="replace")
    targets: set[str] = set()
    unresolved: set[str] = set()
    imports: set[str] = set()
    patterns = (
        r"\bimport\s+(?:[^;\n]*?\s+from\s+)?[\"']([^\"']+)[\"']",
        r"\bimport\s*\(\s*[\"']([^\"']+)[\"']\s*\)",
        r"\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)",
    )
    for pattern in patterns:
        imports.update(re.findall(pattern, text))
    for value in imports:
        target = _frontend_candidate(root, path, value)
        (targets if target else unresolved).add(target or value)
    return sorted(targets), sorted(unresolved)


def literal_paths(root: Path, path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    values = set()
    if path.suffix.lower() in {".json", ".yaml", ".yml"}:
        try:
            payload = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
        except (json.JSONDecodeError, yaml.YAMLError):
            payload = None

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(key)
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, str):
                values.update(LITERAL_PATH.findall(value))

        visit(payload)
    for raw in LITERAL_PATH.findall(text):
        cleaned = raw.rstrip(".,:;)}]\"")
        values.add(cleaned)
    for raw in ROOTED_LITERAL_PATH.findall(text):
        values.add(raw.rstrip(".,:;)}]\""))
    return sorted(raw.rstrip(".,:;)}]\"") for raw in values)


def classification_for(target: str, runtime_scope: str) -> str:
    if "archive" in Path(target).parts:
        return "unknown_do_not_move"
    if runtime_scope == "test_harness":
        return "unknown_do_not_move"
    return "active_keep"


def build_manifest(
    root: Path,
    installed_cron: Path,
    actual_cron: Path,
    observed_at: str,
    *,
    git_snapshot: tuple[bool, dict[str, str], list[dict[str, str]]] | None = None,
) -> dict[str, Any]:
    dirty, git, status_entries = git_snapshot or git_states(root)
    installed_text = installed_cron.read_text(encoding="utf-8")
    actual_text = actual_cron.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(**kwargs: Any) -> None:
        key = (kwargs["source_path"], kwargs["target_path"], kwargs["reference_type"])
        if key in seen:
            return
        seen.add(key)
        records.append(record(root=root, git=git, **kwargs))

    production_queue: deque[str] = deque()
    production_sources: set[str] = set()

    def queue_production(target: str) -> None:
        path = root / target
        if (
            target not in production_sources
            and path.is_file()
            and under_root(root, path)
            and path.suffix.lower() in SCAN_SUFFIXES
            and not set(Path(target).parts).intersection(IGNORED_PARTS)
        ):
            production_sources.add(target)
            production_queue.append(target)

    for target in ACTIVE_ROOTS:
        add(source_kind="runtime_root", source_path="manifest_seed", target_path=target,
            reference_type="required_runtime_root", runtime_scope="production_runtime",
            evidence={"seed": "ARCH-4 inventory reviewed runtime root"})
        queue_production(target)
    for target in CONFIG_ROOTS:
        add(source_kind="config", source_path="manifest_seed", target_path=target,
            reference_type="required_registry_or_descriptor", runtime_scope="production_runtime",
            evidence={"seed": "runtime policy/config source"})
        queue_production(target)
    for target in PROTECTED_PATHS:
        add(source_kind="protected_pointer", source_path="manifest_seed", target_path=target,
            reference_type="protected_latest_or_descriptor", runtime_scope="production_runtime",
            evidence={"seed": "protected fingerprint input"})
        queue_production(target)
    for order, target in enumerate(DAPR_TARGETS, start=1):
        add(source_kind="daily_runner", source_path="scripts/run_daily_tw_stock_auto_update.py", target_path=target,
            reference_type="dapr_subprocess", runtime_scope="production_runtime",
            evidence={"dapr_order": order, "expected_step_count": len(DAPR_TARGETS)})
        queue_production(target)
    for target in CONTROL_PATHS:
        add(source_kind="manifest_control", source_path="manifest_seed", target_path=target,
            reference_type="manifest_control", runtime_scope="manifest_control",
            classification="unknown_do_not_move", evidence={"seed": "manifest gate self-fingerprint"})

    while production_queue:
        source = production_queue.popleft()
        path = root / source
        scope = "production_runtime"
        unresolved: dict[str, list[str]] = {}
        python_targets, python_unresolved = local_python_imports(root, path)
        for target in python_targets:
            add(source_kind="python", source_path=source, target_path=target,
                reference_type="python_ast_import", runtime_scope=scope,
                classification=classification_for(target, scope), evidence={"parser": "ast"})
            queue_production(target)
        if python_unresolved:
            unresolved["python_imports"] = python_unresolved
        frontend_import_targets, frontend_unresolved = frontend_targets(root, path)
        for target in frontend_import_targets:
            add(source_kind="frontend", source_path=source, target_path=target,
                reference_type="frontend_static_or_dynamic_import", runtime_scope=scope,
                classification=classification_for(target, scope), evidence={"parser": "regex"})
            queue_production(target)
        if frontend_unresolved:
            unresolved["frontend_imports"] = frontend_unresolved
        for target in literal_paths(root, path):
            candidate = root / target
            if (
                not set(Path(target).parts).intersection(IGNORED_PARTS)
                and candidate.is_file()
                and under_root(root, candidate)
            ):
                add(source_kind="literal_path", source_path=source, target_path=target,
                    reference_type="literal_repo_path", runtime_scope=scope,
                    classification=classification_for(target, scope), evidence={"parser": "literal_path_regex"})
                queue_production(target)
            else:
                unresolved.setdefault("literal_paths", []).append(target)
        if path.suffix.lower() in {".py", ".js", ".ts", ".vue", ".sh"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            hits = [token for token in DYNAMIC_TOKENS if token in text]
            if hits:
                unresolved["dynamic_tokens"] = hits
        if unresolved:
            add(source_kind="dynamic", source_path=source, target_path="",
                reference_type="dynamic_exception", runtime_scope=scope,
                classification="unknown_do_not_move", evidence={"parser": "fail_closed"},
                dynamic_exception={"status": "unresolved_static_path", "references": unresolved, "quarantine": "unknown_do_not_move"})

    # Test references are evidence only and never expand the production closure.
    # Keep repo-local test dependencies visible so a later move cannot silently
    # discard a fixture/helper that is part of the harness.
    for path in test_source_files(root):
        source = rel(root, path)
        python_targets, python_unresolved = local_python_imports(root, path)
        frontend_import_targets, frontend_unresolved = frontend_targets(root, path)
        for target in sorted(set(python_targets + frontend_import_targets)):
            add(source_kind="python", source_path=source, target_path=target,
                reference_type="python_ast_import", runtime_scope="test_harness",
                classification="unknown_do_not_move", evidence={"parser": "ast", "production_closure_member": target in production_sources})
        for target in literal_paths(root, path):
            candidate = root / target
            if (
                not set(Path(target).parts).intersection(IGNORED_PARTS)
                and candidate.is_file()
                and under_root(root, candidate)
            ):
                add(source_kind="literal_path", source_path=source, target_path=target,
                    reference_type="literal_repo_path", runtime_scope="test_harness",
                    classification="unknown_do_not_move", evidence={"parser": "literal_path_regex", "production_closure_member": target in production_sources})
        unresolved: dict[str, list[str]] = {}
        if python_unresolved:
            unresolved["python_imports"] = python_unresolved
        if frontend_unresolved:
            unresolved["frontend_imports"] = frontend_unresolved
        if unresolved:
            add(source_kind="dynamic", source_path=source, target_path="",
                reference_type="dynamic_exception", runtime_scope="test_harness",
                classification="unknown_do_not_move", evidence={"parser": "fail_closed"},
                dynamic_exception={"status": "unresolved_static_path", "references": unresolved, "quarantine": "unknown_do_not_move"})

    records.sort(key=lambda item: (item["source_path"], item["target_path"], item["reference_type"]))
    protected = {
        target: {"exists": (root / target).is_file(), "sha256": sha256(root / target)}
        for target in PROTECTED_PATHS
    }
    closure_summary = {
        "record_count": len(records),
        "production_record_count": sum(item["runtime_scope"] == "production_runtime" for item in records),
        "test_harness_record_count": sum(item["runtime_scope"] == "test_harness" for item in records),
        "manifest_control_record_count": sum(item["runtime_scope"] == "manifest_control" for item in records),
        "dynamic_exception_count": sum(item["reference_type"] == "dynamic_exception" for item in records),
        "archive_record_count": sum("archive" in Path(item["target_path"]).parts for item in records if item["target_path"]),
        "move_eligible_count": sum(bool(item["move_eligible"]) for item in records),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "repository_root": str(root.resolve()),
        "worktree_dirty": dirty,
        "git_status_entries": status_entries,
        "cron_parity": {
            "installed_path": rel(root, installed_cron),
            "installed_sha256": sha256(installed_cron),
            "actual_evidence_path": str(actual_cron.resolve()),
            "actual_sha256": sha256(actual_cron),
            "installed_daily_commands": cron_commands(installed_text),
            "actual_daily_commands": cron_commands(actual_text),
        },
        "dapr_targets": DAPR_TARGETS,
        "protected_fingerprints": protected,
        "closure_summary": closure_summary,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build no-move runtime physical slimming manifest.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-cron", type=Path, default=None)
    parser.add_argument("--actual-cron", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observed-at", default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    installed = args.installed_cron or root / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"
    observed_at = args.observed_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = build_manifest(root, installed.resolve(), args.actual_cron.resolve(), observed_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "records": len(manifest["records"]), "worktree_dirty": manifest["worktree_dirty"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
