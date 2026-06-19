# Phase R0 Proposal 与 Contract 执行报告

- 生成时间：`2026-06-11T17:44:23+00:00`
- 当前阶段目标：设计人工复盘解释模块 proposal、输出 contract、输入来源盘点与安全边界声明。
- 执行范围：只写 Phase R0 文档和盘点产物；不实现后端业务服务、不接 API、不接前端。

## 1. 修改文件

- 新增 `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- 新增 `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`
- 新增 `data_tw/experiments/manual_review_explanation/phaser0_input_source_inventory.csv`
- 新增 `data_tw/experiments/manual_review_explanation/phaser0_contract_summary.json`

## 2. 生成文件

- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/manual_review_explanation/phaser0_input_source_inventory.csv`
- `data_tw/experiments/manual_review_explanation/phaser0_contract_summary.json`

## 3. 输入来源盘点摘要

允许进入 contract / 未来 R1 只读服务的输入：

- qlib rank / score / rank tier：只解释研究池和排名层级，不解释为收益预测。
- QuantDinger trend：只解释趋势状态和量能配合，不解释为看涨承诺。
- 技术状态：只解释支持、中性、转弱或冲突。
- 价格位置风险：只解释位置偏高、短期过热或回调位置等复盘风险。
- 冻结法人/融资融券规则卡：只作为人工 caution/review/background/auxiliary 线索。
- 数据不足状态：用于避免强行解释。

明确拒绝：

- fundamental 月营收/基本面输入。
- 单期 TWSE current file。
- FinMind `date/create_time` proxy。
- 新外部数据源、token、联网来源。
- 买卖、仓位、收益、概率语义字段。

## 4. 输出 Contract 摘要

输出对象为 `manual_review_explanation`，核心字段包括：

- `symbol`
- `name`
- `asof`
- `overall_status`
- `status_label`
- `confidence`
- `summary`
- `signals`
- `next_review_focus`
- `research_only=true`
- `not_trading_advice=true`
- `data_quality_notes`

`overall_status` 只允许：

- `multi_source_support`
- `manual_review`
- `caution`
- `conflict`
- `data_insufficient`

`signals.type` 只允许：`support`、`risk`、`conflict`、`background`、`data_quality`。

`signals.severity` 只允许：`info`、`watch`、`caution`、`review`。

## 5. 安全语义检查

- 是否出现交易语义：否。
- 是否出现收益/概率语义：否。
- 是否误用冻结规则卡：否，规则卡只允许作为人工解释线索，不允许作为 gate。
- 是否继续 fundamental 主线：否。
- 是否继续正交失败主线：否。
- 是否复活 Entry Model：否。
- 是否联网/token/新数据源：否。

## 6. 安全边界检查

- business_service_written=false
- api_written=false
- frontend_written=false
- network_used=false
- token_used=false
- new_data_source=false
- model_training=false
- provider_write=false
- accepted_latest_switching=false
- trading_or_order=false
- contract_has_trading_semantics=false
- contract_has_return_or_probability_semantics=false
- fundamental_inputs_allowed=false
- frozen_rules_as_gate_allowed=false

## 7. 推荐 Gate

- recommended_gate：`request_phaser1_readonly_service_work`
- gate_reason：R0 已完成 proposal、contract、输入来源盘点与安全边界声明；未写服务/API/前端，未触碰模型、provider、新数据源或交易语义。是否进入 R1 只读服务实现需等待审查者授权。

## 8. 风险与待审查问题

- R1 如果实现服务，必须只读接入既有数据，不得新增数据源或联网。
- 用户可见文案必须继续避免买卖、仓位、收益、概率语义。
- 冻结规则卡必须保持人工解释用途，不得升级为自动 gate、confirmed watch 或模型训练标签。
- fundamental 月营收主线已停止，不能作为本模块输入。

完成后等待审查者审核，不自动进入 R1。
