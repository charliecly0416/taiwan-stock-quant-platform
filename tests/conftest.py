from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolate_runtime_paths(monkeypatch):
    # An operator's configured production directories must not override tmp_path.
    monkeypatch.delenv('TW_PRODUCT_DATA_ROOT', raising=False)
    monkeypatch.delenv('TW_PRODUCT_ARTIFACT_ROOT', raising=False)
