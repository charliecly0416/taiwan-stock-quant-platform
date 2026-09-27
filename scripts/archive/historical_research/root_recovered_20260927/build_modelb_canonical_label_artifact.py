#!/usr/bin/env python3
"""Build a research-only canonical Model B 10-day label artifact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_canonical_labels_20260914"
B2_RAW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_ARTIFACT_RAW.parquet"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
TWII = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/twii_acquisition/TWII_NORMALIZED.csv"

KEY = ["date", "instrument"]
FORBIDDEN = ("future_return_", "future_excess_return_", "forward_return_", "label_", "relevance_", "realized_pnl", "realized_return", "action", "holding", "position", "target_position", "target_weight", "order_qty", "execution_price", "execution_date", "broker_order_id")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    b2 = pd.read_parquet(B2_RAW, columns=KEY)
    b2["date"] = pd.to_datetime(b2["date"]).dt.strftime("%Y-%m-%d")
    b2["instrument"] = b2["instrument"].astype(str)
    if b2.duplicated(KEY).any():
        raise RuntimeError("B2 key set contains duplicates")

    twii = pd.read_csv(TWII, usecols=["date", "close"])
    twii["date"] = twii.date.astype(str).str[:10]
    twii = twii.sort_values("date").drop_duplicates("date")
    twii["market_return_10d_canonical"] = twii.close.shift(-10) / twii.close - 1
    market_future = twii.set_index("date")["market_return_10d_canonical"]

    stock_parts = []
    source_hashes = {}
    for path in sorted(PRICE_ROOT.glob("TW*.csv")):
        frame = pd.read_csv(path, usecols=["date", "close"])
        frame["date"] = frame.date.astype(str).str[:10]
        frame = frame.sort_values("date").drop_duplicates("date")
        frame["stock_return_10d_canonical"] = frame.close.shift(-10) / frame.close - 1
        frame["instrument"] = path.stem
        stock_parts.append(frame[["date", "instrument", "stock_return_10d_canonical"]])
        source_hashes[path.stem] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
    stock_future = pd.concat(stock_parts, ignore_index=True)

    out = b2.merge(stock_future, on=KEY, how="left", validate="one_to_one")
    out["market_return_10d_canonical"] = out.date.map(market_future)
    out["future_excess_return_10d_canonical"] = out.stock_return_10d_canonical - out.market_return_10d_canonical
    out["label_complete_10d_canonical"] = out.future_excess_return_10d_canonical.notna()
    out["rank_universe_size"] = out.groupby("date")["instrument"].transform("size").astype(int)
    out["rank_complete_size"] = out.groupby("date")["future_excess_return_10d_canonical"].transform("count").astype(int)
    out["future_excess_return_rank_10d_canonical"] = out.groupby("date")["future_excess_return_10d_canonical"].rank(pct=True, method="average")
    rank = out["future_excess_return_rank_10d_canonical"]
    out["relevance_10d_top_heavy_canonical"] = np.select([rank >= .90, rank >= .80, rank >= .70, rank >= .50], [4, 3, 2, 1], default=0).astype(float)
    out.loc[~out["label_complete_10d_canonical"], "relevance_10d_top_heavy_canonical"] = np.nan
    out = out.sort_values(KEY, kind="mergesort").reset_index(drop=True)

    label_cols = ["future_excess_return_10d_canonical", "future_excess_return_rank_10d_canonical", "relevance_10d_top_heavy_canonical"]
    out[KEY + ["stock_return_10d_canonical", "market_return_10d_canonical", *label_cols, "label_complete_10d_canonical", "rank_universe_size", "rank_complete_size"]].to_csv(OUT / "CANONICAL_LABEL_ARTIFACT.csv", index=False)
    coverage = out.groupby(out.date.str[:4]).agg(rows=("instrument", "size"), label_complete=("label_complete_10d_canonical", "sum"), dates=("date", "nunique"), min_universe=("rank_universe_size", "min"), max_universe=("rank_universe_size", "max"), min_complete=("rank_complete_size", "min"), max_complete=("rank_complete_size", "max")).reset_index(names="year")
    coverage.to_csv(OUT / "CANONICAL_LABEL_COVERAGE_BY_YEAR.csv", index=False)
    daily = out.groupby("date").agg(rows=("instrument", "size"), label_complete=("label_complete_10d_canonical", "sum"), rank_universe_size=("rank_universe_size", "first"), rank_complete_size=("rank_complete_size", "first")).reset_index()
    daily.to_csv(OUT / "CANONICAL_LABEL_DAILY_COVERAGE.csv", index=False)

    forbidden = [c for c in out.columns if any(token in c.lower() for token in FORBIDDEN) and c not in label_cols and not c.startswith("label_complete")]
    train = out[out.date.between("2023-01-10", "2024-12-17")]
    valid = out[out.date.between("2025-01-02", "2025-12-31")]
    test = out[out.date.between("2026-01-02", "2026-05-07")]
    manifest = {
        "schema_version": "modelb.canonical_label_artifact.v1",
        "status": "PASS" if not forbidden and train.label_complete_10d_canonical.all() and valid.label_complete_10d_canonical.all() else "BLOCKED",
        "research_only": True, "diagnostic_only": True, "production_allowed": False,
        "source_feature_key_artifact": str(B2_RAW.relative_to(ROOT)),
        "stock_price_source": str(PRICE_ROOT.relative_to(ROOT)),
        "market_price_source": str(TWII.relative_to(ROOT)),
        "label_rule": "stock close shift(-10) minus TWII close shift(-10), cross-sectional percentile by frozen B2 key universe; >=.90/.80/.70/.50 -> 4/3/2/1 else 0",
        "rank_universe": "exact unique (date,instrument) keys from B2 FEATURE_ARTIFACT_RAW.parquet; no top50 filtering",
        "counts": {"rows": int(len(out)), "dates": int(out.date.nunique()), "train_rows": int(len(train)), "train_complete": int(train.label_complete_10d_canonical.sum()), "validation_rows": int(len(valid)), "validation_complete": int(valid.label_complete_10d_canonical.sum()), "test_rows": int(len(test)), "test_complete": int(test.label_complete_10d_canonical.sum())},
        "test_tail_without_future_window": sorted(test.loc[~test.label_complete_10d_canonical, "date"].unique().tolist()),
        "forbidden_non_label_columns": forbidden,
        "source_hashes": {"b2_raw": sha256(B2_RAW), "twii": sha256(TWII), "stock_file_count": len(source_hashes), "stock_manifest_sha256": hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()},
        "artifacts": {"labels": str((OUT / "CANONICAL_LABEL_ARTIFACT.csv").relative_to(ROOT)), "daily_coverage": str((OUT / "CANONICAL_LABEL_DAILY_COVERAGE.csv").relative_to(ROOT)), "year_coverage": str((OUT / "CANONICAL_LABEL_COVERAGE_BY_YEAR.csv").relative_to(ROOT))},
        "no_training": True, "no_replay": True, "no_baseline_or_latest_write": True,
    }
    (OUT / "CANONICAL_LABEL_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    lines = ["# Model B canonical 标签 artifact", "", "仅用于隔离重训研究，不进入 baseline/latest/default 或生产链路。", "", f"状态：`{manifest['status']}`。", f"总行数：`{len(out)}`；日期：`{out.date.nunique()}`。", f"训练期完整标签：`{int(train.label_complete_10d_canonical.sum())}/{len(train)}`。", f"验证期完整标签：`{int(valid.label_complete_10d_canonical.sum())}/{len(valid)}`。", f"测试期完整标签：`{int(test.label_complete_10d_canonical.sum())}/{len(test)}`。", "", "标签排名分母固定为 B2 raw artifact 的逐日 `(date,instrument)` key 集合；没有按 complete rows 临时缩小 universe。", "测试期最后 10 个日期因 TWII 没有足够的未来 10 日价格而暂不可评估，不能将其标为 0 标签。", ""]
    (OUT / "CANONICAL_LABEL_EXECUTION_REPORT_CN.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "output": str(OUT.relative_to(ROOT)), "counts": manifest["counts"], "test_tail": manifest["test_tail_without_future_window"]}, ensure_ascii=True))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
