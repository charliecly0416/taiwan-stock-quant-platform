#!/usr/bin/env python3
"""Isolated synthetic-only NMRPA2 contract implementation.

This module is intentionally disconnected from daily-auto and product artifacts.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_IDS = {
    "feature": "nmrpa_feature_contract_v2",
    "target": "nmrpa_target_contract_v1",
    "split": "nmrpa_split_contract_v1",
    "decision_time": "nmrpa_decision_time_policy_v1",
}
SCHEMA_VERSION = "nmrpa2.synthetic.v1"
SYNTHETIC_RE = re.compile(r"^SYNTHETIC_[A-Z0-9_]+$")
REAL_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
TOL_ABS = 1e-12
TOL_REL = 1e-10
SYNTHETIC_TIME_ORDER = {
    "SYNTHETIC_TIME_BEFORE_CUTOFF": 0,
    "SYNTHETIC_TIME_DECISION_CUTOFF": 1,
    "SYNTHETIC_TIME_AFTER_CUTOFF": 2,
}

PROTECTED_PATHS = (
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "data_tw/artifacts/agent_daily_prompt/latest.json",
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
    "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
    "data_tw/ops/daily_auto_update",
)
ACTUAL_CRONTAB_KEY = "__actual_crontab__"
FORBIDDEN_ROOT_PARTS = {
    "latest", "provider", "accepted", "daily_auto_update", "artifacts",
    "option_c_daily_signal", "backend", "frontend", "agent_daily_prompt",
}
FORBIDDEN_TEXT_TOKENS = {
    "label", "outcome", "future_return", "forward_return", "realized_pnl",
    "realized_return", "metric", "rank_ic", "hit_rate", "sharpe",
    "target_position", "target_weight", "order_qty", "broker_order_id",
}

FEATURE_NAMES = (
    "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date",
    "qlib_score_zscore_by_date", "rank_change_1d", "rank_change_3d",
    "rank_change_5d", "top10_flag", "top30_flag", "top50_flag",
    "top30_streak", "top50_streak", "MA5", "MA10", "MA20", "MA60",
    "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20",
    "volume_ratio20", "avg_trading_value_20d", "volume_stability20",
    "missing_rate20", "suspension_proxy", "slippage_proxy", "TWII_ret20",
    "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120",
    "market_volatility20", "market_drawdown60", "market_breadth20",
    "foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy",
    "institutional_total_net_buy",
    *tuple(f"foreign_net_buy_roll{w}" for w in (1, 3, 5, 10)),
    *tuple(f"investment_trust_net_buy_roll{w}" for w in (1, 3, 5, 10)),
    *tuple(f"dealer_net_buy_roll{w}" for w in (1, 3, 5, 10)),
    *tuple(f"institutional_total_net_buy_roll{w}" for w in (1, 3, 5, 10)),
    "institutional_total_net_buy_streak", "institutional_missing_flag",
    "institutional_delay_flag", "institutional_flow_delay_days",
    "institutional_flow_asof_missing_flag", "margin_balance",
    "margin_balance_change", "short_balance", "short_balance_change",
    *tuple(f"margin_balance_change_roll{w}" for w in (1, 3, 5, 10)),
    *tuple(f"short_balance_change_roll{w}" for w in (1, 3, 5, 10)),
    "margin_direction_proxy", "short_direction_proxy",
    "margin_short_divergence_proxy", "margin_short_missing_flag",
    "margin_short_delay_flag", "margin_short_delay_days",
    "margin_short_asof_missing_flag",
)
assert len(FEATURE_NAMES) == 78


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_json(value: Any) -> bytes:
    def check(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ContractError("NMRPA_E_NONFINITE", "canonical JSON contains non-finite number")
        if isinstance(v, dict):
            for key, child in v.items():
                if unicodedata.normalize("NFC", key) != key:
                    raise ContractError("NMRPA_E_UNICODE", "object key is not NFC")
                check(child)
        elif isinstance(v, list):
            for child in v:
                check(child)
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def checksum_without(obj: dict[str, Any], *excluded: str) -> str:
    return digest({k: v for k, v in obj.items() if k not in excluded})


def require_synthetic(value: str, field: str) -> None:
    if not isinstance(value, str) or not SYNTHETIC_RE.fullmatch(value):
        raise ContractError("NMRPA_E_REAL_INPUT", f"{field} must be SYNTHETIC_* sentinel")


def reject_real_dates(value: Any) -> None:
    if REAL_DATE_RE.search(json.dumps(value, ensure_ascii=False)):
        raise ContractError("NMRPA_E_REAL_INPUT", "real date-shaped value is forbidden")


def require_available_by(value: Any, cutoff: str, field: str) -> None:
    if value not in SYNTHETIC_TIME_ORDER or cutoff not in SYNTHETIC_TIME_ORDER:
        raise ContractError("NMRPA_E_PIT", f"{field} uses unknown synthetic time")
    if SYNTHETIC_TIME_ORDER[value] > SYNTHETIC_TIME_ORDER[cutoff]:
        raise ContractError("NMRPA_E_PIT", f"{field} is later than decision cutoff")


def normalized_token_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s\-./\\:]+", "_", normalized)


def validate_untrusted_text(value: str) -> None:
    normalized = normalized_token_text(value)
    if any(token in normalized for token in FORBIDDEN_TEXT_TOKENS):
        raise ContractError("NMRPA_E_FORBIDDEN_CONTENT", "untrusted text contains forbidden token")


def validate_metadata(metadata: dict[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                validate_untrusted_text(str(key)); walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
        elif isinstance(value, str):
            validate_untrusted_text(value)
    walk(metadata)


def validate_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 32:
            raise ContractError("NMRPA_E_ARCHIVE", "too many ZIP members")
        total = 0; normalized_names: set[str] = set()
        for info in infos:
            name = info.filename
            normalized = normalized_token_text(name)
            if name.startswith(("/", "\\")) or ".." in Path(name).parts or normalized in normalized_names:
                raise ContractError("NMRPA_E_ARCHIVE", "unsafe or duplicate ZIP member")
            normalized_names.add(normalized); validate_untrusted_text(name)
            if name.lower().endswith((".zip", ".tar", ".gz", ".bz2", ".xz")):
                raise ContractError("NMRPA_E_ARCHIVE", "nested archive forbidden")
            total += info.file_size
            ratio = info.file_size / max(1, info.compress_size)
            if info.file_size > 8 * 1024 * 1024 or total > 64 * 1024 * 1024 or ratio > 20:
                raise ContractError("NMRPA_E_ARCHIVE", "ZIP size or ratio limit")


def validate_output_root(path: Path) -> Path:
    raw = str(path)
    if ".." in path.parts or path.is_symlink() or any(p.lower() in FORBIDDEN_ROOT_PARTS for p in path.parts):
        raise ContractError("NMRPA_E_OUTPUT_BOUNDARY", f"unsafe isolated root: {raw}")
    resolved = path.resolve(strict=False)
    tmp_root = Path("/tmp").resolve()
    if tmp_root not in resolved.parents or not SYNTHETIC_RE.fullmatch(resolved.name):
        raise ContractError(
            "NMRPA_E_OUTPUT_BOUNDARY",
            "isolated output must be a new SYNTHETIC_* directory below /tmp",
        )
    for protected in PROTECTED_PATHS:
        p = (ROOT / protected).resolve(strict=False)
        if resolved == p or p in resolved.parents or resolved in p.parents:
            raise ContractError("NMRPA_E_OUTPUT_BOUNDARY", "output overlaps protected path")
    return resolved


def fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None}
    if path.is_file():
        return {"exists": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    entries = []
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        entries.append([child.relative_to(path).as_posix(), hashlib.sha256(child.read_bytes()).hexdigest()])
    return {"exists": True, "sha256": digest(entries)}


def protected_fingerprints() -> dict[str, dict[str, Any]]:
    result = {name: fingerprint(ROOT / name) for name in PROTECTED_PATHS}
    cron = subprocess.run(["crontab", "-l"], text=False, capture_output=True, check=False)
    if cron.returncode not in (0, 1):
        raise ContractError("NMRPA_E_PROTECTED_FINGERPRINT", "cannot read actual crontab")
    result[ACTUAL_CRONTAB_KEY] = {
        "exists": cron.returncode == 0,
        "sha256": hashlib.sha256(cron.stdout).hexdigest() if cron.returncode == 0 else None,
    }
    return result


def contract_objects() -> dict[str, dict[str, Any]]:
    common = {"numeric": "ieee754_binary64", "abs_tolerance": TOL_ABS, "rel_tolerance": TOL_REL}
    feature = {
        "contract_id": CONTRACT_IDS["feature"], "implementation_version": "nmrpa.feature.v2",
        "global_numeric_policy": common, "source_ids": ["SYNTHETIC_MODEL_A", "SYNTHETIC_PRICE", "SYNTHETIC_TWII", "SYNTHETIC_INSTITUTIONAL", "SYNTHETIC_MARGIN", "SYNTHETIC_CALENDAR"],
        "ordered_78_formula_records": feature_formula_records(), "eligibility_contract_id": "SYNTHETIC_ELIGIBILITY_V2",
    }
    target = {
        "contract_id": CONTRACT_IDS["target"], "target_name": "residual_downside_risk_10td",
        "formula": "max(0,-(log(C_i_h/C_i_t)-log(TWII_h/TWII_t)))", "direction": "lower_is_better",
        "unit": "log_return", "horizon": 10, "calendar_contract_id": "SYNTHETIC_CALENDAR_V1",
        "price_adjustment": "validated_adjusted_close", "benchmark": "TWII",
        "suspension": "official_carry_forward_only", "delisting": "official_settlement_or_invalid", "missing_policy": "invalid",
    }
    split = {
        "contract_id": CONTRACT_IDS["split"], "role": "prospective_strict_holdout",
        "start_authorization_id": "SYNTHETIC_NOT_AUTHORIZED", "min_valid_dates": 126,
        "purge_td": 10, "embargo_td": 10, "maturity_td": 10,
        "invalid_date_policy": "retain_not_counted", "no_restart_policy": True,
    }
    time = {
        "contract_id": CONTRACT_IDS["decision_time"], "timezone": "Asia/Taipei",
        "local_cutoff": "23:59:59", "utc_serialization": "RFC3339",
        "available_at_fallback": "first_successful_capture", "same_day_policy": "available_at_lte_cutoff",
        "late_source_policy": "fail_closed",
    }
    return {"feature": feature, "target": target, "split": split, "decision_time": time}


def feature_formula_records() -> list[dict[str, Any]]:
    formulas = {
        "qlib_score_raw": "S(i,t)", "qlib_rank": "ordinal(S desc,instrument asc)",
        "qlib_score_percentile_by_date": "N=1?0:(N-rank)/(N-1)",
        "qlib_score_zscore_by_date": "std0(S)=0?0:(S-mean(S))/std0(S)",
        "rank_change_1d": "rank(t-1)-rank(t);missing_lag=0", "rank_change_3d": "rank(t-3)-rank(t);missing_lag=0",
        "rank_change_5d": "rank(t-5)-rank(t);missing_lag=0", "top10_flag": "1[rank<=min(10,N)]",
        "top30_flag": "1[rank<=min(30,N)]", "top50_flag": "1[rank<=min(50,N)]",
        "top30_streak": "consecutive_valid_dates(top30_flag=1)", "top50_streak": "consecutive_valid_dates(top50_flag=1)",
        "MA5": "mean_5(C)", "MA10": "mean_10(C)", "MA20": "mean_20(C)", "MA60": "mean_60(C)",
        "RSI14": "100-100/(1+mean14(max(deltaC,0))/mean14(max(-deltaC,0)));flat=50;loss0=100",
        "MACD": "EMA12(C)-EMA26(C);seed=span_mean;alpha=2/(span+1)",
        "Bollinger_position": "clip((C-mean20(C))/(2*std0_20(C)),-5,5);std0=0=>0",
        "ret20": "C(t)/C(t-20)-1", "volatility20": "std0_20(C(t)/C(t-1)-1)",
        "volume_ratio20": "V(t)/mean20(V);denominator0=0", "avg_trading_value_20d": "mean20(V*W)",
        "volume_stability20": "1/(1+std0_20(V(t)/V(t-1)-1))", "missing_rate20": "missing_adjusted_close_count(expected_grid20)/20",
        "suspension_proxy": "1[V(t)<=0]", "slippage_proxy": "V*W<=0?0:1/sqrt(V*W)",
        "TWII_ret20": "I(t)/I(t-20)-1", "TWII_ret60": "I(t)/I(t-60)-1",
        "TWII_close_vs_MA60": "I(t)/mean60(I)-1", "TWII_close_vs_MA120": "I(t)/mean120(I)-1",
        "market_volatility20": "std0_20(I(t)/I(t-1)-1)", "market_drawdown60": "I(t)/max60(I)-1",
        "market_breadth20": "sum_i(1[C(i,t)>MA20(i,t)])/expected_breadth_set_count",
        "foreign_net_buy": "A_foreign(i,t);confirmed_absent=0", "investment_trust_net_buy": "A_trust(i,t);confirmed_absent=0",
        "dealer_net_buy": "A_dealer(i,t);confirmed_absent=0", "institutional_total_net_buy": "foreign+trust+dealer",
        "institutional_total_net_buy_streak": "signed_consecutive_nonzero(institutional_total_net_buy)",
        "institutional_missing_flag": "1[source_state=confirmed_absent]", "institutional_delay_flag": "1[delay_days>0 OR confirmed_absent]",
        "institutional_flow_delay_days": "present?TD(source_asof,t):0", "institutional_flow_asof_missing_flag": "1[confirmed_absent]",
        "margin_balance": "A_margin_balance(i,t);confirmed_absent=0", "margin_balance_change": "official_change_or_adjacent_balance_difference;confirmed_absent=0",
        "short_balance": "A_short_balance(i,t);confirmed_absent=0", "short_balance_change": "official_change_or_adjacent_balance_difference;confirmed_absent=0",
        "margin_direction_proxy": "sign(margin_balance_change)", "short_direction_proxy": "sign(short_balance_change)",
        "margin_short_divergence_proxy": "margin_direction_proxy-short_direction_proxy",
        "margin_short_missing_flag": "1[source_state=confirmed_absent]", "margin_short_delay_flag": "1[delay_days>0 OR confirmed_absent]",
        "margin_short_delay_days": "present?TD(source_asof,t):0", "margin_short_asof_missing_flag": "1[confirmed_absent]",
    }
    for base in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy", "margin_balance_change", "short_balance_change"):
        for window in (1, 3, 5, 10):
            formulas[f"{base}_roll{window}"] = f"sum_{window}({base});exact_trading_rows"
    if set(formulas) != set(FEATURE_NAMES):
        raise ContractError("NMRPA_E_FEATURE_ALLOWLIST", "formula records do not cover exact 78")
    int8_names = {
        "top10_flag", "top30_flag", "top50_flag", "suspension_proxy",
        "institutional_missing_flag", "institutional_delay_flag",
        "institutional_flow_asof_missing_flag", "margin_direction_proxy",
        "short_direction_proxy", "margin_short_divergence_proxy",
        "margin_short_missing_flag", "margin_short_delay_flag",
        "margin_short_asof_missing_flag",
    }
    integer_names = int8_names | {
        "qlib_rank", "rank_change_1d", "rank_change_3d", "rank_change_5d",
        "top30_streak", "top50_streak", "institutional_total_net_buy_streak",
        "institutional_flow_delay_days", "margin_short_delay_days",
    }
    source_for = {}
    for name in FEATURE_NAMES:
        if name.startswith("TWII_") or name.startswith("market_"):
            source_for[name] = "SYNTHETIC_TWII"
        elif name.startswith(("foreign_", "investment_", "dealer_", "institutional_")):
            source_for[name] = "SYNTHETIC_INSTITUTIONAL"
        elif name.startswith(("margin_", "short_")):
            source_for[name] = "SYNTHETIC_MARGIN"
        elif name.startswith(("qlib_", "rank_", "top")):
            source_for[name] = "SYNTHETIC_MODEL_A"
        else:
            source_for[name] = "SYNTHETIC_PRICE"
    records = []
    for name in FEATURE_NAMES:
        lookback = 1
        matches = [int(x) for x in re.findall(r"(?:MA|ret|roll|volatility|stability|rate|drawdown)(\d+)", name)]
        if matches:
            lookback = max(matches)
        elif name in {"RSI14"}:
            lookback = 15
        elif name in {"MACD"}:
            lookback = 26
        elif name.startswith("TWII_close_vs_MA120"):
            lookback = 120
        records.append({
            "feature_name": name,
            "formula": formulas[name],
            "dtype": "int8" if name in int8_names else "int64" if name in integer_names else "float64",
            "source_contract_id": source_for[name],
            "lookback_trading_rows": lookback,
            "adjustment_policy": "validated_adjusted_close_unadjusted_volume",
            "missing_policy": "fail_closed_except_checksum_proven_neutral",
            "tolerance_abs": 0.0 if name in integer_names else TOL_ABS,
            "tolerance_rel": 0.0 if name in integer_names else TOL_REL,
            "implementation_version": "nmrpa.feature.v2",
        })
    return records


def contract_refs() -> dict[str, str]:
    objects = contract_objects()
    return {
        "feature_contract_sha256": digest(objects["feature"]),
        "target_contract_sha256": digest(objects["target"]),
        "split_contract_sha256": digest(objects["split"]),
        "decision_time_policy_sha256": digest(objects["decision_time"]),
    }


def mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def std0(values: list[float]) -> float:
    m = mean(values)
    return math.sqrt(math.fsum((x - m) ** 2 for x in values) / len(values))


def ema(values: list[float], span: int) -> float:
    current = mean(values[:span])
    alpha = 2.0 / (span + 1.0)
    for value in values[span:]:
        current = alpha * value + (1.0 - alpha) * current
    return current


def signed_streak(values: list[float]) -> int:
    if not values or values[-1] == 0:
        return 0
    sign = 1 if values[-1] > 0 else -1
    count = 0
    for value in reversed(values):
        if (1 if value > 0 else -1 if value < 0 else 0) != sign:
            break
        count += 1
    return sign * count


def _source_rows(
    source: dict[str, Any],
    kind: str,
    minimum: int,
    expected_symbols: list[str],
    decision_date: str,
    instrument: str,
) -> tuple[list[dict[str, Any]], bool]:
    state = source.get("source_state")
    if state == "confirmed_absent":
        if set(source) != {"source_state", "absence_evidence"}:
            raise ContractError("NMRPA_E_SOURCE_SCHEMA", f"{kind} absent source fields must be exact")
        evidence = source.get("absence_evidence")
        required = {
            "evidence_version", "source_kind", "decision_date", "checked_at",
            "authoritative_scope_id", "expected_symbol_set_sha256", "expected_date",
            "request_or_batch_manifest_path", "request_or_batch_manifest_sha256",
            "immutable_response_or_audit_path", "immutable_response_or_audit_sha256",
            "response_scope_start", "response_scope_end", "queried_symbol_count",
            "returned_symbol_count", "returned_rows", "returned_symbol_set_sha256",
            "absent_symbol_set_sha256", "request_manifest_payload",
            "immutable_response_or_audit_payload", "result_class",
        }
        if not isinstance(evidence, dict) or set(evidence) != required or evidence.get("result_class") not in {
            "authoritative_complete_zero_rows", "authoritative_complete_partial_rows"
        } or not all(SHA_RE.fullmatch(str(evidence.get(k, ""))) for k in (
            "expected_symbol_set_sha256", "request_or_batch_manifest_sha256",
            "immutable_response_or_audit_sha256", "returned_symbol_set_sha256",
            "absent_symbol_set_sha256",
        )):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} neutral fill is not checksum-backed")
        expected_hash = digest(expected_symbols)
        if (
            evidence["source_kind"] != kind
            or evidence["decision_date"] != decision_date
            or evidence["expected_date"] != decision_date
            or evidence["response_scope_start"] != decision_date
            or evidence["response_scope_end"] != decision_date
            or evidence["expected_symbol_set_sha256"] != expected_hash
            or evidence["queried_symbol_count"] != len(expected_symbols)
        ):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} evidence scope/time mismatch")
        require_available_by(evidence["checked_at"], "SYNTHETIC_TIME_DECISION_CUTOFF", f"{kind} checked_at")
        returned_rows = evidence["returned_rows"]
        if not isinstance(returned_rows, list) or any(
            not isinstance(item, dict) or set(item) != {"instrument", "source_kind", "decision_date"}
            for item in returned_rows
        ):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} returned rows invalid")
        returned_symbols = [item["instrument"] for item in returned_rows]
        if returned_symbols != sorted(set(returned_symbols)) or any(
            item["source_kind"] != kind or item["decision_date"] != decision_date
            for item in returned_rows
        ) or not set(returned_symbols).issubset(expected_symbols):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} returned set invalid")
        returned = evidence["returned_symbol_count"]
        if not isinstance(returned, int) or not 0 <= returned <= len(expected_symbols):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} returned count invalid")
        absent_symbols = sorted(set(expected_symbols) - set(returned_symbols))
        request_payload = evidence["request_manifest_payload"]
        response_payload = evidence["immutable_response_or_audit_payload"]
        expected_request = {
            "source_kind": kind,
            "decision_date": decision_date,
            "expected_symbols": expected_symbols,
        }
        expected_response = {
            "source_kind": kind,
            "decision_date": decision_date,
            "returned_rows": returned_rows,
        }
        if (
            returned != len(returned_rows)
            or evidence["returned_symbol_set_sha256"] != digest(returned_symbols)
            or evidence["absent_symbol_set_sha256"] != digest(absent_symbols)
            or evidence["request_or_batch_manifest_sha256"] != digest(evidence["request_manifest_payload"])
            or evidence["immutable_response_or_audit_sha256"]
            != digest(response_payload)
            or request_payload != expected_request
            or response_payload != expected_response
        ):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} evidence payload binding mismatch")
        if instrument not in absent_symbols:
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} current instrument is returned, not absent")
        if evidence["result_class"] == "authoritative_complete_zero_rows":
            if returned != 0 or returned_rows or evidence["absent_symbol_set_sha256"] != expected_hash:
                raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} zero-row proof mismatch")
        elif returned in (0, len(expected_symbols)):
            raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} partial proof count invalid")
        for key in ("authoritative_scope_id", "request_or_batch_manifest_path", "immutable_response_or_audit_path"):
            require_synthetic(evidence[key], key)
        return [{} for _ in range(minimum)], True
    if state != "present":
        raise ContractError("NMRPA_E_ABSENCE_EVIDENCE", f"{kind} state {state!r} cannot neutral fill")
    if set(source) != {"source_state", "rows", "delay_days"}:
        raise ContractError("NMRPA_E_SOURCE_SCHEMA", f"{kind} present source fields must be exact")
    if source["delay_days"] != 0:
        raise ContractError("NMRPA_E_SOURCE_CONFLICT", f"{kind} same-day source delay must be zero")
    rows = source.get("rows")
    expected_fields = {
        "institutional": {"date", "available_at", "source_asof", "foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"},
        "margin": {"date", "available_at", "source_asof", "margin_balance", "margin_balance_change", "short_balance", "short_balance_change"},
    }[kind]
    if not isinstance(rows, list) or len(rows) != minimum:
        raise ContractError("NMRPA_E_SOURCE_COVERAGE", f"{kind} needs {minimum} rows")
    dates = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise ContractError("NMRPA_E_SOURCE_SCHEMA", f"{kind} row fields must be exact")
        require_synthetic(row["date"], "source row date")
        require_synthetic(row["available_at"], "source available_at")
        require_synthetic(row["source_asof"], "source_asof")
        require_available_by(row["available_at"], "SYNTHETIC_TIME_DECISION_CUTOFF", f"{kind} available_at")
        if row["source_asof"] != row["date"]:
            raise ContractError("NMRPA_E_SOURCE_CONFLICT", f"{kind} source_asof/date mismatch")
        dates.append(row["date"])
    if dates != sorted(set(dates)):
        raise ContractError("NMRPA_E_SOURCE_SCHEMA", f"{kind} rows duplicate or out of order")
    if kind == "margin":
        for previous, current in zip(rows, rows[1:]):
            if not math.isclose(float(current["margin_balance_change"]), float(current["margin_balance"]) - float(previous["margin_balance"]), abs_tol=TOL_ABS, rel_tol=TOL_REL):
                raise ContractError("NMRPA_E_SOURCE_CONFLICT", "official margin change conflicts with balances")
            if not math.isclose(float(current["short_balance_change"]), float(current["short_balance"]) - float(previous["short_balance"]), abs_tol=TOL_ABS, rel_tol=TOL_REL):
                raise ContractError("NMRPA_E_SOURCE_CONFLICT", "official short change conflicts with balances")
    return rows, False


def compute_features(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    fixture = expand_fixture(fixture)
    reject_real_dates(fixture)
    for key in ("contract_id", "decision_date"):
        require_synthetic(fixture[key], key)
    if fixture.get("decision_time") != "SYNTHETIC_TIME_DECISION_CUTOFF":
        raise ContractError("NMRPA_E_DECISION_TIME", "decision cutoff sentinel mismatch")
    calendar = fixture.get("calendar", {})
    if set(calendar) != {"available_at", "trading_dates"}:
        raise ContractError("NMRPA_E_CALENDAR", "calendar fields must be exact")
    require_available_by(calendar.get("available_at"), fixture["decision_time"], "calendar available_at")
    validate_calendar_artifact(build_calendar_binding(fixture))
    active = sorted(fixture["formal_active_symbols"])
    for symbol in active:
        require_synthetic(symbol, "instrument")
    if len(active) != len(set(active)):
        raise ContractError("NMRPA_E_ELIGIBILITY", "formal active duplicate")
    symbols = fixture.get("symbols", {})
    if set(symbols) != set(active):
        raise ContractError("NMRPA_E_UPSTREAM_OMISSION", "active symbol cannot be omitted or hidden by exclusion")
    for symbol, row in symbols.items():
        if "score" not in row or "price" not in row:
            raise ContractError("NMRPA_E_UPSTREAM_OMISSION", f"{symbol} missing Model A or price")
        require_available_by(row.get("available_at"), fixture["decision_time"], f"{symbol} model available_at")
        if len(row["price"]["close"]) < 121 or len(row["price"]["volume"]) < 60 or len(row["price"]["vwap"]) < 60:
            raise ContractError("NMRPA_E_ELIGIBILITY", f"{symbol} insufficient history")
        p = row["price"]
        if set(p) != {"close", "volume", "vwap", "expected_date_grid_last20", "observed_close_date_grid_last20"}:
            raise ContractError("NMRPA_E_SOURCE_SCHEMA", f"{symbol} price fields must be exact")
        expected_grid = p["expected_date_grid_last20"]
        observed_grid = p["observed_close_date_grid_last20"]
        decision_position = calendar["trading_dates"].index(fixture["decision_date"])
        exact_grid = calendar["trading_dates"][decision_position - 19:decision_position + 1]
        if (
            len(exact_grid) != 20 or expected_grid != exact_grid
            or observed_grid != sorted(set(observed_grid))
            or not set(observed_grid).issubset(expected_grid)
        ):
            raise ContractError("NMRPA_E_SOURCE_SCHEMA", f"{symbol} missing grid invalid")
    twii = [float(x) for x in fixture["twii_close"]]
    if len(twii) < 121:
        raise ContractError("NMRPA_E_SOURCE_COVERAGE", "TWII needs 121 rows")
    scores = {s: float(symbols[s]["score"]) for s in active}
    ranked = sorted(active, key=lambda s: (-scores[s], s))
    rank = {s: i + 1 for i, s in enumerate(ranked)}
    n = len(active)
    score_mean, score_std = mean(list(scores.values())), std0(list(scores.values()))
    breadth = sum(float(symbols[s]["price"]["close"][-1]) > mean([float(x) for x in symbols[s]["price"]["close"][-20:]]) for s in active) / n
    out: list[dict[str, Any]] = []
    refs = contract_refs()
    for symbol in active:
        row = symbols[symbol]
        p = row["price"]
        close = [float(x) for x in p["close"]]
        volume = [float(x) for x in p["volume"]]
        vwap = [float(x) for x in p["vwap"]]
        if any(not math.isfinite(x) for x in close + volume + vwap + twii) or any(x <= 0 for x in close + vwap + twii):
            raise ContractError("NMRPA_E_NONFINITE", symbol)
        if any(x <= 0 for x in volume[-21:-1]):
            raise ContractError("NMRPA_E_SOURCE_CONFLICT", "previous volume must be positive")
        returns = [close[i] / close[i - 1] - 1 for i in range(1, len(close))]
        market_returns = [twii[i] / twii[i - 1] - 1 for i in range(1, len(twii))]
        deltas = [close[i] - close[i - 1] for i in range(len(close) - 14, len(close))]
        gains, losses = mean([max(x, 0) for x in deltas]), mean([max(-x, 0) for x in deltas])
        rsi = 50.0 if gains == losses == 0 else 100.0 if losses == 0 else 100 - 100 / (1 + gains / losses)
        expected_source_dates = calendar["trading_dates"][decision_position - 9:decision_position + 1]
        inst, inst_missing = _source_rows(row["institutional"], "institutional", 10, active, fixture["decision_date"], symbol)
        margin, margin_missing = _source_rows(row["margin"], "margin", 10, active, fixture["decision_date"], symbol)
        for kind, source_rows, missing in (("institutional", inst, inst_missing), ("margin", margin, margin_missing)):
            if not missing and [item["date"] for item in source_rows] != expected_source_dates:
                raise ContractError("NMRPA_E_SOURCE_COVERAGE", f"{kind} rows are not exact trailing ten trading dates")
        def vals(rows: list[dict[str, Any]], field: str) -> list[float]:
            return [float(r.get(field, 0.0)) for r in rows]
        f, it, d = (vals(inst, x) for x in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"))
        total = [a + b + c for a, b, c in zip(f, it, d)]
        mb, sb = vals(margin, "margin_balance"), vals(margin, "short_balance")
        mbc, sbc = vals(margin, "margin_balance_change"), vals(margin, "short_balance_change")
        rr = rank[symbol]
        history = row.get("rank_history", [])
        def lag(k: int) -> int:
            return int(history[-k]) - rr if len(history) >= k else 0
        top30_hist = row.get("top30_history", []) + [rr <= min(30, n)]
        top50_hist = row.get("top50_history", []) + [rr <= min(50, n)]
        def bool_streak(seq: list[bool]) -> int:
            count = 0
            for value in reversed(seq):
                if not value: break
                count += 1
            return count
        c20, v20, w20 = close[-20:], volume[-20:], vwap[-20:]
        price_std = std0(c20)
        current_value = volume[-1] * vwap[-1]
        values: dict[str, float | int] = {
            "qlib_score_raw": scores[symbol], "qlib_rank": rr,
            "qlib_score_percentile_by_date": 0.0 if n == 1 else (n - rr) / (n - 1),
            "qlib_score_zscore_by_date": 0.0 if score_std == 0 else (scores[symbol] - score_mean) / score_std,
            "rank_change_1d": lag(1), "rank_change_3d": lag(3), "rank_change_5d": lag(5),
            "top10_flag": int(rr <= min(10, n)), "top30_flag": int(rr <= min(30, n)), "top50_flag": int(rr <= min(50, n)),
            "top30_streak": bool_streak(top30_hist), "top50_streak": bool_streak(top50_hist),
            "MA5": mean(close[-5:]), "MA10": mean(close[-10:]), "MA20": mean(c20), "MA60": mean(close[-60:]),
            "RSI14": rsi, "MACD": ema(close[-26:], 12) - ema(close[-26:], 26),
            "Bollinger_position": 0.0 if price_std == 0 else max(-5.0, min(5.0, (close[-1] - mean(c20)) / (2 * price_std))),
            "ret20": close[-1] / close[-21] - 1, "volatility20": std0(returns[-20:]),
            "volume_ratio20": 0.0 if mean(v20) == 0 else volume[-1] / mean(v20),
            "avg_trading_value_20d": mean([a * b for a, b in zip(v20, w20)]),
            "volume_stability20": 1 / (1 + std0([volume[i] / volume[i - 1] - 1 for i in range(len(volume) - 20, len(volume))])),
            "missing_rate20": (len(p["expected_date_grid_last20"]) - len(p["observed_close_date_grid_last20"])) / 20,
            "suspension_proxy": int(volume[-1] <= 0),
            "slippage_proxy": 0.0 if current_value <= 0 else 1 / math.sqrt(current_value),
            "TWII_ret20": twii[-1] / twii[-21] - 1, "TWII_ret60": twii[-1] / twii[-61] - 1,
            "TWII_close_vs_MA60": twii[-1] / mean(twii[-60:]) - 1,
            "TWII_close_vs_MA120": twii[-1] / mean(twii[-120:]) - 1,
            "market_volatility20": std0(market_returns[-20:]), "market_drawdown60": twii[-1] / max(twii[-60:]) - 1,
            "market_breadth20": breadth,
            "foreign_net_buy": f[-1], "investment_trust_net_buy": it[-1], "dealer_net_buy": d[-1],
            "institutional_total_net_buy": total[-1],
            "institutional_total_net_buy_streak": signed_streak(total),
            "institutional_missing_flag": int(inst_missing), "institutional_delay_flag": int(inst_missing or row["institutional"].get("delay_days", 0) > 0),
            "institutional_flow_delay_days": int(row["institutional"].get("delay_days", 0)) if not inst_missing else 0,
            "institutional_flow_asof_missing_flag": int(inst_missing),
            "margin_balance": mb[-1], "margin_balance_change": mbc[-1], "short_balance": sb[-1], "short_balance_change": sbc[-1],
            "margin_direction_proxy": (mbc[-1] > 0) - (mbc[-1] < 0), "short_direction_proxy": (sbc[-1] > 0) - (sbc[-1] < 0),
            "margin_short_missing_flag": int(margin_missing), "margin_short_delay_flag": int(margin_missing or row["margin"].get("delay_days", 0) > 0),
            "margin_short_delay_days": int(row["margin"].get("delay_days", 0)) if not margin_missing else 0,
            "margin_short_asof_missing_flag": int(margin_missing),
        }
        values["margin_short_divergence_proxy"] = values["margin_direction_proxy"] - values["short_direction_proxy"]
        if current_value <= 0 and values["suspension_proxy"] != 1:
            raise ContractError("NMRPA_E_SOURCE_CONFLICT", "zero trading value requires suspension")
        for base, series in (("foreign_net_buy", f), ("investment_trust_net_buy", it), ("dealer_net_buy", d), ("institutional_total_net_buy", total), ("margin_balance_change", mbc), ("short_balance_change", sbc)):
            for window in (1, 3, 5, 10):
                values[f"{base}_roll{window}"] = math.fsum(series[-window:])
        if set(values) != set(FEATURE_NAMES) or len(values) != 78:
            raise ContractError("NMRPA_E_FEATURE_ALLOWLIST", "feature order/name drift")
        values = {name: values[name] for name in FEATURE_NAMES}
        candidate = {
            "artifact_type": "prospective_feature_candidate", "schema_version": SCHEMA_VERSION,
            "contract_id": fixture["contract_id"], "decision_date": fixture["decision_date"], "instrument": symbol,
            **refs, "feature_values": values,
        }
        candidate["feature_row_sha256"] = checksum_without(candidate, "feature_row_sha256")
        out.append(candidate)
    return out


def independent_feature_oracle(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    """Readonly recomputation from raw snapshot; intentionally separate from the builder."""
    data = expand_fixture(fixture)
    active = sorted(data["formal_active_symbols"])
    symbols = data["symbols"]
    if set(symbols) != set(active):
        raise ContractError("NMRPA_E_UPSTREAM_OMISSION", "oracle active set mismatch")
    refs = contract_refs()
    scores = {symbol: float(symbols[symbol]["score"]) for symbol in active}
    ranked = sorted(active, key=lambda symbol: (-scores[symbol], symbol))
    ranks = {symbol: i + 1 for i, symbol in enumerate(ranked)}
    score_values = list(scores.values())
    score_mean = math.fsum(score_values) / len(score_values)
    score_std = math.sqrt(math.fsum((x - score_mean) ** 2 for x in score_values) / len(score_values))
    twii = [float(x) for x in data["twii_close"]]
    if len(twii) < 121 or any(x <= 0 or not math.isfinite(x) for x in twii):
        raise ContractError("NMRPA_E_SOURCE_COVERAGE", "oracle TWII invalid")
    breadth_flags = []
    for symbol in active:
        closes = [float(x) for x in symbols[symbol]["price"]["close"]]
        breadth_flags.append(closes[-1] > math.fsum(closes[-20:]) / 20)
    breadth = math.fsum(int(x) for x in breadth_flags) / len(active)
    result = []
    for symbol in active:
        raw = symbols[symbol]
        price = raw["price"]
        close = [float(x) for x in price["close"]]
        volume = [float(x) for x in price["volume"]]
        vwap = [float(x) for x in price["vwap"]]
        expected_grid = price["expected_date_grid_last20"]
        observed_grid = price["observed_close_date_grid_last20"]
        if len(close) < 121 or len(volume) < 60 or len(vwap) < 60 or expected_grid != sorted(set(expected_grid)) or not set(observed_grid).issubset(expected_grid):
            raise ContractError("NMRPA_E_SOURCE_COVERAGE", "oracle price/grid invalid")
        if any(x <= 0 or not math.isfinite(x) for x in close + vwap) or any(x <= 0 for x in volume[-21:-1]):
            raise ContractError("NMRPA_E_SOURCE_CONFLICT", "oracle price/volume invalid")
        inst, inst_missing = _source_rows(raw["institutional"], "institutional", 10, active, data["decision_date"], symbol)
        margin, margin_missing = _source_rows(raw["margin"], "margin", 10, active, data["decision_date"], symbol)
        def column(rows: list[dict[str, Any]], name: str) -> list[float]:
            return [float(row[name]) if name in row else 0.0 for row in rows]
        foreign = column(inst, "foreign_net_buy")
        trust = column(inst, "investment_trust_net_buy")
        dealer = column(inst, "dealer_net_buy")
        total = [math.fsum(v) for v in zip(foreign, trust, dealer)]
        margin_balance = column(margin, "margin_balance")
        margin_change = column(margin, "margin_balance_change")
        short_balance = column(margin, "short_balance")
        short_change = column(margin, "short_balance_change")
        rank = ranks[symbol]
        rank_history = raw.get("rank_history", [])
        lag = lambda n: int(rank_history[-n]) - rank if len(rank_history) >= n else 0
        def trailing_true(values: list[bool]) -> int:
            count = 0
            for value in reversed(values):
                if not value:
                    break
                count += 1
            return count
        returns = [close[i] / close[i - 1] - 1 for i in range(1, len(close))]
        market_returns = [twii[i] / twii[i - 1] - 1 for i in range(1, len(twii))]
        delta14 = [close[i] - close[i - 1] for i in range(len(close) - 14, len(close))]
        gain = math.fsum(max(v, 0) for v in delta14) / 14
        loss = math.fsum(max(-v, 0) for v in delta14) / 14
        rsi = 50.0 if gain == loss == 0 else 100.0 if loss == 0 else 100.0 - 100.0 / (1.0 + gain / loss)
        c20, v20, w20 = close[-20:], volume[-20:], vwap[-20:]
        c20_mean = math.fsum(c20) / 20
        c20_std = math.sqrt(math.fsum((x - c20_mean) ** 2 for x in c20) / 20)
        current_value = volume[-1] * vwap[-1]
        suspension = int(volume[-1] <= 0)
        if current_value <= 0 and suspension != 1:
            raise ContractError("NMRPA_E_SOURCE_CONFLICT", "oracle suspension coupling")
        values: dict[str, float | int] = {
            "qlib_score_raw": scores[symbol], "qlib_rank": rank,
            "qlib_score_percentile_by_date": 0.0 if len(active) == 1 else (len(active) - rank) / (len(active) - 1),
            "qlib_score_zscore_by_date": 0.0 if score_std == 0 else (scores[symbol] - score_mean) / score_std,
            "rank_change_1d": lag(1), "rank_change_3d": lag(3), "rank_change_5d": lag(5),
            "top10_flag": int(rank <= min(10, len(active))), "top30_flag": int(rank <= min(30, len(active))), "top50_flag": int(rank <= min(50, len(active))),
            "top30_streak": trailing_true(raw.get("top30_history", []) + [rank <= min(30, len(active))]),
            "top50_streak": trailing_true(raw.get("top50_history", []) + [rank <= min(50, len(active))]),
            "MA5": math.fsum(close[-5:]) / 5, "MA10": math.fsum(close[-10:]) / 10,
            "MA20": c20_mean, "MA60": math.fsum(close[-60:]) / 60,
            "RSI14": rsi, "MACD": ema(close[-26:], 12) - ema(close[-26:], 26),
            "Bollinger_position": 0.0 if c20_std == 0 else max(-5.0, min(5.0, (close[-1] - c20_mean) / (2 * c20_std))),
            "ret20": close[-1] / close[-21] - 1,
            "volatility20": std0(returns[-20:]), "volume_ratio20": 0.0 if mean(v20) == 0 else volume[-1] / mean(v20),
            "avg_trading_value_20d": math.fsum(a * b for a, b in zip(v20, w20)) / 20,
            "volume_stability20": 1 / (1 + std0([volume[i] / volume[i - 1] - 1 for i in range(len(volume) - 20, len(volume))])),
            "missing_rate20": (len(expected_grid) - len(observed_grid)) / 20,
            "suspension_proxy": suspension, "slippage_proxy": 0.0 if current_value <= 0 else 1 / math.sqrt(current_value),
            "TWII_ret20": twii[-1] / twii[-21] - 1, "TWII_ret60": twii[-1] / twii[-61] - 1,
            "TWII_close_vs_MA60": twii[-1] / (math.fsum(twii[-60:]) / 60) - 1,
            "TWII_close_vs_MA120": twii[-1] / (math.fsum(twii[-120:]) / 120) - 1,
            "market_volatility20": std0(market_returns[-20:]), "market_drawdown60": twii[-1] / max(twii[-60:]) - 1,
            "market_breadth20": breadth,
            "foreign_net_buy": foreign[-1], "investment_trust_net_buy": trust[-1], "dealer_net_buy": dealer[-1],
            "institutional_total_net_buy": total[-1], "institutional_total_net_buy_streak": signed_streak(total),
            "institutional_missing_flag": int(inst_missing), "institutional_delay_flag": int(inst_missing or raw["institutional"].get("delay_days", 0) > 0),
            "institutional_flow_delay_days": 0 if inst_missing else int(raw["institutional"].get("delay_days", 0)),
            "institutional_flow_asof_missing_flag": int(inst_missing),
            "margin_balance": margin_balance[-1], "margin_balance_change": margin_change[-1],
            "short_balance": short_balance[-1], "short_balance_change": short_change[-1],
            "margin_direction_proxy": (margin_change[-1] > 0) - (margin_change[-1] < 0),
            "short_direction_proxy": (short_change[-1] > 0) - (short_change[-1] < 0),
            "margin_short_missing_flag": int(margin_missing), "margin_short_delay_flag": int(margin_missing or raw["margin"].get("delay_days", 0) > 0),
            "margin_short_delay_days": 0 if margin_missing else int(raw["margin"].get("delay_days", 0)),
            "margin_short_asof_missing_flag": int(margin_missing),
        }
        values["margin_short_divergence_proxy"] = int(values["margin_direction_proxy"]) - int(values["short_direction_proxy"])
        for base, series in (("foreign_net_buy", foreign), ("investment_trust_net_buy", trust), ("dealer_net_buy", dealer), ("institutional_total_net_buy", total), ("margin_balance_change", margin_change), ("short_balance_change", short_change)):
            for window in (1, 3, 5, 10):
                values[f"{base}_roll{window}"] = math.fsum(series[-window:])
        if set(values) != set(FEATURE_NAMES):
            raise ContractError("NMRPA_E_FEATURE_ALLOWLIST", "oracle formula coverage")
        candidate = {"artifact_type": "prospective_feature_candidate", "schema_version": SCHEMA_VERSION, "contract_id": data["contract_id"], "decision_date": data["decision_date"], "instrument": symbol, **refs, "feature_values": {name: values[name] for name in FEATURE_NAMES}}
        candidate["feature_row_sha256"] = checksum_without(candidate, "feature_row_sha256")
        result.append(candidate)
    return result


def expand_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Expand deterministic synthetic series specs without external data access."""
    value = json.loads(json.dumps(fixture))
    def series(spec: Any) -> Any:
        if not isinstance(spec, dict) or set(spec) != {"SYNTHETIC_SERIES_SPEC"}:
            return spec
        cfg = spec["SYNTHETIC_SERIES_SPEC"]
        if set(cfg) != {"start", "step", "count"} or int(cfg["count"]) > 256:
            raise ContractError("NMRPA_E_FIXTURE", "invalid synthetic series spec")
        return [float(cfg["start"]) + float(cfg["step"]) * i for i in range(int(cfg["count"]))]
    def date_grid(spec: Any) -> Any:
        if not isinstance(spec, dict) or set(spec) != {"SYNTHETIC_DATE_GRID_SPEC"}:
            return spec
        cfg = spec["SYNTHETIC_DATE_GRID_SPEC"]
        if set(cfg) != {"start", "count"} or not isinstance(cfg["start"], int) or not 1 <= cfg["count"] <= 256:
            raise ContractError("NMRPA_E_FIXTURE", "invalid synthetic date grid spec")
        return [f"SYNTHETIC_TD_{i:03d}" for i in range(cfg["start"], cfg["start"] + cfg["count"])]
    value["twii_close"] = series(value["twii_close"])
    value["calendar"]["trading_dates"] = date_grid(value["calendar"]["trading_dates"])
    for row in value["symbols"].values():
        for field in ("close", "volume", "vwap"):
            row["price"][field] = series(row["price"][field])
        for field in ("expected_date_grid_last20", "observed_close_date_grid_last20"):
            row["price"][field] = date_grid(row["price"][field])
    return value


