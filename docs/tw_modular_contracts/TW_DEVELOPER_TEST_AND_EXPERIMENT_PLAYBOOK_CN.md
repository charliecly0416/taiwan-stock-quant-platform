# 台股量化平台开发、测试与实验手册

生成日期：2026-06-18

## 1. 先判断你要做什么

开发前必须先分类：

| 任务类型 | 应进入的模块 | 第一文件 |
| --- | --- | --- |
| 新数据源 | DataSource / DataIngestion | 数据合同 + registry |
| 新特征 | FeatureArtifact | feature schema + PIT audit |
| 新模型 | Model / ModelAdapter | ModelSignalArtifact |
| 新策略 | StrategyRule | strategy dependency YAML |
| 新回放口径 | ReplayExecution | ReplayResultArtifact |
| 新前端展示 | FrontendReadonlyDisplay | GET-only API payload |
| 新日更能力 | DailyOrchestrator | RunRegistry + validators |
| 新模拟账户行为 | PaperPortfolio | simulation-only artifact |
| 新 Agent 能力 | AgentReadonlyContext | 另开 Agent 专项 |

不能先写脚本跑结果，再倒推合同。必须先确定模块和接口。

## 2. 当前产品默认值从哪里来

当前产品默认模型、默认策略和核心路径来自：

```text
configs/tw_product_artifact_registry.yaml
```

不要在新代码里硬编码以下内容：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
e4_frozen_qlib_2023_2025_ltr
top50_exit_one_worst_sell
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals
```

如果确实需要默认值，读取 registry 或通过已有服务取得。

## 3. 新模型开发流程

### 3.1 允许做的事

```text
训练或加载新模型
生成 raw score
写 ModelAdapter
输出 ModelSignalArtifact
跑 signal validator
跑只读 replay
写审查报告
```

### 3.2 禁止直接做的事

```text
直接让策略读取模型私有 CSV
直接改默认模型
直接改前端展示为默认策略
用训练集收益证明策略优劣
绕过 available_at / PIT 检查
触发 provider publish / accepted latest / broker / order
```

### 3.3 最小产物

```text
model training manifest
raw score artifact
ModelSignalArtifact manifest/signals/schema/audits
validator result
OOS replay result if requested
review document
```

### 3.4 新模型测试

至少跑：

```bash
python -m py_compile <new_model_scripts>
python scripts/validate_tw_modular_artifact_contract.py --artifact <model_signal_manifest>
PYTHONPATH=backend python -m pytest backend/tests/test_phase_yz0_clean_registry.py -q
```

如需进入产品候选，还要补 registry 测试。

## 4. 新策略开发流程

### 4.1 先写 dependency YAML

路径：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
```

必须声明：

```text
required_core_fields
required_capabilities
required_extensions
ranking_usage
max_buy_count
max_sell_count
forbidden_fields
forbidden_actions
diagnostic_only / not_valid_strategy_evidence if needed
```

### 4.2 策略输出

策略只能输出：

```text
OrderIntentArtifact
```

不能输出真实订单、目标仓位、broker id、成交价或未来价格。

### 4.3 策略测试

至少跑：

```bash
python scripts/validate_tw_modular_artifact_contract.py --registry configs/tw_modular_registry.yaml
python scripts/validate_tw_modular_order_intent_artifact.py --artifact <order_intent_manifest>
python scripts/validate_tw_modular_order_intent_replay.py --artifact <replay_manifest>
```

## 5. 新数据/特征开发流程

### 5.1 数据源

必须记录：

```text
provider
raw_path
normalized_path
symbol mapping
asof_date
available_at
coverage audit
schema audit
```

### 5.2 特征

必须记录：

```text
feature_date
instrument
source_data_artifact
lookback_window
signal_asof
available_at
pit_policy
forbidden_future_field_audit
```

### 5.3 数据/特征测试

```bash
python scripts/validate_tw_provider_staging_data.py --staging-dir <staging_dir> --json
python scripts/validate_tw_data_readiness_gate.py --staging-dir <staging_dir> --json
```

如果特征进入模型，还要验证 feature schema 和 PIT audit。

## 6. 回放与实验流程

### 6.1 实验前必须冻结

```text
训练窗口
测试窗口
模型版本
特征版本
策略规则
执行价口径
交易成本
可交易 universe
```

### 6.2 回放不允许

```text
在训练集窗口上证明策略优劣
根据回放收益改信号
根据回放收益选择默认策略
混用 close/open 执行价但不标注
缺价格时静默成交
```

### 6.3 推荐输出

```text
ReplayResultArtifact
summary metrics
daily nav
actions
position snapshots
coverage audit
execution price audit
turnover/drawdown audit
```

## 7. 前端开发流程

前端只能读 API，不能直接读本地 CSV 或实验目录。

当前优先 API：

```text
GET /api/tw-stock/current-strategy-context
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-replay-window
GET /api/tw-stock/readonly-replay-window-index
```

前端展示原则：

```text
简单
准确
清晰
实用
不暴露研究噪音
不展示 deprecated/research-only 为默认选项
不承诺收益/胜率/买卖建议
```

前端测试：

```bash
cd frontend
corepack pnpm build
```

涉及页面变更时，还要补对应 unit/e2e 检查。

## 8. 日更开发流程

当前自动脚本：

```text
scripts/run_daily_tw_stock_auto_update.py
```

定位是 orchestrator，不是业务逻辑堆叠脚本。

新增日更模块时，应按顺序设计：

```text
Data readiness
Feature refresh
Model signal build
Strategy decision build
Readonly snapshot publish
Validators
Latest pointer update
Run registry
```

失败规则：

```text
任何 validator 失败 -> 不更新 latest
没有新数据 -> noop
部分数据缺失 -> blocked 或 pending，不做假成功
previous latest preserved
```

## 9. 模拟账户开发流程

模拟账户允许写 simulation-only 状态，不允许触发真实交易。

必须确认：

```text
paper_account_id
paper_account_epoch
portfolio_state_checksum
input_checksum
readonly_decision_only
not_real_order
not_target_position
not_investment_advice
```

测试：

```bash
PYTHONPATH=backend python -m pytest   backend/tests/test_build_tw_paper_portfolio_decision_artifact.py   backend/tests/test_tw_stock_paper_portfolio_x2.py   backend/tests/test_tw_stock_paper_portfolio_x2r_api.py -q
```

## 10. 常见错误

| 错误 | 后果 |
| --- | --- |
| 新脚本硬编码旧模型 ID | 前端/API 可能重新暴露淘汰模型 |
| 策略直接读模型 CSV | 模型和策略重新耦合 |
| replay 内写策略逻辑 | 新策略必须改 replay engine，工程不可扩展 |
| 前端直接读 artifact 文件 | 部署后路径不可控，安全边界失效 |
| 用训练集收益做结论 | 策略优劣证据无效 |
| 改日更脚本顺手打开 provider publish | 可能切换 accepted latest，风险高 |
| 把 diagnostic-only 策略放到产品选项 | 用户会误解异常策略为可用策略 |

## 11. 开发完成前的最低 checklist

```text
[ ] 是否明确模块类型？
[ ] 是否引用对应合同？
[ ] 是否更新 registry 或说明不需要？
[ ] 是否没有新增硬编码默认模型/策略？
[ ] 是否有 manifest？
[ ] 是否有 validator 结果？
[ ] 是否有 PIT / available_at 检查？
[ ] 是否没有 provider publish / accepted latest / broker / order？
[ ] 是否没有把 research-only 暴露给前端默认选项？
[ ] 是否跑过最小 pytest / build？
```
