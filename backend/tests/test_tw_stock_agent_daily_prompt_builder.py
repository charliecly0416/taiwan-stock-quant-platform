import json
from argparse import Namespace
from pathlib import Path

from scripts.build_tw_agent_daily_prompt_artifact import build_artifact
from scripts.validate_tw_agent_daily_prompt_artifact import validate_artifact


FIXTURE_ROOT = Path("data_tw/golden_samples/agent_daily_prompt_builder")


def _args(tmp_path, fixture="pass", **overrides):
    values = {
        "input_fixture": str(FIXTURE_ROOT / fixture),
        "source_dir": None,
        "output_dir": str(tmp_path / "artifact"),
        "dry_run": True,
        "publish_latest": False,
        "latest_path": str(tmp_path / "latest.json"),
        "max_items": 10,
        "tradingagents_analysis_dir": None,
        "strict_tradingagents_analysis": False,
        "json": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_builder_dry_run_outputs_valid_artifact_without_latest(tmp_path):
    args = _args(tmp_path)

    result = build_artifact(args)
    output_dir = Path(result["output_dir"])

    assert result["ok"] is True
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "prompt_context.json").exists()
    assert (output_dir / "prompt_text.md").exists()
    assert not Path(args.latest_path).exists()
    validation = validate_artifact(output_dir)
    assert validation.ok, validation.errors


def test_builder_prompt_context_preserves_pending_warnings(tmp_path):
    result = build_artifact(_args(tmp_path))
    context = json.loads((Path(result["output_dir"]) / "prompt_context.json").read_text(encoding="utf-8"))

    assert context["date_context"]["execution_price_status"] == "pending"
    assert "next_open_pending" in context["freshness"]["warnings"]
    assert context["paper_portfolio"]["apply_allowed"] is False


def test_builder_publish_latest_writes_only_agent_prompt_pointer(tmp_path):
    latest_path = tmp_path / "agent_latest.json"
    result = build_artifact(_args(tmp_path, publish_latest=True, latest_path=str(latest_path)))

    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest["artifact_type"] == "tw_agent_daily_prompt_latest"
    assert latest["manifest"].endswith("manifest.json")
    assert latest["checksum"] == result["checksum"]
    assert "accepted" not in json.dumps(latest, ensure_ascii=False).lower()


def test_builder_rejects_asof_or_target_date_mismatch(tmp_path):
    args = _args(tmp_path, fixture="asof_mismatch")

    try:
        build_artifact(args)
    except Exception as exc:
        assert "source_target_date_mismatch" in str(exc)
    else:
        raise AssertionError("expected source_target_date_mismatch")


def test_builder_can_include_sanitized_tradingagents_readonly_context(tmp_path):
    tradingagents_dir = Path("data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal")

    result = build_artifact(_args(tmp_path, tradingagents_analysis_dir=str(tradingagents_dir), max_items=1))
    output_dir = Path(result["output_dir"])
    context = json.loads((output_dir / "prompt_context.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    prompt_text = (output_dir / "prompt_text.md").read_text(encoding="utf-8")

    validation = validate_artifact(output_dir)
    assert validation.ok, validation.errors
    ta = context["external_research"]["tradingagents_readonly"]
    assert ta["available"] is True
    assert ta["sanitized_only"] is True
    assert ta["readonly_only"] is True
    assert ta["symbols"][0]["symbol"] == "2330"
    assert "外部多智能体研究摘要" in ta["symbols"][0]["research_summary"]
    assert "tradingagents_readonly_analysis" in manifest["source_artifacts"]
    assert (output_dir / manifest["source_artifacts"]["tradingagents_readonly_analysis"]).exists()
    blob = json.dumps({"context": context, "manifest": manifest, "prompt_text": prompt_text}, ensure_ascii=False)
    assert "raw_tradingagents_state" not in blob
    assert "raw_complete_report" not in blob
    for forbidden in ("Buy", "Sell", "Hold", "price target", "target price", "stop loss", "target_weight"):
        assert forbidden not in blob


def test_builder_strict_tradingagents_context_rejects_invalid_dir(tmp_path):
    args = _args(
        tmp_path,
        tradingagents_analysis_dir=str(tmp_path / "missing-ta"),
        strict_tradingagents_analysis=True,
    )

    try:
        build_artifact(args)
    except Exception as exc:
        assert "tradingagents_readonly_unavailable" in str(exc)
    else:
        raise AssertionError("expected tradingagents_readonly_unavailable")


def test_builder_non_strict_invalid_tradingagents_artifact_is_not_added_to_context(tmp_path):
    tradingagents_dir = Path("data_tw/golden_samples/tradingagents_readonly_analysis/fail_forbidden_semantics")

    result = build_artifact(_args(tmp_path, tradingagents_analysis_dir=str(tradingagents_dir)))
    output_dir = Path(result["output_dir"])
    context = json.loads((output_dir / "prompt_context.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    validation = validate_artifact(output_dir)
    assert validation.ok, validation.errors
    assert "external_research" not in context
    assert "tradingagents_readonly_validation_failed" in context["freshness"]["warnings"]
    assert "tradingagents_readonly_analysis" not in manifest["source_artifacts"]
