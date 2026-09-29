from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd
import requests

from .config import DatasetSpec, datasets, env_config, path, universe


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
        base = dict(spec.params)
        explicit = base.pop("data_id", None)
        symbols = [explicit] if explicit else universe(config)
        if not symbols:
            raise DataError(f"{spec.name}: empty acquisition universe")
        def fetch_symbol(symbol: str) -> list[dict[str, Any]]:
            params = dict(base)
            data_id = re.sub(r"^TW(?=\d+$)", "", str(symbol))
            params.update(dataset=spec.endpoint, data_id=data_id, start_date=start, end_date=asof, token=token)
            try:
                response = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, timeout=60)
                response.raise_for_status()
            except requests.RequestException as exc:
                # requests errors can embed a URL containing the query-string token.
                raise DataError(f"{spec.name}/{data_id}: provider request failed ({type(exc).__name__})") from None
            payload = response.json()
            if payload.get("msg") not in ("success", "Success", None):
                raise DataError(f"{spec.name}/{symbol}: {payload.get('msg')}")
            return payload.get("data") or []
        workers = max(1, min(16, int((config.get("provider_refresh") or {}).get("finmind_workers", 8))))
        if len(symbols) == 1 or workers == 1:
            return [row for symbol in symbols for row in fetch_symbol(symbol)]
        rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(workers, len(symbols)), thread_name_prefix="finmind") as pool:
            futures = {pool.submit(fetch_symbol, symbol): symbol for symbol in symbols}
            try:
                for future in as_completed(futures):
                    rows.extend(future.result())
            except Exception:
                for future in futures:
                    future.cancel()
                raise
        return rows


