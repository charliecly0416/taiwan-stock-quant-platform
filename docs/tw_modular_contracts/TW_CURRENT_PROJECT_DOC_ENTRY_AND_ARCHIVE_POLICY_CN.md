# 台股模块化项目文档入口与归档政策

本文是新统筹、新执行者和新审查者进入当前项目的入口文档。最高层开发原则见：

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`

## 1. 当前应该先读什么

按以下顺序阅读即可建立当前项目认知：

1. `AGENTS.md`
2. `docs/CODEX_HANDOFF_CN.md`
3. `docs/PROJECT_INTRO_CN.md`
4. `docs/PRODUCT_OPERATIONS_REVIEW_CN.md`
5. `docs/ops/DAILY_OPERATIONS_CHECKLIST_CN.md`
6. `docs/ops/STABLE_OPERATIONS_RUNBOOK_CN.md`
7. `docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md`
8. `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
9. `docs/DEVELOPMENT_ONBOARDING_CN.md`

这些文档先说明当前运行事实和日常处理方式，再进入模块边界与开发规则。专项合同、字段字典、日更细节和历史最终总结从 `docs/DEVELOPMENT_ONBOARDING_CN.md` 按任务进入，不需要在接手时全部通读。

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

当前运行状态以 `configs/active_baseline_descriptor.yaml` 为准：

- `e4_frozen_qlib_2018_2022`：Model A，当前唯一 active baseline。
- `modelb_b19r2r_lambdarank_exact50_78f_v2`：Model A+B 的研究候选，只读历史比较与自动影子链，不是默认模型。
- `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`：旧 LTR 研究产物，保留追溯，不作为当前默认候选。

模型开发阶段可以暂时冻结；真实影子运行、收益结算和运维验收不能因此视为完成。当前产品审查与剩余事项见 `docs/PRODUCT_OPERATIONS_REVIEW_CN.md`。

默认策略规则保持 `top50_exit_one_worst_sell`，但真实页面应通过模型/策略选择、只读 snapshot 和 replay window 展示，不允许把策略写死到前端或模型内部。

## 4. 历史文档怎么处理

仍有当前追溯价值的历史阶段文档集中在：

- `docs/archive/phase_history/README_CN.md`

归档范围包括：

- 阶段执行报告。
- 阶段审查交接。
- 修复过程工作文档。
- 执行者/审查者提示词。

2026-09-18 的仓库物理瘦身已删除 1376 个无当前入站引用的历史文档，以及 157 个退出运行/测试闭包的历史实验脚本。删除项没有丢失：精确清单、逐文件 SHA256、恢复命令和隔离恢复验证保存在仓库外备份中。完整范围和恢复方式见 `docs/ops/REPOSITORY_SLIMMING_REPORT_CN.md`。

需要追溯仍保留的路线时，从归档索引按原目录查找；需要精确复现已退休实验时，先从对应备份恢复。日常开发和审查应优先读当前合同、指南、runbook、最终总结和 checklist。

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
