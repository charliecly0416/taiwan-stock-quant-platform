#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_KEYS = {
    "OrderIntent",
    "order_intent",
    "target_weight",
    "target_position",
    "target_quantity",
    "quantity",
    "quantity_instruction",
    "broker",
    "quick_trade",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(raw: str, base: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    candidate = base / path
    if candidate.exists():
        return candidate
    return ROOT / path


def bool_field(payload: dict[str, Any], key: str) -> bool:
    return bool(payload.get(key))


def walk_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(walk_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            hits.extend(walk_forbidden_keys(child, f"{path}[{idx}]"))
    return hits


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "status": "PASS" if ok else "FAIL", "detail": detail})


def validate(job_json: Path) -> dict[str, Any]:
    job = read_json(job_json)
    base = job_json.parent
    chain = job.get("strict_e4_readonly_chain") if isinstance(job.get("strict_e4_readonly_chain"), dict) else {}
    yz2_payload = chain.get("yz2_payload") if isinstance(chain.get("yz2_payload"), dict) else {}
    yz2r_payload = chain.get("yz2r_payload") if isinstance(chain.get("yz2r_payload"), dict) else {}
    checks: list[dict[str, Any]] = []

    price_bridge = str(job.get("strict_e4_readonly_price_bridge_dir") or chain.get("readonly_price_bridge_dir") or "").strip()
    twii_bridge = str(job.get("strict_e4_readonly_twii_bridge") or chain.get("readonly_twii_bridge") or "").strip()
    calendar_bridge = str(job.get("strict_e4_readonly_calendar_bridge") or chain.get("readonly_calendar_bridge") or "").strip()
    price_bridge_path = resolve_path(price_bridge, base) if price_bridge else None
    twii_bridge_path = resolve_path(twii_bridge, base) if twii_bridge else None
    calendar_bridge_path = resolve_path(calendar_bridge, base) if calendar_bridge else None

    add_check(checks, "strict_e4_readonly_chain_attempted", bool_field(chain, "attempted"), str(chain.get("status") or ""))
    add_check(checks, "bridge_args_non_empty", bool(price_bridge and twii_bridge and calendar_bridge), f"price={price_bridge}; twii={twii_bridge}; calendar={calendar_bridge}")
    add_check(checks, "price_bridge_path_exists", bool(price_bridge_path and price_bridge_path.is_dir()), str(price_bridge_path or ""))
    add_check(checks, "twii_bridge_path_exists", bool(twii_bridge_path and twii_bridge_path.is_file()), str(twii_bridge_path or ""))
    add_check(checks, "calendar_bridge_path_exists", bool(calendar_bridge_path and calendar_bridge_path.is_file()), str(calendar_bridge_path or ""))
    add_check(
        checks,
        "yz2_payload_records_bridge_used",
        bool(yz2_payload.get("readonly_price_bridge_used") and yz2_payload.get("readonly_twii_bridge_used") and yz2_payload.get("readonly_calendar_bridge_used")),
        json.dumps({"price": yz2_payload.get("readonly_price_bridge_dir"), "twii": yz2_payload.get("readonly_twii_bridge"), "calendar": yz2_payload.get("readonly_calendar_bridge")}, ensure_ascii=False),
    )
    add_check(
        checks,
        "yz2_chain_records_bridge_used",
        bool(chain.get("readonly_price_bridge_used_by_yz2") and chain.get("readonly_twii_bridge_used_by_yz2") and chain.get("readonly_calendar_bridge_used_by_yz2")),
    )
    add_check(
        checks,
        "yz2r_payload_records_bridge_used",
        bool(yz2r_payload.get("readonly_price_bridge_used") and yz2r_payload.get("readonly_calendar_bridge_used")),
        json.dumps({"price": yz2r_payload.get("readonly_price_bridge_dir"), "calendar": yz2r_payload.get("readonly_calendar_bridge")}, ensure_ascii=False),
    )
    add_check(checks, "yz2r_chain_records_bridge_used", bool(chain.get("readonly_price_bridge_used_by_yz2r") and chain.get("readonly_calendar_bridge_used_by_yz2r")))
    add_check(checks, "no_provider_publish", not bool(job.get("provider_publish_triggered") or chain.get("provider_publish_triggered")))
    add_check(
        checks,
        "no_accepted_latest_switch",
        not bool(job.get("latest_signal_updated") or chain.get("accepted_latest_switch_triggered") or chain.get("qlib_accepted_latest_switch_triggered")),
    )
    add_check(
        checks,
        "no_formal_latest_write",
        not bool(job.get("formal_latest_write_triggered") or job.get("daily_ltr_rerank_latest_write_triggered") or job.get("latest_orthogonal_features_latest_write_triggered")),
    )
    forbidden_hits = walk_forbidden_keys(job)
    add_check(checks, "no_order_target_quantity_broker", not forbidden_hits, "|".join(forbidden_hits))
    add_check(
        checks,
        "no_fallback_to_stale_formal_source_when_bridge_requested",
        not bool(chain.get("formal_normalized_nonempty_used_for_price_or_twii") or chain.get("formal_calendar_used_for_next_day") or yz2_payload.get("formal_normalized_nonempty_used_for_price_or_twii") or yz2_payload.get("formal_calendar_used_for_next_day") or yz2r_payload.get("formal_normalized_nonempty_used_for_price") or yz2r_payload.get("formal_calendar_used_for_next_day")),
    )

    ok = all(check["ok"] for check in checks)
    return {
        "ok": ok,
        "verdict": "PASS" if ok else "FAIL",
        "artifact_type": "TwDailyStrictE4ReadonlyBridgeContractValidatorReport",
        "schema_version": "tw_daily_strict_e4_readonly_bridge_contract_validator_v1",
        "created_at": utc_now(),
        "job_json": str(job_json),
        "checks": checks,
        "summary": {
            "strict_e4_attempted": bool_field(chain, "attempted"),
            "price_bridge": price_bridge,
            "twii_bridge": twii_bridge,
            "calendar_bridge": calendar_bridge,
            "provider_publish_triggered": bool(job.get("provider_publish_triggered") or chain.get("provider_publish_triggered")),
            "accepted_latest_switch_triggered": bool(job.get("latest_signal_updated") or chain.get("accepted_latest_switch_triggered") or chain.get("qlib_accepted_latest_switch_triggered")),
            "formal_normalized_nonempty_used_for_price_or_twii": bool(chain.get("formal_normalized_nonempty_used_for_price_or_twii")),
            "formal_calendar_used_for_next_day": bool(chain.get("formal_calendar_used_for_next_day")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate daily strict E4 readonly price/TWII bridge contract from a job.json.")
    parser.add_argument("--job-json", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = validate(resolve_path(args.job_json, Path.cwd()))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["verdict"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
