---
created_at: 2026-06-25T15:05:56+00:00
status: staged_refresh_complete_waiting_for_review
scope: option_c_yahoo_scrapling_staged_refresh_report
---

# Option C Yahoo Scrapling Staged Refresh Report

## Summary

- job_id: `rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625`
- status: `staged_refresh_complete_waiting_for_review`
- asof: `2026-06-25`
- job_dir: `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625`
- universe_count: `150`
- proxy_used: `True`
- fetch_status: `pass`
- symbols_success: `150` / `150`
- normalized_validation: `pass`
- provider_validation: `pass`
- model_smoke: `pass`
- formal_provider_mutated: `False`
- latest_signal_updated: `False`

## Fetch

```json
{
  "status": "pass",
  "source": "Yahoo Finance chart API via Scrapling",
  "source_policy": "Yahoo-only; no yfinance; no FinMind fallback; no mixed provider",
  "start": "2015-01-01",
  "end": "2026-06-25",
  "proxy_used": true,
  "proxy": "http://127.0.0.1:7890",
  "sleep_seconds": 0.0,
  "symbols_expected": 150,
  "symbols_success": 150,
  "symbols_empty": [],
  "symbols_failed": {},
  "rows_written": 400205,
  "suffix_used": {
    "TW1301": "1301.TW",
    "TW1303": "1303.TW",
    "TW1326": "1326.TW",
    "TW1519": "1519.TW",
    "TW1560": "1560.TW",
    "TW1590": "1590.TW",
    "TW1605": "1605.TW",
    "TW1711": "1711.TW",
    "TW1717": "1717.TW",
    "TW1785": "1785.TWO",
    "TW1802": "1802.TW",
    "TW1815": "1815.TWO",
    "TW2049": "2049.TW",
    "TW2059": "2059.TW",
    "TW2301": "2301.TW",
    "TW2303": "2303.TW",
    "TW2308": "2308.TW",
    "TW2313": "2313.TW",
    "TW2317": "2317.TW",
    "TW2324": "2324.TW",
    "TW2327": "2327.TW",
    "TW2330": "2330.TW",
    "TW2337": "2337.TW",
    "TW2344": "2344.TW",
    "TW2345": "2345.TW",
    "TW2357": "2357.TW",
    "TW2360": "2360.TW",
    "TW2367": "2367.TW",
    "TW2368": "2368.TW",
    "TW2376": "2376.TW",
    "TW2379": "2379.TW",
    "TW2382": "2382.TW",
    "TW2383": "2383.TW",
    "TW2404": "2404.TW",
    "TW2408": "2408.TW",
    "TW2409": "2409.TW",
    "TW2412": "2412.TW",
    "TW2449": "2449.TW",
    "TW2451": "2451.TW",
    "TW2454": "2454.TW",
    "TW2455": "2455.TW",
    "TW2467": "2467.TW",
    "TW2481": "2481.TW",
    "TW2485": "2485.TW",
    "TW2486": "2486.TW",
    "TW2489": "2489.TW",
    "TW2492": "2492.TW",
    "TW2603": "2603.TW",
    "TW2609": "2609.TW",
    "TW2881": "2881.TW",
    "TW2882": "2882.TW",
    "TW2887": "2887.TW",
    "TW2891": "2891.TW",
    "TW3006": "3006.TW",
    "TW3008": "3008.TW",
    "TW3017": "3017.TW",
    "TW3030": "3030.TW",
    "TW3034": "3034.TW",
    "TW3036": "3036.TW",
    "TW3037": "3037.TW",
    "TW3044": "3044.TW",
    "TW3081": "3081.TWO",
    "TW3105": "3105.TWO",
    "TW3131": "3131.TWO",
    "TW3163": "3163.TWO",
    "TW3167": "3167.TW",
    "TW3189": "3189.TW",
    "TW3211": "3211.TWO",
    "TW3231": "3231.TW",
    "TW3260": "3260.TWO",
    "TW3264": "3264.TWO",
    "TW3293": "3293.TWO",
    "TW3324": "3324.TWO",
    "TW3363": "3363.TWO",
    "TW3374": "3374.TWO",
    "TW3376": "3376.TW",
    "TW3443": "3443.TW",
    "TW3450": "3450.TW",
    "TW3481": "3481.TW",
    "TW3491": "3491.TWO",
    "TW3529": "3529.TWO",
    "TW3533": "3533.TW",
    "TW3563": "3563.TW",
    "TW3583": "3583.TW",
    "TW3653": "3653.TW",
    "TW3661": "3661.TW",
    "TW3665": "3665.TW",
    "TW3693": "3693.TWO",
    "TW3702": "3702.TW",
    "TW3711": "3711.TW",
    "TW3714": "3714.TW",
    "TW3715": "3715.TW",
    "TW4749": "4749.TWO",
    "TW4919": "4919.TW",
    "TW4958": "4958.TW",
    "TW4967": "4967.TW",
    "TW4971": "4971.TWO",
    "TW4977": "4977.TW",
    "TW4979": "4979.TWO",
    "TW4989": "4989.TW",
    "TW4991": "4991.TWO",
    "TW5269": "5269.TW",
    "TW5274": "5274.TWO",
    "TW5289": "5289.TWO",
    "TW5347": "5347.TWO",
    "TW5351": "5351.TWO",
    "TW5439": "5439.TWO",
    "TW5483": "5483.TWO",
    "TW5536": "5536.TWO",
    "TW6139": "6139.TW",
    "TW6147": "6147.TWO",
    "TW6187": "6187.TWO",
    "TW6213": "6213.TW",
    "TW6223": "6223.TWO",
    "TW6239": "6239.TW",
    "TW6257": "6257.TW",
    "TW6271": "6271.TW",
    "TW6274": "6274.TWO",
    "TW6282": "6282.TW",
    "TW6285": "6285.TW",
    "TW6290": "6290.TWO",
    "TW6415": "6415.TW",
    "TW6442": "6442.TW",
    "TW6443": "6443.TW",
    "TW6446": "6446.TW",
    "TW6488": "6488.TWO",
    "TW6505": "6505.TW",
    "TW6510": "6510.TWO",
    "TW6515": "6515.TW",
    "TW6531": "6531.TW",
    "TW6669": "6669.TW",
    "TW6683": "6683.TWO",
    "TW6770": "6770.TW",
    "TW6781": "6781.TW",
    "TW6789": "6789.TW",
    "TW6805": "6805.TW",
    "TW6919": "6919.TW",
    "TW7769": "7769.TW",
    "TW8021": "8021.TW",
    "TW8028": "8028.TW",
    "TW8039": "8039.TW",
    "TW8046": "8046.TW",
    "TW8096": "8096.TWO",
    "TW8110": "8110.TW",
    "TW8112": "8112.TW",
    "TW8150": "8150.TW",
    "TW8210": "8210.TW",
    "TW8299": "8299.TWO",
    "TW8358": "8358.TWO",
    "TW8996": "8996.TW"
  },
  "http_status_counts": {
    "200": 150,
    "404": 38
  },
  "per_symbol_sample": [
    {
      "symbol": "TW1301",
      "ticker": "1301.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1303",
      "ticker": "1303.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1326",
      "ticker": "1326.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1519",
      "ticker": "1519.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1560",
      "ticker": "1560.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1590",
      "ticker": "1590.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1605",
      "ticker": "1605.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1711",
      "ticker": "1711.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1717",
      "ticker": "1717.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1785",
      "ticker": "1785.TWO",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1802",
      "ticker": "1802.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1815",
      "ticker": "1815.TWO",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2049",
      "ticker": "2049.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2059",
      "ticker": "2059.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2301",
      "ticker": "2301.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2303",
      "ticker": "2303.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2308",
      "ticker": "2308.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2313",
      "ticker": "2313.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2317",
      "ticker": "2317.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2324",
      "ticker": "2324.TW",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    }
  ],
  "adjustment": "yahoo_adjusted_ohlc_factor_adjclose_over_close"
}
```

