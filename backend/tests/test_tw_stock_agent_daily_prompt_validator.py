import json
import shutil
from pathlib import Path

from scripts.validate_tw_agent_daily_prompt_artifact import compute_checksum, validate_artifact


SAMPLE_ROOT = Path("data_tw/golden_samples/agent_daily_prompt")
APLR_CANDIDATE_ONLY_ROOT = Path("data_tw/artifacts/agent_daily_prompt/2026-07-08")


def test_validator_repo_relative_sources_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    from scripts import validate_tw_agent_daily_prompt_artifact as validator

    source = tmp_path / "data_tw" / "source.json"
    source.parent.mkdir()
    source.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.chdir(backend_dir)
    result = validator.ValidationResult()
    validator.validate_source_artifacts(result, artifact_dir, {"source": "data_tw/source.json"}, allow_golden_missing_sources=False)
    assert result.ok, result.errors
    source.unlink()
    missing = validator.ValidationResult()
    validator.validate_source_artifacts(missing, artifact_dir, {"source": "data_tw/source.json"}, allow_golden_missing_sources=False)
    assert not missing.ok


def _copy_pass_sample(tmp_path):
    sample = tmp_path / "sample"
    shutil.copytree(SAMPLE_ROOT / "pass", sample)
    return sample


def _copy_candidate_only_sample(tmp_path):
    sample = tmp_path / "candidate_only_sample"
    shutil.copytree(APLR_CANDIDATE_ONLY_ROOT, sample)
    return sample


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _refresh_checksum(sample):
    manifest_path = sample / "manifest.json"
    context_path = sample / "prompt_context.json"
    prompt_path = sample / "prompt_text.md"
    manifest = _read_json(manifest_path)
    manifest["checksum"] = compute_checksum(context_path.read_bytes(), prompt_path.read_bytes())
    _write_json(manifest_path, manifest)


def _set_context_path(payload, path, value):
    cursor = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value



def test_agent_daily_prompt_pass_sample_validates_in_strict_source_mode():
    result = validate_artifact(SAMPLE_ROOT / "pass")

    assert result.ok, result.errors


def test_agent_daily_prompt_missing_sources_require_explicit_golden_mode(tmp_path):
    sample = tmp_path / "sample"
    sample.mkdir()
    for name in ("manifest.json", "prompt_context.json", "prompt_text.md"):
        (sample / name).write_bytes((SAMPLE_ROOT / "pass" / name).read_bytes())
    manifest = sample / "manifest.json"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "\"source_stubs/current_strategy_context_stub.json\"",
            "{\"status\":\"missing_allowed_for_golden_sample\"}",
        ).replace(
            "\"source_stubs/readonly_strategy_snapshot_stub.json\"",
            "{\"status\":\"missing_allowed_for_golden_sample\"}",
        ),
        encoding="utf-8",
    )

    strict_result = validate_artifact(sample, allow_golden_missing_sources=False)
    golden_result = validate_artifact(sample, allow_golden_missing_sources=True)

    assert not strict_result.ok
    assert any("missing source allowed only" in error for error in strict_result.errors)
    assert golden_result.ok, golden_result.errors
    assert golden_result.warnings


def test_agent_daily_prompt_fail_samples_are_rejected():
    fail_dirs = [
        "fail_readonly_false",
        "fail_trade_enabled",
        "fail_wrong_model",
        "fail_wrong_strategy",
        "fail_wrong_execution_price",
        "fail_forbidden_action",
        "fail_monitor_write",
        "fail_checksum",
    ]

    for dirname in fail_dirs:
        result = validate_artifact(SAMPLE_ROOT / dirname, allow_golden_missing_sources=True)
        assert not result.ok, dirname


def test_agent_daily_prompt_forbidden_action_sample_hits_safety_audit():
    result = validate_artifact(SAMPLE_ROOT / "fail_forbidden_action", allow_golden_missing_sources=True)

    assert not result.ok
    assert any("forbidden action term" in error for error in result.errors)


def test_agent_daily_prompt_monitor_write_sample_hits_safety_audit():
    result = validate_artifact(SAMPLE_ROOT / "fail_monitor_write", allow_golden_missing_sources=True)

    assert not result.ok
    assert any("monitor" in error and "forbidden action term" in error for error in result.errors)


