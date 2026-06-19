# Phase X1 Paper Decision and Accounting Engine 执行报告

生成日期：2026-06-18

## 1. 执行范围

用户要求按：

```text
docs/tw_modular_daily_update_productization/PHASEX0_REVIEW_AND_PHASEX1_WORK_CN.md
```

执行下一步。但该文件当前不存在。已用 `find docs/tw_modular_daily_update_productization -maxdepth 1 -type f -name '*PHASEX*'` 确认目录中只有：

```text
PHASEX0_PAPER_ACCOUNT_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
PHASEX0_PAPER_PORTFOLIO_CONTRACT_AND_BOUNDARY_AUDIT_EXECUTION_REPORT_CN.md
PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_WORK_CN.md
PHASEX_REVIEW_AND_REVISION_SUGGESTION_CN.md
```

因此本轮按 X0 报告中已放行的 X1 最小闭环执行：

```text
读取当前 paper/sim holdings
读取 readonly model signal
读取 top50_exit_one_worst_sell strategy rule
生成 PaperPortfolioStateArtifact
生成 PaperOrderIntentArtifact
生成 PaperApplyPreviewArtifact
生成 forbidden_action_audit
```

本轮仍是 readonly：

```text
不写 qd_tw_sim_accounts
不写 qd_tw_sim_positions
不写 qd_tw_sim_orders
不写 qd_tw_sim_trades
不 reset
不 apply
不调用 quick-trade
不连接 broker
不触发 real orders
不触发 provider publish
不切 provider accepted latest / qlib accepted latest
不写 monitor config / scan / alerts
不训练 / 调参 / 替换模型
不修改 Agent tool/action
```

## 2. 本轮新增文件

```text
scripts/build_tw_paper_portfolio_decision_artifact.py
backend/tests/test_build_tw_paper_portfolio_decision_artifact.py
tests/fixtures/tw_paper_portfolio_x1_account.json
docs/tw_modular_daily_update_productization/PHASEX1_PAPER_DECISION_AND_ACCOUNTING_ENGINE_EXECUTION_REPORT_CN.md
```

## 3. X1 builder

新增脚本：

```text
scripts/build_tw_paper_portfolio_decision_artifact.py
```

能力：

```text
1. 默认从 data_tw/artifacts/daily_readonly_latest/latest.json 解析 readonly snapshot。
2. 从 snapshot 读取 source_model_signal_artifact。
3. 读取 configs/strategy_dependencies/top50_exit_one_worst_sell.yaml。
4. 支持从 qd_tw_sim_accounts / qd_tw_sim_positions / qd_tw_stock_daily_bars 只读读取模拟账户。
5. 支持 --paper-account-json fixture 输入，便于离线测试。
6. 输出 PaperPortfolioStateArtifact。
7. 输出 PaperOrderIntentArtifact。
8. 输出 PaperApplyPreviewArtifact。
9. 输出 forbidden_action_audit。
```

DB 模式只执行 `SELECT`，不调用 `TWStockSimAccountService.ensure_schema()`，避免 DDL 或账户写入。

输出目录：

```text
data_tw/artifacts/paper_portfolio/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/<run_id>/
```

## 4. Artifact 合同

本轮输出文件：

```text
manifest.json
paper_portfolio_state.json
paper_order_intent.json
paper_apply_preview.json
forbidden_action_audit.json
schema.json
```

`manifest.json` 固定：

```text
artifact_type = PaperDecisionBundleArtifact
schema_version = phase_x.paper_decision_bundle.v1
readonly_only = true
not_applied = true
not_real_order = true
not_target_position = true
not_investment_advice = true
no_broker_order = true
no_quick_trade = true
```

`paper_portfolio_state.json` 固定：

```text
artifact_type = PaperPortfolioStateArtifact
schema_version = phase_x.paper_portfolio_state.v1
paper_account_id
user_id
paper_account_epoch
cash
positions
market_value
total_equity
checksum
```

`paper_order_intent.json` 固定：

```text
artifact_type = PaperOrderIntentArtifact
schema_version = phase_x.paper_order_intent.v1
decision_id
input_checksum
paper_buy_intent / paper_sell_intent / paper_skip
readonly_decision_only = true
not_real_order = true
```

`paper_apply_preview.json` 固定：

```text
artifact_type = PaperApplyPreviewArtifact
schema_version = phase_x.paper_apply_preview.v1
readonly_preview_only = true
not_applied = true
```

