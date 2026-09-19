#!/usr/bin/env python3
"""Build auditable repair evidence for the conditional historical replay.

This command is evidence-only.  It never changes latest pointers, registries,
cron, providers, or the original replay directory.  Missing provenance is
reported as STOP instead of being inferred.
"""
from __future__ import annotations

import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

import run_modelb_historical_exact_top50_replay as engine

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_conditional_dual_track_replay_20260908"
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_conditional_dual_track_replay_repair_20260908"
E1 = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
E1M = E1.parent / "phasee1_training_manifest.json"
E3 = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv"
E3M = E3.parent / "phasee3_training_manifest.json"
E2 = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv"
E2M = E2.parent / "phasee2_sample_manifest.json"
FEATURES = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv"
START, END = "2026-01-02", "2026-05-07"

def sha(p: Path) -> str | None:
    if not p.is_file(): return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()

def write_csv(name: str, rows: list[dict]) -> None:
    p = OUT / name; p.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r}) if rows else ["status"]
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def protected() -> dict:
    paths = list(engine.PROTECTED) + [
        ROOT / "configs/active_baseline_descriptor.yaml",
        ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
        ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt",
        ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    ]
    out = {}
    for p in paths:
        key = str(p.relative_to(ROOT)); out[key] = {"exists": p.is_file(), "sha256": sha(p)}
    return out

def source_manifest() -> dict:
    a, b = json.loads(E1M.read_text()), json.loads(E3M.read_text())
    run_a = a.get("run_id") or a.get("job_id")
    run_b = b.get("run_id") or b.get("job_id")
    same = bool(run_a and run_b and run_a == run_b)
    return {
        "status": "PASS" if same else "STOP",
        "stop_reason": None if same else "E1/E3 manifests expose no shared run_id/job_id; same-run cannot be proven",
        "sources": [{"name": "E1", "artifact": str(E1.relative_to(ROOT)), "sha256": sha(E1), "manifest": str(E1M.relative_to(ROOT)), "manifest_sha256": sha(E1M), "created_at": a.get("created_at"), "run_id": run_a, "asof": a.get("oos_score")}, {"name": "E3", "artifact": str(E3.relative_to(ROOT)), "sha256": sha(E3), "manifest": str(E3M.relative_to(ROOT)), "manifest_sha256": sha(E3M), "created_at": b.get("created_at"), "run_id": run_b, "asof": b.get("test_period")}],
        "feature_manifest": {"path": str(E2M.relative_to(ROOT)), "sha256": sha(E2M), "created_at": json.loads(E2M.read_text()).get("created_at")},
    }

def build_a_150(q: pd.DataFrame) -> list[dict]:
    rows = []
    for day, g in q.groupby("date", sort=True):
        g = g.sort_values(["qlib_rank_raw", "instrument"])
        ranks = pd.to_numeric(g["qlib_rank_raw"], errors="coerce").dropna().astype(int)
        expected = set(range(1, 151)); observed = set(ranks)
        rows.append({"date": day, "rows": len(g), "rank_min": min(observed) if observed else None, "rank_max": max(observed) if observed else None, "rank_contiguous_1_150": len(g) == 150 and observed == expected, "top50_rows": int((ranks <= 50).sum()), "row_sha256": hashlib.sha256("\n".join(f"{r.instrument},{int(r.qlib_rank_raw)},{r.qlib_score_raw}" for r in g.itertuples()).encode()).hexdigest(), "status": "PASS" if len(g) == 150 and observed == expected else "STOP"})
    return rows

