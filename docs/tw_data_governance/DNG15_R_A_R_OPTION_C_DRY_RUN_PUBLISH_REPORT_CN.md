---
created_at: 2026-06-29T13:37:43+00:00
status: daily_signal_dry_run_failed
scope: option_c_yahoo_scrapling_publish_rollback_report
---

# Option C Yahoo Scrapling Publish/Rollback Report

## Summary

- publish_job_id: `dng15_r_a_r_option_c_dry_run_publish_20260626`
- mode: `dry-run-publish`
- status: `daily_signal_dry_run_failed`
- provider_scope: `option_c_150`
- asof: `2026-06-26`
- staged_gate: `pass`
- publish_result: `dry_run_only_no_mutation`
- daily_signal_dry_run: `fail`
- latest_signal_unchanged: `True`

## Payload

```json
{
  "publish_job_id": "dng15_r_a_r_option_c_dry_run_publish_20260626",
  "created_at": "2026-06-29T13:37:36+00:00",
  "mode": "dry-run-publish",
  "provider_scope": "option_c_150",
  "provider_strategy": "Strategy A: Option C dedicated 150-symbol formal normalized/provider; legacy wider provider remains observed-only and is not overwritten",
  "asof": "2026-06-26",
  "staged_job_dir": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy",
  "publish_dir": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626",
  "staged_gate": {
    "status": "pass",
    "errors": [],
    "job_dir": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy",
    "reports": {
      "execution_summary": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/execution_summary.json",
      "fetch": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/fetch_report.json",
      "normalized_validation": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/normalized_validation.json",
      "provider_validation": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/provider_validation.json",
      "model_smoke": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/model_smoke.json",
      "artifact_manifest": "data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/artifact_manifest.json"
    },
    "summary": {
      "execution_status": "staged_refresh_complete_waiting_for_review",
      "asof": "2026-06-26",
      "symbols_success": 150,
      "symbols_expected": 150,
      "normalized_status": "pass",
      "provider_status": "pass",
      "model_smoke_status": "pass",
      "prediction_rows": 150,
      "finite_prediction_share": 1.0
    }
  },
  "backup_plan": {
    "status": "planned",
    "backup_root": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/backup",
    "provider_scope": "option_c_150",
    "strategy": "Option C dedicated 150-symbol provider; legacy wider provider is not overwritten",
    "sources": {
      "option_c_formal_normalized": {
        "path": "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized",
        "exists": true,
        "file_count": 150,
        "total_bytes": 52869572,
        "sample": [
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW3260.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW8046.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2486.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2409.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW3491.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2881.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2303.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW4971.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW5536.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2449.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2408.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW6805.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW6282.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2383.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW3081.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW4991.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW6187.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW3714.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2308.csv",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized/TW2376.csv"
        ]
      },
      "option_c_formal_provider": {
        "path": "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
        "exists": true,
        "file_count": 1052,
        "total_bytes": 11245109,
        "sample": [
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/close.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/vwap.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/volume.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/low.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/open.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/factor.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw2891/high.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/close.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/vwap.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/volume.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/low.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/open.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/factor.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3167/high.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3376/close.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3376/vwap.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3376/volume.day.bin",
          "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/tw3376/low.day.bin"
        ]
      },
      "legacy_formal_normalized_observed_only": {
        "path": "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty",
        "exists": true,
        "file_count": 1987,
        "total_bytes": 628575872,
        "sample": [
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW2430.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW2250.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW3260.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW6116.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW8046.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW3067.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW2547.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW3516.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW6142.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW6680.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW2506.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW1472.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW2906.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW8478.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW1541.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW6691.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW4588.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW5202.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW4167.csv",
          "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW5533.csv"
        ]
      },
      "legacy_formal_provider_observed_only": {
        "path": "data_tw/experiments/yahoo_adjusted_primary/qlib_bin",
        "exists": false,
        "file_count": 0,
        "total_bytes": 0
      }
    }
  },
  "formal_paths": {
    "formal_normalized": "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized",
    "formal_provider": "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
    "legacy_formal_normalized": "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty",
    "legacy_formal_provider": "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
  },
  "latest_signal_before": {
    "exists": true,
    "path": "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "size_bytes": 526,
    "sha256": "43b99ca9850f00fcc364342ab3b295ea4f6691599f1c7b51ba4ab0848b0b0ab1"
  },
  "latest_signal_updated": false,
  "normal_signal_run": false,
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "paper_orders_enabled": false,
    "live_trading_enabled": false,
    "quick_trade_enabled": false,
    "writes_orders": false,
    "writes_positions": false,
    "research_signal_not_order": true
  },
  "errors": [
    "daily signal dry-run failed"
  ],
  "publish_result": {
    "status": "dry_run_only_no_mutation",
    "normalized_publish": "planned_not_executed",
    "provider_publish": "planned_not_executed",
    "rollback": "designed_not_executed_without_publish"
  },
  "daily_signal_dry_run": {
    "status": "fail",
    "command": "/home/chuliyang/software/miniconda3/bin/python examples/tw/run_option_c_daily_signal_option_c_provider.py --asof 2026-06-26 --dry-run",
    "returncode": 1,
    "stdout_path": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/reports/daily_signal_dry_run_stdout.txt",
    "stderr_path": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/reports/daily_signal_dry_run_stderr.txt",
    "stdout_tail": "ModuleNotFoundError. CatBoostModel are skipped. (optional: maybe installing CatBoostModel can fix it.)\nModuleNotFoundError. XGBModel is skipped(optional: maybe installing xgboost can fix it).\n{\n  \"run_id\": \"option_c_provider_dry_run_20260626_20260629T133741Z\",\n  \"status\": \"blocked_formal_validation_failed\",\n  \"run_dir\": \"data_tw/experiments/option_c_daily_signal_option_c_provider/option_c_provider_dry_run_20260626_20260629T133741Z\",\n  \"errors\": [\n    \"option_c_formal_source_missing_asof\",\n    \"option_c_provider_calendar_stale\"\n  ]\n}\n",
    "stderr_tail": "",
    "latest_before": {
      "exists": true,
      "path": "data_tw/experiments/option_c_daily_signal/latest_signal.json",
      "size_bytes": 526,
      "sha256": "43b99ca9850f00fcc364342ab3b295ea4f6691599f1c7b51ba4ab0848b0b0ab1"
    },
    "latest_after": {
      "exists": true,
      "path": "data_tw/experiments/option_c_daily_signal/latest_signal.json",
      "size_bytes": 526,
      "sha256": "43b99ca9850f00fcc364342ab3b295ea4f6691599f1c7b51ba4ab0848b0b0ab1"
    },
    "latest_signal_unchanged": true,
    "normal_signal_run": false
  },
  "latest_signal_after": {
    "exists": true,
    "path": "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "size_bytes": 526,
    "sha256": "43b99ca9850f00fcc364342ab3b295ea4f6691599f1c7b51ba4ab0848b0b0ab1"
  },
  "status": "daily_signal_dry_run_failed",
  "completed_at": "2026-06-29T13:37:43+00:00",
  "artifact_manifest": {
    "status": "pass",
    "job_dir": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626",
    "entries": [
      {
        "path": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/reports/daily_signal_dry_run_stderr.txt",
        "size_bytes": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
      },
      {
        "path": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/reports/daily_signal_dry_run_stdout.txt",
        "size_bytes": 539,
        "sha256": "1c3003b7ff50f9ec4fc8736d7b327ede53ef6cbc370593183bac69259abeb994"
      },
      {
        "path": "data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/reports/publish_execution_summary.json",
        "size_bytes": 12317,
        "sha256": "276a6b72b2fae465665e7084aa60ee2627691cdf7fffefeaeab2c5d8ef054a0e"
      }
    ]
  }
}
```