## 5. 策略逻辑

本轮实现 `top50_exit_one_worst_sell` 的 X1 readonly 决策：

```text
candidate_set = candidate_rank <= 50
sell = 当前模拟持仓中不在 candidate_set 的标的，按 full_qlib_rank 最差优先，最多 1 个
buy = 卖出后若有空位，从 buy_score 降序候选中选未持有标的，最多 1 个
hold/skip = 当前仍保留的模拟持仓输出 paper_skip
```

数量口径：

```text
sell quantity = 当前模拟持仓 quantity
buy quantity = lot_size，默认沿用当前 sim account 服务的 10
```

会计预览口径：

```text
fee_rate = 0.001425
sell_tax_rate = 0.003
buy cash_effect_preview = -(quantity * price + fee)
sell cash_effect_preview = quantity * price - fee - tax
missing price -> applicability = unavailable
cash insufficient -> applicability = unavailable
```

本轮只做 preview，不写成交。

## 6. 本轮产物

### 6.1 committed latest fixture run

命令：

```text
python scripts/build_tw_paper_portfolio_decision_artifact.py \
  --paper-account-json tests/fixtures/tw_paper_portfolio_x1_account.json \
  --run-id x1_readonly_fixture_20260618 \
  --json
```

产物：

```text
data_tw/artifacts/paper_portfolio/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/x1_readonly_fixture_20260618/manifest.json
```

结果：

```text
decision_id = paper_decision_f17c454067c085c0
asof = 2026-06-10
paper_sell_intent = 1
paper_buy_intent = 0
paper_skip = 0
```

说明：当前 committed readonly latest 的 signal artifact `v2_real_provider_daily_manual_trigger_success_20260617T193422Z_u3_success_signal/signals.csv` 只有 header，没有 signal rows。因此该 run 正确产生 sell-only readonly decision。

### 6.2 buy/sell coverage fixture run

命令：

```text
python scripts/build_tw_paper_portfolio_decision_artifact.py \
  --paper-account-json tests/fixtures/tw_paper_portfolio_x1_account.json \
  --model-signal data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u3_readonly_daily_demo_success_signal/manifest.json \
  --signal-asof 2026-03-27 \
  --run-id x1_readonly_fixture_buy_sell_20260618 \
  --json
```

产物：

```text
data_tw/artifacts/paper_portfolio/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/x1_readonly_fixture_buy_sell_20260618/manifest.json
```

结果：

```text
decision_id = paper_decision_626e11a8ca27d37e
asof = 2026-03-27
paper_sell_intent = 1
paper_buy_intent = 1
paper_skip = 0
```

该 run 中：

```text
paper_sell_intent: TW9999，applicability=applicable
paper_buy_intent: TW6683，applicability=unavailable，reason=missing_reference_price
```

说明：fixture 中没有 `TW6683` 的参考价，因此 X1 正确输出 unavailable 原因，不写任何账户。后续真实 DB 模式会从 `qd_tw_stock_daily_bars` 只读补价格。

## 7. forbidden_action_audit

本轮产物的 forbidden audit 为 pass，所有动作均为 false：

```text
sim_account_write = false
paper_order_write = false
paper_execution_write = false
reset = false
broker_order = false
quick_trade = false
real_order = false
provider_publish = false
provider_accepted_latest_switch = false
qlib_accepted_latest_switch = false
monitor_write = false
monitor_scan = false
agent_tool_action_expansion = false
training = false
tuning = false
```

## 8. 验证

已执行：

```text
python -m py_compile scripts/build_tw_paper_portfolio_decision_artifact.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py -q
```

结果：

```text
2 passed
```

第一次直接运行 artifact builder 时 sandbox 出现：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

按环境规则用批准的 escalated 本地命令重跑成功。该命令只写 `data_tw/artifacts/paper_portfolio/**`，没有网络访问和账户写入。

## 9. 是否可以进入 X2

不建议直接进入 X2。

X1 已完成 readonly builder、artifact、preview 和单元测试；但 X2 是写路径，仍需先补：

```text
paper_account_epoch 实现
apply idempotency 存储
reset archive 存储
PaperAuditLogArtifact 存储
same-day apply guard
realized_paper_pnl 口径
真实 DB 模式下的只读 account fixture / smoke
X2 API network denylist 验证
```

建议下一步先做 X1R review，确认 artifact schema、策略口径和 price unavailable 处理是否可接受；审查通过后再进入 X2 apply/reset API。
