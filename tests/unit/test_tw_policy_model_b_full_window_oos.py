from __future__ import annotations

import copy
import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_tw_policy_model_b_full_window_oos as mboos


class FakeBackend:
    def __init__(self):
        self.fit_calls = 0
        self.predict_calls = 0

    def fit(self, rows, features, label, groups, config):
        self.fit_calls += 1
        assert config == mboos.FIXED_MODEL_CONFIG
        return {"synthetic": True, "features": list(features)}

    def predict(self, model, rows, features):
        self.predict_calls += 1
        return [1.0 for _ in rows]

    def model_bytes(self, model):
        return json.dumps(model, sort_keys=True).encode()


class SpyBackend(FakeBackend):
    def __init__(self):
        super().__init__()
        self.visible_rows = []

    def fit(self, rows, features, label, groups, config):
        self.visible_rows.extend(copy.deepcopy(rows))
        return super().fit(rows, features, label, groups, config)

    def predict(self, model, rows, features):
        self.visible_rows.extend(copy.deepcopy(rows))
        return super().predict(model, rows, features)


@pytest.fixture
def features():
    return [f"feature_{i:02d}" for i in range(78)]


@pytest.fixture
def synthetic_case(features):
    calendar = [(date(2098, 1, 1) + timedelta(days=i)).isoformat() for i in range(380)]
    fit_dates = calendar[:200]
    validation_dates = calendar[200:240]
    purge_dates = calendar[240:250]
    score_date = calendar[250]
    fold = {
        "fold_id": "MBOOS_SYNTHETIC",
        "fit_start": fit_dates[0], "fit_end": fit_dates[-1],
        "validation_start": validation_dates[0], "validation_end": validation_dates[-1],
        "label_maturity_cutoff": validation_dates[-1],
        "purge_start": purge_dates[0], "purge_end": purge_dates[-1],
        "score_start": score_date, "score_end": score_date,
        "synthetic_expected_dates": {
            "fit": fit_dates[:2],
            "validation": validation_dates[:1],
            "score": [score_date],
        },
    }

    def row(day, rank, *, label=True):
        value = {
            "date": day,
            "instrument": f"TW{rank:04d}",
            "qlib_rank": rank,
            "same_e1_frozen_qlib_score_source": True,
            "after_qlib_train_end": True,
            "score_source": mboos.EXPECTED_SCORE_SOURCE,
            "institutional_flow_available_at": day,
            "margin_short_available_at": day,
            **{feature: float(rank) for feature in features},
        }
        if label:
            value[mboos.LABEL_COLUMN] = rank % 5
        return value

    fit = [row(day, rank) for day in fit_dates[:2] for rank in range(1, 51)]
    validation = [row(validation_dates[0], rank) for rank in range(1, 51)]
    score = [row(score_date, rank, label=False) for rank in range(1, 51)]
    return fold, calendar, fit, validation, score


def assert_code(code, function, *args, **kwargs):
    with pytest.raises(mboos.ContractError) as captured:
        function(*args, **kwargs)
    assert captured.value.code == code


def test_frozen_30_fold_plan_and_feature_config_pass():
    rows = mboos.validate_fold_plan()
    names, semantic_hash = mboos.feature_contract()
    assert len(rows) == 30 and rows[0]["fold_id"] == "MBOOS_F12" and rows[-1]["fold_id"] == "MBOOS_F41"
    assert all(int(row["validation_dates"]) == 40 and int(row["purge_dates"]) == 10 for row in rows)
    assert len(names) == 78 and semantic_hash == mboos.EXPECTED_FEATURE_HASH
    assert mboos.validate_frozen_config() == mboos.canonical_sha256(mboos.FIXED_MODEL_CONFIG)


def test_preflight_does_not_fit_or_read_real_e2(monkeypatch, tmp_path):
    monkeypatch.setattr(mboos, "OUT_DIR", tmp_path)
    monkeypatch.setattr(mboos, "protected_fingerprints", lambda: {"protected": "same"})
    manifest = mboos.preflight(tmp_path)
    assert manifest["real_e2_payload_read"] is False
    assert manifest["training_performed"] is False and manifest["scoring_performed"] is False
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "execution_report.md", "fold_contract_audit.csv", "forbidden_scope_audit.json",
        "preflight_manifest.json", "synthetic_test_evidence.json",
    ]