class QlibProviderAdapter:
    """Read governed OHLCV snapshots from the configured local Qlib provider."""

    @staticmethod
    def _decode(target: Path, calendar_size: int) -> np.ndarray:
        if target.stat().st_size % 4:
            raise DataError(f"provider field is truncated: {target.name}")
        values = np.fromfile(target, dtype="<f4")
        output = np.full(calendar_size, np.nan)
        if len(values) < 2 or not np.isfinite(values[0]) or values[0] != int(values[0]):
            raise DataError(f"provider field has invalid offset: {target.name}")
        start = int(values[0])
        if start < 0 or start + len(values) - 1 > calendar_size:
            raise DataError(f"provider field exceeds calendar: {target.name}")
        output[start:start + len(values) - 1] = values[1:]
        return output

    def fetch(self, spec: DatasetSpec, *, asof: str, start: str, config: dict) -> list[dict[str, Any]]:
        provider = path(spec.params.get("provider_uri", ""))
        calendar_path = provider / "calendars" / "day.txt"
        if not calendar_path.exists():
            raise DataError(f"provider calendar not found: {calendar_path}")
        calendar = [line.strip()[:10] for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        selected = [index for index, day in enumerate(calendar) if start <= day <= asof]
        rows: list[dict[str, Any]] = []
        for symbol in universe(config):
            folder = provider / "features" / symbol.lower()
            if not folder.exists():
                continue
            fields = {}
            for name in ("open", "high", "low", "close", "volume", "vwap"):
                target = folder / f"{name}.day.bin"
                if not target.exists():
                    raise DataError(f"provider field not found: {target}")
                fields[name] = self._decode(target, len(calendar))
            for index in selected:
                rows.append({"stock_id": symbol, "date": calendar[index], **{name: values[index] for name, values in fields.items()}})
        return rows


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
        self.adapters: dict[str, SourceAdapter] = {
            "finmind": FinMindAdapter(),
            "fixture": FixtureAdapter(),
            "qlib_provider": QlibProviderAdapter(),
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
        sort_fields = [spec.date_field]
        if spec.symbols_field in frame:
            sort_fields.append(spec.symbols_field)
        keys = list(spec.primary_key) or sort_fields
        if any(key not in frame for key in keys) or frame[keys].isna().any().any():
            raise DataError(f"{spec.name}: invalid primary key")
        frame[spec.date_field] = frame[spec.date_field].astype(str).str[:10]
        try:
            dates = frame[spec.date_field].map(lambda value: date.fromisoformat(value).isoformat())
        except ValueError:
            raise DataError(f"{spec.name}: invalid date") from None
        if not dates.eq(frame[spec.date_field]).all():
            raise DataError(f"{spec.name}: date must use YYYY-MM-DD")
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
        return frame.drop_duplicates(keys, keep="last").sort_values(sort_fields).reset_index(drop=True)

    def fetch(self, spec: DatasetSpec, asof: str, start: str | None = None) -> dict[str, Any]:
        if start is None:
            target = self._file(spec.name)
            if target.exists():
                existing = pd.read_csv(target, usecols=[spec.date_field])
                latest = date.fromisoformat(str(existing[spec.date_field].max())[:10])
                start = (latest - timedelta(days=max(2, spec.lag_days + 14))).isoformat()
            else:
                start = (date.fromisoformat(asof) - timedelta(days=spec.history_days)).isoformat()
        try:
            adapter = self.adapters[spec.source]
        except KeyError as exc:
            raise DataError(f"unknown data source: {spec.source}") from exc
        rows = adapter.fetch(spec, asof=asof, start=start, config=self.config)
        return self.store(spec, self.normalize(spec, rows), asof, spec.source)

    def store(self, spec: DatasetSpec, frame: pd.DataFrame, asof: str, source: str) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        target = self._file(spec.name)
        incoming = self.normalize(spec, frame.to_dict("records"))
        if target.exists():
            existing = self.normalize(spec, pd.read_csv(target, dtype={spec.symbols_field: "string"}).to_dict("records"))
            frame = pd.concat([existing, incoming], ignore_index=True)
            frame = self.normalize(spec, frame.to_dict("records"))
        else:
            frame = incoming
        frame.to_csv(target, index=False)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        latest = str(frame[spec.date_field].max())[:10] if not frame.empty else None
        manifest = {"dataset": spec.name, "asof": asof, "available_at": asof,
                    "lag_days": spec.lag_days, "latest_asof": latest, "source": source,
                    "rows": len(frame), "path": str(target), "sha256": digest}
        (self.root / f"{spec.name}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest

    def query(self, name: str, start: str | None = None, end: str | None = None, *, allow_fixture: bool = False) -> pd.DataFrame:
        spec = datasets(self.config).get(name)
        if spec is None:
            raise DataError(f"dataset not registered: {name}")
        target = self._file(name)
        if not target.exists():
            fixture = Path(__file__).with_name("fixtures") / f"{name}.csv"
            if not allow_fixture or not fixture.exists():
                raise DataError(f"dataset not found: {name}")
            target = fixture
        read_types = {spec.symbols_field: "string"} if spec else None
        frame = pd.read_csv(target, dtype=read_types)
        if spec:
            frame = self.normalize(spec, frame.to_dict("records"))
        date_field = spec.date_field if spec else "date"
        if start:
            frame = frame[frame[date_field].astype(str) >= start]
        if end:
            frame = frame[frame[date_field].astype(str) <= end]
        return frame.reset_index(drop=True)

    def query_local_source(self, name: str, start: str | None = None, end: str | None = None, *, symbols: list[str] | None = None) -> pd.DataFrame:
        """Read a configured local source without publishing catalog files.

        Provider-backed datasets do not need a catalog CSV.  When callers omit
        bounds, use the provider calendar so the read path remains useful for
        the clean data endpoint as well as the model service.
        """
        spec = datasets(self.config).get(name)
        if not spec or spec.source != "qlib_provider":
            return self.query(name, start, end)
        provider = path(spec.params.get("provider_uri", ""))
        calendar_path = provider / "calendars" / "day.txt"
        if not start or not end:
            if not calendar_path.exists():
                raise DataError(f"provider calendar not found: {calendar_path}")
            days = [line.strip()[:10] for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not days:
                raise DataError(f"provider calendar is empty: {calendar_path}")
            start = start or days[0]
            end = end or days[-1]
        config = self.config if symbols is None else {**self.config, "universe": symbols, "universe_file": None}
        rows = self.adapters[spec.source].fetch(spec, asof=end, start=start, config=config)
        return self.normalize(spec, rows)

    def acquire_all(self, specs: dict[str, DatasetSpec], asof: str, start: str | None = None) -> list[dict[str, Any]]:
        return [self.fetch(spec, asof, start) for spec in specs.values()]

    def status(self) -> list[dict[str, Any]]:
        result = []
        for name, spec in datasets(self.config).items():
            target = self._file(name)
            manifest_path = self.root / f"{name}.manifest.json"
            item: dict[str, Any] = {"dataset": name, "source": spec.source, "status": "MISSING"}
            if target.exists():
                frame = pd.read_csv(target, dtype={spec.symbols_field: "string"})
                item.update(status="READY" if not frame.empty else "MISSING", rows=len(frame), latest_asof=str(frame[spec.date_field].max()) if not frame.empty else None)
            elif spec.source == "qlib_provider":
                provider = path(spec.params.get("provider_uri", "")); calendar = provider / "calendars" / "day.txt"
                days = [line.strip()[:10] for line in calendar.read_text(encoding="utf-8").splitlines() if line.strip()] if calendar.exists() else []
                symbols = universe(self.config)
                if days and symbols:
                    count, latest, missing = 0, None, []
                    for symbol in symbols:
                        folder = provider / "features" / symbol.lower()
                        try:
                            if any(not (folder / f"{field}.day.bin").is_file()
                                   for field in ("open", "high", "low", "close", "volume", "vwap")):
                                raise DataError("required OHLCV field missing")
                            close = QlibProviderAdapter._decode(folder / "close.day.bin", len(days))
                            valid = np.flatnonzero(np.isfinite(close) & (close > 0))
                            count += len(valid)
                            if len(valid):
                                latest = max(latest or "", days[valid[-1]])
                            else:
                                missing.append(symbol)
                        except (DataError, OSError, ValueError):
                            missing.append(symbol)
                    item.update(status="READY" if count and not missing else "BLOCKED",
                                rows=count, latest_asof=latest, calendar_latest=days[-1],
                                storage="qlib_provider", row_definition="finite_positive_close",
                                missing_symbols=missing)
            if manifest_path.exists():
                item["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
            result.append(item)
        return result
