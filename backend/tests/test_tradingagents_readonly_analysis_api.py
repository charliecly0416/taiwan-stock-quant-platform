from __future__ import annotations

import json
from pathlib import Path

from flask import Flask

from app.routes.tw_stock import tw_stock_bp
from scripts.build_tradingagents_readonly_analysis_artifact import build_artifact


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/mock_raw_state.json"


def _client(*, testing: bool = True):
    app = Flask(__name__)
    app.config["TESTING"] = testing
    app.register_blueprint(tw_stock_bp, url_prefix="/api/tw-stock")
    return app.test_client()


def _build_artifact(root: Path, run_id: str = "api_fixture") -> Path:
    out_dir = root / run_id
    result = build_artifact(fixture_path=FIXTURE, output_dir=out_dir, run_id=run_id)
    assert result["ok"] is True
    return out_dir


def _data(response):
    payload = response.get_json()
    return payload["data"]


def test_tradingagents_readonly_analysis_run_get_success(tmp_path: Path):
    artifact_root = tmp_path / "analysis"
    _build_artifact(artifact_root, run_id="run_a")

    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/run_a",
        query_string={"artifact_root": str(artifact_root)},
    )
    data = _data(resp)

    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["schema_version"] == "tradingagents_readonly_analysis_api_v1"
    assert data["readonly_only"] is True
    assert data["not_order"] is True
    assert data["not_target_position"] is True
    assert data["not_investment_advice"] is True
    assert data["production_trade_enabled"] is False
    assert data["run_id"] == "run_a"
    assert data["source"]["project_path"] == "third_party/tradingagents"
    assert data["sanitized_report"]["symbols"]
    assert data["validation"]["ok"] is True
    assert data["raw_files_included"] is False
    serialized = json.dumps(data, ensure_ascii=False)
    assert "raw_complete_report" not in serialized
    assert "raw_tradingagents_state" not in serialized
    assert "raw_untrusted_files" not in serialized


def test_tradingagents_readonly_analysis_public_manifest_hides_runtime_inputs(tmp_path: Path):
    artifact_root = tmp_path / "analysis"
    artifact_dir = _build_artifact(artifact_root, run_id="run_inputs")
    manifest_path = artifact_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_artifacts"] = [
        {
            "artifact_type": "TradingAgentsControlledRealRunInput",
            "backend_url": "https://chat.pku.edu.cn/v1",
            "llm_provider": "openai",
        }
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/run_inputs",
        query_string={"artifact_root": str(artifact_root)},
    )
    data = _data(resp)
    serialized = json.dumps(data, ensure_ascii=False)

    assert resp.status_code == 200
    assert data["ok"] is True
    assert "input_artifacts" not in data["manifest"]
    assert "backend_url" not in serialized
    assert "chat.pku.edu.cn" not in serialized


def test_tradingagents_readonly_analysis_latest_pointer_get_success(tmp_path: Path):
    artifact_root = tmp_path / "analysis"
    artifact_dir = _build_artifact(artifact_root, run_id="run_latest")
    (artifact_root / "latest.json").write_text(
        json.dumps({"artifact_dir": "run_latest"}, ensure_ascii=False),
        encoding="utf-8",
    )

    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/latest",
        query_string={"artifact_root": str(artifact_root), "include_markdown": "true"},
    )
    data = _data(resp)

    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["artifact_dir"] == str(artifact_dir.resolve())
    assert "sanitized_report_markdown" in data
    assert "TradingAgents Readonly Analysis" in data["sanitized_report_markdown"]


def test_tradingagents_readonly_analysis_missing_latest_is_readonly_error(tmp_path: Path):
    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/latest",
        query_string={"artifact_root": str(tmp_path / "missing")},
    )
    data = _data(resp)

    assert resp.status_code == 200
    assert data["ok"] is False
    assert data["status"] == "latest_missing"
    assert data["readonly_only"] is True
    assert data["production_trade_enabled"] is False


def test_tradingagents_readonly_analysis_validation_failure_hides_raw_file_names(tmp_path: Path):
    artifact_root = tmp_path / "analysis"
    artifact_dir = _build_artifact(artifact_root, run_id="bad_raw")
    (artifact_dir / "raw_complete_report.md").unlink()

    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/bad_raw",
        query_string={"artifact_root": str(artifact_root)},
    )
    data = _data(resp)
    serialized = json.dumps(data, ensure_ascii=False)

    assert resp.status_code == 200
    assert data["ok"] is False
    assert data["status"] == "artifact_validation_failed"
    assert data["validation"]["ok"] is False
    assert data["validation"]["failed_checks"]
    assert "raw_complete_report" not in serialized
    assert "raw_tradingagents_state" not in serialized
    assert "review_only_source_file_check" in serialized


def test_tradingagents_readonly_analysis_production_ignores_artifact_root_query(tmp_path: Path):
    artifact_root = tmp_path / "analysis"
    _build_artifact(artifact_root, run_id="run_a")

    resp = _client(testing=False).get(
        "/api/tw-stock/tradingagents-readonly-analysis/run_a",
        query_string={"artifact_root": str(artifact_root)},
    )
    data = _data(resp)

    assert resp.status_code == 404
    assert data["ok"] is False
    assert data["status"] == "artifact_missing"


def test_tradingagents_readonly_analysis_latest_absolute_path_outside_root_rejected(tmp_path: Path):
    artifact_root = tmp_path / "analysis"
    outside = tmp_path / "outside"
    _build_artifact(outside, run_id="outside_run")
    artifact_root.mkdir(parents=True)
    (artifact_root / "latest.json").write_text(
        json.dumps({"artifact_dir": str((outside / "outside_run").resolve())}, ensure_ascii=False),
        encoding="utf-8",
    )

    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/latest",
        query_string={"artifact_root": str(artifact_root)},
    )
    data = _data(resp)

    assert resp.status_code == 400
    assert data["ok"] is False
    assert data["status"] == "latest_path_outside_root"


def test_tradingagents_readonly_analysis_invalid_run_id_rejected(tmp_path: Path):
    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/..",
        query_string={"artifact_root": str(tmp_path)},
    )
    assert resp.status_code == 400

    resp = _client().get(
        "/api/tw-stock/tradingagents-readonly-analysis/%2e%2e",
        query_string={"artifact_root": str(tmp_path)},
    )
    data = _data(resp)
    assert resp.status_code == 400
    assert data["ok"] is False
    assert data["status"] == "invalid_run_id"


def test_tradingagents_readonly_analysis_route_has_no_write_methods(tmp_path: Path):
    client = _client()
    for method in ["post", "put", "patch", "delete"]:
        assert getattr(client, method)("/api/tw-stock/tradingagents-readonly-analysis/latest").status_code == 405
        assert getattr(client, method)("/api/tw-stock/tradingagents-readonly-analysis/run_a").status_code == 405
