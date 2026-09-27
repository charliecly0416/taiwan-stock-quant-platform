from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
import requests

from .config import DatasetSpec, datasets, env_config


class DataError(RuntimeError):
    pass


class SourceAdapter(Protocol):
    """Fetch raw rows for one configured dataset.

    Adapters know how to talk to a source. They do not normalize or write files;
    that remains one shared DataCatalog path for every dataset.
    """

    def fetch(self, spec: DatasetSpec, *, asof: str, start: str, config: dict) -> list[dict[str, Any]]:
        ...


class FinMindAdapter:
    def fetch(self, spec: DatasetSpec, *, asof: str, start: str, config: dict) -> list[dict[str, Any]]:
        token = os.getenv("FINMIND_TOKEN", "").strip()
        if not token:
            raise DataError("FINMIND_TOKEN is required for a live acquisition")
        params = dict(spec.params)
        params.setdefault("dataset", spec.endpoint)
        params.setdefault("data_id", ",".join(config.get("universe", [])))
        params.setdefault("start_date", start)
        params.setdefault("end_date", asof)
        params["token"] = token
        response = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        if payload.get("msg") not in ("success", "Success", None):
            raise DataError(f"{spec.name}: {payload.get('msg')}")
        return payload.get("data") or []


class FixtureAdapter:
    def fetch(self, spec: DatasetSpec, *, asof: str, start: str, config: dict) -> list[dict[str, Any]]:
        fixture = Path(__file__).with_name("fixtures") / f"{spec.name}.csv"
        if not fixture.exists():
            raise DataError(f"fixture not found: {fixture}")
        return pd.read_csv(fixture).to_dict("records")


class DataCatalog:
    """One data path for every dataset: fetch -> normalize -> store -> query."""

    def __init__(self, config: dict):
        self.config = env_config(config)
        self.root: Path = self.config["data_root"]
        self.root.mkdir(parents=True, exist_ok=True)
        self.adapters: dict[str, SourceAdapter] = {
            "finmind": FinMindAdapter(),
            "fixture": FixtureAdapter(),
        }

    def register_source(self, name: str, adapter: SourceAdapter) -> None:
        """Register a source once; datasets select it with ``source`` in config."""
        self.adapters[name] = adapter

    def _file(self, name: str) -> Path:
        return self.root / f"{name}.csv"

    def normalize(self, spec: DatasetSpec, rows: list[dict[str, Any]]) -> pd.DataFrame:
        frame = pd.DataFrame(rows)
        if frame.empty:
            return pd.DataFrame(columns=list(spec.fields))
        for field in spec.fields:
            if field not in frame:
                frame[field] = pd.NA
        frame = frame[list(spec.fields)]
        frame[spec.date_field] = frame[spec.date_field].astype(str).str[:10]
        if spec.symbols_field in frame:
            symbols = frame[spec.symbols_field].astype(str)
            numeric = symbols.str.extract(r"(\d+)")[0]
            frame[spec.symbols_field] = numeric.fillna(symbols).where(numeric.isna(), numeric.str.zfill(4))
        for field in spec.numeric:
            if field in frame:
                frame[field] = pd.to_numeric(frame[field], errors="coerce")
        missing = [field for field in spec.required if field not in frame or frame[field].isna().all()]
        if missing:
            raise DataError(f"{spec.name}: required fields missing: {', '.join(missing)}")
        sort_fields = [spec.date_field]
        if spec.symbols_field in frame:
            sort_fields.append(spec.symbols_field)
        return frame.drop_duplicates().sort_values(sort_fields).reset_index(drop=True)

    def fetch(self, spec: DatasetSpec, asof: str, start: str | None = None) -> dict[str, Any]:
        start = start or (date.fromisoformat(asof) - timedelta(days=365)).isoformat()
        try:
            adapter = self.adapters[spec.source]
        except KeyError as exc:
            raise DataError(f"unknown data source: {spec.source}") from exc
        rows = adapter.fetch(spec, asof=asof, start=start, config=self.config)
        return self.store(spec, self.normalize(spec, rows), asof, spec.source)

    def store(self, spec: DatasetSpec, frame: pd.DataFrame, asof: str, source: str) -> dict[str, Any]:
        target = self._file(spec.name)
        incoming = self.normalize(spec, frame.to_dict("records"))
        if target.exists():
            existing = self.normalize(spec, pd.read_csv(target).to_dict("records"))
            frame = pd.concat([existing, incoming], ignore_index=True)
            frame = self.normalize(spec, frame.to_dict("records"))
        else:
            frame = incoming
        frame.to_csv(target, index=False)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest = {"dataset": spec.name, "asof": asof, "source": source, "rows": len(frame), "path": str(target), "sha256": digest}
        (self.root / f"{spec.name}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest

    def query(self, name: str, start: str | None = None, end: str | None = None, *, allow_fixture: bool = False) -> pd.DataFrame:
        target = self._file(name)
        if not target.exists():
            fixture = Path(__file__).with_name("fixtures") / f"{name}.csv"
            if not allow_fixture or not fixture.exists():
                raise DataError(f"dataset not found: {name}")
            target = fixture
        spec = datasets(self.config).get(name)
        frame = pd.read_csv(target)
        if spec:
            frame = self.normalize(spec, frame.to_dict("records"))
        date_field = spec.date_field if spec else "date"
        if start:
            frame = frame[frame[date_field].astype(str) >= start]
        if end:
            frame = frame[frame[date_field].astype(str) <= end]
        return frame.reset_index(drop=True)

    def acquire_all(self, specs: dict[str, DatasetSpec], asof: str, start: str | None = None) -> list[dict[str, Any]]:
        return [self.fetch(spec, asof, start) for spec in specs.values()]
