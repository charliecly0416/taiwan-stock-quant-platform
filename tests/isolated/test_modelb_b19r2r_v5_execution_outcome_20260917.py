from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import acquire_modelb_b19r2r_v5_execution_outcome_20260917 as acquisition  # noqa: E402
import build_modelb_b19r2r_v5_prospective_accumulator as accumulator  # noqa: E402


class IncrementingClock:
    def __init__(self, start: str) -> None:
        self.value = datetime.fromisoformat(start)

    def __call__(self) -> datetime:
        value = self.value
        self.value += timedelta(milliseconds=1)
        return value


def payload(ticker: str, *, day: str = acquisition.EXECUTION_DATE, value: float = 100.0) -> dict:
    timestamp = int(datetime.fromisoformat(f"{day}T01:00:00+00:00").timestamp())
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": ticker,
                        "regularMarketTime": int(
                            datetime.fromisoformat("2026-09-17T05:31:00+00:00").timestamp()
                        ),
                    },
                    "timestamp": [timestamp],
                    "indicators": {"quote": [{"open": [value], "close": [value + 1.0]}]},
                }
            ],
        }
    }


def empty_payload(ticker: str) -> dict:
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": ticker,
                        "regularMarketTime": int(
                            datetime.fromisoformat("2026-09-17T05:31:00+00:00").timestamp()
                        ),
                    },
                    "timestamp": [],
                    "indicators": {"quote": [{"open": [], "close": []}]},
                }
            ],
        }
    }


def response(value: dict, url: str) -> acquisition.HttpResult:
    return acquisition.HttpResult(
        status=200,
        url=url,
        headers={"content-type": "application/json", "date": "Thu, 17 Sep 2026 06:00:00 GMT"},
        body=json.dumps(value, separators=(",", ":")).encode(),
        transport="fixture",
    )


def successful_fetcher(url: str, timeout: float) -> acquisition.HttpResult:
    ticker = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
    code = int(ticker.split(".", 1)[0])
    if ticker == "1303.TW":
        return response(empty_payload(ticker), url)
    return response(payload(ticker, value=100.0 + code / 1000.0), url)


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory):
    temp = tmp_path_factory.mktemp("execution_outcome")
    research_root = temp / "research"
    research_root.mkdir()
    protected = temp / "protected.json"
    protected.write_text('{"stable":true}\n', encoding="utf-8")
    old_root = acquisition.RESEARCH_ROOT
    old_protected = acquisition.PROTECTED
    acquisition.RESEARCH_ROOT = research_root
    acquisition.PROTECTED = (protected,)
    output = research_root / "candidate"
    manifest = acquisition.capture(
        output,
        source_accumulator=acquisition.DEFAULT_ACCUMULATOR,
        fetcher=successful_fetcher,
        clock=IncrementingClock("2026-09-17T06:00:00+00:00"),
    )
    try:
        yield output, manifest, protected
    finally:
        acquisition.RESEARCH_ROOT = old_root
        acquisition.PROTECTED = old_protected


def mutable_copy(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    for path in target.rglob("*"):
        if path.is_dir():
            path.chmod(0o755)
        else:
            path.chmod(0o644)
    target.chmod(0o755)
    return target


@pytest.mark.parametrize(
    ("timestamp", "code"),
    [
        ("2026-09-17T00:59:59+00:00", "B19V5X_E_PREOPEN"),
        ("2026-09-17T03:00:00+00:00", "B19V5X_E_INTRADAY"),
    ],
)
def test_before_close_fails_without_network_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timestamp: str, code: str
) -> None:
    research_root = tmp_path / "research"
    research_root.mkdir()
    monkeypatch.setattr(acquisition, "RESEARCH_ROOT", research_root)
    calls = 0

    def forbidden_fetch(url: str, timeout: float):
        nonlocal calls
        calls += 1
        raise AssertionError("network must not be reached")

    output = research_root / "candidate"
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.capture(
            output,
            fetcher=forbidden_fetch,
            clock=IncrementingClock(timestamp),
        )
    assert caught.value.code == code
    assert calls == 0
    assert not output.exists()
    assert not list(research_root.glob("candidate.partial.*"))


