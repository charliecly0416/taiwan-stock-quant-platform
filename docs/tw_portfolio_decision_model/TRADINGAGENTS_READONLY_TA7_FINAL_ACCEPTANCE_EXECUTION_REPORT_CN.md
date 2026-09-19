# TradingAgents Readonly TA7 Final Acceptance 执行报告

生成日期：2026-07-10

## 1. Scope

- Assigned phase: TA7 端到端只读回归与关闭。
- Mainline document: `docs/tw_modular_contracts/TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md`。
- Non-goals confirmed:
  - 不修改默认 qlib/LTR 模型或策略。
  - 不更新 `latest.json` 或 accepted latest。
  - 不触发 provider publish。
  - 不接 broker/order/quick-trade。
  - 不把 raw TradingAgents 输出暴露给 API/Agent/frontend。

## 2. Documents / Contracts / Skills Read

- `TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md`
- `TRADINGAGENTS_READONLY_TA6_CONTROLLED_REAL_RUN_EXECUTION_REPORT_CN.md`
- `coordinator-executor-reviewer-workflow`

## 3. Changes Made

- `scripts/build_tradingagents_readonly_analysis_artifact.py`
  - 修复 `sanitizer_audit`：不再在 manifest 中复述 `target_weight`、`stop_loss`、`Buy/Hold/Overweight` 等 forbidden token。
  - 现在只记录：
    - `removed_term_count`
    - `removed_categories=["external_framework_labels"]`
    - `symbol_count`
  - 增加 `controlled_real_run` 的 metadata-only 展示路径：
    - `sanitized_report.md/json` 不再透传 TradingAgents 原始正文。
    - `research_summary` 仅保留中性运行说明。
    - `bull_points`、`bear_points`、`risk_review_points` 在真实运行展示 artifact 中置空。
    - 原始正文仅保留在 `raw_untrusted` 且 `display_allowed=false` 的审查文件。
  - 清洗 `source_context` 中的 forbidden key/value，避免 `target_weight` 等字段名从上下文旁路进入展示 artifact。
- `backend/app/services/tradingagents_readonly_analysis.py`
  - public GET payload 的 `manifest` 裁掉 `input_artifacts`，避免 LLM backend URL 等运行输入从 API/前端展示面泄漏。
- `backend/tests/test_tradingagents_readonly_analysis_artifact.py`
  - 增加断言：manifest 不得包含 `target_weight`、`stop_loss`。
  - 增加 controlled real run 泄漏回归：
    - raw state 人为包含 `续抱`、`追价`、`现在就买`、`核心部位`、`分批`、`加码`、`60%–70%`、`新增曝险`、`停损`、`权重`。
    - 断言展示 payload 不含上述词，且真实运行模式使用 `external_sections_removed=true`。
- `backend/tests/test_tradingagents_readonly_analysis_api.py`
  - 增加 public manifest 回归：即使 artifact manifest/input index 保留 `backend_url` 供审查复现，GET payload 也不得包含 `input_artifacts`、`backend_url` 或 `chat.pku.edu.cn`。
- 重建 controlled real artifact：
  - `data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke/`

## 4. Evidence Produced

### Controlled Real Run Artifact

已完成一次真实 TradingAgents run：

```text
run_id=ta6_2330_20260601_market_smoke
symbol=2330.TW
trade_date=2026-06-01
selected_analysts=market
llm_base_url=https://chat.pku.edu.cn/v1
```

产物：

```text
data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke/
  manifest.json
  input_artifact_index.json
  sanitized_report.md
  sanitized_report.json
  claim_support_audit.json
  forbidden_semantics_audit.json
  raw_tradingagents_state.json
  raw_complete_report.md
```

### Validator

```bash
python scripts/validate_tradingagents_readonly_analysis_artifact.py \
  data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke --json
```

结果：

```text
ok=true
check_count=55
forbidden_semantics_audit.ok=true
```

人工语义扫描：

