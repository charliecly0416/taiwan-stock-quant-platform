# Phase R12-R16 Modular Readonly Productization 全链路工作文档

生成日期：2026-06-16

## 1. 目标

本文件给出从当前 R9-R11 已完成状态，推进到“可随每日数据更新自动生成只读策略结论，并通过 API/前端展示”的完整执行路径。

最终目标：

```text
每日数据更新完成后，自动生成 modular readonly strategy snapshot；
后端 API 只读读取 snapshot；
前端只读展示策略结论；
不触发真实交易、不输出生产目标仓位、不改变 provider accepted latest 治理。
```

本文件不是一次性无审查上线授权。执行者可以按本文连续推进，但必须在每个 phase 输出执行报告，并由审查者逐 phase 审查。任一 gate 失败，必须停止。

## 2. 当前前置状态

已完成并可作为前置：

- R9：`FullRankArtifact` 标准化完成；
- R10：baseline action `window` 清理完成；
- R11：readonly production readiness review 完成；
- modular contract regression 当前通过；
- replay result validator 当前通过；
- unit tests 当前通过。

仍未完成：

- shadow daily runner；
- readonly publish artifact writer；
- readonly API endpoint；
- frontend readonly display；
- daily orchestrator integration；
- production safety E2E；
- failure isolation / rollback switch。

## 3. 总体架构

产品化链路必须解耦为以下模块：

```text
Data Update / Provider
  -> Model Signal / Full Rank Artifact
  -> Strategy Snapshot Builder
  -> Readonly Publish Artifact
  -> Readonly API
  -> Frontend Readonly Display
  -> Analysis / Audit
```

模块职责：

| 模块 | 职责 | 禁止事项 |
| --- | --- | --- |
| Data Update | 现有每日数据抓取、标准化、qlib 数据刷新 | R12-R16 不重写 provider 治理 |
| Model Signal / Full Rank | 产出模型分数、完整 rank、top50 boundary | 不训练、不调参、不混入未来数据 |
| Strategy Snapshot Builder | 根据标准 signal/rank/strategy rule 生成只读候选结论 | 不读券商持仓、不生成订单 |
| Readonly Publish Artifact | 固化可被 API 读取的只读 snapshot | 不切换 provider accepted latest |
| Readonly API | 只读返回 snapshot | 禁止 POST/PUT/PATCH/DELETE 行为 |
| Frontend | 只读展示结论、来源、日期、审计状态 | 禁止交易按钮、快速下单、目标仓位语义 |
| Analysis / Audit | 校验 contract、checksum、安全边界 | 不作为策略收益新证据 |

## 4. 产品化安全边界

全阶段永久禁止：

- broker；
- quick-trade；
- order；
- 真实交易表写入；
- 读取真实券商持仓；
- 输出生产 target position；
- 自动下单；
- monitor scan/config save；
- provider publish；
- provider accepted latest 切换；
- 覆盖现有默认策略；
- 在未审查情况下修改每日生产日更主流程。

允许最终实现：

- 只读 snapshot artifact；
- 只读 API；
- 只读前端展示；
- 每日数据更新完成后的只读 snapshot 自动生成；
- 失败隔离；
- 手动/配置开关启停。

重要命名约束：

```text
readonly strategy snapshot latest
```

可以有自己的只读 latest pointer，但不得命名或实现为：

```text
accepted latest
provider accepted latest
trade target latest
order latest
```

## 4.1 默认算法 / 策略展示合同

本节冻结产品化只读链路中“默认展示哪个算法、哪个策略，以及还展示哪些对照”。执行者不得自行选择收益最高的组合，也不得把 diagnostic / buggy 规则包装成默认策略。

必须区分：

```text
production trading default
readonly product display default
```

R12-R16 只允许设置 `readonly product display default`，不得设置或暗示 `production trading default`。前端/API 可以默认展示某个只读策略快照，但这不是自动交易默认策略，不是目标仓位，不是下单指令，不触发 broker/order/quick-trade。

### 4.1.1 只读主展示组合

只读产品页面的主展示组合冻结为：

```text
display_role: primary_readonly_candidate
model_id: e4_frozen_qlib_2023_2025_ltr
model_label: frozen qlib 2018-2022 + orthogonal LTR 2023-2025
base_model_id: frozen_qlib_2018_2022
ltr_train_window: 2023-01-01..2025-12-31
strategy_rule: top50_exit_one_worst_sell
candidate_boundary: qlib_top50
ranking_source: LTR rerank within qlib top50
sell_policy: only sell when holding exits qlib top50; if multiple exit, sell the worst full_qlib_rank holding only
buy_policy: buy at most one highest-ranked unheld candidate
execution_policy: next trading day / readonly candidate only
```