def validate_input_snapshot(snapshot: dict[str, Any]) -> None:
    """Validate the fully expanded, synthetic-only input before any package hashes."""
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "contract_id", "decision_date", "decision_time", "calendar",
        "formal_active_symbols", "twii_close", "symbols",
    }:
        raise ContractError("NMRPA_E_INPUT_SCHEMA", "input snapshot top-level fields must be exact")
    if snapshot != expand_fixture(snapshot):
        raise ContractError("NMRPA_E_INPUT_SCHEMA", "input snapshot must be fully expanded")
    if set(snapshot["calendar"]) != {"available_at", "trading_dates"}:
        raise ContractError("NMRPA_E_INPUT_SCHEMA", "calendar fields must be exact")
    if not isinstance(snapshot["formal_active_symbols"], list) or not isinstance(snapshot["twii_close"], list):
        raise ContractError("NMRPA_E_INPUT_SCHEMA", "input arrays invalid")
    if not isinstance(snapshot["symbols"], dict):
        raise ContractError("NMRPA_E_INPUT_SCHEMA", "symbols must be an object")
    symbol_fields = {
        "score", "available_at", "rank_history", "top30_history",
        "top50_history", "price", "institutional", "margin",
    }
    price_fields = {
        "close", "volume", "vwap", "expected_date_grid_last20",
        "observed_close_date_grid_last20",
    }
    for symbol, row in snapshot["symbols"].items():
        require_synthetic(symbol, "snapshot instrument")
        if not isinstance(row, dict) or set(row) != symbol_fields:
            raise ContractError("NMRPA_E_INPUT_SCHEMA", f"{symbol} fields must be exact")
        if not isinstance(row["price"], dict) or set(row["price"]) != price_fields:
            raise ContractError("NMRPA_E_INPUT_SCHEMA", f"{symbol} price fields must be exact")
        for kind in ("institutional", "margin"):
            source = row[kind]
            if not isinstance(source, dict):
                raise ContractError("NMRPA_E_INPUT_SCHEMA", f"{kind} source must be object")
            state = source.get("source_state")
            expected = {"source_state", "absence_evidence"} if state == "confirmed_absent" else {"source_state", "rows", "delay_days"}
            if set(source) != expected:
                raise ContractError("NMRPA_E_INPUT_SCHEMA", f"{kind} source fields must be exact")
    # Reuse the semantic validator after exact shape has been established.
    compute_features(snapshot)


