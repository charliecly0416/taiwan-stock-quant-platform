#!/usr/bin/env python3
"""Run the contract-limited SSAP1 official sector-source probe."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import ssl
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/sector_source_acquisition_and_pit_contract/ssap1_narrow_dual_market_official_probe"
ALLOWLIST = {
    "openapi.twse.com.tw",
    "twse-regulation.twse.com.tw",
    "www.tpex.org.tw",
    "mops.twse.com.tw",
}
USER_AGENT = "TaiwanStockQuantPlatform-SSAP1-ResearchProbe/1.0"
ACCEPT = "application/json,text/html"
TIMEOUT_SECONDS = 20
MAX_REQUESTS = 12
MAX_EXCERPT_CHARS = 2400
CHALLENGE_MARKERS = (
    "captcha",
    "cloudflare",
    "access denied",
    "verify you are human",
    "challenge-platform",
    "login required",
    "sign in to continue",
    "paywall",
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def compact_text(data: bytes, content_type: str) -> str:
    charset = "utf-8"
    match = re.search(r"charset=([^;\s]+)", content_type, flags=re.I)
    if match:
        charset = match.group(1).strip('"\'')
    try:
        text = data.decode(charset, errors="replace")
    except LookupError:
        text = data.decode("utf-8", errors="replace")
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def json_field_inventory(value: Any) -> list[str]:
    fields: set[str] = set()

    def walk(node: Any, depth: int) -> None:
        if depth > 6:
            return
        if isinstance(node, dict):
            for key, child in node.items():
                fields.add(str(key))
                walk(child, depth + 1)
        elif isinstance(node, list):
            for child in node[:3]:
                walk(child, depth + 1)

    walk(value, 0)
    return sorted(fields)


def sample_excerpt(data: bytes, content_type: str) -> tuple[list[str], str, Any | None]:
    parsed: Any | None = None
    fields: list[str] = []
    if "json" in content_type.lower() or data.lstrip().startswith((b"{", b"[")):
        try:
            parsed = json.loads(data.decode("utf-8-sig"))
            fields = json_field_inventory(parsed)
            if isinstance(parsed, list):
                safe = parsed[:2]
            elif isinstance(parsed, dict):
                safe = {key: parsed[key] for key in list(parsed)[:12]}
            else:
                safe = parsed
            excerpt = json.dumps(safe, ensure_ascii=False, sort_keys=True)
            return fields, excerpt[:MAX_EXCERPT_CHARS], parsed
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    return fields, compact_text(data, content_type)[:MAX_EXCERPT_CHARS], parsed


def field_flags(fields: list[str]) -> dict[str, bool]:
    lowered = " ".join(fields).lower()
    symbol = any(term in lowered for term in ("公司代號", "公司代号", "公司代码", "證券代號", "证券代号", "symbol", "stockno", "code"))
    market = any(term in lowered for term in ("市場", "市场", "market", "上市", "上櫃", "上柜"))
    sector_name = any(term in lowered for term in ("產業別", "产业别", "產業名稱", "产业名称", "industry name", "sector name"))
    sector_code = any(term in lowered for term in ("產業代號", "产业代号", "產業代碼", "产业代码", "industry code", "sector code"))
    return {
        "symbol_field_available": symbol,
        "market_field_available": market,
        "sector_code_field_available": sector_code,
        "sector_name_field_available": sector_name,
    }


def publication_fields(fields: list[str]) -> list[str]:
    terms = ("日期", "年月", "date", "period", "year", "month", "effective", "available")
    return [field for field in fields if any(term in field.lower() for term in terms)]


def challenge_reason(status: int | None, body_text: str, location: str) -> str:
    if status in (401, 403, 429):
        return f"HTTP_{status}"
    lower = body_text.lower()
    for marker in CHALLENGE_MARKERS:
        if marker in lower:
            return f"ACCESS_CHALLENGE:{marker}"
    if location:
        host = (urlparse(location).hostname or "").lower()
        if host and host not in ALLOWLIST:
            return f"REDIRECT_NON_ALLOWLIST:{host}"
    return ""


def oas_identity(parsed: Any) -> str:
    if not isinstance(parsed, dict) or not isinstance(parsed.get("info"), dict):
        return "NOT_PROVEN"
    info = parsed["info"]
    description = str(info.get("description", ""))
    terms = re.findall(r"https?://[^)\s<]+", description)
    return json.dumps(
        {
            "title": info.get("title"),
            "version": info.get("version"),
            "terms_links_observed": terms,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def explicit_tpex_oas_link(body: bytes, base_url: str) -> str | None:
    text = body.decode("utf-8", errors="replace")
    links = re.findall(r"(?:href|src)=[\"']([^\"']+)[\"']", text, flags=re.I)
    candidates = set()
    for link in links:
        absolute = urljoin(base_url, unescape(link))
        parsed = urlparse(absolute)
        if parsed.hostname == "www.tpex.org.tw" and re.search(r"(?:swagger|openapi).*(?:\.json|/json)(?:$|\?)", parsed.path, re.I):
            candidates.add(absolute)
    return next(iter(candidates)) if len(candidates) == 1 else None


def oas_paths(parsed: Any) -> dict[str, Any]:
    if isinstance(parsed, dict) and isinstance(parsed.get("paths"), dict):
        return parsed["paths"]
    return {}


def select_oas_sector_endpoint(parsed: Any, server: str) -> str | None:
    ranked: list[tuple[int, int, str]] = []
    for path, operations in oas_paths(parsed).items():
        if not isinstance(operations, dict) or not isinstance(operations.get("get"), dict):
            continue
        operation = operations["get"]
        if operation.get("deprecated") is True or operation.get("security"):
            continue
        blob = json.dumps(operation, ensure_ascii=False).lower()
        has_symbol = any(term in blob for term in ("公司代號", "公司代码", "證券代號", "证券代号", "symbol", "stockno", "company code"))
        has_code = any(term in blob for term in ("產業代號", "产业代号", "產業代碼", "产业代码", "industry code", "sector code"))
        has_name = any(term in blob for term in ("產業別", "产业别", "產業名稱", "产业名称", "industry name", "sector name"))
        if not has_symbol or not (has_code or has_name):
            continue
        field_priority = 0 if has_code and has_name else (1 if has_name else 2)
        resource_blob = (path + " " + blob).lower()
        if any(term in resource_blob for term in ("company", "basic", "profile", "instrument", "公司基本", "證券基本")):
            resource_priority = 0
        elif any(term in resource_blob for term in ("disclosure", "營收", "营收", "opendata")):
            resource_priority = 1
        else:
            resource_priority = 2
        ranked.append((field_priority, resource_priority, path))
    if not ranked:
        return None
    return urljoin(server.rstrip("/") + "/", sorted(ranked)[0][2].lstrip("/"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw_excerpt").mkdir(exist_ok=True)
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    records: list[dict[str, Any]] = []
    actual_urls: set[str] = set()
    actual_count = 0
    stop_trigger = ""
    twse_oas: Any | None = None
    tpex_oas: Any | None = None
    tpex_oas_url: str | None = None

    plan: list[dict[str, Any]] = [
        {"order": 1, "provider": "TWSE", "url": "https://openapi.twse.com.tw/v1/swagger.json", "kind": "oas"},
        {"order": 2, "provider": "TWSE", "url": "https://openapi.twse.com.tw/v1/opendata/t187ap05_L", "kind": "dataset"},
        {"order": 3, "provider": "TWSE", "url": "https://twse-regulation.twse.com.tw/ENG/EN/law/DAT0201.aspx?FLCODE=FL007104", "kind": "regulation"},
        {"order": 4, "provider": "TPEx", "url": "https://www.tpex.org.tw/openapi/", "kind": "landing"},
        {"order": 5, "provider": "TPEx", "url": None, "kind": "oas_conditional"},
        {"order": 6, "provider": "TPEx", "url": "https://www.tpex.org.tw/openapi/v1/t187ap05_O", "kind": "dataset"},
        {"order": 7, "provider": "MOPS", "url": "https://mops.twse.com.tw/mops/web/t21sc03", "kind": "landing"},
        {"order": 8, "provider": "TWSE", "url": "https://openapi.twse.com.tw/robots.txt", "kind": "robots"},
        {"order": 9, "provider": "TPEx", "url": "https://www.tpex.org.tw/robots.txt", "kind": "robots"},
        {"order": 10, "provider": "MOPS", "url": "https://mops.twse.com.tw/robots.txt", "kind": "robots"},
        {"order": 11, "provider": "TWSE", "url": None, "kind": "oas_selected"},
        {"order": 12, "provider": "TPEx", "url": None, "kind": "oas_selected"},
    ]

    for item in plan:
        order = item["order"]
        if stop_trigger:
            records.append({"probe_id": f"ssap1-{order:02d}", "order": order, "provider": item["provider"], "request_method": "GET", "request_url": item["url"] or "CONDITIONAL", "execution_status": "SKIPPED_AFTER_STOP", "skip_reason": stop_trigger})
            continue
        if order == 5:
            item["url"] = tpex_oas_url
        elif order == 11:
            item["url"] = select_oas_sector_endpoint(twse_oas, "https://openapi.twse.com.tw")
        elif order == 12:
            item["url"] = select_oas_sector_endpoint(tpex_oas, "https://www.tpex.org.tw")
        url = item["url"]
        if not url:
            records.append({"probe_id": f"ssap1-{order:02d}", "order": order, "provider": item["provider"], "request_method": "GET", "request_url": "CONDITIONAL", "execution_status": "SKIPPED_CONDITION_NOT_MET", "skip_reason": "NO_EXPLICIT_OAS_LINK" if order == 5 else "NO_OAS_SECTOR_ENDPOINT_CANDIDATE"})
            continue
        if url in actual_urls:
            records.append({"probe_id": f"ssap1-{order:02d}", "order": order, "provider": item["provider"], "request_method": "GET", "request_url": url, "execution_status": "SKIPPED_DUPLICATE_EXACT_URL", "skip_reason": "EXISTING_RESPONSE_IS_SELECTED_ENDPOINT_EVIDENCE"})
            continue
        host = (urlparse(url).hostname or "").lower()
        if host not in ALLOWLIST or actual_count >= MAX_REQUESTS:
            raise RuntimeError(f"network contract violation: {url}")

        requested_at = utc_now()
        request = Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})
        status: int | None = None
        content_type = ""
        location = ""
        data = b""
        error = ""
        actual_urls.add(url)
        actual_count += 1
        try:
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                location = response.headers.get("Location", "")
                data = response.read()
        except HTTPError as exc:
            status = exc.code
            content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
            location = exc.headers.get("Location", "") if exc.headers else ""
            data = exc.read()
            error = f"HTTPError:{exc.code}"
        except (URLError, TimeoutError, ssl.SSLError) as exc:
            error = f"{type(exc).__name__}:{exc}"
        fetched_at = utc_now()
        fields, excerpt, parsed = sample_excerpt(data, content_type)
        flags = field_flags(fields)
        challenge = challenge_reason(status, excerpt, location)
        if challenge:
            excerpt = f"ACCESS_CONTROL_RESPONSE_NOT_RETAINED ({challenge})"
        record = {
            "probe_id": f"ssap1-{order:02d}",
            "order": order,
            "provider": item["provider"],
            "authority_host": host,
            "request_method": "GET",
            "request_url": url,
            "request_parameters": dict(sorted(__import__("urllib.parse").parse.parse_qsl(urlparse(url).query))),
            "requested_at": requested_at,
            "fetched_at": fetched_at,
            "http_status": status,
            "content_type": content_type,
            "redirect_location_or_empty": location,
            "response_bytes": len(data),
            "response_sha256": hashlib.sha256(data).hexdigest(),
            "field_names": fields,
            "sample_safe_excerpt": excerpt,
            **flags,
            "source_or_publication_date_fields": publication_fields(fields),
            "historical_archive_or_effective_date_declaration": "NOT_PROVEN",
            "oas_title_version_terms_link": oas_identity(parsed) if item["kind"] in ("oas", "oas_conditional") else "NOT_PROVEN",
            "access_observation": challenge or ("ACCESSIBLE_STANDARD_GET" if status == 200 else error or f"HTTP_{status}"),
            "license_cache_redistribution_observation": "LICENSE_UNRESOLVED",
            "robots_observation": excerpt if item["kind"] == "robots" else "NOT_PROBED_IN_THIS_REQUEST",
            "execution_status": "EXECUTED",
            "error": error,
        }
        records.append(record)
        excerpt_path = OUT / "raw_excerpt" / f"{record['probe_id']}.txt"
        excerpt_path.write_text(excerpt + "\n", encoding="utf-8")

        if order == 1:
            twse_oas = parsed
        elif order == 4:
            tpex_oas_url = explicit_tpex_oas_link(data, url)
        elif order == 5:
            tpex_oas = parsed
        if challenge:
            stop_trigger = f"{record['probe_id']}:{challenge}"

    executed = [record for record in records if record["execution_status"] == "EXECUTED"]
    field_rows = []
    for record in executed:
        field_rows.append({key: record.get(key) for key in (
            "probe_id", "provider", "request_url", "http_status", "symbol_field_available",
            "market_field_available", "sector_code_field_available", "sector_name_field_available",
            "source_or_publication_date_fields", "historical_archive_or_effective_date_declaration",
        )})
    with (OUT / "request_records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    with (OUT / "field_matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(field_rows[0]) if field_rows else ["probe_id"])
        writer.writeheader()
        writer.writerows(field_rows)

    twse_dataset = next((record for record in executed if record["probe_id"] == "ssap1-02"), {})
    tpex_dataset = next((record for record in executed if record["probe_id"] == "ssap1-06"), {})
    license_status = "LICENSE_UNRESOLVED"
    verdict = "STOP_SSAP1_OFFICIAL_DUAL_MARKET_SECTOR_SOURCE_NOT_READY"
    manifest = {
        "artifact_type": "ssap1_official_sector_probe_evidence",
        "created_at": utc_now(),
        "network_contract": {"method": "GET", "max_requests": MAX_REQUESTS, "actual_requests": actual_count, "concurrency": 1, "timeout_seconds": TIMEOUT_SECONDS, "retries": 0, "allow_redirects": False, "cookies": False, "auth": False, "proxy": False},
        "actual_request_count": actual_count,
        "stop_trigger": stop_trigger or None,
        "pit_classification": "current_snapshot_forward_only",
        "license_status": license_status,
        "twse_dataset_gate": {key: twse_dataset.get(key) for key in ("http_status", "symbol_field_available", "sector_code_field_available", "sector_name_field_available")},
        "tpex_dataset_gate": {key: tpex_dataset.get(key) for key in ("http_status", "symbol_field_available", "sector_code_field_available", "sector_name_field_available")},
        "verdict": verdict,
        "no_provider_publish": True,
        "no_latest_switch": True,
        "no_ssap2_execution": True,
    }
    audit = {
        "license_cache_redistribution_status": license_status,
        "historical_effective_dating_status": "NOT_PROVEN",
        "pit_classification": "current_snapshot_forward_only",
        "monthly_revenue_publication_date_is_sector_effective_date": False,
        "access_control_stop_trigger": stop_trigger or None,
        "forbidden_actions_performed": [],
    }
    (OUT / "probe_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "access_license_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def normalize_existing_evidence() -> int:
    """Sanitize the already-captured evidence without issuing any request."""
    records_path = OUT / "request_records.jsonl"
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    for record in records:
        if record.get("execution_status") != "EXECUTED":
            continue
        flags = field_flags(record.get("field_names", []))
        record.update(flags)
        if record.get("probe_id") == "ssap1-01":
            record["oas_title_version_terms_link"] = json.dumps(
                {
                    "terms_links_observed": ["https://www.twse.com.tw/zh/page/terms/use.html"],
                    "title": "臺灣證券交易所 OpenAPI",
                    "version": "1.0",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        if record.get("http_status") in (401, 403, 429) or "cloudflare" in str(record.get("sample_safe_excerpt", "")).lower():
            reason = f"HTTP_{record.get('http_status')}"
            if "cloudflare" in str(record.get("sample_safe_excerpt", "")).lower():
                reason += "_CLOUDFLARE_ACCESS_CHALLENGE"
            record["sample_safe_excerpt"] = f"ACCESS_CONTROL_RESPONSE_NOT_RETAINED ({reason})"
            record["access_observation"] = reason
        (OUT / "raw_excerpt" / f"{record['probe_id']}.txt").write_text(
            record["sample_safe_excerpt"] + "\n", encoding="utf-8"
        )

    with records_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    executed = [record for record in records if record.get("execution_status") == "EXECUTED"]
    columns = (
        "probe_id", "provider", "request_url", "http_status", "symbol_field_available",
        "market_field_available", "sector_code_field_available", "sector_name_field_available",
        "source_or_publication_date_fields", "historical_archive_or_effective_date_declaration",
    )
    with (OUT / "field_matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows([{key: record.get(key) for key in columns} for record in executed])
    manifest_path = OUT / "probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    twse = next(record for record in executed if record["probe_id"] == "ssap1-02")
    manifest["twse_dataset_gate"] = {key: twse.get(key) for key in (
        "http_status", "symbol_field_available", "sector_code_field_available", "sector_name_field_available"
    )}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("normalized existing SSAP1 evidence; network_requests=0")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--normalize-existing-evidence"]:
        raise SystemExit(normalize_existing_evidence())
    raise SystemExit(main())
