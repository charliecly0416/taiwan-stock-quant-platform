# Phase R1 Repair 工作文档：修复只读集成回归阻塞项

生成日期：2026-06-20

## 1. 工作结论

Phase R1 审查结论为不通过，需要 repair。

本次 repair 只允许修复 R1 暴露出的三个缺口：

```text
frontend simple-chat static check 推荐问题断言漂移
M2 registry/template 缺少 EXECUTION_REPORT_TEMPLATE_CN.md
M4 frontend readonly primary field 缺少 合法窗口 / 手续费/税费 / 审计状态
```

本次 repair 不是新模型或新策略研发。

## 2. 严禁事项

不得执行或触发：

```text
训练新模型
新增策略规则
修改默认模型或默认策略
修改前端默认展示为新模型/新策略
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
```

不得为了通过测试而删除安全断言、放宽 forbidden request 检查、隐藏失败项或伪造 artifact。

## 3. Repair 1：simple-chat 静态检查推荐问题断言

目标文件：

```text
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

当前失败：

```text
测试要求 “明天关注哪些股票？”，但页面当前推荐问题不包含该文案。
```

修复要求：

- 不建议恢复 “明天关注哪些股票？”，该文案更容易被理解为预测或行动暗示。
- 将静态检查改为匹配当前安全的研究型推荐问题。
- 至少覆盖以下当前页面问题：

```text
今天策略是什么？
排名第一是谁？
今天有哪些候选调入？
今天有哪些调出复核？
2330 当前状态如何？
为什么模拟账户不能应用？
数据新鲜度如何？
```

必须保留负向断言：

```text
OPENAI_API_KEY
api.openai.com
chat/completions
@openai
quick-trade
broker
target_position
target_weight
provider publish
accepted latest
monitor scan
monitor alerts
下单
仓位
收益保证
自动交易
目标仓位
```

## 4. Repair 2：补齐 M2 通用执行报告模板

新增文件：

```text
docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
```

模板必须包含以下 marker：

```text
contract_doc
schema_version
input_artifacts
output_artifacts
validator_command
golden_sample_path
allowed_consumers
forbidden_consumers
readonly_boundary
forbidden_actions_audit
production_allowed: false
```

建议同时包含：

```text
diagnostic_only
rollback_or_failure_policy
not_default_model_or_strategy
no_provider_publish
no_accepted_latest_switch
no_monitor_write
no_broker_or_order
```

修复原则：

- 不修改 `scripts/validate_tw_modular_registry_m2.py` 来绕过模板要求。
- 模板用于未来执行报告，不得授权生产默认切换。
- 模板必须强调 validator、golden sample、只读边界和 forbidden actions audit。

## 5. Repair 3：补齐 M4 frontend readonly primary fields

目标文件优先为：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
```

当前缺失：

```text
合法窗口
手续费/税费
审计状态
```

修复要求：

- 在 primary UI 区域明确出现 “合法窗口”。
- 将 “费用/税费” 对齐为 “手续费/税费”，或同时保留等价说明但必须出现 validator 要求文本。
- 在 primary UI 区域明确出现 “审计状态”，值可来自 checksum/validation/status 等只读审计结果。
- 技术详情仍默认折叠。
- 不新增任何写 API、交易入口、仓位建议、provider/latest 操作或 OpenAI 前端调用。

如果执行者认为 validator 文案应兼容现有 UI，也必须先证明当前 UI 已经以用户可见 primary field 方式表达同等信息；否则优先改 UI 文案/字段，不放宽 validator。

## 6. 必须重跑的命令

Repair 后必须重跑：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
python scripts/validate_tw_modular_registry_m2.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/run_tw_modular_contract_regression.py --json
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

如改动 frontend 组件，建议同时重跑：

```bash
cd frontend && corepack pnpm build
```

如果普通沙箱出现：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

可按权限规则提升权限重跑本地只读检查，但不得借此执行网络下载、真实数据拉取、provider/latest/monitor/broker/order/OpenAI。

## 7. 执行报告输出

请输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_EXECUTION_REPORT_CN.md
```

报告结构：

```markdown
# Phase R1 Repair 执行报告

## 1. 结论
## 2. 修改文件
## 3. simple-chat static check 修复
## 4. M2 EXECUTION_REPORT_TEMPLATE 修复
## 5. M4 readonly primary fields 修复
## 6. 重跑命令结果
## 7. Forbidden actions audit
## 8. 是否建议重新审查 R1
```

## 8. Repair 通过标准

Repair 通过必须满足：

```text
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs 通过
python scripts/validate_tw_modular_registry_m2.py --json 通过
python scripts/validate_tw_frontend_readonly_m4.py --json 通过
python scripts/run_tw_modular_contract_regression.py --json 通过
UI2 readonly Playwright / fixture 仍通过
未触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI key
```

Repair 通过后，审查者再决定是否允许进入 R2。