def build_source_manifest(fixture: dict[str, Any]) -> dict[str, Any]:
    fixture = expand_fixture(fixture)
    source_payloads = {
        "calendar": fixture["calendar"],
        "formal_instruments": fixture["formal_active_symbols"],
        "model_a": {s: {"score": r["score"], "available_at": r["available_at"]} for s, r in fixture["symbols"].items()},
        "price": {s: r["price"] for s, r in fixture["symbols"].items()},
        "twii": fixture["twii_close"],
        "institutional": {s: r["institutional"] for s, r in fixture["symbols"].items()},
        "margin": {s: r["margin"] for s, r in fixture["symbols"].items()},
    }
    refs = [{
        "source_kind": kind,
        "source_id": f"SYNTHETIC_SOURCE_{kind.upper()}",
        "source_state": "present",
        "payload_sha256": digest(payload),
        "manifest_sha256": digest({"source_kind": kind, "payload_sha256": digest(payload)}),
    } for kind, payload in source_payloads.items()]
    out = {
        "artifact_type": "prospective_source_reference_manifest",
        "schema_version": SCHEMA_VERSION,
        "contract_id": fixture["contract_id"],
        "decision_date": fixture["decision_date"],
        **contract_refs(),
        "synthetic_input_snapshot_sha256": digest(fixture),
        "calendar_binding": build_calendar_binding(fixture),
        "source_references": refs,
    }
    out["source_reference_set_sha256"] = digest(sorted(refs, key=lambda x: x["source_kind"]))
    out["manifest_sha256"] = checksum_without(out, "manifest_sha256")
    return out