选择理由：

- 用户已明确希望 E4 作为后续默认候选，并随数据更新生成最新只读策略；
- E4 是当前最强的合法 LTR treatment；
- `top50_exit_one_worst_sell` 对应用户后续确认的产品直觉：不跌出 qlib top50 就不因排名波动卖出，跌出时每天最多卖一支最差持仓，再买入一支最高未持有候选；
- 该组合用于只读展示，不构成自动交易授权。

必须同时展示 caveat：

```text
readonly candidate, not an order, not target position, not investment advice
```

### 4.1.2 主对照组合

只读页面必须同时展示一个主对照：

```text
display_role: primary_baseline
model_id: fresh_qlib_adaptive
model_label: repaired fresh qlib adaptive
strategy_rule: top50_exit_one_worst_sell
candidate_boundary: qlib_top50
ranking_source: qlib score/rank
purpose: compare primary_readonly_candidate against current strong qlib baseline under the same product rule
```

如果 `fresh_qlib_adaptive + top50_exit_one_worst_sell` 的正式 artifact 尚未生成，R13/R16 必须先生成或引用通过 validator 的 artifact；不得用其他规则的 fresh qlib 收益冒充同规则对照。

### 4.1.3 可展示的研究对照

前端可以在“研究对照 / 审计”折叠区展示以下组合，但不得把它们作为主默认：

| display_role | model_id | strategy_rule | 展示目的 |
| --- | --- | --- | --- |
| bridge_fresh_ltr | fresh_qlib_2025_ltr | top50_exit_one_worst_sell | 验证 fresh qlib 底座加 2025 LTR 的桥接效果 |
| bridge_frozen_short_ltr | frozen_qlib_2025_ltr | top50_exit_one_worst_sell | 验证 frozen qlib 底座短 LTR 训练窗口 |
| pure_frozen_baseline | frozen_qlib_2018_2022 | top50_exit_one_worst_sell | 展示 E4 相对同一 frozen qlib 底座的增益 |

### 4.1.4 历史回放规则展示边界

以下规则可以在审计/研究页展示历史回放结果，但不得作为日更主展示策略：

| rule | 允许展示位置 | 限制 |
| --- | --- | --- |
| original | research audit only | 原始快速 top10 rotation，非当前用户确认的产品规则 |
| top50_exit_all | research audit only | 长持规则，对 fresh qlib 结果极强，但不是当前主产品规则 |
| one_sell_one_buy_correct | research audit only | 可作为低换手研究对照，但当前主产品规则冻结为 top50_exit_one_worst_sell |
| one_sell_one_buy_buggy_e8r | hidden by default / anomaly audit only | buggy 规则，绝不能进入默认候选或普通用户展示 |

`one_sell_one_buy_buggy_e8r` 若展示，必须显示：

```text
diagnostic only; implementation bug; not a valid strategy
```

### 4.1.5 API / Snapshot 必须携带 display role

R13 起，`strategy_snapshot.json` 必须包含：

```json
{
  "display_role": "primary_readonly_candidate",
  "is_primary_readonly_candidate": true,
  "is_production_trading_default": false,
  "comparison_group": [
    "primary_baseline",
    "bridge_fresh_ltr",
    "bridge_frozen_short_ltr",
    "pure_frozen_baseline"
  ],
  "hidden_diagnostic_rules": [
    "one_sell_one_buy_buggy_e8r"
  ]
}
```

API 不得让前端动态选择“收益最高组合”作为默认。默认展示必须来自本节冻结配置或后续经审查更新的配置。

### 4.1.6 后续改变默认展示的条件

只有在另开审查文档并通过后，才允许改变：

- `primary_readonly_candidate.model_id`；
- `primary_readonly_candidate.strategy_rule`；
- `primary_baseline.model_id`；
- 前端默认排序；
- 哪些组合进入普通用户可见区域。

执行者不得以 R12-R16 的产品化实现为理由自行调整这些选择。

## 5. Phase R12：Shadow Modular Daily Runner

### 5.1 目标

新增独立 shadow runner，验证当前 modular artifact 链路可在日更形态下生成隔离产物。

建议脚本：

```text
scripts/run_tw_modular_shadow_daily.py
```

输出目录：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/
```

### 5.2 输入

只允许读取：

```text
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
data_tw/artifacts/signals/*/manifest.json
data_tw/artifacts/full_rank/*/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

### 5.3 输出

