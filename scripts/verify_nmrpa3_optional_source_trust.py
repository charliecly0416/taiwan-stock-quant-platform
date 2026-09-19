#!/usr/bin/env python3
"""Read-only verification gates for NMRPA3 T_R-G (never reads provider bytes)."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from tw_policy_nmrpa3_optional_source_trust import validate_package

ROOT = Path(__file__).resolve().parents[1]
OPTIONAL_BASE = "data_tw/artifacts/research/nmrpa/optional_source_trust_v1"
OPTIONAL_DIRS = [
    OPTIONAL_BASE, f"{OPTIONAL_BASE}/fixed_logs", f"{OPTIONAL_BASE}/fixed_logs/optional_source_binding_log",
    f"{OPTIONAL_BASE}/fixed_logs/optional_source_binding_log/journals", f"{OPTIONAL_BASE}/fixed_logs/optional_source_binding_log/commit_markers",
    f"{OPTIONAL_BASE}/stores", f"{OPTIONAL_BASE}/stores/optional_source_profile_registry", f"{OPTIONAL_BASE}/stores/authorization_ledger",
    f"{OPTIONAL_BASE}/stores/anchor_ledger", f"{OPTIONAL_BASE}/stores/binding_store", f"{OPTIONAL_BASE}/stores/immutable_historical_head_storage",
    f"{OPTIONAL_BASE}/stores/capture_attempt_store", f"{OPTIONAL_BASE}/stores/response_evidence_store", f"{OPTIONAL_BASE}/stores/sealed_object_store",
    f"{OPTIONAL_BASE}/stores/sealed_object_store/sha256",
]
OPTIONAL_JSON = [f"{OPTIONAL_BASE}/descriptor.json", f"{OPTIONAL_BASE}/fixed_logs/optional_source_binding_log/genesis.json",
                 f"{OPTIONAL_BASE}/fixed_logs/optional_source_binding_log/head.json", f"{OPTIONAL_BASE}/fixed_logs/optional_source_binding_log/historical_heads.json",
                 "configs/tw_policy_nmrpa3_optional_source_trust.json"]
CORE_DIRS = [
    "data_tw/artifacts/research", "data_tw/artifacts/research/nmrpa", "data_tw/artifacts/research/nmrpa/immutable_source_roots",
    "data_tw/artifacts/research/nmrpa/trust_bootstrap_v1",
]
CORE_DIRS += [f"data_tw/artifacts/research/nmrpa/immutable_source_roots/{kind}/nmrpa_{kind}_root_v1" for kind in ("sealed_calendar", "formal_instruments", "adjusted_price", "twii", "modela_signal")]
CORE_DIRS += [f"data_tw/artifacts/research/nmrpa/immutable_source_roots/{kind}" for kind in ("sealed_calendar", "formal_instruments", "adjusted_price", "twii", "modela_signal")]
CORE_DIRS += ["data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/fixed_logs", "data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores"]
CORE_DIRS += [f"data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/fixed_logs/{name}/{leaf}" for name in ("principal_registry_log", "identity_registry_log", "credential_registry_log", "trusted_service_registration_log", "publication_authority_registration_log", "capture_recorder_registration_log") for leaf in ("journals", "commit_markers")]
CORE_DIRS += [f"data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/fixed_logs/{name}" for name in ("principal_registry_log", "identity_registry_log", "credential_registry_log", "trusted_service_registration_log", "publication_authority_registration_log", "capture_recorder_registration_log")]
CORE_DIRS += [f"data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/{name}" for name in ("root_locator_registry", "principal_identity_credential_registry_stores", "trusted_actor_registry_stores", "authorization_ledger", "anchor_ledger", "binding_store", "immutable_historical_head_storage", "project_root_identity_marker", "preopened_descriptor_policy")]
CORE_JSON = [f"data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/fixed_logs/{name}/{leaf}.json" for name in ("principal_registry_log", "identity_registry_log", "credential_registry_log", "trusted_service_registration_log", "publication_authority_registration_log", "capture_recorder_registration_log") for leaf in ("genesis", "head", "historical_heads")] + ["data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/project_root_identity_marker/identity.json", "configs/tw_policy_nmrpa3_real_trust_bootstrap.json"]
LATEST_AND_CRON = [
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "data_tw/artifacts/agent_daily_prompt/latest.json",
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]
PROTECTED_SCRIPTS = ["scripts/tw_policy_nmrpa2.py", "scripts/tw_policy_nmrpa3_source_adapter.py"]
FORMAL_PROVIDER = "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
FORMAL_COUNT = 1206
FORMAL_HASH = "ddaef0f85f4fc93c60531bd9f75fd93cd7f6523b36c4928e84ecaa69a6c9a237"


def _lstat(path: Path) -> dict[str, Any]:
    s = path.lstat()
    return {"type": stat.S_IFMT(s.st_mode), "mode": stat.S_IMODE(s.st_mode), "uid": s.st_uid, "gid": s.st_gid, "size": s.st_size, "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _path_fingerprint(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not os.path.lexists(path):
        return {"state": "ABSENT"}
    info = _lstat(path)
    if stat.S_ISLNK(info["type"]):
        raise RuntimeError(f"STOP protected symlink: {rel}")
    result = {"state": "PRESENT", **info}
    if stat.S_ISREG(info["type"]):
        result["sha256"] = _sha(path)
    return result


def _actual_crontab() -> dict[str, Any]:
    proc = subprocess.run(["crontab", "-l"], capture_output=True, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError("STOP cannot inspect actual crontab")
    return {"state": "PRESENT" if proc.returncode == 0 else "ABSENT", "sha256": hashlib.sha256(proc.stdout).hexdigest() if proc.returncode == 0 else None}


def protected_fingerprints() -> dict[str, Any]:
    paths = CORE_DIRS + CORE_JSON + OPTIONAL_DIRS + OPTIONAL_JSON + LATEST_AND_CRON + PROTECTED_SCRIPTS
    if len(set(CORE_DIRS)) != 43 or len(set(CORE_JSON)) != 20 or len(set(OPTIONAL_DIRS)) != 15 or len(set(OPTIONAL_JSON)) != 5:
        raise RuntimeError(f"STOP manifest count drift: core={len(set(CORE_DIRS))}/{len(set(CORE_JSON))}, optional={len(set(OPTIONAL_DIRS))}/{len(set(OPTIONAL_JSON))}")
    result = {rel: _path_fingerprint(rel) for rel in paths}
    result["__actual_crontab__"] = _actual_crontab()
    return result


def formal_provider_metadata() -> dict[str, Any]:
    root = ROOT / FORMAL_PROVIDER
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("STOP formal provider root missing or symlink")
    # R2 metadata-v1: enumerate relative pathnames, then no-follow lstat only.
    rows = []
    for path in [root, *sorted(root.rglob("*"))]:
        info = _lstat(path)
        if stat.S_ISLNK(info["type"]):
            raise RuntimeError(f"STOP provider symlink: {path.relative_to(root)}")
        rows.append(json.dumps(["." if path == root else path.relative_to(root).as_posix(), "directory" if stat.S_ISDIR(info["type"]) else "regular_file" if stat.S_ISREG(info["type"]) else "symlink" if stat.S_ISLNK(info["type"]) else "other", info["uid"], info["gid"], info["mode"], info["size"], info["mtime_ns"], info["ctime_ns"]], ensure_ascii=True, separators=(",", ":")))
    raw = ("\n".join(rows) + "\n").encode("utf-8")
    return {"algorithm": "r2_pathname_lstat_v1", "record_count": len(rows), "metadata_manifest_sha256": hashlib.sha256(raw).hexdigest(), "provider_payload_bytes_read": 0}


def read_package(root: Path = ROOT) -> dict[str, Any]:
    def load(rel: str) -> Any:
        with (root / rel).open("r", encoding="utf-8") as stream:
            return json.load(stream)
    return validate_package(load(OPTIONAL_JSON[0]), load(OPTIONAL_JSON[1]), load(OPTIONAL_JSON[2]), load(OPTIONAL_JSON[3]), load(OPTIONAL_JSON[4]))


def verify_readonly() -> dict[str, Any]:
    package = read_package()
    before = protected_fingerprints()
    provider = formal_provider_metadata()
    after = protected_fingerprints()
    if before != after:
        raise RuntimeError("STOP protected fingerprint drift during read-only verification")
    if provider["record_count"] != FORMAL_COUNT or provider["metadata_manifest_sha256"] != FORMAL_HASH:
        raise RuntimeError(f"STOP formal provider metadata baseline mismatch: {provider}")
    return {"package": package, "protected_unchanged": True, "protected_count": len(before), "formal_provider": provider}


if __name__ == "__main__":
    print(json.dumps(verify_readonly(), ensure_ascii=False, indent=2, sort_keys=True))