def build_eligibility(fixture: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    fixture = expand_fixture(fixture)
    symbols = sorted(fixture["formal_active_symbols"])
    records = [{
        "instrument": s, "reason": "eligible", "included": True,
        "model_a_count": 1, "price_count": 1, "institutional_count": 1,
        "margin_count": 1, "candidate_sha256": candidates[i]["feature_row_sha256"],
    } for i, s in enumerate(symbols)]
    out = {
        "artifact_type": "dynamic_eligibility_audit", "schema_version": SCHEMA_VERSION,
        "contract_id": fixture["contract_id"], "decision_date": fixture["decision_date"],
        **contract_refs(),
        "date_summary": {
            "formal_active_count": len(symbols), "model_a_join_count": len(symbols),
            "price_join_count": len(symbols), "institutional_join_count": len(symbols),
            "margin_join_count": len(symbols), "included_count": len(candidates),
            "date_valid": True, "formal_active_set_sha256": digest(symbols),
            "included_set_sha256": digest([row["instrument"] for row in candidates]),
        },
        "symbol_records": records,
    }
    out["audit_payload_sha256"] = checksum_without(out, "audit_payload_sha256")
    return out


def forbidden_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    out = {"artifact_type": "nmrpa_forbidden_action_audit", "schema_version": SCHEMA_VERSION, "training_performed": False, "network_accessed": False, "database_accessed": False, "cron_modified": False, "provider_or_latest_written": False, "product_modified": False, "real_data_read": False, "result_value_generated": False, "protected_before": before, "protected_after": after, "protected_unchanged": before == after}
    out["audit_sha256"] = checksum_without(out, "audit_sha256")
    return out


def _event_hash_valid(event: dict[str, Any]) -> bool:
    body = {k: v for k, v in event.items() if k not in {"event_body_sha256", "event_hash"}}
    return (
        event.get("event_body_sha256") == digest(body)
        and event.get("event_hash") == digest({
            "chain_sequence": event.get("chain_sequence"),
            "previous_event_hash": event.get("previous_event_hash"),
            "event_body_sha256": event.get("event_body_sha256"),
        })
    )


def _empty_index() -> dict[str, Any]:
    return {"head_sequence": 0, "head_hash": None, "events": []}


JOURNAL_KEYS = {
    "transaction_id", "expected_head", "expected_hash", "planned_event_files",
    "planned_events", "planned_event_hashes", "phase",
}


def _validate_store_inventory(root: Path, *, pending_journal: dict[str, Any] | None = None) -> None:
    allowed_pending_files = set(pending_journal.get("planned_event_files", [])) if pending_journal else set()
    for dirname in ("events", "journals", "commits"):
        directory = root / dirname
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file() or path.suffix != ".json" or path.name.startswith("."):
                raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", f"unknown {dirname} entry")
    index = json.loads((root / "chain_index.json").read_text()) if (root / "chain_index.json").is_file() else _empty_index()
    actual_events = {p.name for p in (root / "events").glob("*.json")} if (root / "events").exists() else set()
    indexed = list(index.get("events", []))
    committed_files = set(indexed[:pending_journal["expected_head"]]) if pending_journal else set(indexed)
    if not committed_files.issubset(actual_events) or not actual_events.issubset(committed_files | allowed_pending_files):
        raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "unindexed or missing event file")