```bash
rg -n "续抱|續抱|分批|加码|加碼|核心部位|核心仓位|核心倉位|新增曝|停损|停損|追价|追價|追高|低配|超配|60%|70%|权重|權重|进场|進場|买入|買入|买进|買進|持有|曝险|曝險|交易含义|交易含義|实务交易建议|實務交易建議|交易计划|交易計畫" \
  data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke/sanitized_report.md \
  data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke/sanitized_report.json \
  data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke/manifest.json
```

结果：无输出。

Golden samples:

```text
pass_minimal: ok=true
fail_forbidden_semantics: ok=false
```

### GET-only Loader

```bash
PYTHONPATH=/home/chuliyang/taiwan-stock-quant-platform/backend python -c \
"from app.services.tradingagents_readonly_analysis import load_tradingagents_readonly_analysis; p=load_tradingagents_readonly_analysis(run_id='ta6_2330_20260601_market_smoke'); print(p['ok'], p['status'], p['run_id'], p['validation']['ok'], p['raw_files_included']); print('raw_tradingagents_state.json' in str(p)); print(p['forbidden_semantics_audit']['ok'])"
```

结果：

```text
True pass ta6_2330_20260601_market_smoke True False
False
False False
True
```

### Backend Regression

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  backend/tests/test_tw_stock_agent_daily_prompt_builder.py \
  backend/tests/test_tw_stock_agent_simple_chat.py \
  backend/tests/test_tradingagents_readonly_analysis_api.py \
  backend/tests/test_tradingagents_readonly_adapter.py \
  backend/tests/test_tradingagents_readonly_analysis_artifact.py \
  backend/tests/test_tradingagents_vendor_static.py -q
```

结果：

```text
56 passed, 1 skipped
```

说明：`1 skipped` 是 base Python 环境没有 `stockstats`；TradingAgents conda env hook 已单独验证。

### Frontend Readonly Display Static Check

```bash
node frontend/tests/unit/tw-stock-tradingagents-readonly-panel-check.mjs
```

结果：

```text
tw-stock-tradingagents-readonly-panel-check passed
```

### Vendor Clean Check

```bash
find third_party/tradingagents -name '.git' -o -name '.env' -o -name '__pycache__' -o -name '*.pyc' -o -name 'build' -o -name 'tradingagents.egg-info'
```

结果：无输出。

### Latest / Accepted Pointer Check

```bash
find data_tw/artifacts/analysis/tradingagents_readonly -maxdepth 1 -iname 'latest*' -o -name 'accepted*'
```

结果：无输出。

## 5. Compliance With Mainline

- artifact builder -> validator -> GET-only loader -> Agent optional context/backend tests -> frontend readonly panel static check 已覆盖。
- 所有展示输出来自 `sanitized_report.*`。
- raw files 存在但标记为 raw-untrusted/display disallowed，GET loader 不返回 raw 文件。
- `latest.json` 未创建或更新。
- 没有 provider publish。
- 没有 accepted latest switch。
- 没有 broker/order/quick-trade。
- 没有修改默认模型、默认策略或策略 registry。

## 6. Data Gap Decision

- 2026-06-01 controlled real run 已成功，证明 TradingAgents 已可在本项目内用本地行情 provider 独立运行并产出 validator-pass artifact。
- 2026-06-30 仍存在数据缺口；本地 normalized CSV 不覆盖该日期，Scrapling Yahoo chart 返回 HTTP 403。
- 该缺口不阻塞 TA7 关闭；作为后续独立 Yahoo access repair / runtime-only fallback 数据路线处理。

## 7. Files Changed

```text
scripts/build_tradingagents_readonly_analysis_artifact.py
backend/app/services/tradingagents_readonly_analysis.py
backend/tests/test_tradingagents_readonly_analysis_api.py
backend/tests/test_tradingagents_readonly_analysis_artifact.py
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA7_FINAL_ACCEPTANCE_EXECUTION_REPORT_CN.md
data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260601_market_smoke/*
```

## 8. Recommendation For Reviewer

建议 PASS。

允许将 TradingAgents readonly migration 主线标记为关闭，条件是后续任何 2026-06-30 数据补齐工作必须另开明确授权 route，且不得默认 publish provider/latest。
