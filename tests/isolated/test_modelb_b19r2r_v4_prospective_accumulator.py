from __future__ import annotations

import csv
import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_modelb_b19r2r_v4_prospective_accumulator as ledger  # noqa: E402
import materialize_modelb_b19r2r_v4_bundle_20260916 as materializer  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def manifests_for(
    *,
    logical_id: str,
    inventory: Path,
    composite: Path,
    review: Path,
    calendar: Path,
) -> list[dict[str, object]]:
    shared = {
        "asof": materializer.ASOF,
        "source_run_id": logical_id,
        "logical_source_run_id": logical_id,
        "decision_cutoff": materializer.CUTOFF,
        "available_at": "2026-09-16T18:29:00.785090+00:00",
        "pit_status": "PASS",
        "child_inventory": str(inventory),
        "child_inventory_sha256": ledger.sha256(inventory),
        "composite_manifest": str(composite),
        "composite_manifest_sha256": ledger.sha256(composite),
        "composite_independent_review": str(review),
        "composite_independent_review_sha256": ledger.sha256(review),
        "extended_clean_calendar": str(calendar),
        "extended_clean_calendar_sha256": ledger.sha256(calendar),
        "production_allowed": False,
    }
    return [
        {**shared, "schema_version": "exact", "model_id": ledger.MODEL_A_ID},
        {**shared, "schema_version": "features", "feature_columns": [f"f{i}" for i in range(78)]},
        {
            **shared,
            "schema_version": "scores",
            "model_id": ledger.MODEL_ID,
            "model_sha256": ledger.MODEL_SHA256,
            "candidate_id": ledger.CANDIDATE_ID,
            "feature_count": ledger.FEATURE_COUNT,
        },
    ]


def rewired_composite(tmp_path: Path, mutate=None) -> list[dict[str, object]]:
    inventory = json.loads(materializer.CHILD_INVENTORY.read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(inventory)
    inventory_path = tmp_path / "inventory.json"
    write_json(inventory_path, inventory)
    inventory_sha = ledger.sha256(inventory_path)
    logical_id = f"research.logical_composite.20260916.{inventory_sha[:20]}"

    calendar_path = tmp_path / "calendar.txt"
    calendar_path.write_bytes(materializer.EXTENDED_CALENDAR.read_bytes())
    composite = json.loads(materializer.COMPOSITE_MANIFEST.read_text(encoding="utf-8"))
    composite["logical_source_run_id"] = logical_id
    composite["child_inventory_sha256"] = inventory_sha
    composite["child_inventory"] = {
        "path": str(inventory_path), "sha256": inventory_sha, "bytes": inventory_path.stat().st_size,
    }
    composite["calendar_binding"]["extended_calendar"] = {
        "path": str(calendar_path),
        "sha256": ledger.sha256(calendar_path),
        "bytes": calendar_path.stat().st_size,
    }
    composite_path = tmp_path / "composite.json"
    write_json(composite_path, composite)

    review = json.loads(materializer.COMPOSITE_REVIEW.read_text(encoding="utf-8"))
    reviewed = review["reviewed_candidate"]
    reviewed["logical_source_run_id"] = logical_id
    reviewed["child_inventory_sha256"] = inventory_sha
    reviewed["manifest_sha256"] = ledger.sha256(composite_path)
    reviewed["extended_calendar_sha256"] = ledger.sha256(calendar_path)
    review_path = tmp_path / "review.json"
    write_json(review_path, review)
    return manifests_for(
        logical_id=logical_id,
        inventory=inventory_path,
        composite=composite_path,
        review=review_path,
        calendar=calendar_path,
    )


def test_real_logical_composite_binding_passes() -> None:
    manifests = manifests_for(
        logical_id=materializer.SOURCE_RUN,
        inventory=materializer.CHILD_INVENTORY,
        composite=materializer.COMPOSITE_MANIFEST,
        review=materializer.COMPOSITE_REVIEW,
        calendar=materializer.EXTENDED_CALENDAR,
    )
    value = ledger.deep_composite_binding(manifests)
    assert value["inventory_sha256"] == materializer.CHILD_INVENTORY_SHA


def test_run_id_string_without_composite_artifacts_is_rejected() -> None:
    manifests = [{"logical_source_run_id": materializer.SOURCE_RUN, "decision_cutoff": materializer.CUTOFF}] * 3
    with pytest.raises(ledger.ContractError) as caught:
        ledger.deep_composite_binding(manifests)
    assert caught.value.code == "B19V4_E_COMPOSITE_ARTIFACT_HASH"


def test_different_manifest_digest_is_rejected() -> None:
    manifests = manifests_for(
        logical_id=materializer.SOURCE_RUN,
        inventory=materializer.CHILD_INVENTORY,
        composite=materializer.COMPOSITE_MANIFEST,
        review=materializer.COMPOSITE_REVIEW,
        calendar=materializer.EXTENDED_CALENDAR,
    )
    manifests[2] = copy.deepcopy(manifests[2])
    manifests[2]["child_inventory_sha256"] = "0" * 64
    with pytest.raises(ledger.ContractError) as caught:
        ledger.deep_composite_binding(manifests)
    assert caught.value.code == "B19V4_E_COMPOSITE_DIGEST_MISMATCH"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda value: value["children"][0].update({"role": "wrong"}), "B19V4_E_COMPOSITE_CONTRACT"),
        (lambda value: value["children"][0].update({"asof": "2026-09-15"}), "B19V4_E_CHILD_PIT"),
        (
            lambda value: value["children"][0].update({"available_at": "2026-09-17T02:00:00+00:00"}),
            "B19V4_E_CHILD_PIT",
        ),
        (
            lambda value: value["children"][0]["normalized_artifact"].update({"sha256": "0" * 64}),
            "B19V4_E_CHILD_ARTIFACT_HASH",
        ),
    ],
)
def test_deep_inventory_mutations_are_rejected(tmp_path: Path, mutate, code: str) -> None:
    manifests = rewired_composite(tmp_path, mutate)
    with pytest.raises(ledger.ContractError) as caught:
        ledger.deep_composite_binding(manifests)
    assert caught.value.code == code


