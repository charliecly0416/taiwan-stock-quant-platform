from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .types import WorkflowError


class WorkflowSpecError(WorkflowError):
    pass


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    module: str
    needs: tuple[str, ...]
    policy: str
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "module": self.module,
            "needs": list(self.needs),
            "policy": self.policy,
            "config": self.config,
        }


@dataclass(frozen=True)
class WorkflowSpec:
    schema_version: str
    workflow_id: str
    version: str
    nodes: tuple[WorkflowNode, ...]

    @classmethod
    def load(cls, path: Path) -> WorkflowSpec:
        try:
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
            else:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
            raise WorkflowSpecError(f"invalid workflow spec: {path}") from exc
        return cls.from_mapping(payload)

    @classmethod
    def from_mapping(cls, payload: Any) -> WorkflowSpec:
        if not isinstance(payload, dict):
            raise WorkflowSpecError("workflow spec must be an object")
        allowed = {"schema_version", "workflow_id", "version", "nodes"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise WorkflowSpecError(f"unknown workflow fields: {', '.join(unknown)}")
        if payload.get("schema_version") != "tw.workflow.spec.v1":
            raise WorkflowSpecError("unsupported workflow schema_version")
        workflow_id = payload.get("workflow_id")
        version = payload.get("version")
        if (
            not isinstance(workflow_id, str)
            or not re.fullmatch(r"[a-z][a-z0-9_.-]*", workflow_id)
            or not isinstance(version, str)
            or not version
        ):
            raise WorkflowSpecError("invalid workflow_id or version")
        raw_nodes = payload.get("nodes")
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise WorkflowSpecError("workflow nodes must be a non-empty list")
        nodes: list[WorkflowNode] = []
        seen: set[str] = set()
        for raw in raw_nodes:
            if not isinstance(raw, dict):
                raise WorkflowSpecError("workflow node must be an object")
            extra = sorted(set(raw) - {"id", "module", "needs", "policy", "config"})
            if extra:
                raise WorkflowSpecError(f"unknown node fields: {', '.join(extra)}")
            node_id = raw.get("id")
            module = raw.get("module")
            if not isinstance(node_id, str) or not re.fullmatch(
                r"[a-z][a-z0-9_.-]*", node_id
            ):
                raise WorkflowSpecError(f"invalid node id: {node_id}")
            if node_id in seen:
                raise WorkflowSpecError(f"duplicate workflow node: {node_id}")
            seen.add(node_id)
            if not isinstance(module, str) or not re.fullmatch(
                r"[a-z][a-z0-9_.-]*", module
            ):
                raise WorkflowSpecError(f"invalid module id: {module}")
            needs = raw.get("needs", [])
            if not isinstance(needs, list) or any(
                not isinstance(item, str) for item in needs
            ):
                raise WorkflowSpecError(f"needs must be a string list: {node_id}")
            if len(needs) != len(set(needs)):
                raise WorkflowSpecError(f"duplicate dependency in node: {node_id}")
            if node_id in needs:
                raise WorkflowSpecError(f"node depends on itself: {node_id}")
            policy = raw.get("policy")
            config = raw.get("config", {})
            if policy not in {"required", "optional", "nonblocking"}:
                raise WorkflowSpecError(f"invalid node policy: {node_id}")
            if not isinstance(config, dict):
                raise WorkflowSpecError(f"invalid config field: {node_id}")
            nodes.append(WorkflowNode(node_id, module, tuple(needs), policy, config))
        known = {node.node_id for node in nodes}
        for node in nodes:
            missing = sorted(set(node.needs) - known)
            if missing:
                raise WorkflowSpecError(
                    f"unknown dependencies for {node.node_id}: {', '.join(missing)}"
                )
        spec = cls("tw.workflow.spec.v1", workflow_id, version, tuple(nodes))
        spec.topological_nodes()
        spec._validate_nonblocking_dependencies()
        return spec

    def _validate_nonblocking_dependencies(self) -> None:
        by_id = {node.node_id: node for node in self.nodes}

        def ancestors(node: WorkflowNode) -> set[str]:
            result: set[str] = set(node.needs)
            for dependency in node.needs:
                result.update(ancestors(by_id[dependency]))
            return result

        for node in self.nodes:
            if node.policy == "required" and any(
                by_id[dependency].policy == "nonblocking"
                for dependency in ancestors(node)
            ):
                raise WorkflowSpecError(
                    f"required node cannot depend on a nonblocking branch: {node.node_id}"
                )

    def topological_nodes(self) -> tuple[WorkflowNode, ...]:
        by_id = {node.node_id: node for node in self.nodes}
        indegree = {node.node_id: len(node.needs) for node in self.nodes}
        dependents: dict[str, list[str]] = {node.node_id: [] for node in self.nodes}
        order_index = {node.node_id: index for index, node in enumerate(self.nodes)}
        for node in self.nodes:
            for dependency in node.needs:
                dependents[dependency].append(node.node_id)
        ready = [node.node_id for node in self.nodes if indegree[node.node_id] == 0]
        ordered: list[WorkflowNode] = []
        while ready:
            ready.sort(key=order_index.__getitem__)
            current = ready.pop(0)
            ordered.append(by_id[current])
            for child in dependents[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        if len(ordered) != len(self.nodes):
            raise WorkflowSpecError("workflow dependency cycle detected")
        return tuple(ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "workflow_id": self.workflow_id,
            "version": self.version,
            "nodes": [node.to_dict() for node in self.nodes],
        }
