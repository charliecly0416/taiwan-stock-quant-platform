from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from zoneinfo import ZoneInfo
from pathlib import Path
from uuid import uuid4
import fcntl

from .artifacts import manifest, utc_now, write_json
from .config import CONFIG_PATH, datasets, env_config, load_config, models, path, trading_days
from .data import DataCatalog, DataError
from .features import build_b19_features, derive_available_at, validate_b19_inputs, write_b19_feature_artifact
from .models import ModelBlocked, ModelRunner
from .strategy import top50_exit_one_worst_sell


def _load_data(catalog: DataCatalog, names: list[str], *, asof: str, fixture: bool) -> dict:
    output = {}
    for name in names:
        if not fixture and catalog.config.get("datasets", {}).get(name, {}).get("source") == "qlib_provider":
            continue  # Frozen Qlib reads its provider; do not duplicate millions of rows.
        try:
            output[name] = catalog.query(name, end=asof, allow_fixture=fixture)
        except DataError:
            if name == "prices" and not fixture:
                try:
                    output[name] = catalog.query_local_source(name, "2015-01-01", asof)
                except DataError:
                    pass
    return output


def _prepare_shadow_features(*, config: dict, data: dict, asof: str, run_id: str,
                             model_a: object) -> dict:
    """Build and register the current 78F delta without replacing history."""
    stage = config["model_stages"]["b19r2r_frozen"]
    schema_path = path(stage["feature_schema"])
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    order = list(schema.get("feature_order") or [])
    derive_available_at(asof=asof, data=data, config=config)
    validate_b19_inputs(asof=asof, data=data, config=config)
    frame = build_b19_features(asof=asof, model_a=model_a, data=data,
                               config=config, feature_order=order)
    artifact = write_b19_feature_artifact(frame=frame, asof=asof, config=config,
                                          feature_order=order, run_id=run_id)
    stage["feature_delta"] = artifact["path"]
    stage["feature_delta_sha256"] = artifact["sha256"]
    return artifact