def test_nonfinite_feature_and_tw7769_are_rejected(tmp_path: Path) -> None:
    feature_path = tmp_path / "features.csv"
    columns = [f"f{i}" for i in range(78)]
    rows = [{"date": materializer.ASOF, "instrument": f"TW{1000 + i}", **{name: 1 for name in columns}} for i in range(50)]
    rows[0]["f0"] = "nan"
    write_csv(feature_path, rows)
    with pytest.raises(ledger.ContractError) as finite:
        ledger.feature_rows(feature_path, {"feature_columns": columns}, materializer.ASOF, {row["instrument"] for row in rows})
    assert finite.value.code == "B19V3_E_78F_FINITE"

    exact_path = tmp_path / "exact.csv"
    exact = [{"date": materializer.ASOF, "instrument": f"TW{1000 + i}", "rank": i + 1} for i in range(50)]
    exact[0]["instrument"] = "TW7769"
    write_csv(exact_path, exact)
    with pytest.raises(ledger.ContractError) as excluded:
        ledger.exact_rows(exact_path, materializer.ASOF)
    assert excluded.value.code == "B19V3_E_TW7769_EXCLUDED"


def test_precapture_review_requires_explicit_capture_authorization(tmp_path: Path) -> None:
    artifacts = []
    manifests = []
    for index, schema in enumerate(("exact", "features", "scores")):
        artifact = tmp_path / f"artifact{index}.csv"
        artifact.write_text("x\n", encoding="ascii")
        artifacts.append(artifact)
        manifests.append({
            "schema_version": schema,
            "artifact_sha256": ledger.sha256(artifact),
            "logical_source_run_id": materializer.SOURCE_RUN,
        })
    review = {
        "verdict": "PASS",
        "reviewed_candidate": {
            "logical_source_run_id": materializer.SOURCE_RUN,
            "artifact_hashes": {ledger.relative(path): ledger.sha256(path) for path in artifacts},
            "manifest_artifact_hashes": {item["schema_version"]: item["artifact_sha256"] for item in manifests},
        },
        "authorization": {
            "signal_capture_authorized": False,
            "accepted_ledger_append_authorized": False,
            "accepted_ledger_event_written": False,
        },
    }
    review_path = tmp_path / "review.json"
    write_json(review_path, review)
    with pytest.raises(ledger.ContractError) as caught:
        ledger.precapture_review_binding(review_path, manifests, artifacts)
    assert caught.value.code == "B19V4_E_PRECAPTURE_REVIEW"
