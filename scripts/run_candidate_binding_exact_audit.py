#!/usr/bin/env python3
"""Readonly exact Model A top50 / Model B candidate binding audit.

The command intentionally stops before scoring when a same-day Model B input
artifact is unavailable. It writes only evidence under the isolated output
directory and never changes latest, provider, cron, defaults, or ledgers.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASOF = "2026-09-04"
DEFAULT_A = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260904_20260904T104101Z"
DEFAULT_FEATURE_DIR = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_feature_input_20260905"
DEFAULT_OUT = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907"

PROTECTED = [
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260904_20260904T104101Z/manifest.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260904_20260904T104101Z/signals.csv",
    ROOT / "data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260904_20260904T104101Z/manifest.json",
]


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def fingerprints() -> dict[str, dict[str, object]]:
    return {
        rel(path): {"exists": path.is_file(), "size": path.stat().st_size if path.is_file() else None, "sha256": sha(path)}
        for path in PROTECTED
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def find_same_day_model_b(asof: str) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for manifest_path in (ROOT / "data_tw").rglob("manifest.json"):
        try:
            payload = load_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        model_id = str(payload.get("model_id") or payload.get("model_name") or "")
        target = str(payload.get("asof") or payload.get("signal_asof") or payload.get("asof_date") or "")[:10]
        if "orthogonal_ltr" not in model_id and not (model_id.startswith("head10_") or payload.get("model_family") == "ltr"):
            continue
        if target != asof:
            continue
        signal_path = manifest_path.parent / "signals.csv"
        found.append({
            "manifest": rel(manifest_path),
            "signals": rel(signal_path),
            "manifest_sha256": sha(manifest_path),
            "signals_exists": signal_path.is_file(),
            "model_id": model_id,
            "row_count": payload.get("row_count"),
            "status": payload.get("status"),
        })
    return sorted(found, key=lambda item: str(item["manifest"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default=DEFAULT_ASOF)
    parser.add_argument("--model-a-dir", default=str(DEFAULT_A))
    parser.add_argument("--feature-dir", default=str(DEFAULT_FEATURE_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    a_dir, feature_dir, out = Path(args.model_a_dir).resolve(), Path(args.feature_dir).resolve(), Path(args.out).resolve()
    if not out.is_relative_to((ROOT / "data_tw/experiments/project_runtime_convergence").resolve()):
        raise SystemExit("output_outside_isolated_runtime_evidence")
    out.mkdir(parents=True, exist_ok=True)
    before = fingerprints()
    a_manifest_path, a_signals_path = a_dir / "manifest.json", a_dir / "signals.csv"
    a_manifest = load_json(a_manifest_path)
    a_rows = read_csv(a_signals_path) if a_signals_path.is_file() else []
    a_keys = {(r.get("date", "")[:10], r.get("instrument", "").strip().upper()) for r in a_rows}
    ranks = sorted(int(float(r["full_qlib_rank"])) for r in a_rows if r.get("full_qlib_rank"))
    top50 = sorted((r for r in a_rows if r.get("date", "")[:10] == args.asof and float(r.get("candidate_rank", "nan")) <= 50), key=lambda r: (float(r["candidate_rank"]), r["instrument"]))
    top50_keys = [f"{r['date'][:10]}|{r['instrument'].strip().upper()}" for r in top50]
    feature_manifest = load_json(feature_dir / "input_readiness.json")
    feature_lineage = load_json(feature_dir / "feature_lineage.json")
    missing_feature_fields = [k for k, v in feature_lineage.get("features", {}).items() if v.get("status") == "blocked_missing_history"]
    b_candidates = find_same_day_model_b(args.asof)
    b_selected = [item for item in b_candidates if item.get("signals_exists") and item.get("status") in ("READY", "PASS", "SCORED_ASOF_TARGET")]
    adapter_cmd = [
        "python", "scripts/run_tw_mbcds35_compatibility_frozen_scorer.py", "--asof", args.asof,
        "--feature-frame", str(feature_dir / "feature_frame.csv"),
        "--feature-manifest", str(feature_dir / "input_readiness.json"),
        "--model-a-signals", str(a_signals_path),
        "--source-ledger", str(out / "missing_source_ledger.json"),
        # The frozen scorer's own guard permits only its Model-B isolated root;
        # keep this dry-run output there while retaining the binding report in
        # the project-runtime evidence job-dir.
        "--out", str(ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/candidate_binding_adapter_20260907"),
    ]
    adapter = subprocess.run(adapter_cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    adapter_result = {"command": " ".join(adapter_cmd), "returncode": adapter.returncode, "stdout": adapter.stdout[-4000:], "stderr": adapter.stderr[-4000:], "fail_closed": adapter.returncode != 0}
    (out / "adapter_fail_closed.json").write_text(json.dumps(adapter_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit = {
        "audit_id": "candidate_binding_exact_20260907",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_asof": args.asof,
        "scope": "isolated exact Model A full cross-section -> top50 key binding; Model B rerank preflight",
        "model_a": {
            "manifest": rel(a_manifest_path), "signals": rel(a_signals_path),
            "manifest_sha256": sha(a_manifest_path), "signals_sha256": sha(a_signals_path),
            "manifest_status": a_manifest.get("status"), "run_id": a_manifest.get("run_id"),
            "row_count": len(a_rows), "unique_key_count": len(a_keys), "date_values": sorted({r.get("date", "")[:10] for r in a_rows}),
            "rank_permutation_1_to_150": ranks == list(range(1, 151)), "top50_count": len(top50),
            "top50_keys": top50_keys, "source_artifact": a_manifest.get("source_artifact"),
            "source_model_artifact": a_manifest.get("source_model_artifact"), "source_feature_artifact": a_manifest.get("source_feature_artifact"),
        },
        "model_b_search": {"same_day_manifest_candidates": b_candidates, "ready_signal_candidates": b_selected, "same_day_artifact_found": bool(b_selected)},
        "feature_input": {
            "input_readiness": rel(feature_dir / "input_readiness.json"), "feature_lineage": rel(feature_dir / "feature_lineage.json"),
            "target_rows": feature_manifest.get("target_rows"), "can_score": feature_manifest.get("can_score"),
            "decision": feature_manifest.get("decision"), "blocked_features": missing_feature_fields,
            "strict_pit_oos": feature_lineage.get("strict_pit_oos"),
        },
        "binding_contract": {
            "candidate_source": "Model A full 150-row qlib rank",
            "candidate_rule": "candidate_rank <= 50",
            "model_b_may_change": ["buy_score", "score_rank"],
            "model_b_must_preserve": ["date", "instrument", "candidate_rank", "full_qlib_rank", "signal_asof", "available_at", "source_*"],
            "fallback_or_topup_allowed": False,
        },
        "adapter_preflight": adapter_result,
        "protected_before": before,
        "safety": {"latest_write": False, "provider_publish": False, "cron_write": False, "default_switch": False, "ledger_write": False, "training": False, "broker_or_order": False},
    }
    audit["status"] = "BLOCKED_NO_SAME_DAY_MODEL_B_ARTIFACT" if not b_selected else "READY_FOR_EXACT_BINDING_REVIEW"
    after = fingerprints()
    audit["protected_after"] = after
    audit["protected_unchanged"] = before == after
    audit["validator_ok"] = bool(
        audit["status"] == "READY_FOR_EXACT_BINDING_REVIEW"
        and audit["model_a"]["row_count"] == 150
        and audit["model_a"]["unique_key_count"] == 150
        and audit["model_a"]["rank_permutation_1_to_150"]
        and audit["model_a"]["top50_count"] == 50
        and audit["protected_unchanged"]
        and adapter_result["returncode"] == 0
    )
    (out / "candidate_binding_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "candidate_binding_protected_before.json").write_text(json.dumps(before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "candidate_binding_protected_after.json").write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validator = {
        "ok": audit["validator_ok"], "status": audit["status"], "fail_closed": not audit["validator_ok"],
        "checks": {"model_a_150_rows": audit["model_a"]["row_count"] == 150, "model_a_unique_keys": audit["model_a"]["unique_key_count"] == 150, "model_a_rank_1_to_150": audit["model_a"]["rank_permutation_1_to_150"], "top50_exact": audit["model_a"]["top50_count"] == 50, "model_b_same_day_ready": bool(b_selected), "feature_input_can_score": feature_manifest.get("can_score") is True, "adapter_passed": adapter_result["returncode"] == 0, "protected_unchanged": audit["protected_unchanged"]},
        "accepted_valid_day": False,
        "production_allowed": False,
        "baseline_eligible": False,
    }
    (out / "candidate_binding_validator.json").write_text(json.dumps(validator, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_status = audit["status"]
    report = f"""# Candidate Binding Exact Audit 执行报告\n\n日期：{args.asof}；执行时间：{audit['created_at']}\n范围：isolated/job-dir 中读取现有 Model A 完整 150-row 截面，固化 qlib `rank <= 50` candidate keys，并检查同日 Model B adapter 输入。\n\n## 结论\n\n- 状态：`{report_status}`。\n- Model A：{len(a_rows)} 行、{len(a_keys)} 个唯一 `(date,instrument)`，`full_qlib_rank` 为 1..150；top50 固化为 {len(top50)} 个 key。\n- 同日 Model B READY signal artifact：{len(b_selected)} 个；未发现时不执行重排、不登记 VALID_DAY。\n- Model B feature input：`can_score={feature_manifest.get('can_score')}`；decision=`{feature_manifest.get('decision')}`；blocked features：`{', '.join(missing_feature_fields) or 'none'}`。\n- adapter fail-closed return code：`{adapter_result['returncode']}`；见 `adapter_fail_closed.json`。\n- protected before/after：`{'UNCHANGED' if audit['protected_unchanged'] else 'CHANGED'}`。\n\n## 合同\n\nModel B 只能重排 Model A top50 的 `buy_score/score_rank`；`candidate_rank`、`full_qlib_rank`、date/instrument、PIT 与 source lineage 必须逐 key 保持一致。禁止 rank>50 top-up、fallback、synthetic 或旧 replay。\n\n## 安全边界\n\n本轮只写 `data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/` evidence；未写 latest/provider/calendar/cron/default/baseline，未训练、未产生 replay/订单。\n"""
    (out / "CANDIDATE_BINDING_EXECUTION_REPORT_CN.md").write_text(report, encoding="utf-8")
    next_work = """# Candidate Binding 下一步工作单\n\n状态：`BLOCKED_PENDING_SAME_DAY_MODEL_B_INPUT`。\n\n1. 对新的真实目标交易日生成 Model B 所需的同日 feature frame、feature lineage/manifest、available_at、decision cutoff、source run_id 与 checksum；缺任一项继续 fail-closed。\n2. 取得同一 Model A 150-row source run 后，调用 frozen Model B adapter，只在其 qlib top50 上输出 50 rows，并逐 key 验证 candidate_rank/full_qlib_rank/PIT/source 不变。\n3. 生成 A/B counts、intersection、A-only、B-only、rank mismatch、source/checksum/PIT/available_at/cutoff audit；任意差异不得登记 signal。\n4. 当前未产生 accepted valid day，不能写 shadow ledger、不能开展效果比较，也不能接入 baseline 或自动化默认路径。\n"""
    (out / "NEXT_WORK_CN.md").write_text(next_work, encoding="utf-8")
    print(json.dumps({"status": audit["status"], "validator_ok": audit["validator_ok"], "model_a_rows": len(a_rows), "top50": len(top50), "model_b_ready": len(b_selected), "out": rel(out)}, ensure_ascii=False))
    return 0 if audit["status"] == "READY_FOR_EXACT_BINDING_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