def test_synthetic_orchestration_deterministic_ties_and_payload(synthetic_case, features):
    fold, calendar, fit, validation, score = synthetic_case
    backend = FakeBackend()
    first = mboos.run_synthetic_fold(fold=fold, fit_rows=fit, validation_rows=validation, score_rows=score, trading_dates=calendar, features=features, backend=backend)
    second = mboos.run_synthetic_fold(fold=fold, fit_rows=fit, validation_rows=validation, score_rows=list(reversed(score)), trading_dates=calendar, features=features, backend=backend)
    assert first == second
    assert [row["instrument"] for row in first] == [f"TW{i:04d}" for i in range(1, 51)]
    assert set(first[0]) == set(mboos.SCORE_PAYLOAD_FIELDS)
    assert backend.fit_calls == backend.predict_calls == 2


def test_parameter_override_rejected():
    bad = dict(mboos.FIXED_MODEL_CONFIG, n_estimators=121)
    assert_code("MBOOS_E_PARAMETER_OVERRIDE", mboos.validate_frozen_config, bad)


def test_feature_hash_drift_rejected(monkeypatch):
    monkeypatch.setattr(mboos, "EXPECTED_FEATURE_HASH", "0" * 64)
    assert_code("MBOOS_E_FEATURE_HASH", mboos.feature_contract)


def test_real_run_requires_future_exact_authorization(monkeypatch):
    accessed = False
    original = Path.open

    def guarded(self, *args, **kwargs):
        nonlocal accessed
        if "phasee2_ltr_" in self.name:
            accessed = True
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    assert_code("MBOOS_E_REAL_AUTHORIZATION", mboos.main, ["--execute-real", "--authorization-id", "anything"])
    assert accessed is False


def test_real_gate_precedes_payload_even_if_future_constant_is_injected(monkeypatch):
    accessed = False
    original = Path.open

    def guarded(self, *args, **kwargs):
        nonlocal accessed
        if "phasee2_ltr_" in self.name:
            accessed = True
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    monkeypatch.setattr(mboos, "MBOOS2_EXACT_AUTHORIZATION_ID", "review-probe")
    assert_code("MBOOS_E_REAL_NOT_IMPLEMENTED", mboos.main, ["--execute-real", "--authorization-id", "review-probe"])
    assert accessed is False


def test_environment_cannot_install_real_authorization(monkeypatch):
    monkeypatch.setenv("MBOOS2_EXACT_AUTHORIZATION_ID", "env-probe")
    assert_code("MBOOS_E_REAL_AUTHORIZATION", mboos.main, ["--execute-real", "--authorization-id", "env-probe"])


def test_preflight_rejects_non_exact_output_root(monkeypatch, tmp_path):
    exact = tmp_path / "exact"
    monkeypatch.setattr(mboos, "OUT_DIR", exact)
    assert_code("MBOOS_E_OUTPUT_ESCAPE", mboos.preflight, tmp_path / "other")


@pytest.mark.parametrize("field,value,code", [
    ("margin_short_available_at", "", "MBOOS_E_AVAILABILITY_NULL"),
    ("institutional_flow_available_at", "2099-12-31", "MBOOS_E_AVAILABILITY_LATE"),
    ("score_source", "wrong", "MBOOS_E_LINEAGE"),
    ("same_e1_frozen_qlib_score_source", False, "MBOOS_E_LINEAGE"),
    ("qlib_rank", 151, "MBOOS_E_UNIVERSE"),
    ("instrument", "2330", "MBOOS_E_UNIVERSE"),
])
def test_fail_closed_row_contract(synthetic_case, features, field, value, code):
    fold, calendar, _, _, score = synthetic_case
    broken = copy.deepcopy(score)
    broken[0][field] = value
    assert_code(code, mboos.validate_input_rows, broken, features=features, fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)


def test_wrong_feature_count_and_nonfinite(synthetic_case, features):
    fold, calendar, _, _, score = synthetic_case
    assert_code("MBOOS_E_REQUIRED_COLUMN", mboos.validate_input_rows, score, features=features + ["extra"], fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)
    broken = copy.deepcopy(score)
    broken[0][features[0]] = float("inf")
    assert_code("MBOOS_E_FEATURE_NON_FINITE", mboos.validate_input_rows, broken, features=features, fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)