def test_agent_daily_prompt_rejects_english_place_order_in_context(tmp_path):
    sample = _copy_pass_sample(tmp_path)
    context_path = sample / "prompt_context.json"
    context = _read_json(context_path)
    _set_context_path(context, ("strategy", "notes"), "place order for 2330")
    _write_json(context_path, context)
    _refresh_checksum(sample)

    result = validate_artifact(sample)

    assert not result.ok
    assert any("place_order" in error or "order" in error for error in result.errors)


def test_agent_daily_prompt_rejects_english_submit_order_in_context(tmp_path):
    sample = _copy_pass_sample(tmp_path)
    context_path = sample / "prompt_context.json"
    context = _read_json(context_path)
    _set_context_path(context, ("strategy", "notes"), "submit order for 2330")
    _write_json(context_path, context)
    _refresh_checksum(sample)

    result = validate_artifact(sample)

    assert not result.ok
    assert any("submit_order" in error or "order" in error for error in result.errors)


def test_agent_daily_prompt_rejects_english_place_order_in_prompt_body(tmp_path):
    sample = _copy_pass_sample(tmp_path)
    prompt_path = sample / "prompt_text.md"
    prompt_path.write_text(prompt_path.read_text(encoding="utf-8") + "\nUse this artifact to place order for 2330.\n", encoding="utf-8")
    _refresh_checksum(sample)

    result = validate_artifact(sample)

    assert not result.ok
    assert any("prompt_text.md" in error and ("place_order" in error or "order" in error) for error in result.errors)


def test_agent_daily_prompt_allows_english_order_terms_in_safety_prompt_lines(tmp_path):
    sample = _copy_pass_sample(tmp_path)
    prompt_path = sample / "prompt_text.md"
    prompt_path.write_text(prompt_path.read_text(encoding="utf-8") + "\n不能 place order。\nDo not place order.\n", encoding="utf-8")
    _refresh_checksum(sample)

    result = validate_artifact(sample)

    assert result.ok, result.errors


def test_agent_daily_prompt_allows_english_order_terms_in_blocked_policy_fields(tmp_path):
    sample = _copy_pass_sample(tmp_path)
    context_path = sample / "prompt_context.json"
    context = _read_json(context_path)
    answer_policy = context.setdefault("answer_policy", {})
    answer_policy["blocked_question_types"] = list(answer_policy.get("blocked_question_types") or []) + ["place order"]
    answer_policy["forbidden_answer_semantics"] = ["submit order"]
    _write_json(context_path, context)
    _refresh_checksum(sample)

    result = validate_artifact(sample)

    assert result.ok, result.errors


def test_agent_daily_prompt_candidate_only_artifact_validates_in_strict_mode(tmp_path):
    sample = _copy_candidate_only_sample(tmp_path)

    result = validate_artifact(sample)

    assert result.ok, result.errors


def test_agent_daily_prompt_candidate_only_requires_explicit_snapshot_marker(tmp_path):
    sample = _copy_candidate_only_sample(tmp_path)
    context_path = sample / "prompt_context.json"
    context = _read_json(context_path)
    _set_context_path(context, ("strategy", "snapshot_candidate_only"), False)
    _write_json(context_path, context)
    _refresh_checksum(sample)

    result = validate_artifact(sample)

    assert not result.ok
    assert any("snapshot_candidate_only" in error for error in result.errors)


def test_agent_daily_prompt_candidate_only_still_rejects_unsafe_trade_terms(tmp_path):
    unsafe_lines = [
        "Use this artifact to place order for 2330.",
        "Set target_weight to 50% for 2330.",
        "Use target_position for 2330.",
    ]

    for index, line in enumerate(unsafe_lines):
        sample = _copy_candidate_only_sample(tmp_path / str(index))
        prompt_path = sample / "prompt_text.md"
        prompt_path.write_text(prompt_path.read_text(encoding="utf-8") + f"\n{line}\n", encoding="utf-8")
        _refresh_checksum(sample)

        result = validate_artifact(sample)

        assert not result.ok, line
        assert any("forbidden action term" in error for error in result.errors), line