def _journal_matches_transaction(journal: dict[str, Any], marker: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    start = marker["expected_head"]
    planned = events[start:start + len(marker["event_files"])]
    return (
        set(journal) == JOURNAL_KEYS
        and journal["phase"] == "committed"
        and journal["transaction_id"] == marker["transaction_id"]
        and journal["expected_head"] == marker["expected_head"]
        and journal["expected_hash"] == marker["expected_hash"]
        and journal["planned_event_files"] == marker["event_files"]
        and journal["planned_event_hashes"] == marker["event_hashes"]
        and journal["planned_events"] == planned
    )


def _verify_committed_chain(
    root: Path,
    index_override: dict[str, Any] | None = None,
    *,
    pending_journal: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (root / "FROZEN").exists():
        raise ContractError("NMRPA_E_QUARANTINE", "event store is frozen")
    if pending_journal is None and (root / "journals").exists():
        pending = []
        for path in (root / "journals").glob("*.json"):
            value = json.loads(path.read_text())
            if value.get("phase") != "committed":
                pending.append(value)
        if len(pending) > 1:
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "multiple pending journals")
        pending_journal = pending[0] if pending else None
    _validate_store_inventory(root, pending_journal=pending_journal)
    index_path = root / "chain_index.json"
    index = index_override if index_override is not None else (json.loads(index_path.read_text()) if index_path.exists() else _empty_index())
    if set(index) != {"head_sequence", "head_hash", "events"} or not isinstance(index["events"], list):
        raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "chain index shape")
    events: list[dict[str, Any]] = []
    previous = None
    for sequence, filename in enumerate(index["events"], 1):
        path = root / "events" / filename
        if not path.is_file():
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "indexed event missing")
        event = json.loads(path.read_text())
        expected_name = f"{sequence:08d}_{event.get('event_hash')}.json"
        if filename != expected_name or event.get("chain_sequence") != sequence or event.get("previous_event_hash") != previous or not _event_hash_valid(event):
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "event chain/body/hash mismatch")
        previous = event["event_hash"]
        events.append(event)
    if index["head_sequence"] != len(events) or index["head_hash"] != previous:
        raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "index head mismatch")
    marker_items = []
    for marker_path in (root / "commits").glob("*.json") if (root / "commits").exists() else []:
        marker = json.loads(marker_path.read_text())
        required = {"transaction_id", "expected_head", "expected_hash", "event_files", "event_hashes", "committed"}
        if set(marker) != required or marker_path.name != f"{marker['transaction_id']}.json" or marker["committed"] is not True:
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "commit marker shape")
        if not isinstance(marker["expected_head"], int) or len(marker["event_files"]) != len(marker["event_hashes"]) or not marker["event_files"]:
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "empty/misaligned transaction")
        marker_items.append((marker["expected_head"], marker_path, marker))
    marker_items.sort(key=lambda item: item[0])
    covered: list[str] = []
    expected_start = 0
    for _, marker_path, marker in marker_items:
        if pending_journal and marker["transaction_id"] == pending_journal.get("transaction_id"):
            continue
        start = marker["expected_head"]
        if start != expected_start:
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "transaction overlap or gap")
        if marker["expected_hash"] != (events[start - 1]["event_hash"] if start else None):
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "marker expected head mismatch")
        actual = index["events"][start:start + len(marker["event_files"])]
        if actual != marker["event_files"]:
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "marker event range mismatch")
        if [events[start + i]["event_hash"] for i in range(len(actual))] != marker["event_hashes"]:
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "marker hashes mismatch")
        covered.extend(actual)
        journal_path = root / "journals" / marker_path.name
        if not journal_path.is_file() or not _journal_matches_transaction(json.loads(journal_path.read_text()), marker, events):
            raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "committed journal does not exactly bind transaction")
        expected_start += len(actual)
    if covered != index["events"]:
        raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "event not covered by ordered commit markers")
    journal_names = {p.name for p in (root / "journals").glob("*.json")} if (root / "journals").exists() else set()
    marker_names = {p.name for p in (root / "commits").glob("*.json")} if (root / "commits").exists() else set()
    allowed_pending_names = {f"{pending_journal['transaction_id']}.json"} if pending_journal else set()
    if journal_names != marker_names | allowed_pending_names:
        raise ContractError("NMRPA_E_APPEND_ONLY_TAMPER", "orphan journal or marker")
    return index, events


def chain_anchor(index: dict[str, Any]) -> dict[str, Any]:
    value = {
        "artifact_type": "synthetic_external_chain_anchor",
        "schema_version": SCHEMA_VERSION,
        "head_sequence": index["head_sequence"],
        "head_hash": index["head_hash"],
        "event_files_sha256": digest(index["events"]),
    }
    value["anchor_sha256"] = checksum_without(value, "anchor_sha256")
    return value


def write_external_chain_anchor(root: Path, anchor_path: Path) -> dict[str, Any]:
    root_resolved = root.resolve()
    anchor_resolved = anchor_path.resolve(strict=False)
    if root_resolved == anchor_resolved or root_resolved in anchor_resolved.parents or anchor_resolved in root_resolved.parents:
        raise ContractError("NMRPA_E_CHAIN_ANCHOR", "chain anchor must be outside candidate root")
    if anchor_path.exists() or anchor_path.is_symlink():
        raise ContractError("NMRPA_E_CHAIN_ANCHOR", "chain anchor path must be new")
    index, _ = _verify_committed_chain(root)
    value = chain_anchor(index)
    _atomic_json(anchor_path, value)
    return value


def verify_external_chain_anchor(root: Path, anchor_path: Path) -> None:
    if not anchor_path.is_file() or anchor_path.is_symlink():
        raise ContractError("NMRPA_E_CHAIN_ANCHOR", "external chain anchor missing")
    index, _ = _verify_committed_chain(root)
    expected = chain_anchor(index)
    actual = json.loads(anchor_path.read_text())
    if actual != expected:
        raise ContractError("NMRPA_E_CHAIN_ANCHOR", "external chain anchor mismatch or rollback")


def _new_event(body: dict[str, Any], sequence: int, previous_hash: str | None) -> dict[str, Any]:
    event_body = {**body, "chain_sequence": sequence, "previous_event_hash": previous_hash}
    body_hash = digest(event_body)
    event = {**event_body, "event_body_sha256": body_hash}
    event["event_hash"] = digest({"chain_sequence": sequence, "previous_event_hash": previous_hash, "event_body_sha256": body_hash})
    return event