def test_duplicate_and_incomplete_top50_rejected(synthetic_case, features):
    fold, calendar, _, _, score = synthetic_case
    assert_code("MBOOS_E_DUPLICATE_KEY", mboos.validate_input_rows, score + [score[0]], features=features, fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)
    assert_code("MBOOS_E_INCOMPLETE_TOP50", mboos.validate_input_rows, score[:-1], features=features, fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)


def test_label_maturity_and_overlap_rejected(synthetic_case, features):
    fold, calendar, fit, validation, score = synthetic_case
    immature = copy.deepcopy(fit)
    immature[0]["date"] = fold["validation_end"]
    immature[0]["institutional_flow_available_at"] = fold["validation_end"]
    immature[0]["margin_short_available_at"] = fold["validation_end"]
    assert_code("MBOOS_E_SPLIT_RANGE", mboos.validate_input_rows, immature, features=features, fold=fold, split="fit", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)
    overlap = copy.deepcopy(score)
    overlap[0]["date"] = fold["fit_start"]
    assert_code("MBOOS_E_SPLIT_RANGE", mboos.validate_input_rows, overlap, features=features, fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)

    immature_fold = dict(fold, label_maturity_cutoff=fold["validation_start"])
    assert_code("MBOOS_E_LABEL_MATURITY", mboos.validate_input_rows, validation, features=features, fold=immature_fold, split="validation", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)


def test_fold_interval_overlap_rejected(monkeypatch, tmp_path):
    rows = mboos.load_csv(mboos.FOLD_PLAN)
    rows[0]["validation_start"] = rows[0]["fit_end"]
    path = tmp_path / "overlap.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mboos.FOLD_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(mboos, "MBOOS0_FOLD_PLAN", path)
    monkeypatch.setattr(mboos, "EXPECTED_MBOOS0_FOLD_PLAN_SHA256", mboos.sha256_file(path))
    assert_code("MBOOS_E_OVERLAP", mboos.validate_fold_plan, path)


def test_future_and_private_payload_fields_rejected(synthetic_case, features):
    fold, calendar, fit, validation, score = synthetic_case
    output = mboos.run_synthetic_fold(fold=fold, fit_rows=fit, validation_rows=validation, score_rows=score, trading_dates=calendar, features=features, backend=FakeBackend())
    for field in ("future_return_10d", "label_hidden", "private_note"):
        broken = copy.deepcopy(output)
        broken[0][field] = 1
        assert_code("MBOOS_E_FORBIDDEN_PAYLOAD_FIELD", mboos.validate_score_payload, broken, fold=fold, expected_dates=fold["synthetic_expected_dates"]["score"], expected_model_sha256=output[0]["model_sha256"], synthetic=True)


