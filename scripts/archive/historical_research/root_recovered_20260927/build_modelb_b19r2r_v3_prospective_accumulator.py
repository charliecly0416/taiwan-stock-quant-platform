#!/usr/bin/env python3
"""Build the isolated B19R2R V3 prospective signal/outcome accumulator."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ISOLATED_ROOT = ROOT / "data_tw/experiments/modelb_b19r2r_v3_prospective_accumulator"
AUDIT_ROOT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v3_prospective_readiness_20260916"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
DAILY_JOBS = ROOT / "data_tw/ops/daily_auto_update"
MODEL_ID = "modelb_b19r2r_lambdarank_exact50_78f_v2"
MODEL_A_ID = "e4_frozen_qlib_2018_2022"
MODEL_SHA256 = "8d31069593cc8a1cc7c6fa7ac4cf50a9e897a76af0ab446ddbc26551fc5e5421"
FINAL_MODEL_FROZEN_AT = "2026-09-16T13:16:00+00:00"
CANDIDATE_ID = 14
FEATURE_COUNT = 78
EXACT_COUNT = 50
EXCLUDED_SYMBOL = "TW7769"
SCHEMA = "modelb_b19r2r.v3.prospective_event.v1"
FORBIDDEN_CAPTURE_TOKENS = ("label", "outcome", "future", "forward_return", "next_open", "next_close")
PROTECTED = (
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
)


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("B19V3_E_JSON", str(path)) from exc
    if not isinstance(value, dict):
        raise ContractError("B19V3_E_JSON_OBJECT", str(path))
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise ContractError("B19V3_E_CSV", str(path)) from exc


def atomic_json(path: Path, value: Any, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=True, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_bytes(path: Path, value: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_time(value: Any, code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(code, str(value)) from exc
    if parsed.tzinfo is None:
        raise ContractError(code, "timezone required")
    return parsed.astimezone(timezone.utc)


def normalize_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.isdigit():
        symbol = f"TW{symbol}"
    if not symbol:
        raise ContractError("B19V3_E_SYMBOL", "empty")
    return symbol


def number(value: Any, code: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(code, str(value)) from exc
    if not math.isfinite(result):
        raise ContractError(code, str(value))
    return result


def first_value(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and str(row[name]).strip() != "":
            return row[name]
    return None


def protected_fingerprints() -> dict[str, str | None]:
    return {relative(path): sha256(path) if path.is_file() else None for path in PROTECTED}


def validate_out(path: Path) -> None:
    if not path.resolve().is_relative_to(ISOLATED_ROOT.resolve()):
        raise ContractError("B19V3_E_OUTPUT_ESCAPE", str(path))


def forbidden_paths(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if any(token in lowered for token in FORBIDDEN_CAPTURE_TOKENS):
                found.append(path)
            found.extend(forbidden_paths(nested, path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(forbidden_paths(nested, f"{prefix}[{index}]"))
    return found


def manifest_binding(path: Path, artifact: Path, asof: str) -> dict[str, Any]:
    manifest = read_json(path)
    manifest_asof = str(manifest.get("asof") or manifest.get("signal_asof") or "")[:10]
    if manifest_asof != asof:
        raise ContractError("B19V3_E_ASOF_BINDING", str(path))
    declared = str(manifest.get("artifact_sha256") or manifest.get("signals_sha256") or "")
    if declared != sha256(artifact):
        raise ContractError("B19V3_E_ARTIFACT_CHECKSUM", str(artifact))
    if manifest.get("production_allowed") is not False:
        raise ContractError("B19V3_E_PRODUCTION_BOUNDARY", str(path))
    return manifest


def capture_binding(manifests: list[dict[str, Any]]) -> tuple[str, str]:
    runs = {str(item.get("source_run_id") or item.get("source_acquisition_run_id") or "") for item in manifests}
    cutoffs = {str(item.get("decision_cutoff") or "") for item in manifests}
    if "" in runs or len(runs) != 1:
        raise ContractError("B19V3_E_SAME_RUN", repr(sorted(runs)))
    if "" in cutoffs or len(cutoffs) != 1:
        raise ContractError("B19V3_E_CUTOFF_BINDING", repr(sorted(cutoffs)))
    cutoff = next(iter(cutoffs))
    cutoff_time = parse_time(cutoff, "B19V3_E_CUTOFF")
    for manifest in manifests:
        available_at = parse_time(manifest.get("available_at"), "B19V3_E_AVAILABLE_AT")
        if available_at > cutoff_time:
            raise ContractError("B19V3_E_PIT_ORDER", str(manifest.get("available_at")))
        if manifest.get("pit_status") not in {"PASS", "PIT_SAFE", "STRICT_PIT_PASS"}:
            raise ContractError("B19V3_E_PIT_STATUS", str(manifest.get("pit_status")))
    return next(iter(runs)), cutoff


def exact_rows(path: Path, asof: str, *, score: bool = False) -> list[dict[str, Any]]:
    raw_rows = read_csv(path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_rows:
        row_asof = str(raw.get("date") or raw.get("asof") or raw.get("signal_asof") or "")[:10]
        if row_asof != asof:
            raise ContractError("B19V3_E_ROW_ASOF", row_asof)
        symbol = normalize_symbol(raw.get("instrument") or raw.get("symbol"))
        if symbol in seen:
            raise ContractError("B19V3_E_DUPLICATE_SYMBOL", symbol)
        seen.add(symbol)
        rank_value = first_value(raw, ("rank", "score_rank", "full_qlib_rank"))
        rank = int(number(rank_value, "B19V3_E_RANK"))
        row: dict[str, Any] = {"instrument": symbol, "rank": rank}
        if score:
            row["score"] = number(first_value(raw, ("model_b_score", "score")), "B19V3_E_SCORE")
        rows.append(row)
    if len(rows) != EXACT_COUNT or sorted(row["rank"] for row in rows) != list(range(1, EXACT_COUNT + 1)):
        raise ContractError("B19V3_E_EXACT50", f"rows={len(rows)}")
    if EXCLUDED_SYMBOL in seen:
        raise ContractError("B19V3_E_TW7769_EXCLUDED")
    return sorted(rows, key=lambda row: (row["rank"], row["instrument"]))


def feature_rows(path: Path, manifest: dict[str, Any], asof: str, expected: set[str]) -> tuple[list[str], str]:
    rows = read_csv(path)
    columns = manifest.get("feature_columns")
    if not isinstance(columns, list) or len(columns) != FEATURE_COUNT or len(set(columns)) != FEATURE_COUNT:
        raise ContractError("B19V3_E_78F_DECLARATION", str(len(columns or [])))
    feature_columns = [str(item) for item in columns]
    seen: set[str] = set()
    canonical: list[dict[str, Any]] = []
    for row in rows:
        row_asof = str(row.get("date") or row.get("asof") or row.get("signal_asof") or "")[:10]
        if row_asof != asof:
            raise ContractError("B19V3_E_FEATURE_ASOF", row_asof)
        symbol = normalize_symbol(row.get("instrument") or row.get("symbol"))
        if symbol in seen:
            raise ContractError("B19V3_E_FEATURE_DUPLICATE", symbol)
        seen.add(symbol)
        values = [number(row.get(column), "B19V3_E_78F_FINITE") for column in feature_columns]
        canonical.append({"instrument": symbol, "values": values})
    if seen != expected or len(rows) != EXACT_COUNT:
        raise ContractError("B19V3_E_78F_SCOPE", f"rows={len(rows)}")
    if EXCLUDED_SYMBOL in seen:
        raise ContractError("B19V3_E_TW7769_EXCLUDED")
    return feature_columns, canonical_hash(sorted(canonical, key=lambda item: item["instrument"]))


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("object required")
                    events.append(value)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError("B19V3_E_LEDGER_JSON", str(path)) from exc
    previous = "GENESIS"
    for event in events:
        claimed = event.get("event_hash")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        if body.get("previous_event_hash") != previous or canonical_hash(body) != claimed:
            raise ContractError("B19V3_E_LEDGER_CHAIN", str(event.get("asof")))
        previous = str(claimed)
    return events


def event_semantics(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key not in {"created_at", "previous_event_hash", "event_hash"}}


def append_locked(out: Path, body: dict[str, Any], events: list[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    key = (body["event_type"], body["asof"])
    existing = next((item for item in events if (item.get("event_type"), item.get("asof")) == key), None)
    if existing is not None:
        if event_semantics(existing) == event_semantics(body):
            return existing, False
        raise ContractError("B19V3_E_CONFLICTING_EVENT", ":".join(key))
    body["previous_event_hash"] = events[-1]["event_hash"] if events else "GENESIS"
    event = {**body, "event_hash": canonical_hash(body)}
    ledger = out / "events.jsonl"
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, ensure_ascii=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event, True


def calendar_dates(path: Path) -> list[str]:
    if not path.is_file():
        raise ContractError("B19V3_E_CALENDAR", str(path))
    dates = [line.strip()[:10] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not dates or dates != sorted(set(dates)):
        raise ContractError("B19V3_E_CALENDAR_ORDER", str(path))
    if any(len(item) != 10 for item in dates):
        raise ContractError("B19V3_E_CALENDAR", "empty")
    return dates


def following_day(dates: list[str], asof: str, offset: int) -> str:
    following = [date for date in dates if date > asof]
    if len(following) < offset:
        raise ContractError("B19V3_E_LABEL_NOT_MATURE" if offset == 10 else "B19V3_E_EXECUTION_CALENDAR_PENDING", asof)
    return following[offset - 1]


def longest_consecutive_capture_streak(captured: set[str], dates: list[str]) -> int:
    positions = {date: index for index, date in enumerate(dates)}
    if not captured.issubset(positions):
        missing = sorted(captured - positions.keys())
        raise ContractError("B19V3_E_CAPTURE_NOT_IN_CALENDAR", ",".join(missing))
    longest = current = 0
    previous: int | None = None
    for position in sorted(positions[date] for date in captured):
        current = current + 1 if previous is not None and position == previous + 1 else 1
        longest = max(longest, current)
        previous = position
    return longest


def snapshot_calendar(out: Path, source: Path) -> Path:
    dates = calendar_dates(source)
    content = ("\n".join(dates) + "\n").encode()
    digest = hashlib.sha256(content).hexdigest()
    target = out / "calendar_snapshots" / f"{digest}.txt"
    if target.exists():
        if target.is_symlink() or sha256(target) != digest:
            raise ContractError("B19V3_E_CALENDAR_CHECKSUM", str(target))
        if os.stat(target).st_mode & 0o777 != 0o444:
            raise ContractError("B19V3_E_CALENDAR_SNAPSHOT_MODE", str(target))
    else:
        atomic_bytes(target, content, 0o444)
    return target


def signal_calendars(events: list[dict[str, Any]], out: Path | None = None) -> tuple[list[Path], list[str]]:
    signals = [event for event in events if event.get("event_type") == "SIGNAL_CAPTURED"]
    bindings = {(str(event.get("trading_calendar") or ""), str(event.get("trading_calendar_sha256") or "")) for event in signals}
    if not bindings or any(not path or not digest for path, digest in bindings):
        raise ContractError("B19V3_E_CALENDAR_BINDING")
    paths: list[Path] = []
    snapshots: list[list[str]] = []
    for raw_path, digest in sorted(bindings):
        path = resolve(raw_path)
        if out is not None and not path.resolve().is_relative_to((out / "calendar_snapshots").resolve()):
            raise ContractError("B19V3_E_CALENDAR_SNAPSHOT_ESCAPE", str(path))
        if not path.is_file() or sha256(path) != digest:
            raise ContractError("B19V3_E_CALENDAR_CHECKSUM", str(path))
        paths.append(path)
        snapshots.append(calendar_dates(path))
    snapshots.sort(key=len)
    for earlier, later in zip(snapshots, snapshots[1:]):
        if later[:len(earlier)] != earlier:
            raise ContractError("B19V3_E_CALENDAR_FORK")
    merged = snapshots[-1]
    for event in signals:
        path = resolve(str(event["trading_calendar"]))
        if str(event.get("asof")) not in calendar_dates(path):
            raise ContractError("B19V3_E_CAPTURE_NOT_IN_CALENDAR", str(event.get("asof")))
    return paths, merged


def require_current_calendar(events: list[dict[str, Any]], current_path: Path) -> list[str]:
    _, frozen_dates = signal_calendars(events)
    current_dates = calendar_dates(current_path)
    if len(current_dates) <= len(frozen_dates) or current_dates[:len(frozen_dates)] != frozen_dates:
        raise ContractError("B19V3_E_CALENDAR_NOT_STRICT_EXTENSION", str(current_path))
    return current_dates


def materialize(out: Path) -> None:
    events = load_events(out / "events.jsonl")
    captured = [event["asof"] for event in events if event["event_type"] == "SIGNAL_CAPTURED"]
    settled = [event["asof"] for event in events if event["event_type"] == "EXECUTION_SETTLED"]
    matured = [event["asof"] for event in events if event["event_type"] == "LABEL_MATURED"]
    calendar_paths, dates = signal_calendars(events, out)
    streak = longest_consecutive_capture_streak(set(captured), dates)
    summary = {
        "schema_version": "modelb_b19r2r.v3.accumulator_summary.v1",
        "updated_at": now(),
        "model_id": MODEL_ID,
        "model_sha256": MODEL_SHA256,
        "candidate_id": CANDIDATE_ID,
        "feature_count": FEATURE_COUNT,
        "excluded_symbol": EXCLUDED_SYMBOL,
        "captured_days": captured,
        "execution_settled_days": settled,
        "label_matured_days": matured,
        "mainline_minimum_settled_days": 10,
        "mainline_settled_day_count": len(settled),
        "mainline_gate_ready": len(settled) >= 10,
        "v3_replacement_window_days": 30,
        "v3_captured_day_count": len(captured),
        "v3_longest_consecutive_capture_days": streak,
        "v3_window_ready": streak >= 30,
        "trading_calendar_snapshots": [relative(path) for path in calendar_paths],
        "trading_calendar_snapshot_sha256": [sha256(path) for path in calendar_paths],
        "production_allowed": False,
    }
    atomic_json(out / "summary.json", summary)


def capture(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    validate_out(out)
    before = protected_fingerprints()
    paths = [resolve(args.model_a), resolve(args.features), resolve(args.model_b)]
    manifest_paths = [resolve(args.model_a_manifest), resolve(args.features_manifest), resolve(args.model_b_manifest)]
    manifests = [manifest_binding(manifest, artifact, args.asof) for manifest, artifact in zip(manifest_paths, paths)]
    forbidden = sorted({item for value in [*manifests, *[read_csv(path) for path in paths]] for item in forbidden_paths(value)})
    if forbidden:
        raise ContractError("B19V3_E_FUTURE_FIELD_AT_CAPTURE", ",".join(forbidden[:10]))
    source_run, cutoff = capture_binding(manifests)
    if args.asof < FINAL_MODEL_FROZEN_AT[:10] or parse_time(cutoff, "B19V3_E_CUTOFF") < parse_time(
        FINAL_MODEL_FROZEN_AT, "B19V3_E_MODEL_FREEZE"
    ):
        raise ContractError("B19V3_E_BEFORE_FINAL_MODEL_FREEZE", f"asof={args.asof};cutoff={cutoff}")
    model_a = exact_rows(paths[0], args.asof)
    if manifests[0].get("model_id") != MODEL_A_ID:
        raise ContractError("B19V3_E_MODELA_IDENTITY", str(manifests[0].get("model_id")))
    calendar_source = resolve(args.calendar)
    if args.asof not in calendar_dates(calendar_source):
        raise ContractError("B19V3_E_CAPTURE_NOT_IN_CALENDAR", args.asof)
    expected = {row["instrument"] for row in model_a}
    feature_columns, feature_values_hash = feature_rows(paths[1], manifests[1], args.asof, expected)
    model_b = exact_rows(paths[2], args.asof, score=True)
    if {row["instrument"] for row in model_b} != expected:
        raise ContractError("B19V3_E_MODELB_EXACT50_BINDING")
    model_b_manifest = manifests[2]
    if (
        model_b_manifest.get("model_id") != MODEL_ID
        or int(model_b_manifest.get("candidate_id", -1)) != CANDIDATE_ID
        or int(model_b_manifest.get("feature_count", -1)) != FEATURE_COUNT
        or model_b_manifest.get("model_sha256") != MODEL_SHA256
    ):
        raise ContractError("B19V3_E_MODEL_IDENTITY")
    out.mkdir(parents=True, exist_ok=True)
    calendar_path = snapshot_calendar(out, calendar_source)
    lock_path = out / ".events.lock"
    body = {
        "schema_version": SCHEMA,
        "event_type": "SIGNAL_CAPTURED",
        "asof": args.asof,
        "created_at": now(),
        "source_run_id": source_run,
        "decision_cutoff": cutoff,
        "final_model_frozen_at": FINAL_MODEL_FROZEN_AT,
        "model_id": MODEL_ID,
        "model_a_id": MODEL_A_ID,
        "model_sha256": MODEL_SHA256,
        "candidate_id": CANDIDATE_ID,
        "feature_count": FEATURE_COUNT,
        "feature_columns_sha256": canonical_hash(feature_columns),
        "feature_values_sha256": feature_values_hash,
        "trading_calendar": relative(calendar_path),
        "trading_calendar_sha256": sha256(calendar_path),
        "exact50_symbols": sorted(expected),
        "model_a_ranking": model_a,
        "model_b_ranking": model_b,
        "artifacts": [
            {"path": relative(path), "sha256": sha256(path), "manifest": relative(manifest), "manifest_sha256": sha256(manifest)}
            for path, manifest in zip(paths, manifest_paths)
        ],
        "tw7769_excluded": True,
        "contains_future_label": False,
        "training_performed": False,
        "production_allowed": False,
    }
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        event, changed = append_locked(out, body, load_events(out / "events.jsonl"))
        if changed:
            materialize(out)
    if protected_fingerprints() != before:
        raise ContractError("B19V3_E_PROTECTED_MUTATION")
    return event


def signal_event(events: list[dict[str, Any]], asof: str) -> dict[str, Any]:
    found = [event for event in events if event.get("event_type") == "SIGNAL_CAPTURED" and event.get("asof") == asof]
    if len(found) != 1:
        raise ContractError("B19V3_E_SIGNAL_REQUIRED", f"count={len(found)}")
    return found[0]


def sealed_append(out: Path, body: dict[str, Any], public_body: dict[str, Any]) -> dict[str, Any]:
    sealed = out / "sealed_outcomes"
    sealed.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(sealed, 0o700)
    payload_hash = canonical_hash(body)
    public_body["sealed_payload_sha256"] = payload_hash
    payload_path = sealed / f"{public_body['asof']}.{public_body['event_type'].lower()}.json"
    public_body["sealed_payload"] = relative(payload_path)
    lock_path = out / ".events.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        events = load_events(out / "events.jsonl")
        key = (public_body["event_type"], public_body["asof"])
        existing = next((event for event in events if (event.get("event_type"), event.get("asof")) == key), None)
        if existing is not None:
            if event_semantics(existing) != event_semantics(public_body):
                raise ContractError("B19V3_E_CONFLICTING_EVENT", ":".join(key))
            if not payload_path.is_file() or canonical_hash(read_json(payload_path)) != payload_hash:
                raise ContractError("B19V3_E_SEALED_CONFLICT", str(payload_path))
            return existing
        atomic_json(payload_path, body, mode=0o600)
        event, _ = append_locked(out, public_body, events)
        materialize(out)
        return event


def execution_rows(path: Path, asof: str, expected: set[str], expected_date: str) -> list[dict[str, Any]]:
    rows = read_csv(path)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        symbol = normalize_symbol(row.get("instrument") or row.get("symbol"))
        if symbol in seen:
            raise ContractError("B19V3_E_EXECUTION_DUPLICATE", symbol)
        seen.add(symbol)
        execution_date = str(row.get("execution_date") or row.get("date") or "")[:10]
        next_open = number(row.get("next_open"), "B19V3_E_NEXT_OPEN")
        next_close = number(row.get("next_close"), "B19V3_E_NEXT_CLOSE")
        if execution_date != expected_date or next_open <= 0 or next_close <= 0:
            raise ContractError("B19V3_E_EXECUTION_BINDING", symbol)
        output.append({"instrument": symbol, "execution_date": execution_date, "next_open": next_open, "next_close": next_close})
    if seen != expected or len(rows) != EXACT_COUNT or EXCLUDED_SYMBOL in seen:
        raise ContractError("B19V3_E_EXECUTION_SCOPE", f"rows={len(rows)}")
    return sorted(output, key=lambda row: row["instrument"])


def settle_execution(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    validate_out(out)
    before = protected_fingerprints()
    events = load_events(out / "events.jsonl")
    signal = signal_event(events, args.asof)
    calendar_path = resolve(args.calendar)
    execution_date = following_day(require_current_calendar(events, calendar_path), args.asof, 1)
    artifact = resolve(args.prices)
    manifest_path = resolve(args.prices_manifest)
    manifest = read_json(manifest_path)
    if str(manifest.get("artifact_sha256")) != sha256(artifact):
        raise ContractError("B19V3_E_ARTIFACT_CHECKSUM", str(artifact))
    if str(manifest.get("execution_date", ""))[:10] != execution_date:
        raise ContractError("B19V3_E_EXECUTION_DATE", execution_date)
    if parse_time(manifest.get("available_at"), "B19V3_E_AVAILABLE_AT") <= parse_time(signal["decision_cutoff"], "B19V3_E_CUTOFF"):
        raise ContractError("B19V3_E_NOT_PROSPECTIVE")
    expected = set(signal["exact50_symbols"])
    prices = execution_rows(artifact, args.asof, expected, execution_date)
    sealed = {
        "schema_version": "modelb_b19r2r.v3.execution_outcome.v1",
        "asof": args.asof,
        "execution_date": execution_date,
        "available_at": manifest["available_at"],
        "source_run_id": str(manifest.get("source_run_id") or ""),
        "prices": prices,
        "source_artifact": relative(artifact),
        "source_artifact_sha256": sha256(artifact),
    }
    if not sealed["source_run_id"]:
        raise ContractError("B19V3_E_OUTCOME_SOURCE_RUN")
    public = {
        "schema_version": SCHEMA,
        "event_type": "EXECUTION_SETTLED",
        "asof": args.asof,
        "created_at": now(),
        "execution_date": execution_date,
        "outcome_available_at": manifest["available_at"],
        "trading_calendar": relative(calendar_path),
        "trading_calendar_sha256": sha256(calendar_path),
        "production_allowed": False,
    }
    event = sealed_append(out, sealed, public)
    if protected_fingerprints() != before:
        raise ContractError("B19V3_E_PROTECTED_MUTATION")
    return event


def label_rows(path: Path, expected: set[str]) -> list[dict[str, Any]]:
    rows = read_csv(path)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        symbol = normalize_symbol(row.get("instrument") or row.get("symbol"))
        if symbol in seen:
            raise ContractError("B19V3_E_LABEL_DUPLICATE", symbol)
        seen.add(symbol)
        value = number(first_value(row, ("return_t10", "label")), "B19V3_E_LABEL_VALUE")
        output.append({"instrument": symbol, "return_t10": value})
    if seen != expected or len(rows) != EXACT_COUNT or EXCLUDED_SYMBOL in seen:
        raise ContractError("B19V3_E_LABEL_SCOPE", f"rows={len(rows)}")
    return sorted(output, key=lambda row: row["instrument"])


def mature_label(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    validate_out(out)
    before = protected_fingerprints()
    events = load_events(out / "events.jsonl")
    signal = signal_event(events, args.asof)
    if not any(event.get("event_type") == "EXECUTION_SETTLED" and event.get("asof") == args.asof for event in events):
        raise ContractError("B19V3_E_EXECUTION_REQUIRED")
    calendar_path = resolve(args.calendar)
    label_date = following_day(require_current_calendar(events, calendar_path), args.asof, 10)
    artifact = resolve(args.labels)
    manifest_path = resolve(args.labels_manifest)
    manifest = read_json(manifest_path)
    if str(manifest.get("artifact_sha256")) != sha256(artifact):
        raise ContractError("B19V3_E_ARTIFACT_CHECKSUM", str(artifact))
    if str(manifest.get("label_date", ""))[:10] != label_date:
        raise ContractError("B19V3_E_LABEL_DATE", label_date)
    available = parse_time(manifest.get("available_at"), "B19V3_E_AVAILABLE_AT")
    if available.date().isoformat() < label_date or available <= parse_time(signal["decision_cutoff"], "B19V3_E_CUTOFF"):
        raise ContractError("B19V3_E_LABEL_NOT_MATURE", label_date)
    labels = label_rows(artifact, set(signal["exact50_symbols"]))
    sealed = {
        "schema_version": "modelb_b19r2r.v3.mature_label.v1",
        "asof": args.asof,
        "label_date": label_date,
        "available_at": manifest["available_at"],
        "source_run_id": str(manifest.get("source_run_id") or ""),
        "labels": labels,
        "source_artifact": relative(artifact),
        "source_artifact_sha256": sha256(artifact),
    }
    if not sealed["source_run_id"]:
        raise ContractError("B19V3_E_OUTCOME_SOURCE_RUN")
    public = {
        "schema_version": SCHEMA,
        "event_type": "LABEL_MATURED",
        "asof": args.asof,
        "created_at": now(),
        "label_date": label_date,
        "outcome_available_at": manifest["available_at"],
        "trading_calendar": relative(calendar_path),
        "trading_calendar_sha256": sha256(calendar_path),
        "production_allowed": False,
    }
    event = sealed_append(out, sealed, public)
    if protected_fingerprints() != before:
        raise ContractError("B19V3_E_PROTECTED_MUTATION")
    return event


def recursive_values(value: Any, wanted: set[str]) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) in wanted:
                values.append(nested)
            values.extend(recursive_values(nested, wanted))
    elif isinstance(value, list):
        for nested in value:
            values.extend(recursive_values(nested, wanted))
    return values


def recursive_dicts(value: Any) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if isinstance(value, dict):
        values.append(value)
        for nested in value.values():
            values.extend(recursive_dicts(nested))
    elif isinstance(value, list):
        for nested in value:
            values.extend(recursive_dicts(nested))
    return values


def valid_materialized_bundle(value: dict[str, Any], asof: str) -> bool:
    if value.get("schema_version") != "modelb_b19r2r.v3.materialized_input_bundle.v1":
        return False
    if (
        str(value.get("asof") or "")[:10] != asof
        or value.get("model_a_id") != MODEL_A_ID
        or value.get("model_id") != MODEL_ID
        or value.get("model_sha256") != MODEL_SHA256
        or value.get("candidate_id") != CANDIDATE_ID
        or value.get("feature_count") != FEATURE_COUNT
        or value.get("exact50_count") != EXACT_COUNT
        or value.get("tw7769_excluded") is not True
        or value.get("production_allowed") is not False
    ):
        return False
    source_run = str(value.get("source_run_id") or "")
    cutoff_raw = str(value.get("decision_cutoff") or "")
    inputs = value.get("inputs")
    if not source_run or not cutoff_raw or not isinstance(inputs, list) or len(inputs) != 3:
        return False
    try:
        cutoff = parse_time(cutoff_raw, "B19V3_E_CUTOFF")
    except ContractError:
        return False
    if cutoff < parse_time(FINAL_MODEL_FROZEN_AT, "B19V3_E_MODEL_FREEZE"):
        return False
    roles = {str(item.get("role")) for item in inputs if isinstance(item, dict)}
    if roles != {"model_a_exact50", "canonical_78f", "candidate14_model_b_scores"}:
        return False
    for item in inputs:
        if not isinstance(item, dict):
            return False
        digest = str(item.get("artifact_sha256") or "")
        if (
            str(item.get("source_run_id") or "") != source_run
            or item.get("pit_status") not in {"PASS", "PIT_SAFE", "STRICT_PIT_PASS"}
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest.lower())
        ):
            return False
        try:
            if parse_time(item.get("available_at"), "B19V3_E_AVAILABLE_AT") > cutoff:
                return False
        except ContractError:
            return False
    return True


def readiness_audit(args: argparse.Namespace) -> dict[str, Any]:
    out = resolve(args.out)
    if not out.resolve().is_relative_to(AUDIT_ROOT.parent.resolve()):
        raise ContractError("B19V3_E_AUDIT_OUTPUT_ESCAPE", str(out))
    dates = [date for date in calendar_dates(resolve(args.calendar)) if args.start <= date <= args.end]
    jobs_root = resolve(args.jobs_root)
    rows: list[dict[str, Any]] = []
    for date in dates:
        job_paths = sorted(jobs_root.glob(f"daily_tw_stock_auto_update_{date.replace('-', '')}_*/job.json"))
        jobs = [read_json(path) for path in job_paths]
        runs = {str(item) for job in jobs for item in recursive_values(job, {"logical_run_id", "source_acquisition_run_id", "acquisition_run_id"}) if item}
        cutoffs = {str(item) for job in jobs for item in recursive_values(job, {"decision_cutoff"}) if item}
        serialized = "\n".join(json.dumps(job, sort_keys=True) for job in jobs)
        model_a_present = date in serialized and (
            "model_signal" in serialized.lower()
            or "MODEL_INPUT_READY" in serialized
            or (MODEL_A_ID in serialized and '"exact50_count": 50' in serialized)
        )
        handoff_stop = '"status": "STOP"' in serialized or '"same_run_handoff": "STOP"' in serialized
        canonical_78f = MODEL_ID in serialized and '"feature_count": 78' in serialized
        candidate14_score = MODEL_SHA256 in serialized and '"candidate_id": 14' in serialized
        strict_bundles = [value for job in jobs for value in recursive_dicts(job) if valid_materialized_bundle(value, date)]
        strict_bundle_count = len(strict_bundles)
        strict_pit_binding_proven = strict_bundle_count == 1
        strict_bundle_cutoff = str(strict_bundles[0]["decision_cutoff"]) if strict_bundle_count == 1 else ""
        strict_bundle_after_model_freeze = bool(
            strict_bundle_count == 1
            and parse_time(strict_bundle_cutoff, "B19V3_E_CUTOFF") >= parse_time(FINAL_MODEL_FROZEN_AT, "B19V3_E_MODEL_FREEZE")
        )
        reasons: list[str] = []
        if date < FINAL_MODEL_FROZEN_AT[:10]:
            reasons.append("before_final_model_freeze")
        if not jobs:
            reasons.append("daily_job_absent")
        if not runs:
            reasons.append("source_run_unbound")
        if not cutoffs:
            reasons.append("decision_cutoff_unbound")
        if not model_a_present:
            reasons.append("model_a_exact50_unproven")
        if handoff_stop:
            reasons.append("same_run_handoff_STOP")
        if not canonical_78f:
            reasons.append("canonical_78f_not_bound")
        if not candidate14_score:
            reasons.append("candidate14_model_b_score_absent")
        if strict_bundle_count == 0:
            reasons.append("strict_input_bundle_unproven")
        elif strict_bundle_count > 1:
            reasons.append("multiple_strict_input_bundles")
        eligible = (
            date >= FINAL_MODEL_FROZEN_AT[:10]
            and strict_bundle_count == 1
            and strict_pit_binding_proven
            and strict_bundle_after_model_freeze
            and not handoff_stop
        )
        if eligible:
            reasons = []
        materialization_gap = bool(
            date >= FINAL_MODEL_FROZEN_AT[:10]
            and runs
            and cutoffs
            and model_a_present
            and (not canonical_78f or not candidate14_score)
        )
        if eligible:
            readiness_class = "ELIGIBLE"
        elif date < FINAL_MODEL_FROZEN_AT[:10]:
            readiness_class = "BEFORE_FINAL_MODEL_FREEZE"
        elif materialization_gap:
            readiness_class = "MATERIALIZATION_GAP"
        else:
            readiness_class = "SOURCE_OR_LINEAGE_NOT_READY"
        after = [item for item in dates if item > date]
        rows.append({
            "asof": date,
            "status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
            "readiness_class": readiness_class,
            "job_count": len(jobs),
            "source_run_count": len(runs),
            "cutoff_count": len(cutoffs),
            "model_a_evidence_present": model_a_present,
            "canonical_78f_bound": canonical_78f,
            "candidate14_score_bound": candidate14_score,
            "strict_bundle_count": strict_bundle_count,
            "strict_pit_binding_proven": strict_pit_binding_proven,
            "strict_bundle_cutoff": strict_bundle_cutoff,
            "strict_bundle_after_model_freeze": strict_bundle_after_model_freeze,
            "tw7769_excluded_required": True,
            "t10_mature_on_known_calendar": len(after) >= 10,
            "t10_date": after[9] if len(after) >= 10 else "",
            "reasons": ";".join(reasons),
        })
    out.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["asof", "status"]
    atomic_csv(out / "READINESS_BY_DAY.csv", rows, fields)
    summary = {
        "schema_version": "modelb_b19r2r.v3.readiness_audit.v1",
        "created_at": now(),
        "window": {"start": args.start, "end": args.end},
        "calendar": relative(resolve(args.calendar)),
        "calendar_sha256": sha256(resolve(args.calendar)),
        "final_model_frozen_at": FINAL_MODEL_FROZEN_AT,
        "actual_trading_day_count": len(rows),
        "eligible_capture_day_count": sum(row["status"] == "ELIGIBLE" for row in rows),
        "not_eligible_day_count": sum(row["status"] == "NOT_ELIGIBLE" for row in rows),
        "readiness_class_counts": {
            name: sum(row["readiness_class"] == name for row in rows)
            for name in ("ELIGIBLE", "BEFORE_FINAL_MODEL_FREEZE", "MATERIALIZATION_GAP", "SOURCE_OR_LINEAGE_NOT_READY")
        },
        "t10_mature_calendar_day_count": sum(bool(row["t10_mature_on_known_calendar"]) for row in rows),
        "mainline_gate": {"required_real_prospective_settled_days": 10, "accepted_days": 0, "ready": False},
        "v3_replacement_confirmation": {"required_consecutive_capture_days": 30, "accepted_days": 0, "ready": False},
        "b8_compatibility": {
            "date": "2026-09-14",
            "old_shadow_status": "one_unsettled_day_with_entry_only",
            "compatible_with_b19r2r_v3": False,
            "reasons": ["legacy_fillna_or_neutral_semantics", "not_candidate14_canonical_78f", "not_settled"],
            "counted_in_mainline_gate": False,
            "counted_in_v3_window": False,
        },
        "tw7769_policy": "excluded_no_imputation_no_substitution_no_universe_expansion",
        "not_eligible_rows_are_not_ledger_events": True,
        "production_allowed": False,
    }
    atomic_json(out / "READINESS_AUDIT.json", summary)
    input_contract = {
        "schema_version": "modelb_b19r2r.v3.expected_input_bundle.v1",
        "model_id": MODEL_ID,
        "model_a_id": MODEL_A_ID,
        "model_sha256": MODEL_SHA256,
        "candidate_id": CANDIDATE_ID,
        "required_scope": "exact_same_model_a_top50",
        "required_feature_count": FEATURE_COUNT,
        "required_artifacts": ["model_a_exact50", "canonical_78f", "candidate14_model_b_scores"],
        "required_bindings": ["asof", "source_run_id", "decision_cutoff", "available_at_lte_cutoff", "artifact_sha256"],
        "pit_status_allowlist": ["PASS", "PIT_SAFE", "STRICT_PIT_PASS"],
        "excluded_symbol": EXCLUDED_SYMBOL,
        "exclusion_semantics": "no_imputation_no_substitution_no_universe_expansion",
        "future_fields_forbidden_at_capture": list(FORBIDDEN_CAPTURE_TOKENS),
        "production_allowed": False,
    }
    atomic_json(out / "EXPECTED_INPUT_BUNDLE_CONTRACT.json", input_contract)
    return summary


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    item = commands.add_parser("capture")
    item.add_argument("--out", required=True)
    item.add_argument("--asof", required=True)
    item.add_argument("--model-a", required=True)
    item.add_argument("--model-a-manifest", required=True)
    item.add_argument("--features", required=True)
    item.add_argument("--features-manifest", required=True)
    item.add_argument("--model-b", required=True)
    item.add_argument("--model-b-manifest", required=True)
    item.add_argument("--calendar", default=str(CALENDAR))
    item = commands.add_parser("settle-execution")
    item.add_argument("--out", required=True)
    item.add_argument("--asof", required=True)
    item.add_argument("--prices", required=True)
    item.add_argument("--prices-manifest", required=True)
    item.add_argument("--calendar", default=str(CALENDAR))
    item = commands.add_parser("mature-label")
    item.add_argument("--out", required=True)
    item.add_argument("--asof", required=True)
    item.add_argument("--labels", required=True)
    item.add_argument("--labels-manifest", required=True)
    item.add_argument("--calendar", default=str(CALENDAR))
    item = commands.add_parser("readiness-audit")
    item.add_argument("--out", default=str(AUDIT_ROOT))
    item.add_argument("--calendar", default=str(CALENDAR))
    item.add_argument("--jobs-root", default=str(DAILY_JOBS))
    item.add_argument("--start", default="2026-09-02")
    item.add_argument("--end", default="2026-09-16")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        handlers = {
            "capture": capture,
            "settle-execution": settle_execution,
            "mature-label": mature_label,
            "readiness-audit": readiness_audit,
        }
        value = handlers[args.command](args)
    except ContractError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code, "detail": exc.detail}, sort_keys=True))
        return 2
    print(json.dumps({"status": "PASS", "result": value}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