必须生成：

```text
manifest.json
model_signal_manifest.json
full_rank_manifest.json
strategy_dependency_snapshot.yaml
replay_result_manifest.json
validation_report.json
forbidden_scope_audit.json
checksum_manifest.json
shadow_summary.json
```

### 5.4 Gate

必须满足：

```text
all_validators_pass == true
forbidden_scope_audit.status == pass
artifact_output_under_shadow_dir_only == true
no_frontend_change == true
no_api_change == true
no_daily_orchestrator_change == true
no_provider_publish == true
no_accepted_latest_switch == true
no_broker_order == true
```

### 5.5 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
```

## 6. Phase R13：Readonly Publish Artifact Contract / Writer / Validator

### 6.1 目标

在 R12 shadow 通过后，新增只读 publish artifact。该 artifact 是 API/前端唯一允许读取的生产候选输入。

建议 writer：

```text
scripts/publish_tw_modular_readonly_snapshot.py
```

建议 validator：

```text
scripts/validate_tw_modular_readonly_snapshot.py
```

输出目录：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/
```

只读 latest pointer：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

`latest.json` 只允许指向 readonly snapshot，不得修改 provider accepted latest。

### 6.2 Snapshot Schema

`manifest.json` 必须包含：

```json
{
  "artifact_type": "readonly_strategy_snapshot",
  "schema_version": "readonly_strategy_snapshot_r13_v1",
  "asof": "YYYY-MM-DD",
  "created_at": "ISO-8601",
  "created_by": "scripts/publish_tw_modular_readonly_snapshot.py",
  "readonly_only": true,
  "production_trade_enabled": false,
  "display_role": "primary_readonly_candidate",
  "is_primary_readonly_candidate": true,
  "is_production_trading_default": false,
  "source_shadow_manifest": "data_tw/artifacts/shadow_modular_daily/{asof}/manifest.json",
  "source_signal_manifest": "...",
  "source_full_rank_manifest": "...",
  "source_strategy_dependency": "...",
  "snapshot": "strategy_snapshot.json",
  "validation_report": "validation_report.json",
  "forbidden_scope_audit": "forbidden_scope_audit.json",
  "checksum_manifest": "checksum_manifest.json",
  "quality_status": "pass"
}
```

`strategy_snapshot.json` 必须包含：

```json
{
  "asof": "YYYY-MM-DD",
  "model_id": "e4_frozen_qlib_2023_2025_ltr",
  "base_model_id": "frozen_qlib_2018_2022",
  "strategy_rule": "top50_exit_one_worst_sell",
  "candidate_boundary": "qlib_top50",
  "ranking_source": "ltr_rerank_within_qlib_top50",
  "display_role": "primary_readonly_candidate",
  "is_primary_readonly_candidate": true,
  "is_production_trading_default": false,
  "top_candidates": [],
  "exit_candidates": [],
  "hold_candidates": [],
  "explanations": [],
  "data_asof": "YYYY-MM-DD",
  "signal_asof": "YYYY-MM-DD",
  "available_at_policy": "current_or_pit_delayed",
  "readonly_only": true,
  "not_order": true,
  "not_target_position": true,
  "not_investment_advice": true
}
```

字段语义：

- `top_candidates`：只读候选排名，不是买入指令；
- `exit_candidates`：只读风险/跌出候选，不是卖出指令；
- `hold_candidates`：只读延续候选，不代表真实持仓；
- `candidate_boundary`：必须来自 qlib top50；
- `ranking_source`：LTR 只允许在 qlib top50 内重排；
- `available_at_policy`：必须继承已审查 PIT/available_at 合同。

### 6.3 R13 禁止事项

R13 不得：

- 改 API；
- 改前端；
- 改每日日更；
- 改默认策略；
- provider publish；
- accepted latest 切换；
- monitor/broker/order；
- 读取真实持仓；
- 输出 target position。

### 6.4 Gate

必须满足：

```text
readonly_snapshot_validator_ok == true
checksum_ok == true
latest_pointer_points_to_readonly_snapshot_only == true
forbidden_scope_audit.status == pass
```

### 6.5 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_EXECUTION_REPORT_CN.md
```

## 7. Phase R14：Readonly API 接入

### 7.1 目标

新增后端只读 API，从 R13 readonly publish artifact 读取 snapshot，并返回给前端。

API 只能读：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/strategy_snapshot.json
```

### 7.2 API Contract

建议 endpoint：

```text
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-strategy-snapshot/{asof}
```

返回必须包含：

