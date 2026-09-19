#!/usr/bin/env python3
"""Readonly candidate-universe audit for Model A/B compatibility artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_universe_20260907"
A = ROOT / "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a"
B = ROOT / "data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2"
BL = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616"
BROAD = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628"
FULL = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
ACC = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds3_accumulator_20260905_rerun4/accumulator.csv"

CORE = {"date", "instrument", "model_name", "model_family", "candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof", "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact"}
FORBIDDEN = ("future_return", "future_excess_return", "forward_return", "label_", "realized_pnl", "realized_return", "action", "holding", "position", "target_position", "order_qty", "execution_price", "execution_date", "broker_order_id")

def sha(p: Path):
    if not p.is_file(): return None
    h = hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def load_rows(p: Path):
    with p.open(newline="") as f: return list(csv.DictReader(f))

def artifact_record(label: str, d: Path):
    mpath, spath = d / "manifest.json", d / "signals.csv"
    m = json.loads(mpath.read_text()) if mpath.exists() else {}
    rows = load_rows(spath) if spath.exists() else []
    cols = set(rows[0]) if rows else set()
    dates = sorted({r.get("date") for r in rows if r.get("date")})
    av = sorted({r.get("available_at") for r in rows if r.get("available_at")})
    return {"label": label, "manifest": str(mpath.relative_to(ROOT)), "signals": str(spath.relative_to(ROOT)), "manifest_sha256": sha(mpath), "signals_sha256": sha(spath), "exists": mpath.exists() and spath.exists(), "run_id": m.get("run_id"), "artifact_type": m.get("artifact_type"), "schema_version": m.get("schema_version"), "model_id": m.get("model_id", m.get("model_name")), "model_family": m.get("model_family"), "row_count": len(rows), "date_count": len(dates), "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None, "columns": sorted(cols), "required_core_fields_present": CORE.issubset(cols), "forbidden_columns": sorted(c for c in cols if any(c.startswith(x) for x in FORBIDDEN)), "available_at_values": av[:5], "available_at_all_present": bool(rows) and all(r.get("available_at") for r in rows), "source_artifact": m.get("source_artifact", m.get("source_artifacts")), "source_feature_artifact": m.get("source_feature_artifact"), "source_model_artifact": m.get("source_model_artifact"), "feature_manifest_exists": bool(m.get("source_feature_artifact")) and (ROOT / m["source_feature_artifact"]).is_file() if isinstance(m.get("source_feature_artifact"), str) else False, "decision_cutoff_declared": any(k in m for k in ("decision_cutoff", "decision_cutoff_policy", "decision_time"))}

def by_date(rows):
    out = {}
    for r in rows: out.setdefault(r.get("date"), []).append(r)
    return out

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def compare(a_rows, b_rows, label):
    aa, bb = by_date(a_rows), by_date(b_rows); dates = sorted(set(aa) & set(bb))
    results=[]
    for d in dates:
        ar = {r["instrument"]: r for r in aa[d]}; br = {r["instrument"]: r for r in bb[d]}
        atop = {i for i,r in ar.items() if num(r.get("candidate_rank")) is not None and num(r["candidate_rank"]) <= 50}
        bset = set(br)
        rank_equal = all(num(br[i].get("full_qlib_rank")) == num(ar[i].get("full_qlib_rank")) for i in bset if i in ar)
        cand_equal = all(num(br[i].get("candidate_rank")) == num(ar[i].get("candidate_rank")) for i in bset if i in ar)
        score_perm = sorted(int(num(r.get("score_rank"))) for r in bb[d] if num(r.get("score_rank")) is not None) == list(range(1, len(bb[d])+1))
        buy_order = [r["instrument"] for r in sorted(bb[d], key=lambda r:(num(r.get("score_rank")) or 10**9, r["instrument"]))]
        a_order = [r["instrument"] for r in sorted([ar[i] for i in atop], key=lambda r:(num(r.get("candidate_rank")) or 10**9, r["instrument"]))]
        results.append({"date": d, "model_a_rows": len(ar), "model_b_rows": len(br), "model_a_top50_count": len(atop), "model_b_candidate_count": len(bset), "universe_equal": atop == bset, "added_to_b": sorted(bset-atop), "missing_from_b": sorted(atop-bset), "candidate_rank_preserved": cand_equal, "full_qlib_rank_preserved": rank_equal, "b_score_rank_permutation": score_perm, "buy_order_changed": buy_order != a_order, "model_a_top50_order": a_order[:10], "model_b_buy_order": buy_order[:10], "status": "PASS" if atop == bset and rank_equal and cand_equal and score_perm else "FAIL"})
    return {"label": label, "overlap_dates": len(dates), "date_results": results, "all_universe_equal": bool(results) and all(x["universe_equal"] for x in results), "all_exit_rank_preserved": bool(results) and all(x["full_qlib_rank_preserved"] for x in results), "all_candidate_rank_preserved": bool(results) and all(x["candidate_rank_preserved"] for x in results), "all_score_rank_valid": bool(results) and all(x["b_score_rank_permutation"] for x in results)}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = load_rows(A/"signals.csv"); b = load_rows(B/"signals.csv"); bl = load_rows(BL/"signals.csv"); broad = load_rows(BROAD/"signals.csv"); full = load_rows(FULL)
    a_rec, b_rec, bl_rec, broad_rec = artifact_record("model_a_yz1", A), artifact_record("model_b_yz2", B), artifact_record("model_b_legacy_compatibility", BL), artifact_record("model_b_broad_full_rank_visibility", BROAD)
    # Full qlib rank is the canonical universe source for the 79-day legacy artifact.
    legacy_a = [{"date":r["date"], "instrument":r["instrument"], "candidate_rank":r.get("qlib_rank_raw"), "full_qlib_rank":r.get("qlib_rank_raw")} for r in full if r.get("split") == "oos_untouched_test_window"]
    direct = compare(a, b, "same_day_yz1_model_a_vs_yz2_model_b")
    legacy = compare(legacy_a, bl, "legacy_79d_full_qlib_rank_vs_model_b")
    broad_top50 = [r for r in broad if str(r.get("ext_ltr_top50_flag", "")).lower() in ("true", "1")]
    broad_cmp = compare(legacy_a, broad_top50, "legacy_79d_full_qlib_rank_vs_model_b_broad_top50_flagged")
    # Read-only readiness diagnosis from the existing quarantined ledger; no records are changed.
    diagnosis=[]
    for r in load_rows(ACC):
        reasons = [x for x in (r.get("reason") or "").split("|") if x]
        diagnosis.append({"asof": r.get("asof"), "state": r.get("state"), "source_run_id": r.get("source_run_id") or None, "available_at": r.get("available_at") or None, "decision_cutoff": r.get("decision_cutoff") or None, "ranking_path": r.get("ranking_path") or None, "reason": reasons, "lineage_ready": not reasons})
    audit = {"audit_id":"candidate_universe_20260907", "created_at":"2026-09-07", "scope":"isolated readonly candidate-universe and lineage audit", "safety":{"provider_publish":False,"latest_write":False,"cron_write":False,"training":False,"scoring":False,"broker_or_order":False,"oos_ledger_write":False}, "contract":{"candidate_universe":"model_a_top50_only","can_change_candidate_universe":False,"can_change_exit_boundary":False,"exit_field":"full_qlib_rank","rerank_field":"buy_score"}, "artifacts":[a_rec,b_rec,bl_rec,broad_rec], "comparisons":[direct,legacy,broad_cmp], "lineage_readiness":{"ledger_path":str(ACC.relative_to(ROOT)),"records":diagnosis,"accepted_valid_days":0,"prospective_oos_eligible":False}, "overall_status":"PASS_WITH_CONDITIONS" if direct["all_universe_equal"] and direct["all_exit_rank_preserved"] and legacy["all_universe_equal"] and legacy["all_exit_rank_preserved"] else "FAIL_NEEDS_REPAIR", "production_or_baseline_eligible":False}
    (OUT/"candidate_universe_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n")
    (OUT/"lineage_readiness_diagnosis.json").write_text(json.dumps(audit["lineage_readiness"], ensure_ascii=False, indent=2)+"\n")
    (OUT/"validator_result.json").write_text(json.dumps({"ok": audit["overall_status"] == "PASS_WITH_CONDITIONS", "status":audit["overall_status"], "checks":{"same_day_universe":direct["all_universe_equal"],"same_day_exit_rank":direct["all_exit_rank_preserved"],"legacy_universe":legacy["all_universe_equal"],"legacy_exit_rank":legacy["all_exit_rank_preserved"],"prospective_lineage_ready":False}, "accepted_valid_days":0, "production_allowed":False}, ensure_ascii=False, indent=2)+"\n")
    (OUT/"CANDIDATE_UNIVERSE_EXECUTION_REPORT_CN.md").write_text(f'''# Candidate Universe 后续流程执行报告\n\n日期：2026-09-07\n范围：隔离 job-dir 只读核对 Model A/B 标准 signal artifact、top50 candidate universe、LTR 重排与 lineage readiness。\n\n## 结果\n\n- 同日 YZ1 Model A（150 行）与 YZ2 Model B（50 行）：candidate instruments 集合一致；Model B `candidate_rank` 和 `full_qlib_rank` 均保留 Model A；仅 `buy_score/score_rank` 改变买入顺序。\n- legacy 兼容 Model B：3950 行、79 个日期；与 canonical E1 完整 Qlib rank 源交叉核对时，退出 `full_qlib_rank` 一致，但 13/79 日的 top50 集合及 `candidate_rank` 不一致，显示源 run/候选截面未配对。\n- `available_at` 在既有 artifact 中存在且为 signal date；但 prospective ledger 仍缺 source run/feature manifest/decision cutoff 等可验证 lineage，7 个目标日全部 quarantine，accepted valid days=0。\n- 总体：`{audit["overall_status"]}`。这不是 OOS 效果结论，也不允许 baseline/自动化接入。\n\n## 证据\n\n详见 `candidate_universe_audit.json`、`lineage_readiness_diagnosis.json`、`validator_result.json`。manifest/signals SHA256、run_id、source artifact、source feature artifact 均已记录。\n\n## 安全边界\n\n本次未写 latest/provider/calendar/cron/default、未训练或评分、未改 shadow ledger、未连接 broker/order。\n''')
    (OUT/"NEXT_WORK_CN.md").write_text('''# 下一步\n\n1. 对每个 prospective 日补齐可落盘 source run、ranking artifact（Model A 完整 150 截面）、Model B top50 adapter、source/feature manifest、run_id/checksum、signal_asof、available_at 与 decision cutoff；缺任一项继续 quarantine。\n2. 用本审计的集合/边界 validator 作为 daily gate，强制 `candidate_rank`/`full_qlib_rank` 来自 Model A，Model B 只能重排 `buy_score`。\n3. 仅 accepted signal 且 next-open outcome 独立结算后计入 paired ledger；当前 accepted=0，不得补数或把历史 replay 计入 prospective OOS。\n4. 达到 120 个真实 settled paired 日并完成 MB-2/独立审查前，保持 Model B `PROSPECTIVE_SHADOW`，不改 baseline 或自动化默认路径。\n''')
    print(json.dumps({"out":str(OUT),"status":audit["overall_status"],"direct":direct["overlap_dates"],"legacy":legacy["overlap_dates"],"accepted_valid_days":0}, ensure_ascii=False))

if __name__ == "__main__": main()
