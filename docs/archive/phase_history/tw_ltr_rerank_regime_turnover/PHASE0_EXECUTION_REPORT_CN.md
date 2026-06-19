# Phase 0 执行报告：LTR 重排序 + Regime + Turnover 主线

生成时间：2026-06-13T15:10:46+00:00

## 1. 本轮目标

按审查者 Phase 0 步骤文档，仅完成样本范围、特征白名单、禁止特征、标签候选、baseline 对照、数据切分和 Phase 1 gate 的 proposal / inventory / audit。

## 2. 实际完成内容

- 新增只读审计脚本：`scripts/audit_tw_ltr_phase0_contract.py`。
- 生成白名单特征盘点：`phase0_feature_whitelist_inventory.csv`。
- 生成禁止特征审计：`phase0_forbidden_feature_audit.csv`。
- 生成 baseline 盘点：`phase0_baseline_inventory.csv`。
- 生成 gate 汇总：`phase0_gate_summary.json`。
- 生成口径冻结合同：`phase0_sample_feature_label_baseline_contract.md`。

## 3. 改动文件清单

- `scripts/audit_tw_ltr_phase0_contract.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/phase0_sample_feature_label_baseline_contract.md`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_feature_whitelist_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_forbidden_feature_audit.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_baseline_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_gate_summary.json`

## 4. 验证内容与结果

- 白名单覆盖率检查：已覆盖主文档 35 个白名单字段。
- 禁止特征扫描：Phase0 input features 命中数为 0。
- label / input / audit / grouping 隔离：已在合同中冻结，脚本未构建任何训练样本。
- baseline 对照清单：已覆盖 4 个指定 baseline。
- PIT 安全说明：已写入合同与 feature inventory；仅允许当前日及历史可得字段派生。
- 本地证据盘点：prediction 文件 1379 个，top30 文件 1379 个，top50 文件 1379 个，价格文件 1986 个，TWII 存在：True。

## 5. 是否达到本轮门槛

- `phase0_contract_complete=True`
- `forbidden_feature_scan_passed=True`
- `label_input_audit_grouping_isolation_passed=True`
- `baseline_inventory_complete=True`
- `data_split_contract_complete=True`
- 推荐 gate：`request_phase1_ltr_baseline_work`

## 6. 风险 / 异常 / 未解决问题

- Phase 0 未训练、未回放，因此不声明任何 LTR 效果。
- `trend_score` 需要 Phase 1 确认是否存在稳定既有口径；若没有，应保持排除。
- `rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 仅冻结为未来 baseline 名称和对照口径；旧 replay 不能作为本主线收益证据。
- 若 Phase 1 实际样本覆盖不足以支持 train / validation / independent test，必须停止并报告。

## 7. 需要审查者重点检查的点

- 白名单字段是否严格等于主文档范围。
- 禁止字段是否只出现在禁止/审计说明中，没有进入 input feature。
- 标签候选是否保持排序任务语义，而非收益率点预测语义。
- baseline 口径是否满足四个指定 baseline 的冻结要求。
- 推荐 gate 是否可以进入 Phase 1 LTR baseline work。

## 8. 本轮禁止事项遵守情况

本轮未训练模型、未运行 replay、未改前端、未改 API、未写数据库、未联网、未使用 token、未新增数据源、未 provider refresh/publish、未 accepted latest switching、未 monitor 写入或扫描、未接 broker / quick-trade / orders，未输出买入/卖出/持有、仓位、收益率、上涨概率或胜率语义。