def _append_transaction_locked(root: Path, bodies: list[dict[str, Any]], crash_phase: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
    index, _ = _verify_committed_chain(root)
    pending = [p for p in (root / "journals").glob("*.json") if json.loads(p.read_text()).get("phase") != "committed"]
    if pending:
        raise ContractError("NMRPA_E_RECOVERY_REQUIRED", "pending journal must be recovered")
    previous = index["head_hash"]
    events = []
    for offset, body in enumerate(bodies, 1):
        event = _new_event(body, index["head_sequence"] + offset, previous)
        events.append(event)
        previous = event["event_hash"]
    tx = f"SYNTHETIC_TX_{index['head_sequence'] + 1}_{len(events)}"
    files = [f"{e['chain_sequence']:08d}_{e['event_hash']}.json" for e in events]
    journal = {
        "transaction_id": tx, "expected_head": index["head_sequence"],
        "expected_hash": index["head_hash"], "planned_event_files": files,
        "planned_events": events, "planned_event_hashes": [e["event_hash"] for e in events],
        "phase": "planned",
    }
    journal_path = root / "journals" / f"{tx}.json"
    _atomic_json(journal_path, journal)
    if crash_phase == "after_journal":
        return {"recovery_required": True, "transaction_id": tx}
    for event_number, (filename, event) in enumerate(zip(files, events), 1):
        _atomic_json(root / "events" / filename, event)
        if crash_phase == f"after_event_rename_{event_number}":
            return {"recovery_required": True, "transaction_id": tx}
    if crash_phase == "after_event_rename":
        return {"recovery_required": True, "transaction_id": tx}
    new_index = {"head_sequence": events[-1]["chain_sequence"], "head_hash": events[-1]["event_hash"], "events": index["events"] + files}
    _atomic_json(root / "chain_index.json", new_index)
    if crash_phase == "after_index":
        return {"recovery_required": True, "transaction_id": tx}
    marker = {
        "transaction_id": tx, "expected_head": index["head_sequence"],
        "expected_hash": index["head_hash"], "event_files": files,
        "event_hashes": [e["event_hash"] for e in events], "committed": True,
    }
    _atomic_json(root / "commits" / f"{tx}.json", marker)
    if crash_phase == "after_marker":
        return {"recovery_required": True, "transaction_id": tx}
    journal["phase"] = "committed"
    _atomic_json(journal_path, journal)
    _verify_committed_chain(root)
    return events


def append_event(root: Path, body: dict[str, Any], *, crash_phase: str | None = None) -> dict[str, Any]:
    for directory in (root / "events", root / "journals", root / "commits"):
        directory.mkdir(parents=True, exist_ok=True)
    with (root / "writer.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("NMRPA_E_CONCURRENT_WRITER", "contract lock held") from exc
        result = _append_transaction_locked(root, [body], crash_phase)
        return result if isinstance(result, dict) else result[0]


def append_business_event(root: Path, body: dict[str, Any], *, crash_phase: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
    """Apply retry/collision semantics to a synthetic business event."""
    for directory in (root / "events", root / "journals", root / "commits"):
        directory.mkdir(parents=True, exist_ok=True)
    with (root / "writer.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("NMRPA_E_CONCURRENT_WRITER", "contract lock held") from exc
        _, committed = _verify_committed_chain(root)
        business_key = (body.get("contract_id"), body.get("decision_date"), body.get("event_type"))
        existing = next((e for e in committed if (e.get("contract_id"), e.get("decision_date"), e.get("event_type")) == business_key), None)
        if existing is None:
            bodies = [body]
        elif existing.get("payload_sha256") == body.get("payload_sha256"):
            bodies = [{**body, "event_type": "retry_observed", "original_event_hash": existing["event_hash"], "original_business_key": list(business_key), "counter_effect": 0}]
        else:
            collision = {**body, "event_type": "collision_rejected", "original_event_hash": existing["event_hash"], "rejected_payload_sha256": body["payload_sha256"], "counter_effect": 0}
            predicted = _new_event(collision, len(committed) + 1, committed[-1]["event_hash"] if committed else None)
            invalidation = {**body, "event_type": "invalidation", "invalidates_event_hash": existing["event_hash"], "trigger_event_hash": predicted["event_hash"], "counter_effect": -1}
            bodies = [collision, invalidation]
        return _append_transaction_locked(root, bodies, crash_phase)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2) + "\n"); handle.flush(); os.fsync(handle.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def recover(root: Path) -> str:
    for directory in (root / "events", root / "journals", root / "commits"):
        directory.mkdir(parents=True, exist_ok=True)
    with (root / "writer.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("NMRPA_E_CONCURRENT_WRITER", "contract lock held") from exc
        try:
            pending = [p for p in sorted((root / "journals").glob("*.json")) if json.loads(p.read_text()).get("phase") != "committed"]
            if not pending:
                _verify_committed_chain(root)
                return "clean"
            if len(pending) != 1:
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "multiple pending journals")
            journal_path = pending[0]
            journal = json.loads(journal_path.read_text())
            required = {"transaction_id", "expected_head", "expected_hash", "planned_event_files", "planned_events", "planned_event_hashes", "phase"}
            if set(journal) != required or journal["phase"] != "planned":
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "journal shape")
            actual_index = json.loads((root / "chain_index.json").read_text()) if (root / "chain_index.json").exists() else _empty_index()
            if len(actual_index.get("events", [])) < journal["expected_head"]:
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "index shorter than expected head")
            base_files = actual_index["events"][:journal["expected_head"]]
            base_index = {"head_sequence": journal["expected_head"], "head_hash": journal["expected_hash"], "events": base_files}
            index, _ = _verify_committed_chain(root, base_index, pending_journal=journal)
            if journal["expected_head"] != index["head_sequence"] or journal["expected_hash"] != index["head_hash"]:
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "journal expected head/hash")
            events = journal["planned_events"]
            files = journal["planned_event_files"]
            if len(events) != len(files) or [e.get("event_hash") for e in events] != journal["planned_event_hashes"]:
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "journal plans mismatch")
            previous = index["head_hash"]
            for offset, (filename, planned) in enumerate(zip(files, events), 1):
                expected_sequence = index["head_sequence"] + offset
                path = root / "events" / filename
                if not path.exists():
                    _atomic_json(path, planned)
                if not path.is_file() or json.loads(path.read_text()) != planned:
                    raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "event body mismatch")
                if filename != f"{expected_sequence:08d}_{planned.get('event_hash')}.json" or planned.get("chain_sequence") != expected_sequence or planned.get("previous_event_hash") != previous or not _event_hash_valid(planned):
                    raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "event filename/hash/chain mismatch")
                previous = planned["event_hash"]
            proposed_index = {"head_sequence": events[-1]["chain_sequence"], "head_hash": events[-1]["event_hash"], "events": index["events"] + files}
            existing_index = actual_index
            if existing_index not in (index, proposed_index):
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "index mismatch")
            _atomic_json(root / "chain_index.json", proposed_index)
            marker = {"transaction_id": journal["transaction_id"], "expected_head": index["head_sequence"], "expected_hash": index["head_hash"], "event_files": files, "event_hashes": journal["planned_event_hashes"], "committed": True}
            marker_path = root / "commits" / f"{journal['transaction_id']}.json"
            if marker_path.exists() and json.loads(marker_path.read_text()) != marker:
                raise ContractError("NMRPA_E_RECOVERY_MISMATCH", "marker mismatch")
            _atomic_json(marker_path, marker)
            journal["phase"] = "committed"
            _atomic_json(journal_path, journal)
            _verify_committed_chain(root)
            return "recovered"
        except ContractError as exc:
            tx = "SYNTHETIC_UNKNOWN_TX"
            if 'journal' in locals() and isinstance(journal, dict):
                tx = str(journal.get("transaction_id", tx))
            (root / "quarantine").mkdir(exist_ok=True)
            _atomic_json(root / "quarantine" / f"{tx}.json", {"normalized_identifier": tx, "observed_hash": digest(locals().get("journal", {})), "reason": "SYNTHETIC_RECOVERY_MISMATCH", "detected_at": "SYNTHETIC_TIME_RECOVERY", "protected_fingerprint": digest(protected_fingerprints())})
            _atomic_json(root / "FROZEN", {"reason": "SYNTHETIC_RECOVERY_MISMATCH"})
            raise ContractError("NMRPA_E_QUARANTINE", exc.detail) from exc


LEGAL_TRANSITIONS = {"none": "candidate_pending", "candidate_pending": "label_pending", "label_pending": "matured", "matured": "sealed"}


