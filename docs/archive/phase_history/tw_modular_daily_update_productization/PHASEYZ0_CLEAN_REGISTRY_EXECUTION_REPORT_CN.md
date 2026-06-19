# PHASE YZ0 Clean Registry、命名与候选收口执行报告

执行日期：2026-06-18

## 1. 执行范围

本次只执行 `PHASEYZ_STRICT_E4_PRODUCTIZATION_CLEANUP_WORK_CN.md` 的第一步：YZ0 Clean Registry、命名与候选收口。

未进入 YZ1/YZ2/YZ3，未运行模型，未生成新模型分数，未切换 latest/accepted latest 指针，未触发 provider refresh/publish、monitor、broker、order 或 quick-trade。

## 2. 生产模型收口结果

生产可选模型严格收口为 2 个：

- `e4_frozen_qlib_2018_2022`
- `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`

以下旧命名、P3/O4/fresh/bridge/中间实验模型均已从 production selectable 移除，并仅保留为 deprecated 或历史研究语义：

- `e4_frozen_qlib_2023_2025_ltr`
- `fresh_qlib_adaptive`
- `fresh_qlib_2025_ltr`
- `frozen_qlib_2025_ltr`
- `frozen_qlib_2018_2022`
- `p3_daily_ltr_rerank`
- `o4_controlled_ltr`
- `bridge_ltr`

对应文件：`configs/tw_modular_registry.yaml`

## 3. 策略层级收口结果

策略层级已显式拆为：

- `production_selectable`：仅保留 `top50_exit_one_worst_sell`
- `research_only`：保留 `one_sell_one_buy_correct` 与 `one_sell_one_buy_buggy_e8r`
- `deprecated`：`origin`、`original`、`top50_exit_all` 及 smoke/template 策略

`top50_exit_one_worst_sell` 被定义为策略规则，不再绑定旧模型 ID。

`origin` / `original` 明确为 deprecated，不能作为生产可选策略。

`one_sell_one_buy_buggy_e8r` 仅保留为 research-only diagnostic 候选，前端/API 可展示名称已中性化为 `单换手异常候选（研究）`，不暴露原始 `buggy` 语义。

## 4. Replay Matrix 与 Policy

`configs/tw_modular_replay_matrix.yaml` 已标记为历史研究矩阵：

- `matrix_type: historical_research_matrix`
- `not_frontend_or_api_selectable: true`

同时新增 `clean_production_matrix`，只包含 2 个生产 E4 模型与唯一生产策略 `top50_exit_one_worst_sell`。

`configs/tw_replay_window_policy.yaml` 已收口为 YZ0 clean policy：

- `policy_version: replay_window_policy_yz0_clean_v1`
- `default_model_id: e4_frozen_qlib_2018_2022`
- `default_strategy_rule: top50_exit_one_worst_sell`
- `models` 仅包含两个生产 E4 模型

## 5. 后端只读 Replay Window 改造

`backend/app/services/readonly_replay_window.py` 已移除硬编码旧 `VALID_RULES` 集合，策略校验改为读取 `configs/tw_modular_registry.yaml`：

- production strategy：允许查询
- research-only strategy：拒绝为 `research_only_strategy_not_valid_strategy_evidence`
- deprecated strategy：拒绝为 `deprecated_strategy_rule`
- 未注册 strategy：拒绝为 `unknown_strategy_rule`

`backend/app/routes/readonly_replay_window.py` 的默认 `model_id` 与 `strategy_rule` 已改为从 policy/helper 获取，不再硬编码旧模型 `e4_frozen_qlib_2023_2025_ltr`。

## 6. 审计产物

YZ0 审计 JSON 已生成：

- `data_tw/artifacts/phase_yz/yz0_clean_registry_audit.json`

该产物记录了生产模型、生产策略、research-only/deprecated 策略、旧模型移出 production 的列表，以及 YZ0 禁止动作确认。

## 7. 验证结果

已执行：

```bash
python -m py_compile backend/app/services/readonly_replay_window.py backend/app/routes/readonly_replay_window.py
```

结果：通过。

已执行：

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py -q
```

结果：`5 passed in 0.99s`

新增门禁测试覆盖：

- production model count 等于 2，且 ID 完全匹配
- P3/O4/fresh/bridge/旧中间模型不在 production
- `origin` / `original` 不在 production
- `one_sell_one_buy_buggy_e8r` 仅 research-only 且展示名中性化
- replay policy 默认值不再指向旧模型
- backend replay window 拒绝旧模型、deprecated strategy 与 research-only strategy
- service 源码不再保留 `VALID_RULES`

## 8. 禁止动作确认

本阶段未执行以下动作：

- 未运行训练、调参或模型推理
- 未生成或重算模型分数
- 未修改 latest / accepted latest 指针
- 未触发 provider refresh/publish
- 未触发 monitor scan/config save/alerts write
- 未触发 broker/order/quick-trade
- 未改动任何真实交易路径

## 9. 结论

YZ0 已完成。生产可选模型、生产策略、历史矩阵、只读 replay policy 与 backend 校验边界已收口到 strict E4 productization 要求。

可进入 YZ1，但 YZ1 仍需继续保持只读边界，并不得在未明确授权的情况下运行模型或切换 latest 指针。
