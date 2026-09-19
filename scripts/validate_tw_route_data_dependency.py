#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

CATALOG_VALIDATION = ROOT / "data_tw/catalog/dng5_route_dependency_validation.json"
REPORT_PATH = ROOT / "docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_EXECUTION_REPORT_CN.md"

REQUIRED_TOP_LEVEL_FIELDS = [
    "contract_version",
    "route_id",
    "route_type",
    "asof",
    "owner",
    "required_data_layers",
    "required_date_range",
    "required_universe",
    "required_fields",
    "required_latest_concepts",
    "dependencies",
    "optional_dependencies",
    "allowed_fallbacks",
    "forbidden_private_paths",
    "forbidden_actions",
    "expected_outputs",
    "readiness_gate",
]

REQUIRED_DEPENDENCY_FIELDS = [
    "dependency_name",
    "required",
    "layer",
    "dataset_id",
    "artifact_path",
    "latest_concept",
    "required_fields",
    "date_min",
    "date_max",
    "coverage_requirement",
    "pit_required",
    "available_at_required",
    "fallback_allowed",
    "fallback_policy",
    "blocker_if_missing",
]

FORBIDDEN_ACTIONS = {
    "real_data_fetch",
    "provider_refresh",
    "provider_publish",
    "qlib_accepted_latest_switch",
    "readonly_latest_publish",
    "agent_prompt_publish",
    "model_training",
    "model_inference",
    "model_score_generation",
    "strategy_replay",
    "replay_result_nav_generation",
    "broker_order_quick_trade",
    "target_position_or_target_weight",
}

FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_inference_triggered",
    "strategy_replay_triggered",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]

STATUS_BLOCKERS = {
    "MISSING",
    "STALE",
    "BLOCKED_PROVIDER",
    "BLOCKED_SCHEMA",
    "BLOCKED_PIT",
    "BLOCKED_COVERAGE",
    "BLOCKED_VALIDATOR",
    "BLOCKED_QUOTA",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path: str | Path) -> Path:
    path_obj = Path(path)
    if path_obj.is_absolute():
        return path_obj
    return ROOT / path_obj


def rel(path: str | Path) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT.resolve()))
    except (ValueError, FileNotFoundError):
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{rel(path)} must contain a YAML mapping")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_pointer_get(payload: Any, pointer: str) -> tuple[bool, Any]:
    if pointer in ("", "/"):
        return True, payload
    current = payload
    parts = pointer.strip("/").split("/")
    for raw_part in parts:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return False, None
        else:
            return False, None
    return True, current