def test_success_is_complete_auditable_and_does_not_mutate_ledger(candidate) -> None:
    output, manifest, _ = candidate
    result = acquisition.validate_candidate(output)
    assert result["status"] == "PASS"
    assert result["row_count"] == 50
    assert manifest["request_attempt_count"] == 51
    assert len(manifest["attempts"]) == 51
    fallback = [item for item in manifest["attempts"] if item["instrument"] == "TW1303"]
    assert [item["ticker"] for item in fallback] == ["1303.TW", "1303.TWO"]
    assert [item.get("selected", False) for item in fallback] == [False, True]
    assert sum(item.get("selected") is True for item in manifest["attempts"]) == 50
    assert manifest["available_at"] > manifest["fetch_completed_at"]
    assert manifest["available_at"] >= manifest["csv_committed_at"]
    assert manifest["source_ledger_sha256"] == acquisition.sha256(output / acquisition.SOURCE_EVENTS_NAME)
    source = acquisition.load_source_signal(acquisition.DEFAULT_ACCUMULATOR)
    current_calendar = accumulator.calendar_dates(output / acquisition.CALENDAR_NAME)
    assert current_calendar[:-1] == source["calendar_dates"]
    assert current_calendar[-1] == acquisition.EXECUTION_DATE
    assert (output / acquisition.SOURCE_EVENTS_NAME).read_bytes().splitlines() == source[
        "events_path"
    ].read_bytes().splitlines()[:1]
    assert output.stat().st_mode & 0o777 == 0o555
    assert all(path.stat().st_mode & 0o777 == 0o444 for path in output.rglob("*") if path.is_file())
    assert accumulator.load_events(acquisition.DEFAULT_ACCUMULATOR / "events.jsonl")[0]["event_type"] == "SIGNAL_CAPTURED"
    assert len(accumulator.load_events(acquisition.DEFAULT_ACCUMULATOR / "events.jsonl")) == 1


def test_missing_symbol_fails_without_candidate_or_ledger_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    research_root = tmp_path / "research"
    research_root.mkdir()
    protected = tmp_path / "protected.json"
    protected.write_text("stable\n", encoding="ascii")
    monkeypatch.setattr(acquisition, "RESEARCH_ROOT", research_root)
    monkeypatch.setattr(acquisition, "PROTECTED", (protected,))
    ledger_before = acquisition.sha256(acquisition.DEFAULT_ACCUMULATOR / "events.jsonl")

    def missing_fetcher(url: str, timeout: float) -> acquisition.HttpResult:
        ticker = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
        value = empty_payload(ticker) if ticker.startswith("1303.") else payload(ticker)
        return response(value, url)

    output = research_root / "candidate"
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.capture(
            output,
            fetcher=missing_fetcher,
            clock=IncrementingClock("2026-09-17T06:00:00+00:00"),
        )
    assert caught.value.code == "B19V5X_E_MISSING_SYMBOL"
    assert not output.exists()
    failures = list(research_root.glob("candidate.failed.*"))
    assert len(failures) == 1
    assert not (failures[0] / acquisition.CSV_NAME).exists()
    assert not (failures[0] / acquisition.MANIFEST_NAME).exists()
    assert acquisition.sha256(acquisition.DEFAULT_ACCUMULATOR / "events.jsonl") == ledger_before