def append_state(history: list[dict[str, Any]], to_state: str, *, identity: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_maturity_history(history)
    current = history[-1]["to_state"] if history else "none"
    if to_state != "invalid" and LEGAL_TRANSITIONS.get(current) != to_state:
        raise ContractError("NMRPA_E_STATE_TRANSITION", f"illegal {current}->{to_state}")
    if current == "invalid":
        raise ContractError("NMRPA_E_STATE_TRANSITION", f"terminal {current}")
    identity = identity or {
        "contract_id": "SYNTHETIC_CONTRACT", "decision_date": "SYNTHETIC_TD_120",
        "instrument": "SYNTHETIC_SYMBOL_A", "candidate_sha256": "a" * 64,
        "calendar_prefix_sha256": "b" * 64, "calendar_full_sha256": "c" * 64,
        "maturity_endpoint": "SYNTHETIC_TD_130",
    }
    required_identity = {"contract_id", "decision_date", "instrument", "candidate_sha256", "calendar_prefix_sha256", "calendar_full_sha256", "maturity_endpoint"}
    if set(identity) != required_identity:
        raise ContractError("NMRPA_E_STATE_TRANSITION", "maturity identity fields")
    transition = {
        "artifact_type": "sealed_maturity_transition", "schema_version": SCHEMA_VERSION,
        "state_event_id": f"SYNTHETIC_STATE_EVENT_{len(history) + 1}",
        "state_sequence": len(history) + 1,
        "previous_state_hash": history[-1]["state_event_hash"] if history else None,
        "from_state": current, "to_state": to_state,
        "transition_reason": f"SYNTHETIC_REASON_{to_state.upper()}",
        **identity, **contract_refs(), "event_time": f"SYNTHETIC_TIME_STATE_{len(history) + 1}",
        "restricted_seal_ref": "SYNTHETIC_OPAQUE_SEAL" if to_state == "sealed" else None,
        "invalidation_ref": "SYNTHETIC_INVALIDATION_REF" if to_state == "invalid" else None,
    }
    transition["transition_body_sha256"] = checksum_without(transition, "state_event_hash", "transition_body_sha256")
    transition["state_event_hash"] = digest({"state_sequence": transition["state_sequence"], "previous_state_hash": transition["previous_state_hash"], "transition_body_sha256": transition["transition_body_sha256"]})
    return transition


def validate_maturity_history(history: list[dict[str, Any]]) -> None:
    previous_hash = None
    previous_state = "none"
    identity = None
    refs = contract_refs()
    for sequence, state in enumerate(history, 1):
        body_sha = checksum_without(state, "state_event_hash", "transition_body_sha256")
        expected_hash = digest({"state_sequence": sequence, "previous_state_hash": previous_hash, "transition_body_sha256": body_sha})
        current_identity = {k: state.get(k) for k in ("contract_id", "decision_date", "instrument", "candidate_sha256", "calendar_prefix_sha256", "calendar_full_sha256", "maturity_endpoint")}
        if identity is None:
            identity = current_identity
        legal = state.get("to_state") == "invalid" or LEGAL_TRANSITIONS.get(previous_state) == state.get("to_state")
        if (
            state.get("state_sequence") != sequence or state.get("previous_state_hash") != previous_hash
            or state.get("from_state") != previous_state or not legal or previous_state == "invalid"
            or current_identity != identity or any(state.get(k) != v for k, v in refs.items())
            or state.get("transition_body_sha256") != body_sha or state.get("state_event_hash") != expected_hash
            or (state.get("restricted_seal_ref") is not None) != (state.get("to_state") == "sealed")
            or (state.get("invalidation_ref") is not None) != (state.get("to_state") == "invalid")
        ):
            raise ContractError("NMRPA_E_STATE_TRANSITION", "maturity history replay failed")
        previous_hash = state["state_event_hash"]
        previous_state = state["to_state"]


def validate_maturity_set(
    transitions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    calendar: dict[str, Any],
) -> None:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for state in transitions:
        key = (state.get("contract_id"), state.get("decision_date"), state.get("instrument"))
        grouped.setdefault(key, []).append(state)
    expected = {
        (candidate["contract_id"], candidate["decision_date"], candidate["instrument"]): candidate
        for candidate in candidates
    }
    if not expected or set(grouped) != set(expected):
        raise ContractError("NMRPA_E_STATE_TRANSITION", "maturity identities must equal all candidate identities")
    for key, history in grouped.items():
        history.sort(key=lambda item: item.get("state_sequence", -1))
        validate_maturity_history(history)
        first = history[0]
        candidate = expected[key]
        if (
            first["candidate_sha256"] != candidate["feature_row_sha256"]
            or first["calendar_prefix_sha256"] != calendar["prefix_sha256"]
            or first["calendar_full_sha256"] != calendar["full_sha256"]
            or first["maturity_endpoint"] != calendar["maturity_endpoint"]
        ):
            raise ContractError("NMRPA_E_STATE_TRANSITION", "maturity candidate/calendar cross-binding mismatch")


def build_calendar_binding(fixture: dict[str, Any]) -> dict[str, Any]:
    dates = fixture["calendar"]["trading_dates"]
    if dates != sorted(set(dates)) or fixture["decision_date"] not in dates:
        raise ContractError("NMRPA_E_CALENDAR", "calendar must be strict and contain decision date")
    position = dates.index(fixture["decision_date"])
    if position + 10 >= len(dates):
        raise ContractError("NMRPA_E_MATURITY_CALENDAR", "calendar lacks tenth following trading date")
    prefix = dates[:position + 1]
    return {
        "artifact_type": "synthetic_calendar_binding", "schema_version": SCHEMA_VERSION,
        "decision_date": fixture["decision_date"], "prefix_dates": prefix,
        "full_dates": dates, "prefix_sha256": digest(prefix), "full_sha256": digest(dates),
        "maturity_horizon_td": 10, "maturity_endpoint": dates[position + 10],
    }


def validate_calendar_artifact(binding: dict[str, Any], prior: dict[str, Any] | None = None) -> None:
    required = {"artifact_type", "schema_version", "decision_date", "prefix_dates", "full_dates", "prefix_sha256", "full_sha256", "maturity_horizon_td", "maturity_endpoint"}
    if set(binding) != required or binding.get("artifact_type") != "synthetic_calendar_binding" or binding.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("NMRPA_E_CALENDAR", "calendar binding schema")
    prefix, full = binding["prefix_dates"], binding["full_dates"]
    if not isinstance(prefix, list) or not isinstance(full, list) or full != sorted(set(full)) or full[:len(prefix)] != prefix:
        raise ContractError("NMRPA_E_CONTRACT_DRIFT", "calendar duplicate/reorder/prefix mismatch")
    if binding["decision_date"] not in prefix or prefix[-1] != binding["decision_date"]:
        raise ContractError("NMRPA_E_CALENDAR", "decision endpoint mismatch")
    index = full.index(binding["decision_date"])
    if binding["maturity_horizon_td"] != 10 or index + 10 >= len(full) or binding["maturity_endpoint"] != full[index + 10]:
        raise ContractError("NMRPA_E_MATURITY_CALENDAR", "wrong tenth trading-day endpoint")
    if binding["prefix_sha256"] != digest(prefix) or binding["full_sha256"] != digest(full):
        raise ContractError("NMRPA_E_CHECKSUM", "calendar checksum")
    if prior is not None and (prefix[:len(prior["prefix_dates"])] != prior["prefix_dates"] or full[:len(prior["full_dates"])] != prior["full_dates"]):
        raise ContractError("NMRPA_E_CONTRACT_DRIFT", "calendar historical prefix mutation")


def calendar_extends(prefix: list[str], extension: list[str]) -> bool:
    return len(extension) >= len(prefix) and extension[:len(prefix)] == prefix and extension == sorted(set(extension))


COMPLETION_ANCHOR_KEYS = {
    "artifact_type", "schema_version", "contract_id", "ordered_decision_references",
    "protected_fingerprint_set", "committed_chain_anchor_sha256",
    "committed_chain_head_sequence", "committed_chain_head_hash",
    "frozen_at_chain_sequence", "anchor_sha256",
}
COMPLETION_REFERENCE_KEYS = {
    "prospective_sequence", "decision_identity", "candidate_event_hash",
    "candidate_payload_sha256", "candidate_set_sha256", "eligibility_sha256",
    "source_manifest_sha256", "external_input_sha256", "calendar_prefix_sha256",
    "calendar_full_sha256", "acl_audit_sha256",
}


def _replay_committed_completion_cohort(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int] | None:
    """Freeze the first 126 live candidate identities from one committed chain."""
    candidates_by_hash: dict[str, dict[str, Any]] = {}
    active_by_date: dict[str, dict[str, Any]] = {}
    collisions_by_hash: dict[str, dict[str, Any]] = {}
    frozen: list[dict[str, Any]] | None = None
    frozen_hashes: set[str] = set()
    frozen_at = 0
    for event in events:
        event_type = event.get("event_type")
        event_hash = event.get("event_hash")
        decision_date = event.get("decision_date")
        if event.get("contract_id") != "SYNTHETIC_CONTRACT" or not isinstance(event_hash, str):
            return None
        if event_type == "candidate_valid":
            if decision_date in active_by_date or event_hash in candidates_by_hash:
                return None
            candidates_by_hash[event_hash] = event
            active_by_date[decision_date] = event
        elif event_type == "retry_observed":
            original = candidates_by_hash.get(event.get("original_event_hash"))
            if event.get("counter_effect") != 0 or original is None:
                return None
            expected_key = [original.get("contract_id"), original.get("decision_date"), "candidate_valid"]
            if event.get("original_business_key") != expected_key or decision_date != original.get("decision_date"):
                return None
        elif event_type == "collision_rejected":
            original = candidates_by_hash.get(event.get("original_event_hash"))
            if event.get("counter_effect") != 0 or original is None or decision_date != original.get("decision_date"):
                return None
            collisions_by_hash[event_hash] = event
        elif event_type == "invalidation":
            original_hash = event.get("invalidates_event_hash")
            original = candidates_by_hash.get(original_hash)
            trigger = collisions_by_hash.get(event.get("trigger_event_hash"))
            if (
                event.get("counter_effect") != -1
                or original is None
                or trigger is None
                or trigger.get("original_event_hash") != original_hash
                or decision_date != original.get("decision_date")
                or active_by_date.get(decision_date) != original
            ):
                return None
            del active_by_date[decision_date]
            if original_hash in frozen_hashes:
                return None
        elif event_type != "validation_failed":
            return None
        if frozen is None and len(active_by_date) == 126:
            frozen = list(active_by_date.values())
            frozen_hashes = {item["event_hash"] for item in frozen}
            frozen_at = event["chain_sequence"]
    if frozen is None or any(active_by_date.get(item["decision_date"]) != item for item in frozen):
        return None
    return frozen, frozen_at


def completion(
    decision_states: list[dict[str, Any]],
    external_anchor: dict[str, Any] | None = None,
    *,
    expected_anchor_sha256: str | None = None,
    committed_event_store: Path | None = None,
    committed_chain_anchor: Path | None = None,
) -> bool:
    """Replay the externally anchored first 126 prospective identities."""
    required = {
        "prospective_sequence", "decision_identity", "candidate_event",
        "candidate_set", "included_symbols", "eligibility_audit", "maturity_histories",
        "source_manifest", "calendar_binding", "contract_refs", "acl_audit",
    }
    if (
        len(decision_states) < 126
        or any(not isinstance(row, dict) or set(row) != required for row in decision_states)
        or not isinstance(external_anchor, dict)
        or set(external_anchor) != COMPLETION_ANCHOR_KEYS
        or external_anchor.get("artifact_type") != "synthetic_external_completion_anchor"
        or external_anchor.get("schema_version") != SCHEMA_VERSION
        or external_anchor.get("contract_id") != "SYNTHETIC_CONTRACT"
        or external_anchor.get("anchor_sha256") != checksum_without(external_anchor, "anchor_sha256")
        or not isinstance(expected_anchor_sha256, str)
        or not SHA_RE.fullmatch(expected_anchor_sha256)
        or digest(external_anchor) != expected_anchor_sha256
    ):
        return False
    if not isinstance(committed_event_store, Path) or not isinstance(committed_chain_anchor, Path):
        return False
    try:
        verify_external_chain_anchor(committed_event_store, committed_chain_anchor)
        committed_index, committed_events = _verify_committed_chain(committed_event_store)
        for committed_event in committed_events:
            _validate_exact_event_schema(committed_event)
        chain_anchor_value = json.loads(committed_chain_anchor.read_text())
    except (ContractError, OSError, ValueError, json.JSONDecodeError):
        return False
    replayed = _replay_committed_completion_cohort(committed_events)
    if replayed is None:
        return False
    committed_cohort, frozen_at = replayed
    if (
        external_anchor.get("committed_chain_anchor_sha256") != digest(chain_anchor_value)
        or external_anchor.get("committed_chain_head_sequence") != committed_index["head_sequence"]
        or external_anchor.get("committed_chain_head_hash") != committed_index["head_hash"]
        or external_anchor.get("frozen_at_chain_sequence") != frozen_at
    ):
        return False
    ordered = sorted(decision_states, key=lambda row: row["prospective_sequence"])
    if [row["prospective_sequence"] for row in ordered] != list(range(1, len(ordered) + 1)):
        return False
    anchored_refs = external_anchor.get("ordered_decision_references")
    protected = external_anchor.get("protected_fingerprint_set")
    if (
        not isinstance(anchored_refs, list) or len(anchored_refs) != 126
        or any(not isinstance(ref, dict) or set(ref) != COMPLETION_REFERENCE_KEYS for ref in anchored_refs)
        or not isinstance(protected, dict) or not protected
    ):
        return False
    cohort = ordered[:126]
    if [row["candidate_event"] for row in cohort] != committed_cohort:
        return False
    if [(row["prospective_sequence"], row["decision_identity"]) for row in cohort] != [
        (ref["prospective_sequence"], ref["decision_identity"]) for ref in anchored_refs
    ]:
        return False
    identities = [row["decision_identity"] for row in cohort]
    if len(identities) != len(set(identities)):
        return False
    refs = contract_refs()
    for row, anchored in zip(cohort, anchored_refs):
        symbols = row["included_symbols"]
        if not symbols or symbols != sorted(set(symbols)):
            return False
        candidates = row["candidate_set"]
        if (
            not isinstance(candidates, list) or not candidates
            or candidates != sorted(candidates, key=lambda item: item.get("instrument", ""))
            or any(not isinstance(item, dict) or set(item) != {"instrument", "candidate_sha256"} or not SHA_RE.fullmatch(str(item["candidate_sha256"])) for item in candidates)
            or [item["instrument"] for item in candidates] != symbols
        ):
            return False
        candidate_set_sha = digest(candidates)
        event = row["candidate_event"]
        if not isinstance(event, dict) or event.get("event_type") != "candidate_valid" or not _event_hash_valid(event):
            return False
        if event.get("decision_date") != row["decision_identity"] or event.get("payload_sha256") != candidate_set_sha or row["contract_refs"] != refs:
            return False
        eligibility = row["eligibility_audit"]
        if (
            not isinstance(eligibility, dict)
            or set(eligibility) != {"decision_date", "included_symbols", "candidate_set_sha256", "source_manifest_sha256", "eligibility_sha256"}
            or eligibility.get("decision_date") != row["decision_identity"]
            or eligibility.get("included_symbols") != symbols
            or eligibility.get("candidate_set_sha256") != candidate_set_sha
            or eligibility.get("eligibility_sha256") != checksum_without(eligibility, "eligibility_sha256")
        ):
            return False
        source = row["source_manifest"]
        calendar = row["calendar_binding"]
        acl = row["acl_audit"]
        try:
            validate_calendar_artifact(calendar)
        except ContractError:
            return False
        if (
            not isinstance(source, dict)
            or source.get("decision_date") != row["decision_identity"]
            or source.get("manifest_sha256") != checksum_without(source, "manifest_sha256")
            or not SHA_RE.fullmatch(str(source.get("external_input_sha256", "")))
            or source.get("calendar_binding") != calendar
            or any(source.get(k) != v for k, v in refs.items())
            or eligibility.get("source_manifest_sha256") != source.get("manifest_sha256")
            or not isinstance(acl, dict)
            or set(acl) != {"protected_unchanged", "synthetic_only", "protected_before", "protected_after", "protected_current", "audit_sha256"}
            or acl.get("audit_sha256") != checksum_without(acl, "audit_sha256")
            or acl.get("protected_unchanged") is not True
            or acl.get("synthetic_only") is not True
            or acl.get("protected_before") != protected
            or acl.get("protected_after") != protected
            or acl.get("protected_current") != protected
        ):
            return False
        observed_reference = {
            "prospective_sequence": row["prospective_sequence"],
            "decision_identity": row["decision_identity"],
            "candidate_event_hash": event["event_hash"],
            "candidate_payload_sha256": event["payload_sha256"],
            "candidate_set_sha256": candidate_set_sha,
            "eligibility_sha256": eligibility["eligibility_sha256"],
            "source_manifest_sha256": source["manifest_sha256"],
            "external_input_sha256": source["external_input_sha256"],
            "calendar_prefix_sha256": calendar["prefix_sha256"],
            "calendar_full_sha256": calendar["full_sha256"],
            "acl_audit_sha256": acl["audit_sha256"],
        }
        if observed_reference != anchored:
            return False
        histories = row["maturity_histories"]
        if not isinstance(histories, dict) or set(histories) != set(symbols):
            return False
        for symbol, history in histories.items():
            try:
                validate_maturity_history(history)
            except ContractError:
                return False
            candidate = next(item for item in candidates if item["instrument"] == symbol)
            first = history[0] if history else {}
            if (
                not history or history[-1].get("to_state") != "sealed"
                or first.get("instrument") != symbol
                or first.get("candidate_sha256") != candidate["candidate_sha256"]
                or first.get("decision_date") != row["decision_identity"]
                or first.get("contract_id") != external_anchor["contract_id"]
                or first.get("calendar_prefix_sha256") != calendar["prefix_sha256"]
                or first.get("calendar_full_sha256") != calendar["full_sha256"]
                or first.get("maturity_endpoint") != calendar["maturity_endpoint"]
            ):
                return False
    return True


VISIBLE_KEYS = {"artifact_type", "schema_version", "contract_id", "start_state", "latest_attempted_date", "valid_decision_date_count_bucket", "pending_date_count", "sealed_date_count", "invalid_date_count", "remaining_valid_dates", "maturity_wait_state", "integrity_state", "readiness_state", "last_failure_code", "generated_at"}


def visible_status(contract_id: str, decision_date: str, valid_count: int) -> dict[str, Any]:
    bucket = "0_19" if valid_count < 20 else "126" if valid_count >= 126 else "125" if valid_count == 125 else f"{(valid_count // 5) * 5}_{(valid_count // 5) * 5 + 4}"
    hidden: int | str = "suppressed" if valid_count < 20 else valid_count
    return {"artifact_type": "researcher_visible_holdout_status", "schema_version": SCHEMA_VERSION, "contract_id": contract_id, "start_state": "not_started" if valid_count == 0 else "started", "latest_attempted_date": decision_date, "valid_decision_date_count_bucket": bucket, "pending_date_count": hidden, "sealed_date_count": "suppressed" if valid_count < 20 else 0, "invalid_date_count": "suppressed" if valid_count < 20 else 0, "remaining_valid_dates": "suppressed" if valid_count < 20 else max(0, 126 - valid_count), "maturity_wait_state": "not_started" if valid_count == 0 else "waiting", "integrity_state": "synthetic_valid", "readiness_state": "isolated_only", "last_failure_code": "SYNTHETIC_NONE", "generated_at": "SYNTHETIC_TIME_GENERATED"}


def validate_visible(value: dict[str, Any], aggregate_evidence: dict[str, Any] | None = None) -> None:
    if set(value) != VISIBLE_KEYS:
        raise ContractError("NMRPA_E_VISIBLE_LEAK", f"visible keys differ: {sorted(set(value) - VISIBLE_KEYS)}")
    valid_buckets = {"0_19", "125", "126"} | {f"{start}_{start + 4}" for start in range(20, 125, 5)}
    if value["valid_decision_date_count_bucket"] not in valid_buckets:
        raise ContractError("NMRPA_E_VISIBLE_LEAK", "visible count bucket is not an exact allowed range")
    aggregate_keys = {"attempted_date_count", "valid_date_count", "pending_date_count", "sealed_date_count", "invalid_date_count"}
    if not isinstance(aggregate_evidence, dict) or set(aggregate_evidence) != aggregate_keys:
        raise ContractError("NMRPA_E_VISIBLE_COUNT", "restricted aggregate evidence is required")
    counts = [aggregate_evidence[key] for key in aggregate_keys]
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts):
        raise ContractError("NMRPA_E_VISIBLE_COUNT", "aggregate counts must be non-negative integers")
    valid = aggregate_evidence["valid_date_count"]
    pending = aggregate_evidence["pending_date_count"]
    sealed = aggregate_evidence["sealed_date_count"]
    invalid = aggregate_evidence["invalid_date_count"]
    attempted = aggregate_evidence["attempted_date_count"]
    if valid > 126 or pending + sealed != valid or attempted != valid + invalid:
        raise ContractError("NMRPA_E_VISIBLE_COUNT", "attempted must equal valid plus invalid; pending/sealed must partition valid")
    expected_bucket = "0_19" if valid < 20 else "126" if valid == 126 else "125" if valid == 125 else f"{(valid // 5) * 5}_{(valid // 5) * 5 + 4}"
    if value["valid_decision_date_count_bucket"] != expected_bucket:
        raise ContractError("NMRPA_E_VISIBLE_COUNT", "bucket does not match restricted valid count")
    count_keys = ("pending_date_count", "sealed_date_count", "invalid_date_count", "remaining_valid_dates")
    if valid < 20:
        if any(value[key] != "suppressed" for key in count_keys):
            raise ContractError("NMRPA_E_VISIBLE_LEAK", "small sample counts must be suppressed")
    elif (
        value["pending_date_count"] != pending
        or value["sealed_date_count"] != sealed
        or value["invalid_date_count"] != invalid
        or value["remaining_valid_dates"] != 126 - valid
    ):
        raise ContractError("NMRPA_E_VISIBLE_COUNT", "visible counts differ from restricted aggregate evidence")
    expected_start = "not_started" if valid == 0 and invalid == 0 else "started"
    expected_maturity = "not_started" if valid == 0 else "complete" if valid == sealed == 126 else "waiting" if pending > 0 else "partially_sealed"
    expected_integrity = "synthetic_valid" if invalid == 0 else "synthetic_invalid"
    expected_readiness = "isolated_complete" if valid == sealed == 126 and invalid == 0 else "isolated_only"
    if (
        value["start_state"] != expected_start
        or value["maturity_wait_state"] != expected_maturity
        or value["integrity_state"] != expected_integrity
        or value["readiness_state"] != expected_readiness
    ):
        raise ContractError("NMRPA_E_VISIBLE_COUNT", "visible states contradict aggregate counts")
    normalized = unicodedata.normalize("NFKC", json.dumps(value)).casefold()
    normalized = re.sub(r"[\s\-./\\:]+", "_", normalized)
    if any(token in normalized for token in ("checksum", "sha256", "seal_id", "symbol_state", "restricted_path")):
        raise ContractError("NMRPA_E_VISIBLE_LEAK", "restricted visible token")