def catalog_entries_by_dataset(catalog: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    entries: dict[str, list[dict[str, Any]]] = {}
    for entry in catalog.get("entries", []):
        dataset_id = entry.get("dataset_id", "")
        entries.setdefault(dataset_id, []).append(entry)
    return entries


def path_matches(patterns: list[str], path: str) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True
    return False


def latest_summary(latest_status: dict[str, Any], concept: str) -> dict[str, Any]:
    return (latest_status.get("latest_by_concept", {}) or {}).get(concept, {})


def validate_contract(contract_path: Path, catalog_path: Path, latest_status_path: Path) -> dict[str, Any]:
    contract = read_yaml(contract_path)
    catalog = read_json(catalog_path)
    latest_status = read_json(latest_status_path)
    latest_by_concept = latest_status.get("latest_by_concept", {}) or {}
    entries_by_dataset = catalog_entries_by_dataset(catalog)

    schema_errors: list[str] = []
    gate_blockers: list[str] = []
    partial_reasons: list[str] = []
    warnings: list[str] = []
    dependency_results: list[dict[str, Any]] = []
    latest_results: dict[str, dict[str, Any]] = {}

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in contract:
            schema_errors.append(f"missing top-level field: {field}")

    dependencies = contract.get("dependencies", [])
    if not isinstance(dependencies, list) or not dependencies:
        schema_errors.append("dependencies must be a non-empty list")
        dependencies = []

    required_latest_concepts = contract.get("required_latest_concepts", [])
    if not isinstance(required_latest_concepts, list):
        schema_errors.append("required_latest_concepts must be a list")
        required_latest_concepts = []

    for concept in required_latest_concepts:
        if concept not in latest_by_concept:
            schema_errors.append(f"required latest concept not found in latest_status: {concept}")
        else:
            latest = latest_summary(latest_status, concept)
            latest_results[concept] = {
                "exists": True,
                "asof": latest.get("asof", ""),
                "status": latest.get("status", ""),
                "path": latest.get("path", ""),
                "status_reason": latest.get("status_reason", ""),
            }
            if latest.get("status") in STATUS_BLOCKERS:
                partial_reasons.append(f"latest concept {concept} status={latest.get('status')}")

    forbidden_private_paths = contract.get("forbidden_private_paths", [])
    if not isinstance(forbidden_private_paths, list):
        schema_errors.append("forbidden_private_paths must be a list")
        forbidden_private_paths = []

    forbidden_actions = set(contract.get("forbidden_actions", []) or [])
    missing_forbidden_actions = sorted(FORBIDDEN_ACTIONS.difference(forbidden_actions))
    if missing_forbidden_actions:
        schema_errors.append(f"forbidden_actions missing required DNG5 bans: {missing_forbidden_actions}")

    expected_outputs = set(contract.get("expected_outputs", []) or [])
    forbidden_outputs = sorted(expected_outputs.intersection(FORBIDDEN_ACTIONS))
    if forbidden_outputs:
        gate_blockers.append(f"expected_outputs include forbidden actions: {forbidden_outputs}")

    asof = str(contract.get("asof", ""))
    allow_partial = bool((contract.get("readiness_gate", {}) or {}).get("allow_partial", False))

    for index, dep in enumerate(dependencies):
        if not isinstance(dep, dict):
            schema_errors.append(f"dependencies[{index}] must be a mapping")
            continue
        dep_name = dep.get("dependency_name", f"dependencies[{index}]")
        for field in REQUIRED_DEPENDENCY_FIELDS:
            if field not in dep:
                schema_errors.append(f"{dep_name} missing dependency field: {field}")

        artifact_path = str(dep.get("artifact_path", ""))
        artifact_exists = bool(artifact_path) and resolve(artifact_path).exists()
        required = bool(dep.get("required", False))
        fallback_allowed = bool(dep.get("fallback_allowed", False))
        blocker_if_missing = bool(dep.get("blocker_if_missing", False))
        latest_concept = str(dep.get("latest_concept", ""))
        dep_result = {
            "dependency_name": dep_name,
            "required": required,
            "dataset_id": dep.get("dataset_id", ""),
            "layer": dep.get("layer", ""),
            "artifact_path": artifact_path,
            "artifact_exists": artifact_exists,
            "latest_concept": latest_concept,
            "catalog_statuses": [entry.get("status", "") for entry in entries_by_dataset.get(dep.get("dataset_id", ""), [])],
            "gate_status": "PASS",
            "messages": [],
        }

        if latest_concept and latest_concept not in latest_by_concept:
            schema_errors.append(f"{dep_name} latest_concept not found in latest_status: {latest_concept}")
        elif latest_concept:
            latest = latest_summary(latest_status, latest_concept)
            dep_result["latest_status"] = latest.get("status", "")
            dep_result["latest_asof"] = latest.get("asof", "")
            if latest.get("asof") and asof and latest.get("asof") < asof:
                message = f"{dep_name} latest_concept {latest_concept} asof {latest.get('asof')} older than contract asof {asof}"
                dep_result["messages"].append(message)
                if required and not fallback_allowed:
                    gate_blockers.append(message)
                    dep_result["gate_status"] = "BLOCK"
                else:
                    partial_reasons.append(message)
                    dep_result["gate_status"] = "PARTIAL"

        if artifact_path and path_matches(forbidden_private_paths, artifact_path):
            message = f"{dep_name} artifact_path matches forbidden_private_paths: {artifact_path}"
            gate_blockers.append(message)
            dep_result["messages"].append(message)
            dep_result["gate_status"] = "BLOCK"

        if not artifact_exists:
            message = f"{dep_name} artifact_path missing: {artifact_path}"
            dep_result["messages"].append(message)
            if required and (blocker_if_missing or not fallback_allowed):
                gate_blockers.append(message)
                dep_result["gate_status"] = "BLOCK"
            elif required and fallback_allowed:
                partial_reasons.append(message)
                dep_result["gate_status"] = "PARTIAL"
            else:
                warnings.append(message)
                dep_result["gate_status"] = "WARN"

        if dep.get("pit_required") is True and not dep.get("required_fields"):
            schema_errors.append(f"{dep_name} pit_required=true requires non-empty required_fields")
        dependency_results.append(dep_result)

    gate = contract.get("readiness_gate", {}) or {}
    gate_checks = gate.get("required_gate_checks", []) or []
    gate_check_results: list[dict[str, Any]] = []
    if not isinstance(gate_checks, list):
        schema_errors.append("readiness_gate.required_gate_checks must be a list")
        gate_checks = []
    for check in gate_checks:
        check_name = check.get("check_name", "")
        path = str(check.get("path", ""))
        pointer = str(check.get("json_pointer", ""))
        expected = check.get("expected")
        blocker_if_mismatch = bool(check.get("blocker_if_mismatch", False))
        partial_if_match = bool(check.get("partial_if_match", False))
        check_result = {
            "check_name": check_name,
            "path": path,
            "json_pointer": pointer,
            "expected": expected,
            "exists": resolve(path).exists() if path else False,
            "actual": None,
            "passed": False,
            "gate_status": "PASS",
        }
        if not path or not resolve(path).exists():
            message = f"gate check {check_name} path missing: {path}"
            check_result["gate_status"] = "BLOCK" if blocker_if_mismatch else "WARN"
            if blocker_if_mismatch:
                gate_blockers.append(message)
            else:
                warnings.append(message)
            gate_check_results.append(check_result)
            continue
        payload = read_json(resolve(path))
        found, actual = json_pointer_get(payload, pointer)
        check_result["actual"] = actual
        if not found:
            message = f"gate check {check_name} pointer not found: {pointer}"
            check_result["gate_status"] = "BLOCK" if blocker_if_mismatch else "WARN"
            if blocker_if_mismatch:
                gate_blockers.append(message)
            else:
                warnings.append(message)
        elif actual == expected:
            check_result["passed"] = True
            if partial_if_match:
                partial_reasons.append(f"gate check {check_name} matched partial condition {pointer}={actual}")
                check_result["gate_status"] = "PARTIAL"
        else:
            message = f"gate check {check_name} expected {expected!r} at {pointer}, actual {actual!r}"
            if blocker_if_mismatch:
                gate_blockers.append(message)
                check_result["gate_status"] = "BLOCK"
            else:
                partial_reasons.append(message)
                check_result["gate_status"] = "PARTIAL"
        gate_check_results.append(check_result)

    if schema_errors or gate_blockers:
        gate_result = "BLOCK"
    elif partial_reasons:
        gate_result = "PARTIAL" if allow_partial else "BLOCK"
        if not allow_partial:
            gate_blockers.extend(partial_reasons)
    else:
        gate_result = "PASS"

    return {
        "schema_version": "v1.dng5.route_dependency.validation",
        "generated_at": utc_now(),
        "contract_path": rel(contract_path),
        "catalog_path": rel(catalog_path),
        "latest_status_path": rel(latest_status_path),
        "route_id": contract.get("route_id", ""),
        "route_type": contract.get("route_type", ""),
        "asof": contract.get("asof", ""),
        "validation_ok": not schema_errors,
        "gate_pass": gate_result == "PASS",
        "gate_result": gate_result,
        "schema_errors": schema_errors,
        "gate_blockers": gate_blockers,
        "partial_reasons": sorted(set(partial_reasons)),
        "warnings": warnings,
        "latest_results": latest_results,
        "dependency_results": dependency_results,
        "gate_check_results": gate_check_results,
        "claims": {
            "pass_claim": gate.get("pass_claim", ""),
            "partial_claim": gate.get("partial_claim", ""),
            "blocked_claim": gate.get("blocked_claim", ""),
        },
        "forbidden_action_flags": {key: False for key in FORBIDDEN_ACTION_KEYS},
    }


def update_catalog(validation: dict[str, Any]) -> dict[str, Any]:
    catalog = read_json(CATALOG_VALIDATION)
    if not catalog:
        catalog = {
            "schema_version": "v1.dng5.route_dependency.validation_catalog",
            "validations": {},
        }
    catalog["generated_at"] = utc_now()
    catalog.setdefault("validations", {})[validation.get("route_id", validation.get("contract_path", ""))] = validation
    validations = catalog.get("validations", {})
    catalog["summary"] = {
        "route_count": len(validations),
        "pass_count": sum(1 for item in validations.values() if item.get("gate_result") == "PASS"),
        "partial_count": sum(1 for item in validations.values() if item.get("gate_result") == "PARTIAL"),
        "block_count": sum(1 for item in validations.values() if item.get("gate_result") == "BLOCK"),
    }
    catalog["ok"] = all(item.get("validation_ok") for item in validations.values())
    catalog["all_gate_pass"] = all(item.get("gate_pass") for item in validations.values())
    catalog["forbidden_action_flags"] = {key: False for key in FORBIDDEN_ACTION_KEYS}
    write_json(CATALOG_VALIDATION, catalog)
    return catalog


def write_report(catalog: dict[str, Any]) -> None:
    validations = catalog.get("validations", {})
    rows = []
    for route_id, item in sorted(validations.items()):
        rows.append(
            f"| `{route_id}` | `{item.get('gate_result')}` | `{item.get('gate_pass')}` | "
            f"{'; '.join(item.get('gate_blockers') or item.get('partial_reasons') or [''])} |"
        )
    table = "\n".join(rows)
    report = f"""# DNG5 RouteDataDependencyContract 执行报告

生成日期：{utc_now()}

## 1. 本轮产物

- `docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md`
- `scripts/validate_tw_route_data_dependency.py`
- `data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml`
- `data_tw/catalog/route_dependency_contract_examples/qlib_ltr_model_b_20260625.yaml`
- `data_tw/catalog/route_dependency_contract_examples/strategy_input_bundle_20260625.yaml`
- `data_tw/catalog/dng5_route_dependency_validation.json`

## 2. 模板字段

模板要求顶层字段：`contract_version`、`route_id`、`route_type`、`asof`、`owner`、`required_data_layers`、`required_date_range`、`required_universe`、`required_fields`、`required_latest_concepts`、`dependencies`、`optional_dependencies`、`allowed_fallbacks`、`forbidden_private_paths`、`forbidden_actions`、`expected_outputs`、`readiness_gate`。

每个 dependency 要求：`dependency_name`、`required`、`layer`、`dataset_id`、`artifact_path`、`latest_concept`、`required_fields`、`date_min`、`date_max`、`coverage_requirement`、`pit_required`、`available_at_required`、`fallback_allowed`、`fallback_policy`、`blocker_if_missing`。

## 3. Validator 检查逻辑

Validator 只读本地 YAML、DataCatalog、latest_status、readiness matrix 和既有 artifact 路径。检查内容包括：

- 必填顶层字段与 dependency 字段。
- `required_latest_concepts` 与 dependency `latest_concept` 是否存在于 `latest_status.latest_by_concept`。
- `artifact_path` 是否存在；required 且缺失时不得 `gate_pass=true`。
- dependency 路径是否命中 `forbidden_private_paths`。
- `forbidden_actions` 是否覆盖 DNG5 全部禁止动作，`expected_outputs` 是否包含 forbidden action。
- `readiness_gate.required_gate_checks` 的 JSON pointer 是否满足期望值。
- 输出区分 `validation_ok`、`gate_result` 和 `gate_pass`，防止 partial 被误解成 full ready。

## 4. 三个示例验证结果

| route_id | gate_result | gate_pass | 主要原因 |
| --- | --- | --- | --- |
{table}

## 5. 防绕过规则

新路线必须在合同中声明 DataCatalog / latest_status / bundle 路径和 latest 概念。策略路线只能引用 StrategyInputBundle / ReplayInputBundle；模型路线必须声明 qlib provider view、ModelSignalArtifact、FeatureStore 或明确 qlib-only fallback。直接消费未声明的 `data_tw/experiments/**` 私有路径会被 `forbidden_private_paths` 阻断。

## 6. Forbidden Action Audit

本轮只生成合同、validator、示例和报告。未执行真实抓数、provider refresh/publish、qlib accepted latest switch、readonly/Agent publish、模型训练、模型推理、模型 score 生成、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、target_position 或 target_weight。

## 7. DNG6 建议

建议进入 DNG6 daily auto catalog integration，但范围应限定为 catalog/readiness/dashboard 集成。不得把 DNG5 的合同 gate 通过解释成 publish_latest_gate、Model B LTR、replay execution 或生产就绪。
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DNG5 RouteDataDependencyContract.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--latest-status", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write-catalog", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validation = validate_contract(resolve(args.contract), resolve(args.catalog), resolve(args.latest_status))
    if not args.no_write_catalog:
        catalog = update_catalog(validation)
        write_report(catalog)
    if args.json:
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if validation["validation_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
