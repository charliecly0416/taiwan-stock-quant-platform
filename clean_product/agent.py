"""Artifact-backed research Q&A with an optional, explicitly enabled transport."""
from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

from .artifacts import sha256
from .config import path
from .validation import read_signal_artifact, validate_baseline, verify_file

DISCLAIMER = "仅供研究观察，不构成投资建议；研究分数只表示相对排序。"
UNSAFE = re.compile(r"买|買|卖|賣|下单|下單|仓位|倉位|保证|保證|胜率|勝率|上涨概率|上漲機率|"
                    r"\b(buy|sell|orders?|broker|trade|trading|profit|guarantee)\b|"
                    r"target[_ -]?(weight|position)|quick[_ -]?trade|"
                    r"monitor|provider|accepted.latest|retrain|调参|調參", re.I)


def _read(filename: Path) -> dict:
    value = json.loads(filename.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("AGENT_ARTIFACT_SCHEMA_INVALID")
    return value


def load_prompt(config: dict, asof: str) -> tuple[dict, dict, list[dict]]:
    if date.fromisoformat(asof).isoformat() != asof:
        raise ValueError("AGENT_ASOF_INVALID")
    validate_baseline(config)
    settings = config.get("agent", {})
    root = path(settings.get("prompt_root", "data_tw/artifacts/agent_daily_prompt")).resolve()
    directory = (root / asof).resolve()
    if not directory.is_relative_to(root):
        raise ValueError("AGENT_ARTIFACT_PATH_INVALID")
    for name in ("manifest.json", "prompt_context.json", "prompt_text.md"):
        target = directory / name
        if not target.resolve().is_relative_to(directory) or (target.exists() and target.stat().st_size > 1_000_000):
            raise ValueError("AGENT_ARTIFACT_PATH_OR_SIZE_INVALID")
    manifest = _read(directory / "manifest.json")
    context_file, text_file = directory / "prompt_context.json", directory / "prompt_text.md"
    context = _read(context_file)
    checksum = "sha256:" + hashlib.sha256(context_file.read_bytes() + b"\n" + text_file.read_bytes()).hexdigest()
    if manifest.get("checksum") != checksum:
        raise ValueError("AGENT_CHECKSUM_MISMATCH")
    if (manifest.get("artifact_type") != "tw_agent_daily_prompt"
            or manifest.get("schema_version") != "tw_agent_daily_prompt_v1"
            or context.get("schema_version") != "tw_agent_daily_prompt_context_v1"
            or manifest.get("validation", {}).get("ok") is not True):
        raise ValueError("AGENT_ARTIFACT_SCHEMA_INVALID")
    for flags in (manifest, context.get("safety", {})):
        if (any(flags.get(key) is not True for key in ("readonly_only", "not_order", "not_target_position"))
                or flags.get("production_trade_enabled") is not False):
            raise ValueError("AGENT_SAFETY_FLAGS_INVALID")
    default = config.get("product", {}).get("default_model", "model_a")
    expected_model = config["models"][default]["canonical_id"]
    if (manifest.get("signal_asof") != asof or context.get("date_context", {}).get("signal_asof") != asof
            or manifest.get('target_date') != context.get('date_context', {}).get('target_date')
            or manifest.get("model_ids", {}).get("base") != expected_model
            or context.get("model_context", {}).get("base_model_id") != expected_model):
        raise ValueError("AGENT_IDENTITY_MISMATCH")
    candidate_only = context.get("strategy", {}).get("snapshot_candidate_only") is True
    expected_strategy = "candidate_only_no_strategy_replay" if candidate_only else config.get("strategy")
    expected_execution = "not_applicable_candidate_only_no_strategy_replay" if candidate_only else config.get("execution")
    if (manifest.get("strategy_rule") != expected_strategy
            or manifest.get("execution_price_mode") != expected_execution
            or context.get("strategy", {}).get("strategy_rule") != expected_strategy
            or context.get("date_context", {}).get("execution_price_mode") != expected_execution):
        raise ValueError("AGENT_STRATEGY_CONTEXT_MISMATCH")

    source_roots = [path(settings.get("source_root", "data_tw/artifacts")).resolve(), root]
    if config.get('artifact_root'):
        source_roots.append(path(config['artifact_root']).resolve())
    lineage = context.get("source_lineage", {})
    sources = {}
    # Immutable files prove history. A mutable latest pointer is not a source.
    for key in ("controlled_model_signal_manifest", "controlled_model_signal_csv",
                "readonly_snapshot_manifest", "readonly_snapshot_payload"):
        target = path(lineage.get(key, "")).resolve()
        if not any(target.is_relative_to(source_root) for source_root in source_roots):
            raise ValueError("AGENT_SOURCE_PATH_INVALID")
        verify_file(target, lineage.get(key + "_sha256", ""))
        sources[key] = target
    signal = _read(sources["controlled_model_signal_manifest"])
    stage = config["model_stages"]["model_a_frozen"]
    clean_signal = signal.get('schema_version') == 'tw.clean.artifact.v1'
    if not clean_signal and (signal.get("model_id") != expected_model or signal.get("asof") != asof
            or signal.get("status") != "READY"
            or path(signal.get("source_model_artifact", "")).resolve() != path(stage["model_path"]).resolve()):
        raise ValueError("AGENT_SOURCE_MODEL_IDENTITY_MISMATCH")
    verify_file(stage["model_path"], stage["model_sha256"])
    snapshot = _read(sources["readonly_snapshot_manifest"])
    if snapshot.get("asof") != asof or snapshot.get("model_id") != expected_model:
        raise ValueError("AGENT_SNAPSHOT_IDENTITY_MISMATCH")
    if clean_signal:
        snapshot_payload = _read(sources['readonly_snapshot_payload'])
        if (snapshot.get('source_signal_sha256') != sha256(sources['controlled_model_signal_manifest'])
                or path(snapshot.get('source_signal_manifest', '')).resolve() != sources['controlled_model_signal_manifest']
                or snapshot.get('payload_sha256') != sha256(sources['readonly_snapshot_payload'])
                or snapshot.get('snapshot_candidate_only') is not True or not candidate_only
                or snapshot_payload.get('asof') != asof or snapshot_payload.get('model_id') != expected_model
                or snapshot_payload.get('snapshot_candidate_only') is not True or snapshot_payload.get('no_apply') is not True
                or snapshot_payload.get('rankings') != context.get('rankings', {}).get('qlib_top50_compact')):
            raise ValueError('AGENT_SNAPSHOT_LINEAGE_MISMATCH')

    import pandas as pd
    if clean_signal:
        signal, signal_rows = read_signal_artifact(sources['controlled_model_signal_manifest'].parent, config, default, asof)
        if signal['status'] != 'READY' or path(signal['files']['signals']['path']).resolve() != sources['controlled_model_signal_csv']:
            raise ValueError('AGENT_SOURCE_SIGNAL_SCHEMA_INVALID')
        signal_rows = signal_rows.rename(columns={'score': 'raw_score'})
    else:
        signal_rows = pd.read_csv(sources["controlled_model_signal_csv"])
    required = {"date", "instrument", "candidate_rank", "raw_score"}
    if not required.issubset(signal_rows) or signal_rows.instrument.duplicated().any():
        raise ValueError("AGENT_SOURCE_SIGNAL_SCHEMA_INVALID")
    if not signal_rows.date.astype(str).eq(asof).all():
        raise ValueError("AGENT_SOURCE_SIGNAL_DATE_MISMATCH")
    signals = signal_rows.set_index("instrument")
    ranking = context.get("rankings", {})
    rows = ranking.get("qlib_top50_compact", ranking.get("qlib_top10_compact", []))
    if not isinstance(rows, list) or not rows or len(rows) > 50:
        raise ValueError("AGENT_RANKINGS_UNAVAILABLE")
    for index, row in enumerate(rows, 1):
        symbol = row.get("instrument", "")
        score = float(row.get("qlib_score", float("nan")))
        if (not re.fullmatch(r"TW\d{4,6}", symbol) or symbol not in signals.index
                or row.get("candidate_rank") != index or not math.isfinite(score)
                or int(signals.loc[symbol, "candidate_rank"]) != index
                or not math.isclose(float(signals.loc[symbol, "raw_score"]), score, rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("AGENT_RANKING_SOURCE_MISMATCH")
    return manifest, context, rows


def simple_chat(config: dict, question: str, asof: str, *, symbol: str = "", max_items: int = 5, adapter=None) -> dict:
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1000:
        raise ValueError("question must contain 1..1000 characters")
    if not isinstance(symbol, str) or (symbol and not re.fullmatch(r"(?:TW)?\d{4,6}", symbol)):
        raise ValueError("symbol must be a Taiwan stock code")
    if type(max_items) is not int or not 1 <= max_items <= 20:
        raise ValueError("maxItems must be an integer between 1 and 20")
    result = {"status": "BLOCKED", "blocked": True, "mode": "artifact_local",
              "citations": [], "warnings": [], "readonly": True, "simulation_only": True,
              "research_only_disclaimer": DISCLAIMER}
    if UNSAFE.search(question):
        return {**result, "reason": "RESEARCH_ONLY_QUESTION", "intent": "blocked_action",
                "answer": "这里仅解释研究证据，无法提供交易行动、仓位或收益承诺。可询问当前排名、资料日期与策略口径。"}
    try:
        manifest, context, rows = load_prompt(config, asof)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {**result, "reason": str(exc) if isinstance(exc, ValueError) else "AGENT_ARTIFACT_UNAVAILABLE",
                "intent": "context_unavailable", "answer": "每日研究上下文未通过验证，目前无法据此给出准确回答。"}
    citation = f"agent_prompt:{asof}:{manifest['checksum']}"
    digest = {"signal_asof": asof, "target_date": manifest.get("target_date"), "checksum": manifest["checksum"]}
    if adapter is not None or config.get('agent', {}).get('remote_enabled') is True:
        try:
            if adapter is None:
                from .agent_transport import OpenAIAdapter
                adapter = OpenAIAdapter.from_config(config['agent'])
            # Paths and other local audit metadata are never sent remotely.
            controlled = {'date_context': digest, 'model_context': {'base_model_id': manifest['model_ids']['base']},
                          'rankings': {'qlib_top50_compact': [
                              {key: row[key] for key in ('instrument', 'candidate_rank', 'qlib_score')} for row in rows]},
                          'strategy': {'strategy_rule': manifest['strategy_rule'],
                                       'execution_price_mode': manifest['execution_price_mode'],
                                       'snapshot_candidate_only': context.get('strategy', {}).get('snapshot_candidate_only') is True}}
            remote = adapter.complete(question=question, context=controlled, citation=citation)
            if (not isinstance(remote, dict) or set(remote) - {'answer', 'citations', 'warnings'}
                    or not isinstance(remote.get('answer'), str) or not 1 <= len(remote['answer']) <= 8000
                    or remote.get('citations') != [citation]
                    or not isinstance(remote.get('warnings', []), list)
                    or not all(isinstance(item, str) and len(item) <= 500 for item in remote.get('warnings', []))
                    or UNSAFE.search(json.dumps(remote, ensure_ascii=False))):
                raise ValueError('AGENT_REMOTE_OUTPUT_REJECTED')
            mentioned = set(re.findall(r'TW[0-9]{4,6}', remote['answer']))
            if not mentioned.issubset({item['instrument'] for item in rows}):
                raise ValueError('AGENT_REMOTE_OUTPUT_REJECTED')
            return {**result, **remote, 'status': 'READY', 'blocked': False, 'mode': 'artifact_remote',
                    'intent': 'research_context', 'context_digest': digest}
        except Exception:
            return {**result, 'mode': 'artifact_remote', 'reason': 'AGENT_REMOTE_UNAVAILABLE_OR_REJECTED',
                    'answer': '远端研究回答暂不可用或未通过证据检查，请稍后重试。'}
    requested = symbol or next(iter(re.findall(r"(?<![A-Za-z0-9])(?:TW)?\d{4,6}(?!\d)", question)), "")
    if requested:
        requested = requested if requested.startswith("TW") else "TW" + requested
        row = next((item for item in rows if item["instrument"] == requested), None)
        answer = (f"{asof}，{requested} 在已验证候选中排名第 {row['candidate_rank']}，研究分数 {float(row['qlib_score']):.6g}。"
                  if row else f"{asof} 的每日上下文未包含 {requested}；无法推断它在完整市场中的排名或状态。")
        intent = "symbol_context"
    elif re.search(r"策略|strategy|规则|規則|执行|執行", question, re.I):
        candidate_only = context.get("strategy", {}).get("snapshot_candidate_only") is True
        answer = (f"{asof} 的快照只有模型候选，没有持仓、退出决策或策略回放证据。"
                  if candidate_only else f"{asof} 的策略口径为 {manifest['strategy_rule']}，执行时点为 {manifest['execution_price_mode']}；这只是研究规则说明。")
        intent = "strategy_context"
    elif re.search(r"日期|最新|资料|資料|数据|數據|date|fresh", question, re.I):
        answer = f"本次上下文的信号日期是 {asof}，目标日期是 {manifest.get('target_date')}；未验证更晚日期。"
        intent = "date_context"
    elif re.search(r"排名|排序|候选|候選|第一|top|rank|模型|model", question, re.I):
        shown = rows[:1 if re.search(r"第一|榜首|top\s*1\b", question, re.I) else max_items]
        answer = f"{asof} 的已验证研究排序：" + "；".join(f"#{row['candidate_rank']} {row['instrument']}" for row in shown) + "。"
        intent = "ranking_context"
    else:
        answer, intent = "现有每日上下文不足以回答这个问题。可查询候选排名、指定股票、资料日期或策略规则。", "insufficient_evidence"
    return {**result, "status": "READY", "blocked": False, "intent": intent, "answer": answer,
            "citations": [citation], "context_digest": digest,
            "warnings": ["本地证据解释；未调用远端语言模型。"]}