def _validate_exact_schema(value: Any) -> None:
    schema_path = ROOT / "schemas/tw_policy_nmrpa2_candidate.schema.json"
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        detail = errors[0].message
        raise ContractError("NMRPA_E_SCHEMA", detail)


def _validate_exact_event_schema(value: Any) -> None:
    schema_path = ROOT / "schemas/tw_policy_nmrpa2_candidate.schema.json"
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator({"$ref": "#/$defs/event", "$defs": schema["$defs"]})
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        raise ContractError("NMRPA_E_SCHEMA", errors[0].message)
    expected_refs = contract_refs()
    if any(value.get(key) != expected for key, expected in expected_refs.items()):
        raise ContractError("NMRPA_E_CONTRACT_DRIFT", "committed event contract digest drift")


def _candidate_equal(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    if set(actual) != set(expected):
        return False
    for key in set(actual) - {"feature_values"}:
        if actual[key] != expected[key]:
            return False
    if set(actual["feature_values"]) != set(FEATURE_NAMES):
        return False
    integer_names = {record["feature_name"] for record in feature_formula_records() if record["dtype"] in {"int8", "int64"}}
    for name in FEATURE_NAMES:
        left, right = actual["feature_values"][name], expected["feature_values"][name]
        if name in integer_names:
            if isinstance(left, bool) or not isinstance(left, int) or left != right:
                return False
        elif isinstance(left, bool) or not isinstance(left, (int, float)) or not math.isclose(float(left), float(right), abs_tol=TOL_ABS, rel_tol=TOL_REL):
            return False
    return True


def validate_candidate_root(
    root: Path,
    *,
    expected_input_sha256: str,
    expected_chain_anchor: Path,
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(expected_input_sha256):
        raise ContractError("NMRPA_E_INPUT_ANCHOR", "expected input digest must be explicit SHA-256")
    required = ("synthetic_input_snapshot.json", "source_manifest.json", "eligibility_audit.json", "feature_candidates.json", "event.json", "maturity_transitions.json", "visible_status.json", "forbidden_action_audit.json")
    missing = [name for name in required if not (root / name).is_file()]
    if missing: raise ContractError("NMRPA_E_REQUIRED_FILE_MISSING", ",".join(missing))
    payloads = {name: json.loads((root / name).read_text()) for name in required}
    reject_real_dates(payloads)
    snapshot = payloads["synthetic_input_snapshot.json"]
    validate_input_snapshot(snapshot)
    if digest(snapshot) != expected_input_sha256:
        raise ContractError("NMRPA_E_INPUT_ANCHOR", "snapshot differs from package-external expected digest")
    manifest = payloads["source_manifest.json"]
    if manifest.get("synthetic_input_snapshot_sha256") != digest(snapshot):
        raise ContractError("NMRPA_E_SOURCE_CHECKSUM", "snapshot digest mismatch")
    _validate_exact_schema(snapshot)
    for name in required[1:]:
        value = payloads[name]
        for item in value if name in {"feature_candidates.json", "maturity_transitions.json"} else [value]:
            _validate_exact_schema(item)
    expected_refs = contract_refs()
    candidates = payloads["feature_candidates.json"]
    for row in candidates:
        if row.get("feature_row_sha256") != checksum_without(row, "feature_row_sha256"):
            raise ContractError("NMRPA_E_CHECKSUM", "feature row checksum")
    oracle = independent_feature_oracle(snapshot)
    if len(candidates) != len(oracle) or any(not _candidate_equal(actual, expected) for actual, expected in zip(candidates, oracle)):
        raise ContractError("NMRPA_E_FEATURE_RECOMPUTE", "candidate differs from independent 78-feature oracle")
    if manifest != build_source_manifest(snapshot):
        raise ContractError("NMRPA_E_SOURCE_CHECKSUM", "source manifest/cross-binding mismatch")
    validate_calendar_artifact(manifest["calendar_binding"])
    eligibility = payloads["eligibility_audit.json"]
    if eligibility != build_eligibility(snapshot, oracle):
        raise ContractError("NMRPA_E_ELIGIBILITY", "eligibility audit/candidate binding mismatch")
    for artifact in (manifest, eligibility, *candidates):
        if any(artifact.get(key) != value for key, value in expected_refs.items()):
            raise ContractError("NMRPA_E_CONTRACT_DRIFT", "contract digest mismatch")
    event = payloads["event.json"]
    verify_external_chain_anchor(root / "event_store", expected_chain_anchor)
    _, committed = _verify_committed_chain(root / "event_store")
    if not committed or event != committed[-1] or event.get("payload_sha256") != digest(candidates) or event.get("event_type") != "candidate_valid":
        raise ContractError("NMRPA_E_HASH_CHAIN", "top event is not committed candidate binding")
    if any(event.get(key) != value for key, value in expected_refs.items()):
        raise ContractError("NMRPA_E_CONTRACT_DRIFT", "event contract digest")
    history = payloads["maturity_transitions.json"]
    calendar = manifest["calendar_binding"]
    validate_maturity_set(history, candidates, calendar)
    audit = payloads["forbidden_action_audit.json"]
    current = protected_fingerprints()
    if (
        audit["audit_sha256"] != checksum_without(audit, "audit_sha256")
        or set(audit["protected_before"]) != set(PROTECTED_PATHS) | {ACTUAL_CRONTAB_KEY}
        or audit["protected_before"] != audit["protected_after"] or audit["protected_after"] != current
        or audit["protected_unchanged"] is not True
        or any(audit[k] for k in ("training_performed", "network_accessed", "database_accessed", "cron_modified", "provider_or_latest_written", "product_modified", "real_data_read", "result_value_generated"))
    ):
        raise ContractError("NMRPA_E_PROTECTED_BOUNDARY", "forbidden audit failed")
    validate_visible(payloads["visible_status.json"], {
        "attempted_date_count": 1,
        "valid_date_count": 1,
        "pending_date_count": 1,
        "sealed_date_count": 0,
        "invalid_date_count": 0,
    })
    return {"ok": True, "code": "OK", "candidate_count": len(candidates), "feature_count": 78, "protected_unchanged": True, "real_accumulation_started": False}


def build(
    fixture_path: Path,
    output_root: Path,
    *,
    expected_input_sha256: str,
    chain_anchor_path: Path,
) -> dict[str, Any]:
    output_root = validate_output_root(output_root)
    if fixture_path.is_symlink(): raise ContractError("NMRPA_E_INPUT_BOUNDARY", "fixture symlink forbidden")
    fixture = expand_fixture(json.loads(fixture_path.read_text()))
    reject_real_dates(fixture)
    validate_input_snapshot(fixture)
    if digest(fixture) != expected_input_sha256:
        raise ContractError("NMRPA_E_INPUT_ANCHOR", "fixture differs from explicit expected digest")
    before = protected_fingerprints()
    if output_root.exists():
        raise ContractError("NMRPA_E_OUTPUT_BOUNDARY", "isolated output root must not already exist")
    output_root.mkdir(parents=True)
    candidates = compute_features(fixture)
    source = build_source_manifest(fixture)
    eligibility = build_eligibility(fixture, candidates)
    event_body = {"artifact_type": "prospective_accumulation_event", "schema_version": SCHEMA_VERSION, "contract_id": fixture["contract_id"], "decision_date": fixture["decision_date"], "event_type": "candidate_valid", "attempt_id": "SYNTHETIC_ATTEMPT_1", "event_time": "SYNTHETIC_TIME_EVENT", "payload_sha256": digest(candidates), **contract_refs()}
    event = append_event(output_root / "event_store", event_body)
    calendar = source["calendar_binding"]
    states = [append_state([], "candidate_pending", identity={
        "contract_id": fixture["contract_id"], "decision_date": fixture["decision_date"],
        "instrument": candidate["instrument"], "candidate_sha256": candidate["feature_row_sha256"],
        "calendar_prefix_sha256": calendar["prefix_sha256"], "calendar_full_sha256": calendar["full_sha256"],
        "maturity_endpoint": calendar["maturity_endpoint"],
    }) for candidate in candidates]
    visible = visible_status(fixture["contract_id"], fixture["decision_date"], 1)
    for name, value in (("synthetic_input_snapshot.json", fixture), ("source_manifest.json", source), ("eligibility_audit.json", eligibility), ("feature_candidates.json", candidates), ("event.json", event), ("maturity_transitions.json", states), ("visible_status.json", visible)):
        _atomic_json(output_root / name, value)
    after = protected_fingerprints()
    _atomic_json(output_root / "forbidden_action_audit.json", forbidden_audit(before, after))
    write_external_chain_anchor(output_root / "event_store", chain_anchor_path)
    result = validate_candidate_root(
        output_root,
        expected_input_sha256=expected_input_sha256,
        expected_chain_anchor=chain_anchor_path,
    )
    _atomic_json(output_root / "validation_result.json", result)
    return result