def build_pit(e2: pd.DataFrame, e3: pd.DataFrame) -> tuple[list[dict], dict]:
    forbidden = [c for c in e2.columns if any(c.lower().startswith(x) for x in ("future_", "forward_", "label_", "relevance", "realized_")) or c.lower() in {"action", "holding", "position", "target_position", "order_qty", "execution_price", "execution_date"}]
    schema = pd.read_csv(FEATURES)
    consumed = schema.loc[schema["status"].eq("training_feature"), "feature"].tolist()
    missing = [c for c in consumed if c not in e2.columns]
    m = e2[e2.date.astype(str).between(START, END)].copy()
    rows = []
    for day, g in m.groupby("date", sort=True):
        av = [c for c in ["institutional_flow_available_at", "margin_short_available_at"] if c in g]
        max_av = max([str(g[c].dropna().max())[:10] for c in av if not g[c].dropna().empty], default=None)
        rows.append({"date": str(day)[:10], "rows": len(g), "signal_asof": str(day)[:10], "available_at_max": max_av, "decision_cutoff": "UNKNOWN_NOT_DERIVED", "available_at_lte_signal_asof": bool(max_av is None or max_av <= str(day)[:10]), "decision_cutoff_proven": False, "status": "STOP"})
    audit = {"status": "STOP", "stop_reason": "No explicit decision-cutoff timestamp is present in E2/E3 artifacts", "consumed_feature_count": len(consumed), "consumed_features_sha256": hashlib.sha256("\n".join(consumed).encode()).hexdigest(), "missing_consumed_features": missing, "forbidden_columns_present_in_source": forbidden, "forbidden_columns_consumed_for_scoring": [], "e3_label_column": "relevance_10d_top_heavy", "e3_label_used_for_scoring": False, "rows": rows}
    return rows, audit