def test_atomic_output_escape_and_protected_path_rejected(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    mboos.atomic_write(allowed / "ok.json", b"ok", allowed_root=allowed)
    assert (allowed / "ok.json").read_bytes() == b"ok"
    assert (allowed / "ok.json").stat().st_mode & 0o777 == 0o644
    assert_code("MBOOS_E_OUTPUT_ESCAPE", mboos.atomic_write, tmp_path / "escape.json", b"bad", allowed_root=allowed)
    protected = ROOT / mboos.PROTECTED_8[0]
    assert_code("MBOOS_E_OUTPUT_ESCAPE", mboos.atomic_write, protected, b"bad", allowed_root=allowed)


def test_cli_defaults_to_preflight(monkeypatch):
    called = []
    monkeypatch.setattr(mboos, "preflight", lambda: called.append(True) or {"status": "IMPLEMENTATION_COMPLETE_PENDING_INDEPENDENT_REVIEW"})
    monkeypatch.setattr(mboos, "OUT_DIR", mboos.ROOT / "synthetic-output")
    assert mboos.main([]) == 0
    assert called == [True]


def test_payload_duplicate_and_late_available_rejected(synthetic_case, features):
    fold, calendar, fit, validation, score = synthetic_case
    output = mboos.run_synthetic_fold(fold=fold, fit_rows=fit, validation_rows=validation, score_rows=score, trading_dates=calendar, features=features, backend=FakeBackend())
    kwargs = dict(fold=fold, expected_dates=fold["synthetic_expected_dates"]["score"], expected_model_sha256=output[0]["model_sha256"], synthetic=True)
    assert_code("MBOOS_E_DUPLICATE_KEY", mboos.validate_score_payload, output + [output[0]], **kwargs)
    late = copy.deepcopy(output)
    late[0]["available_at"] = "2099-12-31"
    assert_code("MBOOS_E_AVAILABILITY_LATE", mboos.validate_score_payload, late, **kwargs)


def test_strict_real_exact_calendar_group_row_and_top50_closure(synthetic_case, features):
    fold, calendar, _, _, score = synthetic_case
    second_day = calendar[251]
    strict_fold = dict(fold, fold_id="MBOOS_FXX", score_end=second_day, score_dates="2", score_rows="100")
    strict_fold.pop("synthetic_expected_dates")
    assert_code("MBOOS_E_DATE_SET_CLOSURE", mboos.validate_input_rows, score, features=features, fold=strict_fold, split="score", trading_dates=calendar, mode=mboos.InputMode.STRICT_REAL)
    complete = score + [{**row, "date": second_day, "institutional_flow_available_at": second_day, "margin_short_available_at": second_day} for row in score]
    clean = mboos.validate_input_rows(complete, features=features, fold=strict_fold, split="score", trading_dates=calendar, mode=mboos.InputMode.STRICT_REAL)
    assert len(clean) == 100
    assert_code("MBOOS_E_ROW_COUNT_CLOSURE", mboos.validate_input_rows, complete[:-1], features=features, fold=strict_fold, split="score", trading_dates=calendar, mode=mboos.InputMode.STRICT_REAL)


def test_synthetic_and_strict_real_modes_cannot_mix(synthetic_case, features):
    fold, calendar, _, _, score = synthetic_case
    assert_code("MBOOS_E_SYNTHETIC_MODE", mboos.validate_input_rows, score, features=features, fold=fold, split="score", trading_dates=calendar, mode=mboos.InputMode.STRICT_REAL)
    real_fold = dict(fold, fold_id="MBOOS_FXX")
    assert_code("MBOOS_E_SYNTHETIC_MODE", mboos.validate_input_rows, score, features=features, fold=real_fold, split="score", trading_dates=calendar, mode=mboos.InputMode.SYNTHETIC_TINY)
    assert_code("MBOOS_E_INPUT_MODE", mboos.validate_input_rows, score, features=features, fold=fold, split="score", trading_dates=calendar, mode="synthetic_tiny")


def test_backend_receives_exact_projection_without_extras(synthetic_case, features):
    fold, calendar, fit, validation, score = synthetic_case
    for rows in (fit, validation, score):
        for row in rows:
            row.update({"future_return_10d": 99, "private_note": "secret", "order_qty": 10, "target_weight": 1})
    backend = SpyBackend()
    mboos.run_synthetic_fold(fold=fold, fit_rows=fit, validation_rows=validation, score_rows=score, trading_dates=calendar, features=features, backend=backend)
    allowed_fit = {"date", "instrument", mboos.LABEL_COLUMN, *features}
    allowed_score = {"date", "instrument", *features}
    assert all(set(row) in (allowed_fit, allowed_score) for row in backend.visible_rows)
    assert not any(any(token in field for token in ("future", "private", "order", "target")) for row in backend.visible_rows for field in row)


@pytest.mark.parametrize("mutation,code", [
    ({"score_rank": 2}, "MBOOS_E_SCORE_RANK"),
    ({"qlib_rank": 2}, "MBOOS_E_QLIB_RANK"),
    ({"signal_asof": "2099-01-01"}, "MBOOS_E_SIGNAL_DATE"),
    ({"fold_id": "wrong"}, "MBOOS_E_PAYLOAD_IDENTITY"),
    ({"feature_hash": "0" * 64}, "MBOOS_E_PAYLOAD_IDENTITY"),
    ({"model_sha256": "0" * 64}, "MBOOS_E_PAYLOAD_IDENTITY"),
    ({"raw_score": float("inf")}, "MBOOS_E_PREDICTION"),
])
def test_score_payload_identity_and_numeric_closure(synthetic_case, features, mutation, code):
    fold, calendar, fit, validation, score = synthetic_case
    output = mboos.run_synthetic_fold(fold=fold, fit_rows=fit, validation_rows=validation, score_rows=score, trading_dates=calendar, features=features, backend=FakeBackend())
    broken = copy.deepcopy(output)
    broken[0].update(mutation)
    assert_code(code, mboos.validate_score_payload, broken, fold=fold, expected_dates=fold["synthetic_expected_dates"]["score"], expected_model_sha256=output[0]["model_sha256"], synthetic=True)


def test_atomic_rejects_root_and_nested_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root_link = tmp_path / "root-link"
    root_link.symlink_to(outside, target_is_directory=True)
    assert_code("MBOOS_E_OUTPUT_SYMLINK", mboos.atomic_write, root_link / "escape", b"bad", allowed_root=root_link)
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "nested").symlink_to(outside, target_is_directory=True)
    assert_code("MBOOS_E_OUTPUT_SYMLINK", mboos.atomic_write, allowed / "nested" / "escape", b"bad", allowed_root=allowed)
    assert not (outside / "escape").exists()
    target = allowed / "target"
    target.symlink_to(outside / "target")
    assert_code("MBOOS_E_OUTPUT_SYMLINK", mboos.atomic_write, target, b"bad", allowed_root=allowed)
    assert not (outside / "target").exists()


