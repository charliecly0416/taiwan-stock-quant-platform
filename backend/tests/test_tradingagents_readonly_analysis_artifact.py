from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "scripts" / "build_tradingagents_readonly_analysis_artifact.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_tradingagents_readonly_analysis_artifact.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load_module("build_tradingagents_readonly_analysis_artifact", BUILD_SCRIPT)
validator = _load_module("validate_tradingagents_readonly_analysis_artifact", VALIDATE_SCRIPT)


def test_builder_creates_pass_minimal_artifact_from_fixture(tmp_path: Path):
    fixture = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/mock_raw_state.json"
    out_dir = tmp_path / "artifact"
    result = builder.build_artifact(fixture_path=fixture, output_dir=out_dir, run_id="pytest_pass")

    assert result["ok"] is True
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((out_dir / "sanitized_report.json").read_text(encoding="utf-8"))
    raw = json.loads((out_dir / "raw_tradingagents_state.json").read_text(encoding="utf-8"))

    assert manifest["readonly_only"] is True
    assert manifest["production_trade_enabled"] is False
    assert manifest["no_openai_call"] is True
    assert manifest["no_network_call"] is True
    assert manifest["no_tradingagents_graph_call"] is True
    assert manifest["source"]["project_path"] == "third_party/tradingagents"
    assert "target_weight" not in json.dumps(manifest, ensure_ascii=False)
    assert "stop_loss" not in json.dumps(manifest, ensure_ascii=False)
    assert report["symbols"][0]["forbidden_decision_removed"] is True
    assert report["symbols"][0]["raw_decision_label_removed"] is True
    assert raw["raw_untrusted"] is True
    assert raw["display_allowed"] is False

    validation = validator.validate(out_dir)
    assert validation["ok"] is True, validation


def test_committed_pass_minimal_golden_validates():
    artifact_dir = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal"
    validation = validator.validate(artifact_dir)
    assert validation["ok"] is True, validation


def test_forbidden_semantics_golden_fails():
    artifact_dir = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/fail_forbidden_semantics"
    validation = validator.validate(artifact_dir)
    assert validation["ok"] is False
    failed = [check for check in validation["checks"] if check["status"] == "fail"]
    assert any(check["name"] == "forbidden_semantics_absent_from_display_files" for check in failed)


