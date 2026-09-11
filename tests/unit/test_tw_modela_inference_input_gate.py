from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/build_tw_model_inference_input.py"

if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))

spec = importlib.util.spec_from_file_location("tw_modela_inference_input_gate", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_stale_legacy_price_market_readiness_does_not_block_dynamic_model_score(tmp_path, monkeypatch) -> None:
    readiness = tmp_path / "price_market_calendar.json"
    readiness.write_text(
        """{
  "asof": "2026-06-25",
  "can_continue_to_model_score": true,
  "dependencies": [
    {
      "dependency_name": "legacy_price_store",
      "applies_to_gates": ["model_score"],
      "can_continue": true
    }
  ]
}
""",
        encoding="utf-8",
    )
    dashboard = tmp_path / "daily_readiness_dashboard.json"
    dashboard.write_text(
        """{
  "asof": "2026-08-13",
  "forbidden_actions_audit": {
    "all_false": true,
    "actions": {"provider_publish_triggered": false}
  }
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PRICE_MARKET_READINESS", readiness)
    monkeypatch.setattr(module, "READINESS_DASHBOARD", dashboard)

    gate = module.readiness_gate("2026-08-13")

    assert gate["status"] == "READY"
    assert gate["errors"] == []
    assert gate["price_market_readiness_asof"] == "2026-06-25"
    assert gate["legacy_price_market_readiness_asof_mismatch_ignored"] is True
    assert "legacy_price_market_readiness_asof_mismatch_ignored_for_dynamic_daily_asof" in gate["warnings"]


def test_matching_price_market_readiness_false_still_blocks_model_score(tmp_path, monkeypatch) -> None:
    readiness = tmp_path / "price_market_calendar.json"
    readiness.write_text(
        """{
  "asof": "2026-08-13",
  "can_continue_to_model_score": false,
  "dependencies": []
}
""",
        encoding="utf-8",
    )
    dashboard = tmp_path / "daily_readiness_dashboard.json"
    dashboard.write_text(
        """{
  "asof": "2026-08-13",
  "forbidden_actions_audit": {"all_false": true, "actions": {}}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PRICE_MARKET_READINESS", readiness)
    monkeypatch.setattr(module, "READINESS_DASHBOARD", dashboard)

    gate = module.readiness_gate("2026-08-13")

    assert gate["status"] == "BLOCKED_INPUT_NOT_READY"
    assert "price_market_readiness_blocks_model_score" in gate["errors"]
    assert gate["warnings"] == []