def test_provider_duplicate_wrong_date_and_nonfinite_are_rejected() -> None:
    ticker = "2330.TW"
    duplicate = payload(ticker)
    result = duplicate["chart"]["result"][0]
    result["timestamp"] *= 2
    result["indicators"]["quote"][0]["open"] *= 2
    result["indicators"]["quote"][0]["close"] *= 2
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.parse_target_bar(duplicate, ticker)
    assert caught.value.code == "B19V5X_E_DUPLICATE_TARGET_BAR"

    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.parse_target_bar(payload(ticker, day="2026-09-16"), ticker)
    assert caught.value.code == "B19V5X_E_WRONG_DATE"

    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.parse_target_bar(payload(ticker, value=float("nan")), ticker)
    assert caught.value.code == "B19V5X_E_NONFINITE_PRICE"

    wrong_symbol = payload(ticker)
    wrong_symbol["chart"]["result"][0]["meta"]["symbol"] = "2317.TW"
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.parse_target_bar(wrong_symbol, ticker)
    assert caught.value.code == "B19V5X_E_PROVIDER_SYMBOL"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value["chart"]["result"][0].update({"indicators": None}), "B19V5X_E_PROVIDER_SCHEMA"),
        (
            lambda value: value["chart"]["result"][0]["indicators"].update({"quote": [None]}),
            "B19V5X_E_PROVIDER_SCHEMA",
        ),
        (
            lambda value: value["chart"]["result"][0].update({"timestamp": ["bad-timestamp"]}),
            "B19V5X_E_PROVIDER_TIMESTAMP",
        ),
        (
            lambda value: value["chart"]["result"][0]["meta"].update({"regularMarketTime": None}),
            "B19V5X_E_FINAL_CLOSE_UNPROVEN",
        ),
    ],
)
def test_malformed_nested_provider_values_are_governed(mutation, code: str) -> None:
    ticker = "2330.TW"
    value = payload(ticker)
    mutation(value)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.parse_target_bar(value, ticker)
    assert caught.value.code == code


@pytest.mark.parametrize(
    ("failure_kind", "expected_code"),
    [
        ("fetch_exception", "B19V5X_E_NETWORK"),
        ("fetch_result_exception", "B19V5X_E_UNEXPECTED"),
        ("parser_exception", "B19V5X_E_UNEXPECTED"),
        ("malformed_provider", "B19V5X_E_PROVIDER_SCHEMA"),
    ],
)
def test_capture_exceptions_freeze_failure_and_preserve_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
    expected_code: str,
) -> None:
    research_root = tmp_path / failure_kind
    research_root.mkdir()
    protected = tmp_path / f"{failure_kind}.protected"
    protected.write_text("stable\n", encoding="ascii")
    monkeypatch.setattr(acquisition, "RESEARCH_ROOT", research_root)
    monkeypatch.setattr(acquisition, "PROTECTED", (protected,))
    protected_before = acquisition.sha256(protected)
    accumulator_before = acquisition.accumulator_fingerprints(acquisition.DEFAULT_ACCUMULATOR)

    if failure_kind == "fetch_exception":
        def fetcher(url: str, timeout: float):
            raise RuntimeError("fixture fetch failure")
    elif failure_kind == "fetch_result_exception":
        def fetcher(url: str, timeout: float):
            return object()
    else:
        def fetcher(url: str, timeout: float) -> acquisition.HttpResult:
            ticker = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
            value = payload(ticker)
            if failure_kind == "malformed_provider":
                value["chart"]["result"][0]["indicators"] = None
            return response(value, url)

    if failure_kind == "parser_exception":
        def unexpected_parser(value, ticker):
            raise RuntimeError("fixture parser failure")

        monkeypatch.setattr(acquisition, "parse_target_bar", unexpected_parser)

    output = research_root / "candidate"
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.capture(
            output,
            fetcher=fetcher,
            clock=IncrementingClock("2026-09-17T06:00:00+00:00"),
        )
    assert caught.value.code == expected_code
    assert not output.exists()
    assert not list(research_root.glob("candidate.partial.*"))
    failures = list(research_root.glob("candidate.failed.*"))
    assert len(failures) == 1
    failure = failures[0]
    record = acquisition.read_json(failure / "CAPTURE_FAILURE.json")
    assert record["error_code"] == expected_code
    assert record["protected_unchanged"] is True
    assert record["accumulator_unchanged"] is True
    assert failure.stat().st_mode & 0o777 == 0o555
    assert all(path.stat().st_mode & 0o777 == 0o444 for path in failure.rglob("*") if path.is_file())
    assert acquisition.sha256(protected) == protected_before
    assert acquisition.accumulator_fingerprints(acquisition.DEFAULT_ACCUMULATOR) == accumulator_before


