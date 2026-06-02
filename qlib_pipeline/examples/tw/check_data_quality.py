from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def read_symbol_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["symbol"] = df["symbol"].astype(str).str.upper()
    return df.sort_values("date")


def expected_dates_for(df: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if df.empty:
        return pd.DatetimeIndex([])
    start = df["date"].min()
    end = df["date"].max()
    return calendar[(calendar >= start) & (calendar <= end)]


def check_symbol(path: Path, calendar: pd.DatetimeIndex) -> tuple[dict, list[dict]]:
    df = read_symbol_csv(path)
    symbol = path.stem.upper()
    cases: list[dict] = []

    duplicated = df[df["date"].duplicated(keep=False)]
    for _, row in duplicated.head(20).iterrows():
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "duplicate_date", "detail": "duplicate date row"})

    expected = expected_dates_for(df, calendar)
    actual = pd.DatetimeIndex(df["date"].dropna().unique())
    missing = expected.difference(actual)
    missing_ratio = float(len(missing) / len(expected)) if len(expected) else 0.0
    if len(missing):
        groups = []
        start = prev = missing[0]
        for date in missing[1:]:
            if (date - prev).days <= 4:
                prev = date
                continue
            groups.append((start, prev))
            start = prev = date
        groups.append((start, prev))
        for start, end in groups[:20]:
            cases.append({
                "symbol": symbol,
                "date": start.date().isoformat(),
                "issue": "missing_trade_dates",
                "detail": f"{start.date().isoformat()} to {end.date().isoformat()}",
            })

    ohlc_cols = ["open", "high", "low", "close"]
    for col in ohlc_cols + ["volume"]:
        bad = df[df[col].isna()]
        for _, row in bad.head(20).iterrows():
            cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": f"{col}_nan", "detail": "NaN value"})

    non_positive = df[(df[ohlc_cols] <= 0).any(axis=1)]
    for _, row in non_positive.head(30).iterrows():
        values = {col: row[col] for col in ohlc_cols}
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "non_positive_ohlc", "detail": str(values)})

    high_bad = df[df["high"] < df[["open", "close"]].max(axis=1)]
    for _, row in high_bad.head(30).iterrows():
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "high_below_open_close", "detail": f"open={row.open}, high={row.high}, close={row.close}"})

    low_bad = df[df["low"] > df[["open", "close"]].min(axis=1)]
    for _, row in low_bad.head(30).iterrows():
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "low_above_open_close", "detail": f"open={row.open}, low={row.low}, close={row.close}"})

    negative_volume = df[df["volume"] < 0]
    for _, row in negative_volume.head(20).iterrows():
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "negative_volume", "detail": f"volume={row.volume}"})

    zero_volume = df[df["volume"] == 0]
    for _, row in zero_volume.head(20).iterrows():
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "zero_volume", "detail": "volume=0"})

    close_ret = df["close"].pct_change().abs()
    large_move = df[close_ret > 0.2].copy()
    for idx, row in large_move.head(30).iterrows():
        cases.append({"symbol": symbol, "date": row["date"].date().isoformat(), "issue": "large_adjusted_close_move", "detail": f"abs_ret={close_ret.loc[idx]:.4f}"})

    summary = {
        "symbol": symbol,
        "rows": int(len(df)),
        "start_date": df["date"].min().date().isoformat() if len(df) else "",
        "end_date": df["date"].max().date().isoformat() if len(df) else "",
        "expected_trade_days": int(len(expected)),
        "missing_trade_days": int(len(missing)),
        "missing_trade_day_ratio": missing_ratio,
        "close_nan": int(df["close"].isna().sum()),
        "volume_nan": int(df["volume"].isna().sum()),
        "non_positive_ohlc": int(len(non_positive)),
        "high_below_open_close": int(len(high_bad)),
        "low_above_open_close": int(len(low_bad)),
        "negative_volume": int(len(negative_volume)),
        "zero_volume": int(len(zero_volume)),
        "large_adjusted_close_move_gt20pct": int(len(large_move)),
        "duplicate_dates": int(df["date"].duplicated().sum()),
        "issue_count": int(len(cases)),
    }
    return summary, cases


def to_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "无可疑案例"
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.6f}")
        else:
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))
    header = "| " + " | ".join(display.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in display.to_numpy(dtype=str)]
    return "\n".join([header, sep] + rows)


def write_report(output_dir: Path, summary: pd.DataFrame, cases: pd.DataFrame) -> None:
    worst = summary.sort_values(["issue_count", "missing_trade_day_ratio"], ascending=[False, False]).head(15)
    issue_counts = cases["issue"].value_counts().reset_index() if not cases.empty else pd.DataFrame(columns=["issue", "count"])
    issue_counts.columns = ["issue", "count"]
    report = output_dir / "data_quality_report.md"
    with report.open("w", encoding="utf-8") as f:
        f.write("# 台股数据质量检查报告\n\n")
        f.write("## 摘要\n\n")
        f.write(f"- 检查 symbols: {len(summary)}\n")
        f.write(f"- 可疑案例数: {len(cases)}\n")
        f.write(f"- close NaN 总数: {int(summary['close_nan'].sum())}\n")
        f.write(f"- volume NaN 总数: {int(summary['volume_nan'].sum())}\n")
        f.write(f"- OHLC 非正总数: {int(summary['non_positive_ohlc'].sum())}\n")
        f.write(f"- high/open/close 异常总数: {int(summary['high_below_open_close'].sum())}\n")
        f.write(f"- low/open/close 异常总数: {int(summary['low_above_open_close'].sum())}\n")
        f.write("\n## 问题类型统计\n\n")
        f.write(to_markdown_table(issue_counts) if not issue_counts.empty else "无可疑案例")
        f.write("\n\n## 最可疑股票\n\n")
        cols = ["symbol", "rows", "start_date", "end_date", "missing_trade_days", "missing_trade_day_ratio", "non_positive_ohlc", "large_adjusted_close_move_gt20pct", "issue_count"]
        f.write(to_markdown_table(worst[cols]))
        f.write("\n\n## 说明\n\n")
        f.write("本报告只标记问题，不删除或修补数据。后续应优先检查 `suspicious_cases.csv` 中的原始 OHLC 异常和大幅跳动日期。\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check normalized TW data quality.")
    parser.add_argument("--data-dir", default="data_tw/normalized")
    parser.add_argument("--calendar-symbol", default="TWII")
    parser.add_argument("--output-dir", default="data_tw/experiments/data_quality")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    calendar_df = read_symbol_csv(data_dir / f"{args.calendar_symbol.upper()}.csv")
    calendar = pd.DatetimeIndex(calendar_df["date"].dropna().unique()).sort_values()

    summaries = []
    all_cases = []
    for path in sorted(data_dir.glob("TW*.csv")):
        summary, cases = check_symbol(path, calendar)
        summaries.append(summary)
        all_cases.extend(cases)

    summary_df = pd.DataFrame(summaries).sort_values("symbol")
    cases_df = pd.DataFrame(all_cases).sort_values(["symbol", "date", "issue"]) if all_cases else pd.DataFrame(columns=["symbol", "date", "issue", "detail"])
    summary_df.to_csv(output_dir / "summary.csv", index=False)
    cases_df.to_csv(output_dir / "suspicious_cases.csv", index=False)
    write_report(output_dir, summary_df, cases_df)
    print(f"wrote {output_dir / 'summary.csv'}")
    print(f"wrote {output_dir / 'suspicious_cases.csv'}")
    print(f"wrote {output_dir / 'data_quality_report.md'}")
    print(summary_df.sort_values('issue_count', ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