```json
{
  "ok": true,
  "readonly_only": true,
  "asof": "YYYY-MM-DD",
  "quality_status": "pass",
  "snapshot": {},
  "source_manifest": "...",
  "warnings": []
}
```

### 7.3 API 禁止事项

API 不得：

- 提供 POST/PUT/PATCH/DELETE；
- 写任何 snapshot；
- 触发 runner；
- 触发 provider refresh/publish；
- 切换 accepted latest；
- 触发 monitor；
- 触发 broker/order；
- 返回 target position；
- 返回“买入/卖出指令”语义。

### 7.4 API 测试

必须新增或更新只读测试：

- latest snapshot 读取成功；
- 指定 asof snapshot 读取成功；
- snapshot 缺失时返回安全错误；
- forbidden keyword/static scan；
- 不存在写入型 route；
- 不触发 provider/monitor/broker/order mock。

### 7.5 Gate

必须满足：

```text
api_readonly_tests_pass == true
api_static_safety_scan_pass == true
no_write_endpoint == true
no_provider_monitor_broker_order_call == true
```

### 7.6 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_EXECUTION_REPORT_CN.md
```

## 8. Phase R15：Frontend Readonly Display

### 8.1 目标

在台湾股票页面新增只读展示区域，读取 R14 API，展示：

- snapshot 日期；
- 模型与策略规则；
- top candidates；
- exit candidates；
- 数据来源 manifest；
- quality status；
- readonly safety labels。

### 8.2 前端文案边界

允许文案：

```text
只读候选
研究排名
调入候选
调出观察
策略快照
数据日期
模型来源
审计状态
```

禁止文案：

```text
下单
买入指令
卖出指令
目标仓位
自动交易
一键交易
券商同步
保证收益
胜率承诺
```

### 8.3 前端行为边界

前端不得：

- 添加交易按钮；
- 添加 quick-trade；
- 添加 broker 操作；
- 保存 monitor config；
- 触发 scan；
- 调 provider refresh/publish；
- 修改 accepted latest；
- 写 snapshot。

### 8.4 E2E

必须执行只读 E2E：

- 页面可加载；
- snapshot 正常展示；
- 缺失 snapshot 时安全降级；
- network audit 无 POST/PUT/PATCH/DELETE 到交易/monitor/provider；
- console 无错误；
- UI 不出现禁止文案；
- 移动端/桌面端不重叠。

### 8.5 Gate

必须满足：

```text
frontend_readonly_e2e_pass == true
network_no_forbidden_write == true
console_no_error == true
forbidden_text_scan_pass == true
```

### 8.6 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_FRONTEND_READONLY_DISPLAY_EXECUTION_REPORT_CN.md
```

## 9. Phase R16：Daily Auto Update Integration

### 9.1 目标

在每日数据更新成功后，自动触发 readonly modular snapshot 生成与 publish，使前端/API 可看到最新只读策略结论。

R16 是第一个允许接触真实日更 orchestrator 的阶段，但只能作为失败隔离的只读后置步骤。

### 9.2 集成原则

只允许在现有每日更新完成后追加：

```text
daily data update success
  -> qlib/current signal data ready
  -> run modular readonly shadow
  -> validate shadow
  -> publish readonly snapshot
  -> validate publish artifact
  -> update readonly snapshot latest pointer
```

不得改变：

- 数据抓取 provider 顺序；
- provider accepted latest 治理；
- qlib 默认策略生产路径；
- monitor/broker/order；
- 前端/API 写入权限。

### 9.3 Feature Flag

必须新增显式开关，默认关闭：

```text
ENABLE_TW_MODULAR_READONLY_DAILY=false
```

只有打开时才运行 R16 后置步骤。关闭时现有日更行为必须完全不变。

建议附加开关：

```text
TW_MODULAR_READONLY_DAILY_FAIL_OPEN=true
```

含义：readonly snapshot 失败时不阻塞原每日数据更新。

### 9.4 Failure Isolation

R16 必须满足：

- readonly snapshot 失败不影响数据更新成功状态；
- 失败写入独立 audit；
- 不回滚 provider 数据；
- 不切换 accepted latest；
- 不触发交易链路；
- 前端保留上一版已通过 validator 的 readonly snapshot，并显示 stale warning。

### 9.5 Daily Run Audit

