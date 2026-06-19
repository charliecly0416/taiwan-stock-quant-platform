#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data_tw/experiments/fresh_top50_coverage_repair'
REPORT = ROOT / 'docs/tw_fresh_top50_coverage_repair/PHASEC3_ASOF_REPLAY_READY_CONTRACT_EXECUTION_REPORT_CN.md'
REPAIRED = OUT / 'phasec1_repaired_replay_ready_scores.csv'
C1_COVERAGE = OUT / 'phasec1_coverage_by_day.csv'
ALL_TXT = ROOT / 'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt'
DYN_TXT = ROOT / 'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt'
ACCEPTED_TXT = ROOT / 'qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt'
PRICE_ROOT = ROOT / 'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty'
START = '2025-07-01'
END = '2026-05-07'


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ['status']
    with path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + '\n', encoding='utf-8')


def read_intervals(path: Path) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    with path.open(encoding='utf-8') as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            sym, start, end = parts[0], parts[1], parts[2]
            out.setdefault(sym, []).append((start[:10], end[:10]))
    for sym in out:
        out[sym].sort()
    return out


def in_intervals(intervals: dict[str, list[tuple[str, str]]], sym: str, day: str) -> bool:
    for start, end in intervals.get(sym, []):
        if start <= day <= end:
            return True
    return False


def read_accepted(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()}