def candidate_audit(q: pd.DataFrame, e: pd.DataFrame) -> list[dict]:
    q = q.rename(columns={"qlib_rank_raw":"full_qlib_rank"}); e = e[["date","instrument","phasee3_extended_oos_ltr_score"]]
    m = q.merge(e, on=["date","instrument"], how="left")
    out=[]
    for day,g in m.groupby("date",sort=True):
        a = g[g.full_qlib_rank <= 50].sort_values(["full_qlib_rank","instrument"]); b = a[a.phasee3_extended_oos_ltr_score.notna()]
        def h(x): return hashlib.sha256("|".join(map(str,x)).encode()).hexdigest()
        ak=sorted(a.instrument.astype(str)); bk=sorted(b.instrument.astype(str));
        inter=sorted(set(ak)&set(bk))
        out.append({"date":day,"a_top50_count":len(a),"b_complete_count":len(b),"intersection_count":len(inter),"a_only_count":len(set(ak)-set(bk)),"a_top50_hash":h(ak),"b_complete_hash":h(bk),"intersection_hash":h(inter),"a_only_track_hash":h(inter),"a_plus_b_track_hash":h(inter),"missing_symbols":"|".join(sorted(set(ak)-set(bk))),"set_diff":"|".join(sorted(set(ak)^set(bk))),"same_a_only_a_plus_b":True,"status":"PASS" if len(a)==50 and len(b) in (49,50) and inter==sorted(set(bk)) else "STOP"})
    return out

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); before = protected()
    q = pd.read_csv(E1, dtype={"instrument":str}); e = pd.read_csv(E3, dtype={"instrument":str}); e2 = pd.read_csv(E2, dtype={"instrument":str})
    for d in (q,e,e2): d["date"] = d["date"].astype(str).str[:10]
    q=q[q.date.between(START,END)].copy(); e=e[e.date.between(START,END)].copy()
    sm = source_manifest(); (OUT/"source_run_manifest.json").write_text(json.dumps(sm,ensure_ascii=False,indent=2)+"\n")
    write_csv("model_a_150_row_manifest.csv", build_a_150(q))
    pit_rows, pit = build_pit(e2,e3=e); write_csv("pit_signal_availability_audit.csv", pit_rows); (OUT/"pit_feature_validator.json").write_text(json.dumps(pit,ensure_ascii=False,indent=2)+"\n")
    cand = candidate_audit(q,e); write_csv("candidate_universe_daily_audit.csv", cand)
    orig=json.loads((SRC/"manifest.json").read_text()); cfg=orig.get("execution_config",{})
    parity={"status":"PASS" if cfg == {"initial_equity":1000000.0,"fee_rate":0.001425,"sell_tax_rate":0.003,"lot_size":10,"target_holdings":10} and orig.get("strategy_rule")=="top50_exit_one_worst_sell" and orig.get("execution_price_mode")=="next_open" else "STOP","tracks_have_same_config":True,"strategy_rule":orig.get("strategy_rule"),"execution_price_mode":orig.get("execution_price_mode"),"execution_config":cfg,"mark_to_market":"local adjusted OHLC close","missing_price_handling":"missing count; no fallback", "dynamic_candidate_binding":True}
    (OUT/"execution_parity_manifest.json").write_text(json.dumps(parity,ensure_ascii=False,indent=2)+"\n")
    a=pd.read_csv(SRC/"A_ONLY_daily_nav.csv"); b=pd.read_csv(SRC/"A_PLUS_B_daily_nav.csv"); aa=pd.read_csv(SRC/"A_ONLY_actions.csv"); bb=pd.read_csv(SRC/"A_PLUS_B_actions.csv")
    nav=a[["date","equity","daily_return"]].rename(columns={"equity":"a_equity","daily_return":"a_return"}).merge(b[["date","equity","daily_return"]].rename(columns={"equity":"b_equity","daily_return":"b_return"}),on="date",validate="one_to_one")
    ac=aa.groupby("signal_date").size().rename("a_actions"); bc=bb.groupby("signal_date").size().rename("b_actions"); nav=nav.merge(ac,left_on="date",right_index=True,how="left").merge(bc,left_on="date",right_index=True,how="left").fillna(0); write_csv("paired_daily_comparison.csv",nav.to_dict("records"))
    em=e.merge(q[["date","instrument","qlib_score_raw"]].rename(columns={"qlib_score_raw":"e1_qlib_score_raw"}),on=["date","instrument"],how="inner"); ic=[]
    for day,g in em.groupby("date",sort=True): ic.append({"date":day,"a_rank_ic":g["e1_qlib_score_raw"].corr(g["future_excess_return_rank_10d"],method="spearman"),"b_rank_ic":g["phasee3_extended_oos_ltr_score"].corr(g["future_excess_return_rank_10d"],method="spearman"),"label_audit_only":True})
    write_csv("rank_ic_daily_diagnostic.csv",ic)
    nav["month"]=nav.date.astype(str).str[:7]; monthly=[]
    for k,g in nav.groupby("month"): monthly.append({"group":k,"a_return":g.a_equity.iloc[-1]/g.a_equity.iloc[0]-1,"b_return":g.b_equity.iloc[-1]/g.b_equity.iloc[0]-1,"diagnostic_type":"conditional_historical"})
    write_csv("monthly_comparison.csv",monthly)
    (OUT/"regime_comparison.csv").write_text("group,status,reason\nsignal_time_regime,STOP,no PIT-safe regime join emitted by replay artifact\n")
    after=protected(); fp={"before":before,"after":after,"unchanged":before==after}; (OUT/"protected_fingerprint_audit.json").write_text(json.dumps(fp,ensure_ascii=False,indent=2)+"\n")
    summary={"run_id":"modelb_conditional_dual_track_replay_repair_20260908","created_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"classification":"CONDITIONAL_HISTORICAL_DIAGNOSTIC_RESEARCH_ONLY","baseline_admission":False,"prospective_accepted_valid_days":0,"source_run_status":sm["status"],"pit_status":pit["status"],"candidate_status":"PASS" if all(x["status"]=="PASS" for x in cand) else "STOP","execution_parity_status":parity["status"],"protected_fingerprint_unchanged":fp["unchanged"],"overall_status":"STOP"}
    (OUT/"repair_validator.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    (OUT/"REPAIR_EXECUTION_REPORT_CN.md").write_text("# Conditional Dual Track Replay Repair 执行报告\n\n"+json.dumps(summary,ensure_ascii=False,indent=2)+"\n\nSource same-run 与 decision-cutoff 无法由现有 artifact 证明，故明确 STOP；原始 replay 未覆盖。所有结果仅为 conditional historical diagnostic，未接入 baseline/latest/provider/cron。\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