def test_builder_removes_common_english_tradingagents_decision_terms(tmp_path: Path):
    fixture = tmp_path / "raw_state.json"
    fixture.write_text(
        json.dumps(
            {
                "run_id": "english_terms",
                "created_at": "2026-06-30T00:00:00+00:00",
                "signal_asof": "2026-06-29",
                "target_date": "2026-06-30",
                "selected_analysts": ["market"],
                "symbols": [
                    {
                        "symbol": "2330",
                        "instrument": "TW2330",
                        "research_summary": "Final Transaction Proposal: Buy with price target and stop loss. 可以续抱但不要追价。",
                        "bull_points": ["Overweight because momentum improved. 核心部位可分批加码到 60%–70%。"],
                        "bear_points": ["Hold if data is stale. 不适合新增曝险。"],
                        "risk_review_points": ["Position sizing must not be displayed. 停损与权重不能展示。"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "artifact"

    result = builder.build_artifact(fixture_path=fixture, output_dir=out_dir)

    assert result["ok"] is True
    validation = validator.validate(out_dir)
    assert validation["ok"] is True, validation
    rendered = (out_dir / "sanitized_report.md").read_text(encoding="utf-8")
    lowered = rendered.lower()
    assert "buy" not in lowered
    assert "overweight" not in lowered
    assert "hold" not in lowered
    assert "price target" not in lowered
    assert "stop loss" not in lowered
    assert "position sizing" not in lowered
    assert "续抱" not in rendered
    assert "追价" not in rendered
    assert "核心部位" not in rendered
    assert "分批加码" not in rendered
    assert "60%–70%" not in rendered
    assert "新增曝险" not in rendered
    assert "停损" not in rendered
    assert "权重" not in rendered


def test_controlled_real_run_uses_neutral_metadata_only_display(tmp_path: Path):
    fixture = tmp_path / "raw_state.json"
    fixture.write_text(
        json.dumps(
            {
                "run_id": "controlled_terms",
                "run_mode": "controlled_real_run",
                "created_at": "2026-06-30T00:00:00+00:00",
                "signal_asof": "2026-06-01",
                "target_date": "2026-06-01",
                "selected_analysts": ["market"],
                "safety": {
                    "no_openai_call": False,
                    "no_network_call": False,
                    "no_tradingagents_graph_call": False,
                },
                "runtime_paths": {
                    "results_dir": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_terms/results",
                    "data_cache_dir": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_terms/cache",
                    "memory_log_path": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_terms/memory/log.jsonl",
                },
                "symbols": [
                    {
                        "symbol": "2330.TW",
                        "source_context": {
                            "context_source": "controlled_real_run",
                            "target_weight": "60%–70%",
                            "decision_label_removed": True,
                        },
                        "research_summary": "可以续抱，不建议追价，現在就買最划算。",
                        "bull_points": ["核心部位可分批加码到 60%–70%。"],
                        "bear_points": ["不适合新增曝险。"],
                        "risk_review_points": ["停损与权重不能展示，仓位宜保守。"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "artifact"

    result = builder.build_artifact(fixture_path=fixture, output_dir=out_dir)

    assert result["ok"] is True
    validation = validator.validate(out_dir)
    assert validation["ok"] is True, validation
    rendered = (out_dir / "sanitized_report.md").read_text(encoding="utf-8")
    report = json.loads((out_dir / "sanitized_report.json").read_text(encoding="utf-8"))
    display_blob = json.dumps(report, ensure_ascii=False) + "\n" + rendered
    assert report["symbols"][0]["external_sections_removed"] is True
    labels = report["symbols"][0]["research_labels"]
    assert labels["source_section_presence"]["debate"] is True
    assert labels["source_section_presence"]["risk"] is True
    assert labels["source_text_density_bucket"] in {"short", "medium", "long"}
    assert labels["evidence_quality_flags"]["has_numeric_context"] is True
    assert labels["review_queue_flags"]["needs_human_fact_check"] is True
    assert labels["sanitizer_counters"]["forbidden_term_category_count"] >= 1
    assert labels["sanitizer_counters"]["raw_text_chars_bucketed"] > 0
    assert report["symbols"][0]["bull_points"] == []
    assert report["symbols"][0]["bear_points"] == []
    assert report["symbols"][0]["risk_review_points"] == []
    for term in ("续抱", "追价", "現在就買", "核心部位", "分批", "加码", "60%–70%", "新增曝险", "停损", "权重"):
        assert term not in display_blob


def test_controlled_real_run_requires_research_labels_shape(tmp_path: Path):
    fixture = tmp_path / "raw_state.json"
    fixture.write_text(
        json.dumps(
            {
                "run_id": "controlled_missing_labels",
                "run_mode": "controlled_real_run",
                "created_at": "2026-06-30T00:00:00+00:00",
                "signal_asof": "2026-06-01",
                "target_date": "2026-06-01",
                "selected_analysts": ["market"],
                "safety": {
                    "no_openai_call": False,
                    "no_network_call": False,
                    "no_tradingagents_graph_call": False,
                },
                "runtime_paths": {
                    "results_dir": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_missing_labels/results",
                    "data_cache_dir": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_missing_labels/cache",
                    "memory_log_path": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_missing_labels/memory/log.jsonl",
                },
                "symbols": [{"symbol": "2330.TW", "research_summary": "market risk text 123"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "artifact"
    assert builder.build_artifact(fixture_path=fixture, output_dir=out_dir)["ok"] is True
    report_path = out_dir / "sanitized_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    del report["symbols"][0]["research_labels"]
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation = validator.validate(out_dir)

    assert validation["ok"] is False
    failed = [check for check in validation["checks"] if check["status"] == "fail"]
    assert any(check["name"] == "sanitized_report_research_labels_shape" for check in failed)


def test_research_labels_reject_forbidden_actionable_fields(tmp_path: Path):
    fixture = tmp_path / "raw_state.json"
    fixture.write_text(
        json.dumps(
            {
                "run_id": "controlled_bad_labels",
                "run_mode": "controlled_real_run",
                "created_at": "2026-06-30T00:00:00+00:00",
                "signal_asof": "2026-06-01",
                "target_date": "2026-06-01",
                "selected_analysts": ["market"],
                "safety": {
                    "no_openai_call": False,
                    "no_network_call": False,
                    "no_tradingagents_graph_call": False,
                },
                "runtime_paths": {
                    "results_dir": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_bad_labels/results",
                    "data_cache_dir": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_bad_labels/cache",
                    "memory_log_path": "data_tw/artifacts/analysis/tradingagents_readonly/controlled_bad_labels/memory/log.jsonl",
                },
                "symbols": [{"symbol": "2330.TW", "research_summary": "market risk text 123"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "artifact"
    assert builder.build_artifact(fixture_path=fixture, output_dir=out_dir)["ok"] is True
    report_path = out_dir / "sanitized_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["symbols"][0]["research_labels"]["buy_now"] = True
    report["symbols"][0]["research_labels"]["source_text_density_bucket"] = "Buy"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation = validator.validate(out_dir)

    assert validation["ok"] is False
    failed = [check for check in validation["checks"] if check["status"] == "fail"]
    assert any(check["name"] == "sanitized_report_research_labels_shape" for check in failed)
    assert any(check["name"] == "forbidden_fields_absent" for check in failed)
    assert any(check["name"] == "forbidden_semantics_absent_from_display_files" for check in failed)


def test_cli_json_modes_return_expected_codes(tmp_path: Path, capsys):
    fixture = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/mock_raw_state.json"
    out_dir = tmp_path / "cli_artifact"
    assert builder.main(["--fixture", str(fixture), "--output-dir", str(out_dir), "--run-id", "cli_case", "--json"]) == 0
    build_payload = json.loads(capsys.readouterr().out)
    assert build_payload["ok"] is True

    assert validator.main([str(out_dir), "--json"]) == 0
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_payload["ok"] is True

    fail_dir = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/fail_forbidden_semantics"
    assert validator.main([str(fail_dir), "--json"]) == 1
    fail_payload = json.loads(capsys.readouterr().out)
    assert fail_payload["ok"] is False
