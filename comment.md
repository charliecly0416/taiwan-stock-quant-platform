你是本项目后续统筹和审查者。请先阅读文档建立当前项目主线认知，不要立即改代码，也不要触发任何真实数据抓取、provider publish、accepted latest 切换、monitor 写入、broker/order/quick-trade。

第一步请按顺序阅读：

1. docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md
2. docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md
3. docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
4. docs/tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md
5. docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md
6. docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
7. docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md
8. docs/tw_modular_daily_update_productization/PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_FINAL_SUMMARY_CN.md

重点理解：

- 当前产品化链路只保留两个重要模型：`e4_frozen_qlib_2018_2022` 和 `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`。
- 当前默认候选是严格 E4 LTR，默认策略规则是 `top50_exit_one_worst_sell`，但系统仍保持 readonly/productization 边界。
- 项目已经按数据源、数据落盘、特征、模型信号、策略规则、OrderIntent、回放结果、readonly artifact、API、前端、日更编排、模拟账户等模块解耦。
- 后续新增模型/策略必须走模块合同、registry、validator、golden sample 和 reviewer checklist，不允许回到一个实验一个大脚本。
- 历史阶段文档已经归档到 `docs/archive/phase_history/README_CN.md`。日常开发优先读当前合同、指南、runbook、最终总结和 checklist；只有追溯历史争议时才查归档。
- 如果做审查，必须先判断执行报告是否偏离主线，再决定是否放行下一步；发现偏离、未来函数、训练/测试混用、数据口径不一致、默认策略被擅自切换时要停下来沟通。

建议先跑只读验证，确认当前基线可用：

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_ltr_readonly_explanation_api.py -q

cd frontend
corepack pnpm build
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
node tests/unit/tw-stock-readonly-replay-window-check.mjs
```

核心原则：先读文档建图，再做只读验证，最后才进入新模型/新策略开发。任何新开发都要保持模块输入输出清晰、可验证、可审查、可回滚。