def test_atomic_detects_root_replacement_before_install(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    original = mboos._assert_bound_directory
    replaced = False

    def replace_then_assert(path, identity, code):
        nonlocal replaced
        if not replaced and path == allowed:
            replaced = True
            os.rename(allowed, tmp_path / "old-root")
            allowed.mkdir()
        return original(path, identity, code)

    monkeypatch.setattr(mboos, "_assert_bound_directory", replace_then_assert)
    assert_code("MBOOS_E_OUTPUT_ROOT_REPLACED", mboos.atomic_write, allowed / "result", b"bad", allowed_root=allowed)
    assert not (allowed / "result").exists()


def test_atomic_detects_nested_parent_replacement(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    parent = allowed / "nested"
    parent.mkdir(parents=True)
    original = mboos._assert_bound_directory
    replaced = False

    def replace_then_assert(path, identity, code):
        nonlocal replaced
        if not replaced and path == parent:
            replaced = True
            os.rename(parent, allowed / "old-parent")
            parent.mkdir()
        return original(path, identity, code)

    monkeypatch.setattr(mboos, "_assert_bound_directory", replace_then_assert)
    assert_code("MBOOS_E_OUTPUT_PARENT_REPLACED", mboos.atomic_write, parent / "result", b"bad", allowed_root=allowed)
    assert not (parent / "result").exists()


def _atomic_residuals(directory):
    return sorted(path.name for path in directory.iterdir() if path.name.endswith((".stage", ".rollback")))


def test_atomic_final_install_root_swap_removes_candidate_from_moved_root(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    moved = tmp_path / "moved-root"
    allowed.mkdir()
    original = os.replace
    swapped = False

    def swap_at_install(src, dst, *args, **kwargs):
        nonlocal swapped
        if not swapped and str(src).endswith(".stage") and dst == "result":
            swapped = True
            os.rename(allowed, moved)
            allowed.mkdir()
        return original(src, dst, *args, **kwargs)

    monkeypatch.setattr(mboos.os, "replace", swap_at_install)
    assert_code("MBOOS_E_OUTPUT_ROOT_REPLACED", mboos.atomic_write, allowed / "result", b"candidate", allowed_root=allowed)
    assert not (allowed / "result").exists()
    assert not (moved / "result").exists()
    assert _atomic_residuals(allowed) == _atomic_residuals(moved) == []


def test_atomic_final_install_parent_swap_restores_existing_target(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    parent = allowed / "nested"
    moved = allowed / "moved-parent"
    parent.mkdir(parents=True)
    target = parent / "result"
    target.write_bytes(b"before")
    before_inode = target.stat().st_ino
    original = os.replace
    swapped = False

    def swap_at_install(src, dst, *args, **kwargs):
        nonlocal swapped
        if not swapped and str(src).endswith(".stage") and dst == "result":
            swapped = True
            os.rename(parent, moved)
            parent.mkdir()
        return original(src, dst, *args, **kwargs)

    monkeypatch.setattr(mboos.os, "replace", swap_at_install)
    assert_code("MBOOS_E_OUTPUT_PARENT_REPLACED", mboos.atomic_write, target, b"candidate", allowed_root=allowed)
    assert not (parent / "result").exists()
    assert (moved / "result").read_bytes() == b"before"
    assert (moved / "result").stat().st_ino == before_inode
    assert _atomic_residuals(parent) == _atomic_residuals(moved) == []


def test_atomic_final_identity_mismatch_rolls_back_absent_target(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    original = mboos._entry_identity
    calls = 0

    def mismatch_after_install(name, parent_fd):
        nonlocal calls
        value = original(name, parent_fd)
        if name == "result":
            calls += 1
            if calls == 1:
                return (value[0], value[1] + 1, value[2], value[3])
        return value

    monkeypatch.setattr(mboos, "_entry_identity", mismatch_after_install)
    assert_code("MBOOS_E_OUTPUT_FINAL_IDENTITY", mboos.atomic_write, allowed / "result", b"candidate", allowed_root=allowed)
    assert not (allowed / "result").exists()
    assert _atomic_residuals(allowed) == []


def test_atomic_cleanup_failure_is_terminal_taint_and_retry_removes_payload(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    moved = tmp_path / "moved-root"
    allowed.mkdir()
    original_replace = os.replace
    original_unlink = os.unlink
    swapped = False
    failed_once = False

    def swap_at_install(src, dst, *args, **kwargs):
        nonlocal swapped
        if not swapped and str(src).endswith(".stage") and dst == "result":
            swapped = True
            os.rename(allowed, moved)
            allowed.mkdir()
        return original_replace(src, dst, *args, **kwargs)

    def fail_first_candidate_cleanup(path, *args, **kwargs):
        nonlocal failed_once
        if path == "result" and not failed_once:
            failed_once = True
            raise OSError("injected cleanup failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(mboos.os, "replace", swap_at_install)
    monkeypatch.setattr(mboos.os, "unlink", fail_first_candidate_cleanup)
    assert_code("MBOOS_E_OUTPUT_ROLLBACK_TAINT", mboos.atomic_write, allowed / "result", b"candidate", allowed_root=allowed)
    assert failed_once
    assert not (allowed / "result").exists() and not (moved / "result").exists()
    assert _atomic_residuals(allowed) == _atomic_residuals(moved) == []


def test_atomic_cleanup_failure_restores_existing_target_before_terminal_taint(monkeypatch, tmp_path):
    allowed = tmp_path / "allowed"
    moved = tmp_path / "moved-root"
    allowed.mkdir()
    target = allowed / "result"
    target.write_bytes(b"before")
    before_inode = target.stat().st_ino
    original_replace = os.replace
    original_unlink = os.unlink
    swapped = False
    failed_once = False

    def swap_at_install(src, dst, *args, **kwargs):
        nonlocal swapped
        if not swapped and str(src).endswith(".stage") and dst == "result":
            swapped = True
            os.rename(allowed, moved)
            allowed.mkdir()
        return original_replace(src, dst, *args, **kwargs)

    def fail_first_candidate_cleanup(path, *args, **kwargs):
        nonlocal failed_once
        if path == "result" and not failed_once:
            failed_once = True
            raise OSError("injected cleanup failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(mboos.os, "replace", swap_at_install)
    monkeypatch.setattr(mboos.os, "unlink", fail_first_candidate_cleanup)
    assert_code("MBOOS_E_OUTPUT_ROLLBACK_TAINT", mboos.atomic_write, target, b"candidate", allowed_root=allowed)
    assert not (allowed / "result").exists()
    assert (moved / "result").read_bytes() == b"before"
    assert (moved / "result").stat().st_ino == before_inode
    assert _atomic_residuals(allowed) == _atomic_residuals(moved) == []


def test_atomic_nominal_install_replaces_regular_target_without_residuals(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    target = allowed / "result"
    target.write_bytes(b"before")
    mboos.atomic_write(target, b"after", allowed_root=allowed)
    assert target.read_bytes() == b"after"
    assert target.stat().st_mode & 0o777 == 0o644
    assert _atomic_residuals(allowed) == []