## Normalized Validation

```json
{
  "status": "pass",
  "errors": [],
  "data_dir": "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized",
  "symbols_expected": 150,
  "files_found": 150,
  "missing_count": 0,
  "empty_count": 0,
  "issue_symbol_count": 0,
  "symbols_with_asof": 150,
  "missing_asof_count": 0,
  "date_max_min": "2026-06-25",
  "date_max_max": "2026-06-25",
  "total_rows": 400205,
  "missing_symbols": [],
  "empty_symbols": [],
  "missing_asof_symbols": [],
  "issues_sample": {},
  "per_symbol_sample": [
    {
      "symbol": "TW1301",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1303",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1326",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1519",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1560",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1590",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1605",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1711",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1717",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1785",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1802",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW1815",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2049",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2059",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2301",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2303",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2308",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2313",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2317",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    },
    {
      "symbol": "TW2324",
      "rows": 2789,
      "date_min": "2015-01-05",
      "date_max": "2026-06-25"
    }
  ]
}
```

## Provider Validation

```json
{
  "status": "pass",
  "errors": [],
  "provider": "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/staged_qlib_bin",
  "calendar_min": "2015-01-05",
  "calendar_max": "2026-06-25",
  "calendar_count": 2789,
  "calendar_has_asof": true,
  "active_universe_count": 150,
  "expected_field_counts": {
    "close": 150,
    "factor": 150,
    "high": 150,
    "low": 150,
    "open": 150,
    "volume": 150,
    "vwap": 150
  },
  "missing_feature_symbols": [],
  "unexpected_fields_sample": {},
  "rejected_fields_present": []
}
```

## Model Smoke

```json
{
  "status": "pass",
  "provider": "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/staged_qlib_bin",
  "asof": "2026-06-25",
  "symbols": 150,
  "prediction_rows": 150,
  "finite_prediction_share": 1.0,
  "score_stats": {
    "count": 150,
    "finite_count": 150,
    "min": -0.06646933879585182,
    "p1": -0.047388800505628575,
    "p5": -0.03075654224756389,
    "p50": 0.007873550877721226,
    "p95": 0.09764459056194391,
    "p99": 0.1167408908372758,
    "max": 0.12971933602788344,
    "mean": 0.013978574754957647,
    "std": 0.036320598123506354
  },
  "output": "data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/reports/staged_prediction.csv",
  "published_latest_signal": false,
  "formal_provider_mutated": false
}
```

## Explicit Non-Actions

- No FinMind fallback or mixed-provider fill was used.
- No formal normalized directory was overwritten.
- No formal qlib provider was overwritten.
- No latest_signal.json was updated.
- No paper/live trading, broker connection, orders, target positions, retraining, tuning, recorder switch, or universe expansion was performed.
