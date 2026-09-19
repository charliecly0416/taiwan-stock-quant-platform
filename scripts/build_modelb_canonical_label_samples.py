#!/usr/bin/env python3
"""Build isolated B4 samples using canonical features and canonical labels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914"
B2_RAW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_ARTIFACT_RAW.parquet"
B2_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
LABEL_DIR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_canonical_labels_20260914"
LABELS = LABEL_DIR / "CANONICAL_LABEL_ARTIFACT.csv"
LABEL_MANIFEST = LABEL_DIR / "CANONICAL_LABEL_MANIFEST.json"

FIT_START, FIT_END = "2023-01-10", "2024-12-17"
EMBARGO_START, EMBARGO_END = "2024-12-18", "2024-12-31"
VALID_START, VALID_END = "2025-01-02", "2025-12-31"
TEST_START, TEST_END = "2026-01-02", "2026-05-07"
LABEL = "relevance_10d_top_heavy_canonical"
KEY = ["date", "instrument"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    schema = json.loads(B2_SCHEMA.read_text())
    features = list(schema["feature_order"])
    b2 = pd.read_parquet(B2_RAW)
    b2["date"] = pd.to_datetime(b2.date).dt.strftime("%Y-%m-%d")
    labels = pd.read_csv(LABELS)
    labels["date"] = pd.to_datetime(labels.date).dt.strftime("%Y-%m-%d")
    merged = b2.merge(labels, on=KEY, how="inner", validate="one_to_one")
    if len(merged) != len(b2) or merged.duplicated(KEY).any():
        raise RuntimeError("B2/label join is not one-to-one")
    finite = np.isfinite(merged[features].to_numpy(dtype=float)).all(axis=1)
    merged["feature_complete_78_verified"] = finite
    merged["label_complete"] = merged[LABEL].notna()
    merged["b4_split"] = np.select(
        [merged.date.between(FIT_START, FIT_END), merged.date.between(EMBARGO_START, EMBARGO_END), merged.date.between(VALID_START, VALID_END), merged.date.between(TEST_START, TEST_END)],
        ["fit_train", "embargo_10_trade_dates", "validation", "test_2026"], default="outside_frozen_split",
    )
    primary = merged[merged.feature_complete_78_verified & merged.label_complete].copy()
    train = primary[primary.b4_split.isin(["fit_train", "embargo_10_trade_dates", "validation"])].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    test = primary[primary.b4_split.eq("test_2026")].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    if train.empty or test.empty or train[LABEL].isna().any() or test[LABEL].isna().any():
        raise RuntimeError("canonical B4 samples are empty or incomplete")
    for frame in [train, test]:
        frame[features] = frame[features].astype(float)
        frame[LABEL] = frame[LABEL].astype(float)
    keep = KEY + ["b4_split", "feature_raw_complete_78", "feature_complete_78_verified", "label_complete", "rank_universe_size", "rank_complete_size", *features, LABEL]
    train[keep].to_parquet(OUT / "B4_CANONICAL_TRAIN_SAMPLE.parquet", index=False)
    test[keep].to_parquet(OUT / "B4_CANONICAL_TEST_SAMPLE.parquet", index=False)
    coverage = merged.groupby("b4_split", dropna=False).agg(rows=("instrument", "size"), feature_complete=("feature_complete_78_verified", "sum"), label_complete=("label_complete", "sum"), primary_rows=("label_complete", lambda s: int((s & merged.loc[s.index, "feature_complete_78_verified"]).sum())), dates=("date", "nunique")).reset_index()
    coverage.to_csv(OUT / "B4_CANONICAL_COVERAGE_AUDIT.csv", index=False)
    split_audit = []
    for name, frame in [("fit_train", train[train.b4_split.eq("fit_train")]), ("embargo_10_trade_dates", train[train.b4_split.eq("embargo_10_trade_dates")]), ("validation", train[train.b4_split.eq("validation")]), ("test_2026", test)]:
        groups = frame.groupby("date").size()
        split_audit.append({"split": name, "rows": int(len(frame)), "dates": int(frame.date.nunique()), "date_min": str(frame.date.min()), "date_max": str(frame.date.max()), "group_min": int(groups.min()), "group_median": float(groups.median()), "group_max": int(groups.max()), "key_sha256": hashlib.sha256(frame[KEY].sort_values(KEY).to_csv(index=False, lineterminator="\n").encode()).hexdigest()})
    pd.DataFrame(split_audit).to_csv(OUT / "B4_CANONICAL_SPLIT_AUDIT.csv", index=False)
    manifest = {
        "schema_version": "modelb.b4.canonical_label_samples.v1", "status": "PASS", "research_only": True, "diagnostic_only": True, "production_allowed": False,
        "feature_source": str(B2_RAW.relative_to(ROOT)), "feature_schema": str(B2_SCHEMA.relative_to(ROOT)), "label_source": str(LABELS.relative_to(ROOT)), "label_manifest_sha256": sha256(LABEL_MANIFEST),
        "feature_count": len(features), "feature_order_sha256": hashlib.sha256(json.dumps(features, separators=(",", ":")).encode()).hexdigest(), "label_column": LABEL, "neutral_fill": False, "primary_complete_case_only": True,
        "rank_universe": "B2 raw unique (date,instrument) key set; rank denominator is frozen before primary feature filtering", "splits": split_audit,
        "tail_unavailable_test_dates": sorted(merged.loc[merged.date.between(TEST_START, TEST_END) & ~merged.label_complete, "date"].unique().tolist()),
        "artifacts": {"train": str((OUT / "B4_CANONICAL_TRAIN_SAMPLE.parquet").relative_to(ROOT)), "test": str((OUT / "B4_CANONICAL_TEST_SAMPLE.parquet").relative_to(ROOT)), "coverage": str((OUT / "B4_CANONICAL_COVERAGE_AUDIT.csv").relative_to(ROOT)), "split_audit": str((OUT / "B4_CANONICAL_SPLIT_AUDIT.csv").relative_to(ROOT))},
        "no_training": True, "no_replay": True, "no_baseline_or_latest_write": True,
    }
    (OUT / "B4_CANONICAL_EXECUTOR_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    report = ["# B4 canonical label 样本执行报告", "", "本目录为隔离研究样本，不连接 baseline/latest/default。", "", f"状态：`{manifest['status']}`。", f"训练/embargo/validation 总样本：`{len(train)}`；可评估 test 样本：`{len(test)}`。", f"test 可评估日期：`{test.date.nunique()}`；尾部不可评估日期：`{len(manifest['tail_unavailable_test_dates'])}`。", "", "排名分母先按 B2 raw key 集合冻结，再应用 feature complete 和 label complete 过滤；没有用过滤后的行重新排名。", ""]
    (OUT / "B4_CANONICAL_EXECUTION_REPORT_CN.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(OUT.relative_to(ROOT)), "train_rows": len(train), "test_rows": len(test), "test_dates": int(test.date.nunique()), "tail_dates": manifest["tail_unavailable_test_dates"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
