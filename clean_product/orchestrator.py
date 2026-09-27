from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from .config import CONFIG_PATH, datasets, env_config, load_config, models
from .data import DataCatalog
from .models import ModelRunner


def run_daily(asof: str | None = None, *, config_path: Path = CONFIG_PATH, dry_run: bool = False) -> dict:
    config = env_config(load_config(config_path))
    asof = asof or date.today().isoformat()
    catalog = DataCatalog(config)
    specs = datasets(config)
    manifests = []
    if not dry_run:
        manifests = catalog.acquire_all(specs, asof)
    prices = catalog.query("prices", end=asof, allow_fixture=dry_run)
    runner = ModelRunner(config)
    signals = [runner.run(name, prices, asof) for name in models(config)]
    result = {"asof": asof, "status": "READY", "datasets": manifests, "models": [{"model": s.model, "role": models(config)[s.model].role, "rows": len(s.rows)} for s in signals], "readonly": True}
    output = config.get("artifact_root") / "daily" / asof
    output.mkdir(parents=True, exist_ok=True)
    (output / "run.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
