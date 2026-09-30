from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from .config import env_config, load_config, models, trading_days
from .data import DataCatalog, DataError
from .models import ModelRunner, SignalResult
from .replay import replay
from .strategy import top50_exit_one_worst_sell
from .validation import read_signal_artifact, validate_baseline, verify_file


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _stock_code(symbol: str) -> str:
    match = re.fullmatch(r"(?:TW)?([0-9]{4,6})", symbol.strip(), re.IGNORECASE) if isinstance(symbol, str) else None
    if not match:
        raise ValueError("symbol must be a Taiwan stock code (4–6 digits, optional TW prefix)")
    return match.group(1)


def _technical(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the small, explainable technical set used by the clean workbench."""
    if frame.empty:
        return frame.copy()
    output = frame.rename(columns={"stock_id": "instrument", "Trading_Volume": "volume"}).copy()
    output["instrument"] = "TW" + output.instrument.astype(str).str.extract(r"(\d+)")[0].str.zfill(4)
    output["date"] = output.date.astype(str).str[:10]
    output = output.sort_values(["instrument", "date"])
    output["close"] = pd.to_numeric(output["close"], errors="coerce")
    volume = pd.to_numeric(output.get("volume", pd.Series(index=output.index, dtype=float)), errors="coerce")
    grouped = output.groupby("instrument", group_keys=False)
    output["ma5"] = grouped["close"].transform(lambda values: pd.to_numeric(values, errors="coerce").rolling(5, min_periods=1).mean())
    output["ma20"] = grouped["close"].transform(lambda values: pd.to_numeric(values, errors="coerce").rolling(20, min_periods=1).mean())
    returns = grouped["close"].transform(lambda values: pd.to_numeric(values, errors="coerce").pct_change(fill_method=None))
    output["ret5"] = grouped["close"].transform(lambda values: pd.to_numeric(values, errors="coerce").pct_change(5, fill_method=None))
    output["ret20"] = grouped["close"].transform(lambda values: pd.to_numeric(values, errors="coerce").pct_change(20, fill_method=None))
    output["volatility20"] = returns.groupby(output["instrument"]).transform(lambda values: values.rolling(20, min_periods=5).std())
    output["volume_ratio20"] = volume / volume.groupby(output["instrument"]).transform(lambda values: values.rolling(20, min_periods=1).mean()).replace(0, np.nan)
    delta = grouped["close"].transform(lambda values: pd.to_numeric(values, errors="coerce").diff())
    gain = delta.clip(lower=0).groupby(output["instrument"]).transform(lambda values: values.rolling(14, min_periods=1).mean())
    loss = (-delta.clip(upper=0)).groupby(output["instrument"]).transform(lambda values: values.rolling(14, min_periods=1).mean())
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    output["rsi14"] = rsi.mask(loss.eq(0) & gain.gt(0), 100).fillna(50)
    return output


class ProductService:
    def __init__(self, config: dict | None = None) -> None:
        self.config = env_config(config or load_config()); self.catalog = DataCatalog(self.config); self.runner = ModelRunner(self.config)

    def trading_days(self) -> list[str]:
        return trading_days(self.config)

    def latest_asof(self) -> str | None:
        days = self.trading_days(); return days[-1] if days else None

    def _model_data(self, asof: str, start: str | None = None) -> dict[str, pd.DataFrame]:
        start = start or (date.fromisoformat(asof) - timedelta(days=400)).isoformat()
        data: dict[str, pd.DataFrame] = {"prices": self.catalog.query_local_source("prices", start, asof)}
        for name in ("institutional", "margin", "twii"):
            try: data[name] = self.catalog.query(name, start, asof)
            except DataError: pass
        return data

    def _stored_signal(self, model: str, asof: str) -> SignalResult | None:
        artifact_root = self.config["artifact_root"]
        if self.config["models"][model].get("role") == "shadow":
            if self.config.get("_shadow_error"):
                return SignalResult(model, asof, pd.DataFrame(), "BLOCKED", self.config["_shadow_error"])
            artifact_root = self.config.get("_shadow_root", artifact_root)
        root = artifact_root / "signals" / model / asof
        if not root.exists():
            shadow = self.config.get("_shadow_status", {})
            if (self.config["models"][model].get("role") == "shadow" and shadow.get("asof") == asof
                    and shadow.get("status") in {"BLOCKED", "RUNNING"}):
                return SignalResult(model, asof, pd.DataFrame(), "BLOCKED", shadow.get("reason", "SHADOW_RUNNING"))
            return None
        try:
            validate_baseline(self.config)
            payload, rows = read_signal_artifact(root, self.config, model, asof)
            return SignalResult(model, asof, rows, payload["status"], payload.get("reason"), root,
                                payload.get("full_qlib_ranks"))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            return SignalResult(model, asof, pd.DataFrame(columns=["date", "instrument", "score", "rank"]),
                                "BLOCKED", f"SIGNAL_ARTIFACT_INVALID: {exc}")

    def _track_status(self, model: str, asof: str | None) -> dict[str, Any]:
        signal = self._stored_signal(model, asof) if asof else None
        if signal is None:
            return {"status": "NO_ARTIFACT", "reason": "尚未生成正式模型产物", "asof": None, "rows": 0}
        return {"status": signal.status, "reason": signal.reason, "asof": signal.asof,
                "rows": len(signal.rows), "fixture": False}

    def signal(self, model: str, asof: str | None = None) -> SignalResult:
        asof = asof or self.latest_asof()
        if not asof: raise ValueError("no provider trading date available")
        stored = self._stored_signal(model, asof)
        if stored:
            return stored
        if self.config.get("datasets", {}).get("prices", {}).get("source") == "qlib_provider":
            data = {}  # Frozen stages read provider/features directly, never this duplicate price frame.
            if self.config["models"][model].get("role") == "shadow":
                baseline = self._stored_signal(self.config.get("product", {}).get("default_model", "model_a"), asof)
                if baseline and baseline.status == "READY":
                    cached = baseline.rows.copy()
                    cached.attrs["full_qlib_ranks"] = baseline.full_ranks
                    data["__model_a_signals"] = {asof: cached}
        else:
            data = self._model_data(asof)
        return self.runner.run(model, asof, data=data, write=False)

    def overview(self) -> dict[str, Any]:
        asof = self.latest_asof(); tracks = []
        for name, spec in models(self.config).items():
            snapshot = self._track_status(name, asof)
            tracks.append({"id": name, "label": self.config["models"][name].get("label", name), "description": self.config["models"][name].get("description"), "role": spec.role, "production_allowed": spec.production_allowed, **snapshot})
        default = self.config.get("product", {}).get("default_model", "model_a")
        baseline = next((item for item in tracks if item["id"] == default), {})
        data_status = self.catalog.status()
        required = set(self.config["models"][default].get("required_datasets", ["prices"]))
        for item in data_status:
            item["mainline_required"] = item["dataset"] in required
        return {"status": "READY" if baseline.get("status") == "READY" else "BLOCKED",
                "reason": baseline.get("reason"), "product": self.config.get("product", {}), "asof": asof, "strategy": self.config.get("strategy"), "execution": self.config.get("execution"), "models": tracks, "data": data_status, "operations": self.operations(), "examples": {**self.config.get("research_examples", {}), "paper_date": next((day for day in reversed(self.trading_days()) if day < (asof or "")), None)}, "readonly": True, "simulation_only": True}

    def readiness(self) -> dict[str, Any]:
        reasons = []
        asof = None
        try:
            validate_baseline(self.config)
            stage = self.config["model_stages"]["model_a_frozen"]
            if stage.get("model_sha256"):
                verify_file(stage["model_path"], stage["model_sha256"])
            asof = self.latest_asof()
            default = self.config.get("product", {}).get("default_model", "model_a")
            signal = self._stored_signal(default, asof) if asof else None
            if not asof:
                reasons.append("PROVIDER_CALENDAR_UNAVAILABLE")
            elif signal is None:
                reasons.append("BASELINE_SIGNAL_NOT_MATERIALIZED")
            elif signal.status != "READY":
                reasons.append(signal.reason or "BASELINE_SIGNAL_BLOCKED")
            if not reasons and self.config.get("agent", {}).get("build_daily_prompt"):
                from .agent import load_prompt
                load_prompt(self.config, asof)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            reasons.append(str(exc))
        return {"ready": not reasons, "status": "ready" if not reasons else "blocked",
                "asof": asof, "reasons": reasons, "scope": "validated_baseline_artifact",
                "readonly": True, "simulation_only": True}

    def rankings(self, model: str, asof: str | None = None, limit: int = 50) -> dict[str, Any]:
        result = self.signal(model, asof); spec = self.config["models"][model]
        artifact = None
        if result.artifact_dir:
            manifest_path = result.artifact_dir / "manifest.json"
            if manifest_path.exists():
                artifact = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {"status": result.status, "reason": result.reason, "model": model, "label": spec.get("label", model), "role": spec.get("role"), "asof": result.asof, "rows": _records(result.rows.head(limit)), "row_count": len(result.rows), "artifact": artifact, "readonly": True, "simulation_only": True}

    def compare(self, left: str, right: str, asof: str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        lhs, rhs = self.signal(left, asof), self.signal(right, asof)
        if lhs.status != "READY" or rhs.status != "READY":
            mainline_blocking = any(result.status != "READY" and self.config["models"][name].get("role") == "baseline" for name, result in ((left, lhs), (right, rhs)))
            return {"status": "BLOCKED", "asof": asof or self.latest_asof(), "left": {"model": left, "status": lhs.status, "reason": lhs.reason}, "right": {"model": right, "status": rhs.status, "reason": rhs.reason}, "mainline_blocking": mainline_blocking, "readonly": True}
        merged = lhs.rows[["instrument", "rank", "score"]].rename(columns={"rank": "left_rank", "score": "left_score"}).merge(rhs.rows[["instrument", "rank", "score"]].rename(columns={"rank": "right_rank", "score": "right_score"}), on="instrument", how="outer")
        merged["rank_change"] = merged.left_rank - merged.right_rank
        payload: dict[str, Any] = {"status": "READY", "asof": lhs.asof, "left": left, "right": right, "overlap_top50": len(set(lhs.rows.head(50).instrument) & set(rhs.rows.head(50).instrument)), "rows": _records(merged.sort_values("right_rank", na_position="last").head(60)), "readonly": True, "simulation_only": True}
        if start or end:
            if not start or not end:
                raise ValueError("comparison replay requires both start and end")
            payload["window"] = {"start": start, "end": end, "left": self.run_replay(left, start, end), "right": self.run_replay(right, start, end)}
        return payload

    def strategy(self, model: str, asof: str | None = None) -> dict[str, Any]:
        result = self.signal(model, asof)
        if result.status != "READY": return {"status": "BLOCKED", "reason": result.reason, "model": model, "asof": result.asof, "readonly": True}
        # A read-only strategy preview has no account holdings input.  Keep it
        # deterministic and fast by showing the current candidate intents;
        # replay is the only surface that carries holdings across days.
        intents = top50_exit_one_worst_sell(result.rows, set(), max_positions=int(self.config.get("simulation", {}).get("max_positions", 50)), full_ranks=result.full_ranks)
        return {"status": "READY", "model": model, "asof": result.asof, "strategy": self.config.get("strategy"), "execution": self.config.get("execution"), "top50": _records(result.rows.head(50)), "intents": _records(intents), "readonly": True, "simulation_only": True}

    def market(self, symbol: str, start: str, end: str) -> dict[str, Any]:
        digits = _stock_code(symbol)
        warmup_start = (date.fromisoformat(start) - timedelta(days=90)).isoformat()
        kwargs = {"symbols": ["TW" + digits]} if self.config.get("datasets", {}).get("prices", {}).get("source") == "qlib_provider" else {}
        frame = self.catalog.query_local_source("prices", warmup_start, end, **kwargs)
        rows = frame[frame.stock_id.astype(str).str.extract(r"(\d+)")[0].str.zfill(4).eq(digits)]
        technical = _technical(rows)
        if technical.empty:
            return {"status": "BLOCKED", "reason": "MARKET_DATA_UNAVAILABLE", "symbol": digits,
                    "start": start, "end": end, "rows": [], "summary": {}, "readonly": True, "simulation_only": True}
        technical = technical[technical.date.between(start, end)]
        latest = technical.tail(1)
        if not latest.empty and (not np.isfinite(latest.iloc[0]["close"]) or latest.iloc[0]["close"] <= 0):
            return {"status": "BLOCKED", "reason": "MARKET_LATEST_CLOSE_INVALID", "symbol": digits,
                    "start": start, "end": end, "rows": [], "summary": {}, "readonly": True, "simulation_only": True}
        summary = _records(latest)[0] if not latest.empty else {}
        return {"status": "READY" if summary else "BLOCKED", "reason": None if summary else "MARKET_DATA_UNAVAILABLE", "symbol": digits, "start": start, "end": end, "rows": _records(technical), "summary": summary, "readonly": True, "simulation_only": True}

    def ranking_changes(self, model: str, asof: str | None = None, lookback: int = 1) -> dict[str, Any]:
        asof = asof or self.latest_asof()
        if not asof:
            raise ValueError("no provider trading date available")
        days = self.trading_days()
        if asof not in days:
            return {"status": "BLOCKED", "model": model, "asof": asof, "reason": f"requested date is not in provider calendar: {asof}", "readonly": True, "simulation_only": True}
        if type(lookback) is not int or not 1 <= lookback <= 60:
            raise ValueError("lookback must be between 1 and 60")
        index = days.index(asof); prior_index = index - lookback
        if prior_index < 0:
            return {"status": "BLOCKED", "model": model, "asof": asof, "lookback": lookback,
                    "reason": "RANKING_HISTORY_INSUFFICIENT", "readonly": True, "simulation_only": True}
        current, previous = self.signal(model, asof), self.signal(model, days[prior_index])
        if current.status != "READY" or previous.status != "READY":
            return {"status": "BLOCKED", "model": model, "asof": asof, "previous_asof": days[prior_index], "reason": current.reason or previous.reason, "readonly": True, "simulation_only": True}
        current_top = current.rows.sort_values("rank").head(50)
        previous_top = previous.rows.sort_values("rank").head(50)
        current_map = dict(zip(current_top.instrument.astype(str), current_top["rank"].astype(int)))
        previous_map = dict(zip(previous_top.instrument.astype(str), previous_top["rank"].astype(int)))
        entered = sorted(set(current_map) - set(previous_map), key=lambda item: current_map[item])
        exited = sorted(set(previous_map) - set(current_map), key=lambda item: previous_map[item])
        stayed = sorted(set(current_map) & set(previous_map), key=lambda item: current_map[item])
        return {"status": "READY", "model": model, "asof": asof, "previous_asof": days[prior_index], "lookback": index - prior_index, "entered": [{"instrument": item, "rank": current_map[item]} for item in entered[:50]], "exited": [{"instrument": item, "rank": previous_map[item]} for item in exited[:50]], "stayed": [{"instrument": item, "rank": current_map[item], "rank_change": previous_map[item] - current_map[item]} for item in stayed[:50]], "readonly": True, "simulation_only": True}

    def cross_analysis(self, model: str, asof: str | None = None, limit: int = 50) -> dict[str, Any]:
        ranking = self.signal(model, asof)
        if ranking.status != "READY":
            return {"status": "BLOCKED", "model": model, "asof": ranking.asof, "reason": ranking.reason, "rows": [], "readonly": True, "simulation_only": True}
        start = (date.fromisoformat(ranking.asof) - timedelta(days=90)).isoformat()
        if self.config.get("datasets", {}).get("prices", {}).get("source") == "qlib_provider":
            frame = self.catalog.query_local_source("prices", start, ranking.asof, symbols=ranking.rows.head(limit).instrument.tolist())
        else:
            frame = self._model_data(ranking.asof, start).get("prices", pd.DataFrame())
        if frame.empty:
            return {"status": "BLOCKED", "reason": "TECHNICAL_CONTEXT_UNAVAILABLE", "model": model,
                    "asof": ranking.asof, "rows": [], "readonly": True, "simulation_only": True}
        latest = _technical(frame)
        latest = latest[latest.date.eq(ranking.asof)]
        rows = ranking.rows.head(max(1, min(int(limit), 50))).merge(latest, on="instrument", how="left")
        if not np.isfinite(rows[['close', 'ma20', 'rsi14']].to_numpy(dtype=float)).all():
            return {"status": "BLOCKED", "reason": "TECHNICAL_CONTEXT_INCOMPLETE", "model": model,
                    "asof": ranking.asof, "rows": [], "readonly": True, "simulation_only": True}
        rows["research_state"] = rows.apply(lambda row: "观察优先级" if pd.notna(row.get("ma20")) and row.get("close", 0) >= row.get("ma20", 0) else "人工复核", axis=1)
        rows["evidence"] = rows.apply(lambda row: f"排名 #{int(row['rank'])}；收盘相对 MA20 {'偏强' if row.get('close', 0) >= row.get('ma20', 0) else '待确认'}", axis=1)
        return {"status": "READY", "model": model, "asof": ranking.asof, "rows": _records(rows), "readonly": True, "simulation_only": True}

    def paper_state(self, model: str = "model_a", asof: str | None = None) -> dict[str, Any]:
        spec = self.config.get("models", {}).get(model)
        if spec is None:
            raise ValueError(f"unknown model: {model}")
        if spec.get("role") != "baseline" or spec.get("production_allowed") is not True:
            return {"status": "BLOCKED", "model": model, "asof": asof,
                    "reason": "MODEL_NOT_ADMITTED_FOR_PAPER_ACCOUNT",
                    "readonly": True, "simulation_only": True}
        asof = asof or self.latest_asof()
        if not asof:
            raise ValueError("no provider trading date available")
        simulation = self.config.get("simulation") or {}
        initial_cash = float(simulation.get("initial_cash", 1_000_000))
        return {"status": "READY", "model": model, "asof": asof, "mode": "simulation_only", "persisted": False, "initial_cash": initial_cash, "cash": initial_cash, "market_value": 0.0, "nav": initial_cash, "positions": [], "reason": "clean 主线只展示只读模拟状态；成交需要通过历史回放产生，不连接券商。", "readonly": True, "simulation_only": True}

    def agent_context(self, model: str = "model_a", asof: str | None = None) -> dict[str, Any]:
        ranking = self.rankings(model, asof, 5); strategy = self.strategy(model, ranking.get("asof"))
        ready = ranking["status"] == strategy["status"] == "READY"
        return {"status": "READY" if ready else "BLOCKED", "reason": ranking.get("reason") or strategy.get("reason"), "model": model, "asof": ranking.get("asof"), "ranking": ranking.get("rows", []), "strategy": strategy.get("intents", []), "disclaimer": "仅基于已验证的 clean 研究产物解释，不构成投资建议，不生成订单。", "readonly": True, "simulation_only": True}

    def explain(self, symbol: str, model: str = "model_a", asof: str | None = None) -> dict[str, Any]:
        digits = _stock_code(symbol)
        ranking = self.rankings(model, asof, 150)
        if ranking["status"] != "READY":
            return {"status": "BLOCKED", "symbol": digits, "model": model, "asof": ranking.get("asof"), "reason": ranking.get("reason"), "readonly": True, "simulation_only": True}
        item = next((row for row in ranking["rows"] if row.get("instrument") == "TW" + digits), None)
        if item is None:
            return {"status": "READY", "symbol": digits, "model": model, "asof": ranking["asof"], "answer": "该标的不在当前模型候选范围内；请结合资料日期和完整榜单人工复核。", "evidence": [], "readonly": True, "simulation_only": True}
        return {"status": "READY", "symbol": digits, "model": model, "asof": ranking["asof"], "answer": f"{digits} 当前在 {ranking['label']} 研究排序第 {item['rank']}；该分数只表示相对排序，不能解释为收益率、胜率或上涨概率。请结合行情与策略回放继续人工复核。", "evidence": [{"type": "ModelSignalArtifact", "rank": item["rank"], "score": item["score"]}], "readonly": True, "simulation_only": True}

    def run_replay(self, model: str, start: str, end: str) -> dict[str, Any]:
        data = self._model_data(end, start); return replay(self.config, data, model, start, end)

    def operations(self) -> dict[str, Any]:
        root = self.config.get("_artifact_store", self.config["artifact_root"]) / "daily"
        scheduler_file = root.parent / 'scheduler_status.json'
        scheduler = json.loads(scheduler_file.read_text()) if scheduler_file.is_file() else None
        maintenance_file = root.parent / 'ops/health.json'
        try:
            maintenance = json.loads(maintenance_file.read_text()) if maintenance_file.is_file() else None
        except (ValueError, OSError):
            maintenance = {"status": "CRITICAL", "alerts": [{"code": "MAINTENANCE_STATUS_INVALID", "severity": "CRITICAL"}]}
        runs = []
        for run in sorted([*root.glob('*/run.json'), *root.glob('*/*/run.json')], reverse=True):
            try:
                item = json.loads(run.read_text(encoding="utf-8"))
                if not isinstance(item, dict):
                    raise ValueError('daily run must be a mapping')
            except (ValueError, OSError):
                item = {"status": "BLOCKED", "reason": "DAILY_RUN_INVALID", "run_id": run.parent.name}
            if item.get("dry_run") is not True:
                runs.append(item)
        runs.sort(key=lambda item: (item.get('created_at') or item.get('run_id') or '', item.get('asof') or ''), reverse=True)
        payload = runs[0] if runs else None
        return {"status": payload.get("status") if payload else "NO_RUN", "latest": payload,
                "latest_scheduled": next((item for item in runs if item.get('trigger_reason') == 'scheduled'), scheduler),
                "latest_manual": next((item for item in runs if item.get('trigger_reason') == 'manual'), None),
                "artifact_root": str(self.config["artifact_root"]),
                "active_release": self.config.get("_active_release"), "scheduler": scheduler,
                "shadow": self._shadow_operations(root.parent),
                "maintenance": maintenance, "readonly": True}

    @staticmethod
    def _shadow_operations(store):
        result = {}
        for key, filename in (("latest", "shadow_status.json"), ("scheduled", "shadow_scheduler_status.json")):
            target = store / filename
            try:
                result[key] = json.loads(target.read_text()) if target.is_file() else None
            except (OSError, ValueError):
                result[key] = {"status": "BLOCKED", "reason": "SHADOW_STATUS_INVALID"}
        return result
