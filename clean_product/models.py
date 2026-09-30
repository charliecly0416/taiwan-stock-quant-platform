from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import pickle
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
import yaml

from .artifacts import manifest, write_json
from .config import env_config, path, universe
from .validation import pipeline_fingerprint, validate_baseline, validate_signal_rows, verify_file


class ModelBlocked(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass
class SignalResult:
    model: str
    asof: str
    rows: pd.DataFrame
    status: str = "READY"
    reason: str | None = None
    artifact_dir: Path | None = None
    full_ranks: dict[str, int] | None = None


class StageRegistry:
    def __init__(self) -> None:
        self._stages: dict[str, Callable[..., pd.DataFrame]] = {}

    def register(self, name: str, fn: Callable[..., pd.DataFrame]) -> None:
        self._stages[name] = fn

    def run(self, name: str, frame: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        if name not in self._stages:
            raise ModelBlocked("UNKNOWN_MODEL_STAGE", name)
        return self._stages[name](frame, **kwargs)


@lru_cache(maxsize=8)
def _pickle(pathname: str):
    with Path(pathname).open("rb") as handle:
        return pickle.load(handle)


@lru_cache(maxsize=4)
def _parquet(pathname: str) -> pd.DataFrame:
    return pd.read_parquet(pathname)


@lru_cache(maxsize=4)
def _joblib(pathname: str):
    return joblib.load(pathname)


@lru_cache(maxsize=4)
def _csv(pathname: str, mtime_ns: int, size: int) -> pd.DataFrame:
    return pd.read_csv(pathname)


def _verify_stage_assets(stage: dict) -> None:
    for key, filename in (("model", "model_path"), ("training_manifest", "training_manifest"),
                          ("inference_config", "inference_config"),
                          ("raw_prediction_archive", "raw_prediction_archive"),
                          ("feature_schema", "feature_schema"),
                          ("historical_features", "historical_features"),
                          ("prediction_archive", "prediction_archive")):
        if stage.get(key + "_sha256"):
            verify_file(stage[filename], stage[key + "_sha256"])
    if stage.get("feature_delta"):
        verify_file(stage["feature_delta"], stage["feature_delta_sha256"])


def _rank(frame: pd.DataFrame, *, score: str = "score") -> pd.DataFrame:
    output = frame.copy()
    output[score] = pd.to_numeric(output[score], errors="coerce")
    output = output[np.isfinite(output[score])].sort_values([score, "instrument"], ascending=[False, True], kind="mergesort")
    output["rank"] = np.arange(1, len(output) + 1)
    return output[["date", "instrument", score, "rank"]].rename(columns={score: "score"}).reset_index(drop=True)


def _fixture_model_a(_: pd.DataFrame, *, asof: str, data: dict[str, pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
    prices = data.get("prices", pd.DataFrame()).copy()
    if "instrument" not in prices and "stock_id" in prices:
        prices = prices.rename(columns={"stock_id": "instrument"})
    prices["instrument"] = "TW" + prices.instrument.astype(str).str.extract(r"(\d+)")[0].str.zfill(4)
    prices["date"] = prices.get("date", pd.Series(dtype=str)).astype(str)
    rows = prices[prices.date.eq(asof)].copy()
    if rows.empty:
        raise ModelBlocked("FIXTURE_PRICE_DATE_MISSING", asof)
    rows["score"] = pd.to_numeric(rows.get("score", rows.get("close")), errors="coerce")
    return _rank(rows[["date", "instrument", "score"]])


def _archive_prediction(stage: dict, asof: str) -> pd.DataFrame | None:
    target = path(stage["prediction_archive"])
    if not target.exists():
        return None
    if target.suffix == ".csv":
        if stage.get("prediction_archive_sha256"):
            verify_file(target, stage["prediction_archive_sha256"])
        stat = target.stat()
        frame = _csv(str(target), stat.st_mtime_ns, stat.st_size)
        rows = frame[frame.date.astype(str).eq(asof)].rename(columns={
            stage.get("archive_score_column", "score"): "score",
            stage.get("archive_rank_column", "rank"): "rank"})
        if rows.empty:
            return None
        rows = rows[["date", "instrument", "score", "rank"]].sort_values("rank").reset_index(drop=True)
        validate_signal_rows(rows, asof)
        if stage.get("raw_prediction_archive"):
            raw_path = verify_file(stage["raw_prediction_archive"], stage["raw_prediction_archive_sha256"])
            raw_stat = raw_path.stat()
            raw = _csv(str(raw_path), raw_stat.st_mtime_ns, raw_stat.st_size)
            raw = raw[raw.date.astype(str).eq(asof)].rename(columns={
                stage.get("archive_score_column", "score"): "score",
                stage.get("raw_archive_rank_column", "rank"): "rank"})
            validate_signal_rows(raw, asof)
            aligned = rows.merge(raw[["instrument", "score"]], on="instrument", how="left", suffixes=("", "_raw"), validate="one_to_one")
            if not aligned.score.eq(aligned.score_raw).all():
                raise ModelBlocked("MODELA_ARCHIVE_SCORE_MISMATCH")
            rows.attrs["full_qlib_ranks"] = dict(zip(raw.instrument, raw['rank'].astype(int)))
        return rows
    prediction = _pickle(str(target))
    frame = prediction.rename("score").to_frame() if isinstance(prediction, pd.Series) else prediction.copy()
    if "score" not in frame:
        frame.columns = ["score"]
    frame = frame.reset_index().rename(columns={"datetime": "date"})
    if not {"date", "instrument", "score"}.issubset(frame):
        return None
    frame["date"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
    rows = frame[frame.date.eq(asof)][["date", "instrument", "score"]]
    return _rank(rows) if not rows.empty else None


def _qlib_prediction(stage: dict, config: dict, asof: str) -> pd.DataFrame:
    rows = _qlib_prediction_range(stage, config, asof, asof).get(asof)
    if rows is None or rows.empty:
        raise ModelBlocked("MODELA_PROVIDER_DATE_MISSING", asof)
    return rows


def _selected_universe(stage: dict, start: str, end: str) -> set[tuple[str, str]]:
    """Apply the frozen E1 as-of post-score policy, never the current Top150."""
    source = path(stage["selection_prices"]); universe_file = path(stage["selection_universe"])
    if not source.is_dir() or not universe_file.is_file():
        raise ModelBlocked("MODELA_SELECTION_INPUT_MISSING")
    frames = []
    for filename in sorted(source.glob("TW*.csv")):
        if filename.stem == "TWII":
            continue
        rows = pd.read_csv(filename, usecols=["date", "close", "vwap", "volume"])
        rows["date"] = rows.date.astype(str).str[:10]
        rows = rows[rows.date.between(str(stage["handler_start"]), end)].sort_values("date")
        if rows.empty:
            continue
        close = pd.to_numeric(rows.close, errors="coerce")
        volume = pd.to_numeric(rows.volume, errors="coerce")
        vwap = pd.to_numeric(rows.vwap, errors="coerce")
        value = vwap.where(vwap.notna() & vwap.gt(0), close) * volume
        rows["trailing_value_60"] = value.rolling(60, min_periods=20).mean()
        valid = close.notna() & close.gt(0) & volume.notna() & volume.ge(0)
        valid &= pd.Series(np.arange(1, len(rows) + 1), index=rows.index).ge(60)
        valid &= rows.trailing_value_60.notna() & rows.date.between(start, end)
        selected = rows.loc[valid, ["date", "trailing_value_60"]].copy()
        selected["instrument"] = filename.stem.upper(); frames.append(selected)
    if not frames or not any(len(frame) for frame in frames):
        raise ModelBlocked("MODELA_SELECTION_DATE_UNAVAILABLE", f"{start}..{end}")
    frame = pd.concat(frames, ignore_index=True)
    ranges = pd.read_csv(universe_file, sep="\t", names=["instrument", "start", "end"])
    frame = frame.merge(ranges, on="instrument", how="inner")
    frame = frame[frame.date.ge(frame.start) & frame.date.le(frame.end)]
    frame = frame.drop_duplicates(["date", "instrument"]).sort_values(
        ["date", "trailing_value_60"], ascending=[True, False], kind="stable")
    frame = frame.groupby("date", group_keys=False).head(150)
    if frame.empty:
        raise ModelBlocked("MODELA_SELECTION_DATE_UNAVAILABLE", f"{start}..{end}")
    return set(frame[["date", "instrument"]].itertuples(index=False, name=None))


def _qlib_prediction_range(stage: dict, config: dict, start: str, end: str) -> dict[str, pd.DataFrame]:
    provider = path(stage["provider_uri"]); model_path = path(stage["model_path"])
    selected = _selected_universe(stage, start, end) if stage.get("selection_prices") else None
    import qlib
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.data.dataset import DatasetH
    qlib.init(provider_uri=str(provider), region="tw", expression_cache=None, dataset_cache=None)
    rank_scope = str(stage.get("rank_scope", "full")).lower()
    if rank_scope not in {"full", "selected"}:
        raise ModelBlocked("MODELA_RANK_SCOPE_INVALID", rank_scope)
    if rank_scope == "selected" and selected:
        instruments = sorted({symbol for day, symbol in selected if start <= day <= end})
    else:
        instruments = universe(config)
    handler = {"class": "Alpha158", "module_path": "qlib.contrib.data.handler", "kwargs": {
        "start_time": stage.get("handler_start", "2015-05-04"), "end_time": end,
        "fit_start_time": stage.get("fit_start", stage.get("handler_start", "2015-05-04")), "fit_end_time": str(stage.get("fit_end", "2022-12-31")),
        "instruments": instruments,
    }}
    if stage.get("inference_config"):
        frozen = yaml.safe_load(path(stage["inference_config"]).read_text())
        handler = frozen["task"]["dataset"]["kwargs"]["handler"]
        handler["kwargs"]["end_time"] = end
    model = _pickle(str(model_path))
    if not isinstance(model, LGBModel): raise ModelBlocked("MODELA_IDENTITY_MISMATCH", str(type(model)))
    # Alpha158 materializes a large feature matrix.  Keep the historical
    # cross-section semantics while bounding peak memory for the full Taiwan
    # universe.  A chunk is scored independently and ranks are assigned only
    # after all chunks are merged, so chunking cannot change ordering.
    chunk_size = max(1, int(stage.get("inference_chunk_size", 250)))
    predictions = []
    for offset in range(0, len(instruments), chunk_size):
        chunk_handler = dict(handler)
        chunk_kwargs = dict(handler.get("kwargs", {}))
        chunk_kwargs["instruments"] = instruments[offset:offset + chunk_size]
        chunk_handler["kwargs"] = chunk_kwargs
        dataset = DatasetH(handler=chunk_handler, segments={"window": (start, end)})
        predictions.append(model.predict(dataset, segment="window").rename("score").to_frame().reset_index().rename(columns={"datetime": "date"}))
    if not predictions:
        raise ModelBlocked("MODELA_PROVIDER_UNIVERSE_EMPTY")
    prediction = pd.concat(predictions, ignore_index=True)
    prediction["date"] = pd.to_datetime(prediction.date).dt.date.astype(str)
    result = {}
    for day, rows in prediction.groupby("date"):
        full = _rank(rows[["date", "instrument", "score"]])
        expected = {symbol for selected_day, symbol in (selected or ()) if selected_day == day}
        missing = expected - set(full.instrument)
        if missing:
            raise ModelBlocked("MODELA_SELECTED_PRICE_OR_FEATURE_MISSING", ",".join(sorted(missing)[:10]))
        candidates = full if selected is None else full[full.instrument.map(lambda symbol: (day, symbol) in selected)]
        ranked = _rank(candidates)
        ranked.attrs["full_qlib_ranks"] = dict(zip(full.instrument, full['rank'].astype(int)))
        result[day] = ranked
    return result


def _model_a_frozen(frame: pd.DataFrame, *, asof: str, config: dict, stage: dict, fixture: bool, data: dict[str, pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
    if fixture:
        return _fixture_model_a(frame, asof=asof, data=data)
    cached = data.get("__model_a_signals", {}).get(asof)
    if cached is not None:
        return cached.copy()
    archived = _archive_prediction(stage, asof)
    return archived if archived is not None else _qlib_prediction(stage, config, asof)


def _fixture_b(frame: pd.DataFrame, *, asof: str, data: dict[str, pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
    output = frame.head(50).copy()
    prices = data.get("prices", pd.DataFrame()).copy()
    if "instrument" not in prices and "stock_id" in prices:
        prices = prices.rename(columns={"stock_id": "instrument"})
    if not prices.empty:
        prices = prices[prices.date.astype(str).le(asof)].copy()
        prices["instrument"] = "TW" + prices.instrument.astype(str).str.extract(r"(\d+)")[0].str.zfill(4)
        prices = prices.sort_values(["instrument", "date"])
        prices["momentum"] = prices.groupby("instrument")["close"].pct_change(1)
        latest = prices.groupby("instrument", as_index=False).tail(1)[["instrument", "momentum"]]
        output = output.merge(latest, on="instrument", how="left")
        output["score"] = output["score"] + output["momentum"].fillna(0) * .01
    return _rank(output[["date", "instrument", "score"]])


def _b19r2r(frame: pd.DataFrame, *, asof: str, config: dict, stage: dict, fixture: bool, data: dict[str, pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
    if fixture:
        excluded = {str(item).upper() for item in stage.get("exclude", [])}
        exact = frame.head(50)
        return _fixture_b(exact[~exact.instrument.isin(excluded)], asof=asof, data=data)
    exact = frame.head(50).copy()
    excluded = {str(item).upper() for item in stage.get("exclude", [])}
    exact = exact[~exact.instrument.astype(str).str.upper().isin(excluded)].copy()
    schema = json.loads(path(stage["feature_schema"]).read_text(encoding="utf-8"))
    order = list(schema.get("feature_order") or [])
    if len(order) != 78 or len(set(order)) != 78:
        raise ModelBlocked("B19R2R_FEATURE_SCHEMA_INVALID")
    historical = path(stage["historical_features"])
    features = _parquet(str(historical)).copy() if historical.exists() else pd.DataFrame()
    delta = path(stage["feature_delta"]) if stage.get("feature_delta") else None
    if delta:
        verify_file(delta, stage.get("feature_delta_sha256"))
        current = pd.read_parquet(delta)
        current["date"] = current.date.astype(str).str[:10]
        if (current.empty or current.date.nunique() != 1 or current.duplicated(["date", "instrument"]).any()
                or (not features.empty and current.date.min() <= features.date.astype(str).str[:10].max())):
            raise ModelBlocked("B19R2R_DELTA_SCOPE_INVALID")
        features = pd.concat([features, current], ignore_index=True)
    if not features.empty:
        features["date"] = features["date"].astype(str).str[:10]
        features = features[features.date.eq(asof)]
    if features.empty:
        # A same-named, finite column is not proof of the frozen PIT transform.
        # New dates need an admitted feature producer with availability lineage.
        raise ModelBlocked("B19R2R_VALIDATED_78F_UNAVAILABLE", asof)
    if "feature_raw_complete_78" in features:
        features = features[features.feature_raw_complete_78.eq(True)]
    features = exact[["date", "instrument"]].merge(features, on=["date", "instrument"], how="left", validate="one_to_one")
    numeric = features.reindex(columns=order).apply(pd.to_numeric, errors="coerce")
    missing = [name for name in order if name not in numeric or not np.isfinite(numeric[name]).all()]
    if missing:
        raise ModelBlocked("B19R2R_INCOMPLETE_78F", ",".join(missing[:8]))
    training_manifest = json.loads(path(stage["training_manifest"]).read_text(encoding="utf-8"))
    if training_manifest.get("model_id") != "modelb_b19r2r_lambdarank_exact50_78f_v2":
        raise ModelBlocked("B19R2R_IDENTITY_MISMATCH")
    model = _joblib(str(path(stage["model_path"])))
    if list(model.booster_.feature_name()) != order:
        raise ModelBlocked("B19R2R_FEATURE_ORDER_MISMATCH")
    scored = exact[["date", "instrument"]].copy()
    scored["score"] = np.asarray(model.predict(numeric[order]), dtype=float)
    return _rank(scored)


class ModelRunner:
    """Execute every registered model through one stage contract."""

    def __init__(self, config: dict):
        self.config = env_config(config)
        self.stages = StageRegistry()
        self.stages.register("model_a_frozen", _model_a_frozen)
        self.stages.register("b19r2r_frozen", _b19r2r)

    def run(self, model_name: str, asof: str, *, data: dict[str, pd.DataFrame] | None = None, fixture: bool = False, write: bool = True) -> SignalResult:
        spec = (self.config.get("models") or {}).get(model_name)
        if not spec:
            raise ValueError(f"unknown model: {model_name}")
        data, frame = data or {}, pd.DataFrame()
        status, reason = "READY", None
        full_ranks, candidate_ranks = {}, {}
        try:
            if not fixture:
                validate_baseline(self.config)
            if not spec.get("stages"):
                raise ModelBlocked("MODEL_PIPELINE_EMPTY")
            for stage_name in spec.get("stages", []):
                stage = (self.config.get("model_stages") or {}).get(stage_name, {})
                if not fixture:
                    _verify_stage_assets(stage)
                frame = self.stages.run(stage_name, frame, asof=asof, config=self.config, stage=stage, fixture=fixture, data=data)
                validate_signal_rows(frame, asof)
                if stage_name == "model_a_frozen":
                    candidate_ranks = dict(zip(frame.instrument.astype(str), frame['rank'].astype(int)))
                    full_ranks = frame.attrs.get("full_qlib_ranks", candidate_ranks)
            frame["candidate_rank"] = frame.instrument.map(candidate_ranks).fillna(frame['rank']).astype(int)
            frame["full_qlib_rank"] = frame.instrument.map(full_ranks).fillna(frame['rank']).astype(int)
            frame["score_rank"] = frame["rank"]
            frame["buy_score"] = frame["score"]
        except ModelBlocked as exc:
            status, reason = "BLOCKED", str(exc)
            frame = pd.DataFrame(columns=["date", "instrument", "score", "rank"])
        except Exception as exc:
            status, reason = "BLOCKED", f"MODEL_INPUT_INVALID: {type(exc).__name__}: {exc}"
            frame = pd.DataFrame(columns=["date", "instrument", "score", "rank"])
        base = self.config["artifact_root"] / "dry_runs" / "signals" if fixture else self.config["artifact_root"] / "signals"
        output = base / model_name / asof
        if status != "READY" and not fixture:
            output = self.config["artifact_root"] / "failed_runs" / "signals" / model_name / asof / uuid4().hex
        if write:
            output.mkdir(parents=True, exist_ok=True)
            signals = output / "signals.csv"
            frame.to_csv(signals, index=False)
            write_json(output / "manifest.json", manifest(
                artifact_type="ModelSignalArtifact", status=status, asof=asof, run_id=f"{model_name}-{asof}",
                files={"signals": signals}, model=model_name, label=spec.get("label", model_name), role=spec.get("role"),
                production_allowed=bool(spec.get("production_allowed")), reason=reason, row_count=len(frame), fixture=fixture,
                canonical_id=spec.get("canonical_id", model_name),
                pipeline_fingerprint=pipeline_fingerprint(self.config, model_name), full_qlib_ranks=full_ranks,
                baseline_candidate_ranks=candidate_ranks,
            ))
        return SignalResult(model_name, asof, frame, status, reason, output if write else None, full_ranks)

    def precompute(self, dates: list[str], *, data: dict[str, Any], fixture: bool = False) -> None:
        if fixture or not dates: return
        validate_baseline(self.config)
        stage = self.config["model_stages"]["model_a_frozen"]; ready: dict[str, pd.DataFrame] = {}; missing = []
        _verify_stage_assets(stage)
        for day in dates:
            archived = _archive_prediction(stage, day)
            if archived is None: missing.append(day)
            else: ready[day] = archived
        if missing:
            ready.update(_qlib_prediction_range(stage, self.config, min(missing), max(missing)))
        data["__model_a_signals"] = ready
