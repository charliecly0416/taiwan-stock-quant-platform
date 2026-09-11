# 台股模块化项目文档入口与归档政策

本文是新统筹、新执行者和新审查者进入当前项目的入口文档。最高层开发原则见：

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`

## 1. 当前应该先读什么

按以下顺序阅读即可建立当前项目认知：

1. `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
2. `docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md`
3. `docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md`
4. `docs/tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md`
5. `docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md`
6. `docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md`
7. `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md`
8. `docs/tw_modular_daily_update_productization/PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_FINAL_SUMMARY_CN.md`

这些文档覆盖最高层开发原则、当前模块边界、模型与策略选择、日更链路、前端/API 串联、模拟账户和验收方式。

## 2. 当前项目结构原则

当前台股链路应保持模块化：

- 数据源与日更模块只产生标准化数据和 readiness/manifest。
- 特征模块只产生 PIT-safe feature artifact。
- 模型模块只读取标准输入并输出 ModelSignal。
- 策略模块只读取模型/排名/持仓状态并输出 OrderIntent。
- 回放模块只读取 OrderIntent/价格/费用配置并输出 ReplayResult。
- readonly artifact/API/前端只展示标准产物，不回读实验私有文件。
- 自动化脚本负责串联模块，不把模型、策略、回放逻辑写成一个大脚本。

## 3. 当前核心模型与默认策略

当前前端和产品化链路只保留两个重要模型：

- `e4_frozen_qlib_2018_2022`：冻结 qlib 底座。
- `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`：冻结 qlib + 正交 LTR，当前默认候选。

默认策略规则保持 `top50_exit_one_worst_sell`，但真实页面应通过模型/策略选择、只读 snapshot 和 replay window 展示，不允许把策略写死到前端或模型内部。

## 4. 历史文档怎么处理

历史阶段文档已经压缩归档到：

- `docs/archive/phase_history/README_CN.md`

归档范围包括：

- 阶段执行报告。
- 阶段审查交接。
- 修复过程工作文档。
- 执行者/审查者提示词。

归档不是删除证据。需要追溯某条路线时，从归档索引按原目录查找。日常开发和审查不应从历史阶段报告入手，应优先读当前合同、指南、runbook、最终总结和 checklist。

## 5. 新开发必须遵守的最低门槛

新增数据、模型、策略、回放或前端功能前，至少确认：

- 是否有明确输入/输出 artifact 合同。
- 是否有 PIT/available_at/训练窗口/回放窗口边界。
- 是否不会触发 provider publish、accepted latest switch、monitor 写入、broker/order/quick-trade。
- 是否有 validator 或 golden sample。
- 是否有前端只读展示和 API 字段说明。
- 是否能通过当前回归测试。

## 6. 推荐只读验证命令

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_ltr_readonly_explanation_api.py -q

cd frontend
corepack pnpm build
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
node tests/unit/tw-stock-readonly-replay-window-check.mjs
```

完整页面 E2E 会打开趋势/K 线等现有只读数据接口，可能触发行情 GET。它不应产生写入、下单或 accepted latest 切换。