def run_daily(asof: str | None = None, *, config_path: Path = CONFIG_PATH, dry_run: bool = False, trigger_reason: str = "manual", local_only: bool = False, publish: bool = False) -> dict:
    if publish and dry_run:
        raise ValueError("FIXTURE_PUBLICATION_FORBIDDEN")
    if not publish:
        return _run_daily(asof, config_path=config_path, dry_run=dry_run, trigger_reason=trigger_reason, local_only=local_only)
    config = env_config(load_config(config_path))
    store = config["_artifact_store"]
    store.mkdir(parents=True, exist_ok=True)
    with (store / "daily.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "BLOCKED", "reason": "DAILY_ALREADY_RUNNING", "latest_pointer_written": False}
        started = utc_now()
        attempt = {"status": "RUNNING", "asof": asof, "started_at": started,
                   "created_at": started, "trigger_reason": trigger_reason,
                   "active_asof": config.get("_active_release", {}).get("asof"),
                   "run_id": f"attempt-{uuid4().hex}", "local_only": local_only,
                   "latest_pointer_written": False}
        def record(payload):
            write_json(store / "daily_status.json", payload)
            if trigger_reason == "scheduled":
                write_json(store / "scheduler_status.json", payload)
        record(attempt)
        try:
            result = _run_daily(asof, config_path=config_path, dry_run=dry_run,
                                trigger_reason=trigger_reason, local_only=local_only, publish=True)
        except Exception as exc:
            result = {**attempt, "status": "BLOCKED", "created_at": utc_now(),
                      "reason": f"DAILY_EXECUTION_FAILED: {type(exc).__name__}"}
            record(result)
            write_json(store / "daily" / (asof or "attempts") / attempt["run_id"] / "run.json", result)
            raise
        result = {**attempt, **result, "created_at": utc_now()}
        record(result)
        write_json(store / "daily" / (result.get("asof") or "attempts") / result["run_id"] / "run.json", result)
        return result


def _run_daily(asof: str | None = None, *, config_path: Path = CONFIG_PATH, dry_run: bool = False, trigger_reason: str = "manual", local_only: bool = False, publish: bool = False) -> dict:
    if trigger_reason not in ("manual", "scheduled"):
        raise ValueError("trigger_reason must be manual or scheduled")
    config = env_config(load_config(config_path))
    if config.get("daily", {}).get("shadow_separate"):
        config["daily"]["include_shadow"] = False
    if asof is None and publish and not local_only:
        from .provider_refresh import market_asof
        asof = market_asof(config, datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat())
        if config.get("_active_release", {}).get("asof") == asof:
            from .service import ProductService
            if ProductService(config).readiness()["ready"]:
                result = {"status": "READY", "reason": "NO_NEW_MARKET_SESSION", "asof": asof,
                          "trigger_reason": trigger_reason, "created_at": utc_now(), "latest_pointer_written": False}
                return result
    asof = asof or date.today().isoformat()
    date.fromisoformat(asof)
    store = config.get("_artifact_store", config["artifact_root"])
    active = config.get("_active_release", {})
    if publish and active.get("asof", "") > asof:
        raise ValueError("DAILY_PUBLICATION_DATE_REGRESSION")
    run_id = f"{asof}-{utc_now()}-{uuid4().hex[:8]}"
    if publish:
        config["artifact_root"] = store / "releases" / run_id
        config["data_root"] = config["artifact_root"] / "data"
        config.setdefault("agent", {})["prompt_root"] = str(config["artifact_root"] / "agent_daily_prompt")
        # Use actual instrument lifetimes, not a one-day bridge export that
        # accidentally excludes every earlier date from replay and paper.
        stage = config["model_stages"]["model_a_frozen"]
        stage["selection_universe"] = str(Path(stage["provider_uri"]) / "instruments/all.txt")
    refresh = {"status": "SKIPPED", "reason": "disabled_or_fixture"}
    if not dry_run and not local_only and (config.get("provider_refresh") or {}).get("enabled") is True:
        try:
            from .provider_refresh import refresh_yahoo_provider
            refresh = refresh_yahoo_provider(config, asof, run_id)
            stage = config["model_stages"]["model_a_frozen"]
            stage["provider_uri"] = refresh["provider"]
            stage["selection_prices"] = refresh["selection_prices"]
            stage["selection_universe"] = refresh["universe_file"]
            config["universe_file"] = refresh["universe_file"]
            config["datasets"]["prices"].setdefault("params", {})["provider_uri"] = refresh["provider"]
        except Exception as exc:
            refresh = {"status": "BLOCKED", "reason": f"DATA_REFRESH_FAILED: {type(exc).__name__}"}
    catalog = DataCatalog(config); specs = datasets(config); acquired = []
    if refresh.get("status") == "BLOCKED":
        acquired.append({"dataset": "prices", "status": "BLOCKED", "reason": refresh["reason"]})
    if not dry_run and not local_only and refresh.get("status") != "BLOCKED":
        for name, spec in specs.items():
            if spec.source == "qlib_provider" and refresh.get("status") == "READY":
                acquired.append({"dataset": name, "status": "READY", "asof": asof, "source": spec.source})
                continue
            if config.get("daily", {}).get("include_shadow") is False and name not in {
                    dataset for model in config["models"].values() if model.get("role") == "baseline"
                    for dataset in model.get("required_datasets", ["prices"])}:
                continue
            try:
                acquired.append({"status": "READY", **catalog.fetch(spec, asof)})
            except Exception as exc:
                acquired.append({"dataset": name, "status": "BLOCKED",
                                 "reason": f"DATA_ACQUISITION_FAILED: {type(exc).__name__}"})
    data = _load_data(catalog, list(specs), asof=asof, fixture=dry_run)
    # Frozen Qlib stages read their provider directly.  Shadow feature
    # construction needs a bounded OHLCV history, so load only the configured
    # lookback instead of duplicating the full provider in every daily run.
    if config.get("daily", {}).get("include_shadow") is True and not dry_run:
        try:
            start = (date.fromisoformat(asof) - timedelta(days=400)).isoformat()
            data["prices"] = catalog.query_local_source("prices", start, asof)
        except DataError as exc:
            data["__shadow_price_error"] = str(exc)
    runner = ModelRunner(config); tracks = []
    failed_datasets = {item["dataset"] for item in acquired if item["status"] != "READY"}
    ordered_models = sorted(models(config).items(), key=lambda item: (item[1].role != "baseline", item[0]))
    for name, spec in ordered_models:
        if spec.role == "shadow" and config.get("daily", {}).get("include_shadow") is False:
            tracks.append({"model": name, "role": spec.role, "status": "SKIPPED",
                           "reason": "SHADOW_SCHEDULED_SEPARATELY" if config.get("daily", {}).get("shadow_separate") else "SHADOW_RESEARCH_ON_DEMAND", "signal_rows": 0,
                           "intents": [], "mainline_blocking": False, "feature_artifact": None})
            continue
        required = config["models"][name].get("required_datasets", ["prices"])
        missing = sorted(set(required) & failed_datasets)
        if missing:
            tracks.append({"model": name, "role": spec.role, "status": "BLOCKED",
                           "reason": "REQUIRED_DATASET_UNAVAILABLE: " + ",".join(missing),
                           "signal_rows": 0, "intents": [], "mainline_blocking": spec.role == "baseline",
                           "feature_artifact": None})
            continue
        feature_artifact = None
        if spec.role == "shadow" and config.get("daily", {}).get("include_shadow") is True and not dry_run:
            try:
                if data.get("__shadow_price_error"):
                    raise ModelBlocked("B19R2R_PRICE_HISTORY_MISSING", data["__shadow_price_error"])
                model_a = data.get("__model_a_signals", {}).get(asof)
                if model_a is None:
                    raise ModelBlocked("B19R2R_MODELA_SIGNAL_MISSING", asof)
                feature_artifact = _prepare_shadow_features(config=config, data=data, asof=asof,
                                                            run_id=run_id, model_a=model_a)
            except ModelBlocked as exc:
                tracks.append({"model": name, "role": spec.role, "status": "BLOCKED",
                               "reason": str(exc), "signal_rows": 0, "intents": [],
                               "mainline_blocking": False, "feature_artifact": None})
                continue
            except Exception as exc:
                tracks.append({"model": name, "role": spec.role, "status": "BLOCKED",
                               "reason": f"SHADOW_FEATURE_BUILD_FAILED: {type(exc).__name__}",
                               "signal_rows": 0, "intents": [], "mainline_blocking": False,
                               "feature_artifact": None})
                continue
        try:
            if feature_artifact:
                runner = ModelRunner(config)
            signal = runner.run(name, asof, data=data, fixture=dry_run)
        except Exception as exc:
            tracks.append({"model": name, "role": spec.role, "status": "BLOCKED",
                           "reason": f"MODEL_EXECUTION_FAILED: {type(exc).__name__}", "signal_rows": 0,
                           "intents": [], "mainline_blocking": spec.role == "baseline"})
            continue
        intent_rows = []
        if signal.status == "READY":
            if spec.role == "baseline":
                cached = signal.rows.copy()
                cached.attrs["full_qlib_ranks"] = signal.full_ranks
                data["__model_a_signals"] = {asof: cached}
            intents = top50_exit_one_worst_sell(signal.rows, max_positions=int(config.get("simulation", {}).get("max_positions", 50)), full_ranks=signal.full_ranks)
            intent_rows = intents.to_dict("records")
            intent_root = config["artifact_root"] / "dry_runs" / "intents" if dry_run else config["artifact_root"] / "intents"
            target = intent_root / name / asof
            target.mkdir(parents=True, exist_ok=True); intents.to_csv(target / "intents.csv", index=False)
            write_json(target / "manifest.json", manifest(
                artifact_type="OrderIntentArtifact", status="READY", asof=asof,
                run_id=f"{name}-{asof}", files={"intents": target / "intents.csv"},
                model=name, strategy=config.get("strategy"), execution=config.get("execution"),
                source_signal=str(signal.artifact_dir / "manifest.json") if signal.artifact_dir else None,
                fixture=dry_run, readonly=True, simulation_only=True))
        tracks.append({"model": name, "role": spec.role, "status": signal.status, "reason": signal.reason,
                       "signal_rows": len(signal.rows), "intents": intent_rows,
                       "mainline_blocking": spec.role == "baseline", "feature_artifact": feature_artifact})
    baseline = next((item for item in tracks if item["role"] == "baseline"), None)
    status = "READY" if baseline and baseline["status"] == "READY" else "BLOCKED"
    history = []
    if publish and status == "READY":
        count = max(1, min(5, int(config.get("daily", {}).get("history_sessions", 1))))
        days = [day for day in trading_days(config) if day < asof]
        for day in (days[-(count - 1):] if count > 1 else []):
            prior = runner.run(baseline["model"], day, data={}, fixture=False)
            history.append({"asof": day, "status": prior.status, "signal_rows": len(prior.rows), "reason": prior.reason})
            if prior.status != "READY":
                status = "BLOCKED"
    prompt = {'status': 'DISABLED', 'mainline_blocking': False}
    if config.get('agent', {}).get('build_daily_prompt') is True:
        if dry_run or status != 'READY':
            prompt = {'status': 'SKIPPED', 'reason': 'FIXTURE_OR_BASELINE_BLOCKED', 'mainline_blocking': False}
        else:
            try:
                from .agent_builder import build_prompt
                prompt = {**build_prompt(config, asof, config['artifact_root'] / 'agent_daily_prompt'), 'mainline_blocking': False}
            except Exception as exc:
                prompt = {'status': 'BLOCKED', 'reason': f'AGENT_BUILD_FAILED: {type(exc).__name__}', 'mainline_blocking': False}
    result = {"schema_version": "tw.clean.daily.v1", "asof": asof, "status": status, "datasets": acquired, "models": tracks, "readonly": True, "simulation_only": True, "dry_run": dry_run,
              "run_id": run_id, "trigger_reason": trigger_reason,
              "created_at": utc_now(), "agent_prompt": prompt, "local_only": local_only,
              "provider_refresh": refresh, "history_signals": history, "keep_previous_latest_on_failure": True, "latest_pointer_written": False}
    if publish:
        from .service import ProductService
        if status == "READY" and config.get("agent", {}).get("build_daily_prompt") and prompt.get("status") != "READY":
            result.update(status="BLOCKED", reason="RELEASE_AGENT_UNAVAILABLE")
        elif status == "READY" and not ProductService(config).readiness()["ready"]:
            result.update(status="BLOCKED", reason="RELEASE_READINESS_FAILED")
        if result["status"] == "READY":
            stage = config["model_stages"]["model_a_frozen"]
            release = {"schema_version": "tw.clean.release.v1", "asof": asof, "run_id": run_id,
                       "artifact_root": str(config["artifact_root"].resolve()),
                       "provider": stage["provider_uri"], "selection_prices": stage["selection_prices"],
                       "universe_file": stage["selection_universe"], "created_at": utc_now(),
                       "config_universe_file": config.get("universe_file")}
            shadow = next((item for item in tracks if item.get("role") == "shadow"), None)
            if shadow and shadow.get("feature_artifact"):
                release["shadow_feature_delta"] = shadow["feature_artifact"]["path"]
                release["shadow_feature_delta_sha256"] = shadow["feature_artifact"]["sha256"]
            write_json(config["artifact_root"] / "release.json", release)
            write_json(store / "active.json", release)
            result["latest_pointer_written"] = True
    daily_root = store / "dry_runs" / "daily" if dry_run else store / "daily"
    output = daily_root / asof / result['run_id']
    output.mkdir(parents=True, exist_ok=False); write_json(output / "run.json", result)
    if trigger_reason == "scheduled":
        write_json(store / "scheduler_status.json", {key: result[key] for key in
                   ("status", "asof", "run_id", "trigger_reason", "created_at", "latest_pointer_written")})
    return result
