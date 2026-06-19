# Phase V5 外部数据就绪与 U 链收口执行报告

生成日期：2026-06-17

## 1. 目标

将 V4R 的可解释 fallback 继续推进到 `all_required_ready`，启动 U 链并更新 readonly latest。

## 2. 关键修复

- `scripts/pull_tw_provider_staging_data.py`
  - orthogonal O2 读取改为优先使用 `daily_ltr_rerank_latest.json`。
  - 将 orthogonal coverage denominator 改为 artifact 自带 `top50_input_count`，避免旧的全量 150 口径误伤 Top50 正交日更。
- `scripts/repair_p3rrr_orthogonal_source_freshness.py`
  - 补齐 FinMind institutional / margin raw freshness 到 `2026-06-17`。
- `scripts/build_p3rr_latest_orthogonal_features.py`
  - 生成 `latest_orthogonal_features_2026-06-17.csv`。
- `scripts/run_tw_ltr_p3_daily_rerank_readonly.py`
  - 生成 `daily_ltr_rerank_latest.json`，其 `asof=2026-06-17`、`status=ready`、`pit_pass=true`。

## 3. 真实运行结果

Run ID：
- `phasev5_external_provider_all_ready_codex_v2`

结果：
- `status=success`
- `gate_status=all_required_ready`
- `readonly_latest_updated=true`
- `u_chain_started=true`

## 4. 关键证据

### 4.1 provider network audit

- `request_count=25`
- `actual_external_request_count=25`
- `successful_request_count=15`
- `failed_request_count=10`
- `unauthorized_request_count=0`
- allowed hosts only:
  - `api.finmindtrade.com`
  - `query1.finance.yahoo.com`

### 4.2 provider staging / readiness

- `yahoo_daily_price.status=ready`
- `yahoo_daily_price.fallback_used=true`
- `finmind_daily_price.status=ready`
- `finmind_institutional_flow.status=ready`
- `finmind_margin_short.status=ready`
- `orthogonal_o2_features.status=ready`
- `orthogonal_o2_features.actual_latest_asof=2026-06-17`
- `orthogonal_o2_features.coverage_ratio=1.0`

### 4.3 U-chain validation

`u_chain_summary.json` 显示：
- ingestion passed
- feature artifact passed
- model signal passed
- order intent passed
- readonly snapshot passed
- run registry passed

## 5. 验证

- `scripts/validate_tw_provider_staging_data.py` passed
- `scripts/validate_tw_data_readiness_gate.py` passed
- `scripts/validate_tw_real_provider_daily_readonly_update.py` passed
- golden 回归 passed
- `python -m py_compile` passed

## 6. 前端情况

- 前端 build passed
- 真实后端 E2E 已验证按钮路径与安全边界。
- 当前 E2E harness 仍在 browser 代理绑定上存在环境差异，未作为 V5 成功判定依据。

## 7. 安全边界

未发现：
- provider publish
- accepted latest switch
- qlib accepted latest switch
- monitor config/scan/alerts 写入
- broker / quick-trade / orders
- Agent 修改

## 8. 结论

V5 已完成：外部 provider fallback、orthogonal freshness 追平、`all_required_ready`、U 链启动、readonly latest 更新。