每日运行必须写：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/daily_run_audit/{run_id}.json
```

必须包含：

- daily update run id；
- data asof；
- signal asof；
- shadow manifest；
- publish manifest；
- validation status；
- failure reason；
- feature flag 状态；
- forbidden scope audit；
- 是否更新 readonly latest pointer。

### 9.6 R16 禁止事项

R16 仍不得：

- provider publish；
- provider accepted latest 切换；
- broker/order；
- quick-trade；
- 读取真实持仓；
- 输出 target position；
- 自动调整 monitor；
- 把 readonly snapshot 当成交易指令。

### 9.7 Gate

必须满足：

```text
feature_flag_default_off == true
daily_update_behavior_unchanged_when_off == true
readonly_snapshot_generated_when_on == true
failure_does_not_block_daily_update == true
readonly_latest_pointer_only == true
no_provider_accepted_latest_change == true
no_monitor_broker_order == true
```

### 9.8 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_EXECUTION_REPORT_CN.md
```

## 10. Phase R17：Final Productization Acceptance

### 10.1 目标

完成最终验收，判断是否可以认为“只读产品化链路已完成”。

### 10.2 必审材料

必须审查：

```text
PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
PHASER13_READONLY_PUBLISH_ARTIFACT_EXECUTION_REPORT_CN.md
PHASER14_READONLY_API_EXECUTION_REPORT_CN.md
PHASER15_FRONTEND_READONLY_DISPLAY_EXECUTION_REPORT_CN.md
PHASER16_DAILY_READONLY_INTEGRATION_EXECUTION_REPORT_CN.md
```

### 10.3 最终验收命令

至少执行：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
python -m pytest
```

若有前端：

```bash
corepack pnpm build
npx playwright test
```

实际命令以项目现有测试体系为准，执行者必须报告不能运行的原因。

### 10.4 最终通过标准

只有全部满足，才可收尾：

```text
shadow runner pass
publish artifact validator pass
API readonly tests pass
frontend readonly E2E pass
daily integration fail-open pass
feature flag default off pass
readonly latest pointer pass
no provider accepted latest change
no monitor/broker/order
no target position output
no forbidden frontend wording
```

### 10.5 R17 结论模板

允许结论：

```text
Modular readonly strategy snapshot production chain is accepted.
It updates readonly research snapshots after daily data update when enabled.
It does not perform trading, target-position generation, broker action, monitor action, provider publish, or accepted-latest switching.
```

不允许结论：

```text
自动交易已上线
默认策略已切换
真实仓位会自动调整
provider accepted latest 已由本链路管理
策略收益已由产品化阶段重新证明
```

## 11. 执行顺序

推荐顺序：

```text
R12 shadow runner
  -> 审查
R13 readonly publish artifact
  -> 审查
R14 readonly API
  -> 审查
R15 frontend readonly display
  -> 审查
R16 daily integration
  -> 审查
R17 final acceptance
```

如果执行者希望合并 R13-R15，也必须分别输出三个执行报告，审查者分别审查。

R16 不允许和 R12-R15 合并执行。

## 12. 执行者总 Prompt

请按：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

从 R12 开始执行 modular readonly productization。你可以按阶段连续推进，但每个阶段必须单独输出执行报告，并满足对应 gate 后才进入下一阶段。

本链路最终目标是：每日数据更新成功后，自动生成只读策略 snapshot，API 只读读取，前端只读展示。全程禁止 broker、quick-trade、order、真实持仓读取、target position、monitor 写入、provider publish、provider accepted latest 切换。R16 之前不得修改真实日更脚本；R16 修改也必须受 feature flag 控制，默认关闭，失败不阻塞原日更。

每份执行报告必须列出：

- 修改文件；
- 新增 artifact；
- 输入输出；
- 命令与结果；
- validator；
- forbidden scope audit；
- 是否触碰前端/API/日更；
- 是否触碰 provider/accepted latest/monitor/broker/order；
- 是否满足本 phase gate；
- 下一阶段是否建议放行。

## 13. 审查者总 Prompt

请按：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

逐阶段审查执行者报告。重点确认：

- 是否严格按阶段推进；
- 是否每个 phase 都有独立执行报告；
- R12 是否只做 shadow；
- R13 是否只做 readonly publish artifact；
- R14 是否 API 只读；
- R15 是否前端只读；
- R16 是否 feature flag 默认关闭、失败隔离、不阻塞原日更；
- 是否没有 provider publish / provider accepted latest 切换；
- 是否没有 monitor/broker/quick-trade/order；
- 是否没有 target position 或真实交易语义；
- 是否没有用产品化阶段重新包装收益结论；
- validator、E2E、forbidden scope audit 是否真实通过。

任何阶段发现越界写入、交易链路触发、accepted latest 混淆、API 写接口、前端交易语义或 daily integration 默认开启，必须停止并要求修复，不得放行。