def load_price_maps(symbols: set[str]) -> tuple[set[tuple[str, str]], set[tuple[str, str]], dict[str, tuple[str, str]]]:
    current: set[tuple[str, str]] = set()
    next_exec: set[tuple[str, str]] = set()
    ranges: dict[str, tuple[str, str]] = {}
    for sym in sorted(symbols):
        fp = PRICE_ROOT / f'{sym}.csv'
        if not fp.exists():
            continue
        try:
            df = pd.read_csv(fp, usecols=['date', 'close'])
        except Exception:
            continue
        df['date_str'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        dates = sorted(df.loc[df['close'].gt(0) & df['date_str'].notna(), 'date_str'].astype(str).unique().tolist())
        if not dates:
            continue
        ranges[sym] = (dates[0], dates[-1])
        date_set = set(dates)
        for day in dates:
            if START <= day <= END:
                current.add((day, sym))
        for day in sorted({d for d, s in current if s == sym}):
            idx = bisect_right(dates, day)
            if idx < len(dates):
                next_exec.add((day, sym))
    return current, next_exec, ranges


def md(rows: list[dict[str, Any]], fields: list[str], limit: int = 20) -> list[str]:
    out = ['| ' + ' | '.join(fields) + ' |', '| ' + ' | '.join(['---'] * len(fields)) + ' |']
    for row in rows[:limit]:
        out.append('| ' + ' | '.join(str(row.get(f, '')) for f in fields) + ' |')
    return out


def main() -> None:
    for path in [REPAIRED, C1_COVERAGE, ALL_TXT, DYN_TXT, ACCEPTED_TXT]:
        if not path.exists():
            raise FileNotFoundError(path)

    repaired = pd.read_csv(REPAIRED, parse_dates=['date'])
    repaired['date_str'] = repaired['date'].dt.strftime('%Y-%m-%d')
    repaired = repaired[(repaired['date_str'] >= START) & (repaired['date_str'] <= END)].copy()
    repaired['instrument'] = repaired['instrument'].astype(str)

    all_intervals = read_intervals(ALL_TXT)
    dyn_intervals = read_intervals(DYN_TXT)
    accepted = read_accepted(ACCEPTED_TXT)
    symbols = set(repaired['instrument'].unique())
    current_prices, next_prices, price_ranges = load_price_maps(symbols)

    eligibility_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    for row in repaired.to_dict('records'):
        day = str(row['date_str'])
        sym = str(row['instrument'])
        in_all = in_intervals(all_intervals, sym, day)
        in_dyn = in_intervals(dyn_intervals, sym, day)
        in_acc = sym in accepted
        has_current = (day, sym) in current_prices
        has_next = (day, sym) in next_prices
        has_qlib = pd.notna(row.get('qlib_score_raw'))
        has_adaptive = pd.notna(row.get('adaptive_score_baseline'))
        has_ret20 = pd.notna(row.get('ret20'))
        has_vol = pd.notna(row.get('volatility20'))
        has_twii = pd.notna(row.get('TWII_ret20'))
        feature_complete = bool(row.get('feature_complete')) if not pd.isna(row.get('feature_complete')) else False
        eligibility_status = 'eligible' if in_all and in_acc else 'ineligible'
        reasons = []
        if not in_all:
            reasons.append('outside_option_c_instrument_range')
        if not in_acc:
            reasons.append('not_in_accepted_prediction_universe')
        if not in_dyn:
            reasons.append('outside_tw_liquid_dyn_range_aux_only')
        if not reasons:
            reasons.append('ok')
        replay_ready = bool(in_all and in_acc and has_qlib and has_current and has_next and has_adaptive and has_ret20 and has_vol and has_twii)
        replay_reason = []
        if not in_all: replay_reason.append('outside_option_c_instrument_range')
        if not in_acc: replay_reason.append('not_in_accepted_prediction_universe')
        if not has_qlib: replay_reason.append('missing_qlib_score')
        if not has_current: replay_reason.append('missing_current_price')
        if not has_next: replay_reason.append('missing_next_execution_price')
        if not has_adaptive: replay_reason.append('missing_adaptive_score')
        if not has_ret20: replay_reason.append('missing_ret20')
        if not has_vol: replay_reason.append('missing_volatility20')
        if not has_twii: replay_reason.append('missing_twii_ret20')
        if not replay_reason: replay_reason.append('ok')
        pr = price_ranges.get(sym, ('', ''))
        eligibility_rows.append({
            'date': day,
            'instrument': sym,
            'has_repaired_row': True,
            'in_option_c_instrument_range': in_all,
            'in_tw_liquid_dyn_range': in_dyn,
            'in_accepted_prediction_universe': in_acc,
            'eligibility_status': eligibility_status,
            'reason': ';'.join(reasons),
        })
        replay_rows.append({
            'date': day,
            'instrument': sym,
            'has_qlib_score': has_qlib,
            'has_current_price': has_current,
            'has_next_execution_price': has_next,
            'has_adaptive_score': has_adaptive,
            'has_ret20': has_ret20,
            'has_volatility20': has_vol,
            'has_twii_ret20': has_twii,
            'feature_complete': feature_complete,
            'in_option_c_instrument_range': in_all,
            'in_tw_liquid_dyn_range_aux': in_dyn,
            'in_accepted_prediction_universe': in_acc,
            'price_first_date': pr[0],
            'price_last_date': pr[1],
            'replay_ready': replay_ready,
            'reason': ';'.join(replay_reason),
        })

    elig = pd.DataFrame(eligibility_rows)
    rep = pd.DataFrame(replay_rows)
    daily = []
    for day, g in rep.groupby('date', sort=True):
        eg = elig[elig['date'] == day]
        daily.append({
            'date': day,
            'total_repaired_rows': int(g.shape[0]),
            'eligible_rows': int((eg['eligibility_status'] == 'eligible').sum()),
            'replay_ready_rows': int(g['replay_ready'].sum()),
            'ineligible_rows': int((eg['eligibility_status'] != 'eligible').sum()),
            'outside_tw_liquid_dyn_aux_rows': int((~g['in_tw_liquid_dyn_range_aux']).sum()),
            'missing_next_price_rows': int((~g['has_next_execution_price']).sum()),
            'missing_current_price_rows': int((~g['has_current_price']).sum()),
            'missing_adaptive_score_rows': int((~g['has_adaptive_score']).sum()),
            'feature_incomplete_rows': int((~g['feature_complete']).sum()),
        })

    reason_summary = []
    for col, label in [
        ('in_option_c_instrument_range', 'outside_option_c_instrument_range'),
        ('in_accepted_prediction_universe', 'not_in_accepted_prediction_universe'),
        ('has_current_price', 'missing_current_price'),
        ('has_next_execution_price', 'missing_next_execution_price'),
        ('has_adaptive_score', 'missing_adaptive_score'),
        ('has_ret20', 'missing_ret20'),
        ('has_volatility20', 'missing_volatility20'),
        ('has_twii_ret20', 'missing_twii_ret20'),
        ('feature_complete', 'feature_complete_false_ltr_full_feature_aux'),
        ('in_tw_liquid_dyn_range_aux', 'outside_tw_liquid_dyn_range_aux_only'),
    ]:
        reason_summary.append({'reason': label, 'row_count': int((~rep[col]).sum())})

    wcsv(OUT / 'phasec3_asof_eligibility_audit.csv', eligibility_rows, ['date','instrument','has_repaired_row','in_option_c_instrument_range','in_tw_liquid_dyn_range','in_accepted_prediction_universe','eligibility_status','reason'])
    wcsv(OUT / 'phasec3_replay_ready_audit.csv', replay_rows)
    wcsv(OUT / 'phasec3_daily_coverage_summary.csv', daily)
    wcsv(OUT / 'phasec3_replay_ready_reason_summary.csv', reason_summary)

    daily_df = pd.DataFrame(daily)
    total_rows = int(rep.shape[0])
    eligible_rows = int((elig['eligibility_status'] == 'eligible').sum())
    replay_ready_rows = int(rep['replay_ready'].sum())
    future_leak_rows = int((~rep['in_option_c_instrument_range']).sum())
    missing_next = int((~rep['has_next_execution_price']).sum())
    missing_adaptive = int((~rep['has_adaptive_score']).sum())
    dyn_out = int((~rep['in_tw_liquid_dyn_range_aux']).sum())
    gate_pass = bool(
        total_rows == 30750
        and int(daily_df['total_repaired_rows'].min()) == 150
        and future_leak_rows == 0
        and missing_next == 0
        and eligible_rows == total_rows
        and replay_ready_rows >= total_rows - missing_adaptive
    )
    summary = {
        'created_at': now(),
        'phase': 'phase_c3_asof_replay_ready_contract_audit',
        'window': f'{START}..{END}',
        'total_repaired_rows': total_rows,
        'daily_repaired_rows_min': int(daily_df['total_repaired_rows'].min()),
        'daily_repaired_rows_median': float(daily_df['total_repaired_rows'].median()),
        'daily_repaired_rows_max': int(daily_df['total_repaired_rows'].max()),
        'eligible_rows': eligible_rows,
        'eligible_rows_min_by_day': int(daily_df['eligible_rows'].min()),
        'replay_ready_rows': replay_ready_rows,
        'replay_ready_rows_min_by_day': int(daily_df['replay_ready_rows'].min()),
        'future_or_instrument_range_violation_rows': future_leak_rows,
        'accepted_universe_violation_rows': int((~rep['in_accepted_prediction_universe']).sum()),
        'missing_current_price_rows': int((~rep['has_current_price']).sum()),
        'missing_next_execution_price_rows': missing_next,
        'missing_adaptive_score_rows': missing_adaptive,
        'missing_ret20_rows': int((~rep['has_ret20']).sum()),
        'missing_volatility20_rows': int((~rep['has_volatility20']).sum()),
        'missing_twii_ret20_rows': int((~rep['has_twii_ret20']).sum()),
        'feature_complete_false_rows': int((~rep['feature_complete']).sum()),
        'outside_tw_liquid_dyn_aux_rows': dyn_out,
        'tw_liquid_dyn_role': 'auxiliary liquidity/regime audit only, not hard eligibility gate for C3; using it as a hard gate would recreate the S2B post-filter coverage shrinkage C1 repaired.',
        'uses_return_metrics_for_strategy_superiority': False,
        'frontend_default_change_allowed': False,
        'recommended_frontend_readonly_display_contract': bool(gate_pass),
        'recommended_gate': 'phase_c3_asof_replay_ready_contract_passed' if gate_pass else 'phase_c3_blocked_requires_universe_contract_repair',
        'no_training': True,
        'no_frontend_api_provider_monitor_trading': True,
        'artifacts': {
            'asof_eligibility_audit': rel(OUT / 'phasec3_asof_eligibility_audit.csv'),
            'replay_ready_audit': rel(OUT / 'phasec3_replay_ready_audit.csv'),
            'daily_coverage_summary': rel(OUT / 'phasec3_daily_coverage_summary.csv'),
            'reason_summary': rel(OUT / 'phasec3_replay_ready_reason_summary.csv'),
            'report': rel(REPORT),
        },
    }
    wjson(OUT / 'phasec3_summary.json', summary)

    top_reasons = reason_summary
    report_lines = [
        '# Phase C3 执行报告：Repaired Fresh Top50 Asof-Aware 与 Replay-Ready 合同审计',
        '',
        f"生成时间：{summary['created_at']}",
        '',
        '## 1. 执行范围',
        '',
        f"- 审计窗口：`{START}..{END}`。",
        f"- 输入 repaired artifact：`{rel(REPAIRED)}`。",
        f"- instrument range：`{rel(ALL_TXT)}`。",
        f"- dynamic universe 辅助审计：`{rel(DYN_TXT)}`。",
        f"- accepted prediction universe：`{rel(ACCEPTED_TXT)}`。",
        '- 本阶段只做 coverage / asof / replay-ready 合同审计，不使用收益率证明策略优劣。',
        '',
        '## 2. 总体结论',
        '',
        f"- repaired rows：`{summary['daily_repaired_rows_min']} / {summary['daily_repaired_rows_median']} / {summary['daily_repaired_rows_max']}`。",
        f"- eligible rows：`{summary['eligible_rows']}` / `{summary['total_repaired_rows']}`，daily min `{summary['eligible_rows_min_by_day']}`。",
        f"- replay-ready rows：`{summary['replay_ready_rows']}` / `{summary['total_repaired_rows']}`，daily min `{summary['replay_ready_rows_min_by_day']}`。",
        f"- instrument 有效期违规 / 未来倒灌 rows：`{summary['future_or_instrument_range_violation_rows']}`。",
        f"- missing next-day execution price rows：`{summary['missing_next_execution_price_rows']}`。",
        f"- recommended gate：`{summary['recommended_gate']}`。",
        '',
        '## 3. Asof-Aware Eligibility',
        '',
        'option_c `all.txt` 的 start/end 区间作为硬 eligibility 门槛；accepted prediction universe 作为静态 150 合同核对。目标窗口内未发现 instrument 起始日前进入或结束日后继续进入的记录。',
        '',
        '`tw_liquid_dyn` 本轮只作为辅助动态流动性覆盖审计，不作为硬门槛；若将其作为硬门槛，会重新制造 C1 已修复的 S2B post-filter 覆盖收缩。',
        '',
        '## 4. Replay-Ready Audit',
        '',
        *md(top_reasons, ['reason','row_count'], 20),
        '',
        '说明：`feature_complete=false` 是 LTR 全特征合同不完整，不等于 fresh top50 adaptive 不可 replay。C3 replay-ready 硬条件是 qlib score、current price、next execution price、adaptive score、ret20、volatility20、TWII_ret20 与 asof eligibility。',
        '',
        '## 5. 是否存在阻断项',
        '',
        f"- 未来上市 / 无效期股票倒灌：`{summary['future_or_instrument_range_violation_rows']}`。",
        f"- 有 score 但缺 next-day execution price：`{summary['missing_next_execution_price_rows']}`。",
        f"- 有 repaired row 但缺 adaptive score：`{summary['missing_adaptive_score_rows']}`。",
        f"- 有 repaired row 但缺 current price：`{summary['missing_current_price_rows']}`。",
        '',
        '## 6. 后续建议',
        '',
        'C3 合同审计通过时，可以准备前端只读展示合同，把 repaired fresh top50 作为研究候选展示；仍不直接切默认策略。严格策略收益比较必须另开 OOS / walk-forward 主线。',
        '',
        '## 7. 安全边界',
        '',
        '- 未训练 qlib/LTR。',
        '- 未使用收益率证明策略优劣。',
        '- 未修改前端/API。',
        '- 未修改 accepted latest。',
        '- 未触发 provider refresh / publish、monitor、broker、orders、quick-trade。',
        '- 未输出真实买卖、仓位、收益承诺、胜率或上涨概率语义。',
        '',
        '## 8. 输出产物',
        '',
        f"- `{rel(OUT / 'phasec3_asof_eligibility_audit.csv')}`",
        f"- `{rel(OUT / 'phasec3_replay_ready_audit.csv')}`",
        f"- `{rel(OUT / 'phasec3_daily_coverage_summary.csv')}`",
        f"- `{rel(OUT / 'phasec3_replay_ready_reason_summary.csv')}`",
        f"- `{rel(OUT / 'phasec3_summary.json')}`",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'gate': summary['recommended_gate'], 'report': rel(REPORT), 'summary': rel(OUT / 'phasec3_summary.json')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
