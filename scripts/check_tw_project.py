#!/usr/bin/env python3
"""Run read-only structural checks for the Taiwan stock project."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tw_stock_workflow.spec import WorkflowSpec
from tw_stock_workflow.task_dispatcher import (
    TaskDispatcher,
    TaskRequestError,
    load_task_request,
)


LIFECYCLE_REGISTRY = ROOT / "configs/script_lifecycle_registry.yaml"


def _load_document(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _check_config_syntax() -> dict[str, Any]:
    files = sorted(
        path
        for path in (ROOT / "configs").rglob("*")
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"}
    )
    failures: list[dict[str, str]] = []
    for path in files:
        try:
            _load_document(path)
        except Exception as exc:  # pragma: no cover - exact parser errors vary
            failures.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
    return {
        "name": "config_syntax",
        "ok": not failures,
        "file_count": len(files),
        "failures": failures,
    }


def _check_task_requests(dispatcher: TaskDispatcher) -> dict[str, Any]:
    files = sorted((ROOT / "configs/tasks").glob("*.yaml"))
    failures: list[dict[str, str]] = []
    for path in files:
        try:
            dispatcher.plan(load_task_request(path))
        except TaskRequestError as exc:
            failures.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
    return {
        "name": "registered_task_requests",
        "ok": not failures,
        "file_count": len(files),
        "failures": failures,
    }


def _check_workflow_specs() -> dict[str, Any]:
    files = sorted((ROOT / "configs/workflows").glob("*.yaml"))
    failures: list[dict[str, str]] = []
    for path in files:
        try:
            WorkflowSpec.load(path)
        except Exception as exc:  # pragma: no cover - exact validation varies
            failures.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
    return {
        "name": "workflow_specs",
        "ok": not failures,
        "file_count": len(files),
        "failures": failures,
    }


def _check_script_lifecycle() -> dict[str, Any]:
    payload = _load_document(LIFECYCLE_REGISTRY)
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != "tw.script.lifecycle.v1"
    ):
        raise ValueError("unsupported script lifecycle registry")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("script lifecycle registry must contain rules")

    script_root = ROOT / str(payload.get("root") or "scripts")
    files = sorted(
        path
        for path in script_root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".sh", ".mjs"}
    )
    counts: Counter[str] = Counter()
    unclassified: list[str] = []
    for path in files:
        relative = path.relative_to(script_root).as_posix()
        lifecycle = None
        for rule in rules:
            patterns = rule.get("patterns", []) if isinstance(rule, dict) else []
            if any(fnmatch.fnmatch(relative, str(pattern)) for pattern in patterns):
                lifecycle = str(rule.get("lifecycle"))
                break
        if lifecycle is None:
            lifecycle = str(payload.get("default_lifecycle") or "unclassified")
            unclassified.append(relative)
        counts[lifecycle] += 1

    return {
        "name": "script_lifecycle",
        "ok": True,
        "file_count": len(files),
        "lifecycle_counts": dict(sorted(counts.items())),
        "default_lifecycle": payload.get("default_lifecycle"),
        "unclassified_count": len(unclassified),
        "unclassified_examples": unclassified[:20],
    }


def run_checks() -> dict[str, Any]:
    dispatcher = TaskDispatcher(ROOT)
    checks = [
        _check_config_syntax(),
        _check_task_requests(dispatcher),
        _check_workflow_specs(),
        _check_script_lifecycle(),
    ]
    return {
        "schema_version": "tw.project.health.v1",
        "status": "PASS" if all(check["ok"] for check in checks) else "FAIL",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run read-only project health checks"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON"
    )
    args = parser.parse_args()
    try:
        result = run_checks()
    except (OSError, ValueError, TaskRequestError, json.JSONDecodeError, yaml.YAMLError) as exc:
        result = {
            "schema_version": "tw.project.health.v1",
            "status": "FAIL",
            "error": str(exc),
        }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"project health: {result['status']}")
        if "checks" in result:
            for check in result["checks"]:
                detail = (
                    f" ({check.get('file_count', 0)} files)"
                    if "file_count" in check
                    else ""
                )
                print(f"- {check['name']}: {'PASS' if check['ok'] else 'FAIL'}{detail}")
                if check.get("unclassified_count"):
                    print(
                        f"  lifecycle defaulted for {check['unclassified_count']} scripts; "
                        "review the registry when adding production scripts"
                    )
        if result.get("error"):
            print(f"error: {result['error']}")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
