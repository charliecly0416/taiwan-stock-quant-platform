"""Static checks for the repo-local vendored TradingAgents source."""
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "third_party" / "tradingagents"


def test_tradingagents_vendor_required_files_exist():
    required = [
        "README.md",
        "LICENSE",
        "ATTRIBUTION.md",
        "pyproject.toml",
        "tradingagents/default_config.py",
        "tradingagents/graph/trading_graph.py",
        "tradingagents/agents/schemas.py",
        "tradingagents/reporting.py",
    ]
    missing = [path for path in required if not (VENDOR / path).exists()]
    assert missing == []


def test_tradingagents_vendor_does_not_include_local_generated_state():
    forbidden_names = {
        ".git",
        ".env",
        "__pycache__",
        "build",
        "tradingagents.egg-info",
    }
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--", str(VENDOR.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
    ).splitlines()
    offenders = [
        path
        for path in tracked
        if Path(path).name in forbidden_names or Path(path).suffix == ".pyc"
    ]
    assert offenders == []


def test_tradingagents_vendor_attribution_pins_source_revision():
    attribution = (VENDOR / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "85946c2f60768ab2dae23a5a36cd927662feef94" in attribution
    assert "Apache License 2.0" in attribution
    assert "/home/chuliyang/TradingAgents" in attribution


def test_tradingagents_vendor_runtime_docs_warn_against_external_dependency():
    mainline = (
        ROOT
        / "docs"
        / "tw_modular_contracts"
        / "TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md"
    ).read_text(encoding="utf-8")
    assert "不在运行时依赖 /home/chuliyang/TradingAgents" in mainline
    assert "third_party/tradingagents" in mainline


def test_tradingagents_optional_requirements_are_isolated_from_backend_runtime():
    optional = (ROOT / "requirements-tradingagents.txt").read_text(encoding="utf-8")
    backend = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")
    assert "langgraph" in optional
    assert "langgraph" not in backend