def test_validator_rejects_backdated_available_at(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    tampered = mutable_copy(output, tmp_path / "backdated")
    evidence_path = tampered / acquisition.AVAILABILITY_NAME
    manifest_path = tampered / acquisition.MANIFEST_NAME
    evidence = acquisition.read_json(evidence_path)
    manifest = acquisition.read_json(manifest_path)
    for key in ("started_at", "fetch_completed_at", "available_at"):
        evidence[key] = "2026-09-17T05:00:00+00:00"
        manifest[key] = "2026-09-17T05:00:00+00:00"
    acquisition.write_json(evidence_path, evidence)
    manifest["availability_evidence_sha256"] = acquisition.sha256(evidence_path)
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(tampered)
    assert caught.value.code == "B19V5X_E_TIMELINE"


def test_validator_rejects_49_rows_even_with_rehashed_manifest(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    tampered = mutable_copy(output, tmp_path / "rows49")
    csv_path = tampered / acquisition.CSV_NAME
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    csv_path.write_bytes(acquisition.csv_bytes(rows[:-1]))
    manifest_path = tampered / acquisition.MANIFEST_NAME
    manifest = acquisition.read_json(manifest_path)
    manifest["artifact_sha256"] = acquisition.sha256(csv_path)
    manifest["row_count"] = 49
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(tampered)
    assert caught.value.code == "B19V5X_E_EXACT50_SCOPE"


def test_validator_rejects_calendar_fork_and_evidence_tamper(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    forked = mutable_copy(output, tmp_path / "calendar_fork")
    calendar_path = forked / acquisition.CALENDAR_NAME
    dates = accumulator.calendar_dates(calendar_path)
    dates[-2] = "2026-09-15"
    calendar_path.write_text("\n".join(dates) + "\n", encoding="ascii")
    manifest_path = forked / acquisition.MANIFEST_NAME
    manifest = acquisition.read_json(manifest_path)
    manifest["current_calendar_sha256"] = acquisition.sha256(calendar_path)
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(forked)
    assert caught.value.code == "B19V5X_E_CALENDAR_EXTENSION"

    evidence = mutable_copy(output, tmp_path / "evidence_tamper")
    raw_path = next((evidence / "raw").iterdir())
    raw_path.write_bytes(raw_path.read_bytes() + b"\n")
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(evidence)
    assert caught.value.code == "B19V5X_E_ATTEMPT_INVENTORY"


@pytest.mark.parametrize("replacement", ["equal", "skip"])
def test_validator_requires_strict_next_day_calendar_extension(
    candidate, tmp_path: Path, replacement: str
) -> None:
    output, _, _ = candidate
    tampered = mutable_copy(output, tmp_path / replacement)
    source = acquisition.load_source_signal(acquisition.DEFAULT_ACCUMULATOR)
    dates = list(source["calendar_dates"])
    if replacement == "skip":
        dates.append("2026-09-18")
    calendar_path = tampered / acquisition.CALENDAR_NAME
    calendar_path.write_text("\n".join(dates) + "\n", encoding="ascii")
    manifest_path = tampered / acquisition.MANIFEST_NAME
    manifest = acquisition.read_json(manifest_path)
    manifest["current_calendar_sha256"] = acquisition.sha256(calendar_path)
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(tampered)
    assert caught.value.code == "B19V5X_E_CALENDAR_EXTENSION"


def test_validator_recomputes_selected_raw_after_hash_updates(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    tampered = mutable_copy(output, tmp_path / "raw_rehashed")
    manifest_path = tampered / acquisition.MANIFEST_NAME
    manifest = acquisition.read_json(manifest_path)
    selected = next(item for item in manifest["attempts"] if item.get("selected") is True)
    raw_path = tampered / selected["raw"]
    raw = json.loads(raw_path.read_bytes())
    raw["chart"]["result"][0]["indicators"]["quote"][0]["open"][0] += 10.0
    raw_path.write_text(json.dumps(raw, separators=(",", ":")), encoding="utf-8")
    selected["raw_sha256"] = acquisition.sha256(raw_path)
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(tampered)
    assert caught.value.code == "B19V5X_E_SELECTED_RAW_BINDING"


def test_validator_rejects_rehashed_request_time_tamper(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    tampered = mutable_copy(output, tmp_path / "request_time")
    manifest_path = tampered / acquisition.MANIFEST_NAME
    manifest = acquisition.read_json(manifest_path)
    attempt = manifest["attempts"][0]
    request_path = tampered / attempt["request"]
    request = acquisition.read_json(request_path)
    request["started_at"] = "2026-09-17T04:00:00+00:00"
    acquisition.write_json(request_path, request)
    attempt["request_started_at"] = request["started_at"]
    attempt["request_sha256"] = acquisition.sha256(request_path)
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(tampered)
    assert caught.value.code == "B19V5X_E_TIMELINE"


def test_validator_rejects_rehashed_cross_attempt_time_reversal(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    tampered = mutable_copy(output, tmp_path / "cross_attempt_time")
    manifest_path = tampered / acquisition.MANIFEST_NAME
    manifest = acquisition.read_json(manifest_path)
    prior = manifest["attempts"][0]
    later = manifest["attempts"][1]
    assert prior["instrument"] == later["instrument"] == "TW1303"
    assert prior["fetched_at"] < later["request_started_at"]
    reversed_start = "2026-09-17T06:00:00.001500+00:00"
    assert manifest["started_at"] < reversed_start < prior["fetched_at"] < later["fetched_at"]
    request_path = tampered / later["request"]
    request = acquisition.read_json(request_path)
    request["started_at"] = reversed_start
    acquisition.write_json(request_path, request)
    later["request_started_at"] = reversed_start
    later["request_sha256"] = acquisition.sha256(request_path)
    acquisition.write_json(manifest_path, manifest)
    with pytest.raises(acquisition.AcquisitionError) as caught:
        acquisition.validate_candidate(tampered)
    assert caught.value.code == "B19V5X_E_TIMELINE"


def test_settle_rejects_legacy_minimal_manifest_before_ledger_write(candidate, tmp_path: Path) -> None:
    output, _, _ = candidate
    legacy = tmp_path / "legacy.json"
    artifact = output / acquisition.CSV_NAME
    acquisition.write_json(
        legacy,
        {
            "artifact_sha256": acquisition.sha256(artifact),
            "execution_date": acquisition.EXECUTION_DATE,
            "available_at": "2026-09-17T06:00:00+00:00",
        },
    )
    ledger_path = acquisition.DEFAULT_ACCUMULATOR / "events.jsonl"
    before = acquisition.sha256(ledger_path)
    args = argparse.Namespace(
        out=str(acquisition.DEFAULT_ACCUMULATOR),
        asof=acquisition.SIGNAL_ASOF,
        prices=str(artifact),
        prices_manifest=str(legacy),
        calendar=str(output / acquisition.CALENDAR_NAME),
    )
    with pytest.raises(accumulator.ContractError) as caught:
        accumulator.settle_execution(args)
    assert caught.value.code == "B19V5_E_EXECUTION_MANIFEST_SCHEMA"
    assert acquisition.sha256(ledger_path) == before
    assert len(accumulator.load_events(ledger_path)) == 1


def test_settle_rejects_strong_candidate_without_independent_execution_review(candidate) -> None:
    output, _, _ = candidate
    artifact = output / acquisition.CSV_NAME
    manifest = output / acquisition.MANIFEST_NAME
    ledger_path = acquisition.DEFAULT_ACCUMULATOR / "events.jsonl"
    before = acquisition.sha256(ledger_path)
    args = argparse.Namespace(
        out=str(acquisition.DEFAULT_ACCUMULATOR),
        asof=acquisition.SIGNAL_ASOF,
        prices=str(artifact),
        prices_manifest=str(manifest),
        calendar=str(output / acquisition.CALENDAR_NAME),
        execution_review="",
    )
    with pytest.raises(accumulator.ContractError) as caught:
        accumulator.settle_execution(args)
    assert caught.value.code == "B19V5_E_EXECUTION_REVIEW_REQUIRED"
    assert acquisition.sha256(ledger_path) == before
    assert len(accumulator.load_events(ledger_path)) == 1


def test_execution_review_binding_accepts_exact_candidate_and_implementation(
    candidate, tmp_path: Path
) -> None:
    output, manifest, _ = candidate
    artifact = output / acquisition.CSV_NAME
    manifest_path = output / acquisition.MANIFEST_NAME
    calendar = output / acquisition.CALENDAR_NAME
    signal = acquisition.load_source_signal(acquisition.DEFAULT_ACCUMULATOR)["event"]
    validator_path = ROOT / "scripts/validate_modelb_b19r2r_v5_prospective_accumulator.py"
    review = {
        "schema_version": "modelb_b19r2r.v5.execution_outcome_independent_review.v1",
        "verdict": "PASS",
        "reviewed_candidate": {
            "manifest": accumulator.relative(manifest_path),
            "manifest_sha256": acquisition.sha256(manifest_path),
            "artifact": accumulator.relative(artifact),
            "artifact_sha256": acquisition.sha256(artifact),
            "current_calendar": accumulator.relative(calendar),
            "current_calendar_sha256": acquisition.sha256(calendar),
            "source_run_id": manifest["source_run_id"],
            "source_signal_event_hash": signal["event_hash"],
            "source_signal_run_id": signal["source_run_id"],
            "source_ledger_sha256": manifest["source_ledger_sha256"],
        },
        "reviewed_implementation": {
            "acquisition_sha256": acquisition.sha256(Path(acquisition.__file__)),
            "accumulator_sha256": acquisition.sha256(Path(accumulator.__file__)),
            "accumulator_validator_sha256": acquisition.sha256(validator_path),
        },
        "authorization": {
            "authorized_asof": acquisition.SIGNAL_ASOF,
            "authorized_event_type": "EXECUTION_SETTLED",
            "maximum_new_events": 1,
            "execution_settlement_authorized": True,
            "accepted_ledger_append_authorized": True,
            "accepted_ledger_event_written": False,
            "label_maturation_authorized": False,
            "production_change_authorized": False,
        },
    }
    review_path = tmp_path / "review.json"
    acquisition.write_json(review_path, review)

    assert accumulator.execution_review_binding(
        review_path,
        manifest_path=manifest_path,
        artifact=artifact,
        calendar=calendar,
        signal=signal,
        acquisition_implementation=Path(acquisition.__file__),
    )["verdict"] == "PASS"

    review["reviewed_candidate"]["source_run_id"] = signal["source_run_id"]
    acquisition.write_json(review_path, review)
    with pytest.raises(accumulator.ContractError) as caught:
        accumulator.execution_review_binding(
            review_path,
            manifest_path=manifest_path,
            artifact=artifact,
            calendar=calendar,
            signal=signal,
            acquisition_implementation=Path(acquisition.__file__),
        )
    assert caught.value.code == "B19V5_E_EXECUTION_REVIEW"
