# Phase R1 后端只读服务执行报告

- 生成时间：`2026-06-11T17:53:26+00:00`
- 当前阶段目标：实现人工复盘解释模块后端只读服务层，按照 R0 contract 组装 explanation JSON。
- 执行范围：只新增服务层与单元测试；未写 API route，未接前端，未联网，未新增数据源。

## 1. 修改文件

- 新增 `backend/app/services/tw_manual_review_explanation.py`
- 新增 `backend/tests/test_tw_manual_review_explanation.py`
- 新增 `docs/tw_manual_review_explanation/PHASER1_EXECUTION_REPORT_CN.md`

## 2. 生成文件

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `docs/tw_manual_review_explanation/PHASER1_EXECUTION_REPORT_CN.md`

## 3. 服务输入输出摘要

R1 服务 `TWManualReviewExplanationService` 只接受调用方传入的内存 dict，不主动读取文件、数据库、网络或外部服务。

允许输入组：

- `qlib_rank` / `qlib`
- `trend`
- `technical_status`
- `position_risk` / `positionRisk`
- `frozen_rule_cards`
- 数据缺失状态

输出字段遵循 R0 contract：

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

服务内置校验：

- `overall_status` 枚举校验。
- `signals.type` 与 `signals.severity` 枚举校验。
- `confidence` 仅表示解释完整度，枚举为 `low/medium/high`。
- 禁止字段扫描。
- 禁止文案扫描。
- `signals` 最多 5 条。
- 冻结规则卡只输出人工解释线索，不输出 raw rule id。

## 4. 测试覆盖摘要

已新增单元测试覆盖：

1. 强排名 + 位置偏高：输出 support 与 risk，不出现交易/仓位/收益/概率语义。
2. 排名弱 + 技术弱：输出 `manual_review` 或 `caution`，不写成卖出语义。
3. 信息冲突：研究排名靠前但趋势/技术转弱，输出 conflict 或包含冲突结构。
4. 数据不足：输出 `data_insufficient`，包含 `data_quality` signal。
5. 冻结规则卡：只产生人工解释线索，不变成 gate、confirmed watch 或模型标签。
6. 禁止语义扫描：禁止字段和禁止文案会触发校验错误。

## 5. 验证命令

- `python -m py_compile backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py -q`

结果：6 个专项测试通过。

## 6. 安全边界检查

- 是否写 API：否。
- 是否接前端：否。
- 是否联网/token：否。
- 是否新增数据源：否。
- 是否写数据库/provider：否。
- 是否 provider refresh/publish：否。
- 是否 accepted latest switching：否。
- 是否训练模型：否。
- 是否 monitor config save / monitor scan / alerts write：否。
- 是否 broker / quick-trade / orders：否。
- 是否出现交易/收益/概率语义：正常输出无；测试中仅作为禁止语义扫描输入。
- 是否误用冻结规则卡：否，冻结规则卡只映射为 `frozen_rule_card` 人工解释线索。

## 7. 推荐 Gate

- recommended_gate：`request_phaser2_readonly_api_work`
- gate_reason：R1 后端只读服务与单元测试已完成；服务不主动读取外部数据、不写 API route、不接前端、不联网、不写数据库/provider、不训练模型，且专项测试验证无交易/仓位/收益/概率语义。

## 8. 风险与待审查问题

- R2 若接只读 API，必须另行授权并保持 route 只读，不接 monitor、broker、orders 或 provider。
- R2 需要继续保留禁止语义扫描，避免用户可见文案出现买卖、仓位、收益或概率语义。
- 当前 R1 不处理真实数据读取，后续服务接入既有上下文时仍需审查字段映射。

完成后等待审查者审核，不自动进入 R2。
