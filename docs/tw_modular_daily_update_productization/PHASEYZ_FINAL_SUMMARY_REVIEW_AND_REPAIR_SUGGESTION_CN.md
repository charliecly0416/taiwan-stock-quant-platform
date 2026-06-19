# Phase YZ Final Summary 审查与收口前修复建议

生成日期：2026-06-18

审查对象：

```text
docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
backend/app/services/phase_yz3_productization_status.py
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
backend/app/services/tw_stock_paper_portfolio.py
backend/app/routes/tw_stock.py
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
data_tw/artifacts/phase_yz/**
/tmp/quantdinger_tw_phase_yz3rr_e2e/network_audit.json
/tmp/quantdinger_tw_phase_yz3rr_e2e/console_audit.json
```

## 1. 总体结论

YZ 路线不能直接最终收尾，需要一个很小的 YZ4 收口修复。

可以确认已完成的部分：

```text
clean registry 已只保留两个产品化 E4 模型；
production strategy 已收口到 top50_exit_one_worst_sell；
origin/original 已不作为前端/API 生产策略；
Model A strict E4 qlib signal 已能生成 150 行；
Model B strict E4 orthogonal LTR signal 已能生成 50 行；
strict E4 top50 orthogonal coverage 已补为 50/50；
execution_price_mode 已固化为 next_open；
next_open 缺失时前端能显示 pending，且 E2E 中 paper apply 没有写入；
readonly replay window 不再默认请求旧 e4_frozen_qlib_2023_2025_ltr；
E2E network audit 未发现 provider/accepted latest/monitor/broker/order/quick-trade 写入。
```

但仍有两个收口前问题：

```text
High: paper portfolio 后端仍硬编码旧模型 e4_frozen_qlib_2023_2025_ltr 作为 apply 校验；
Medium: clean E4 replay artifact 当前为空，前端“只读回放窗口”只是安全占位，不是完整可用回放展示。
```

因此建议：

```text
YZ 可以判定为“主链路方向正确，模型/数据/前端 pending 展示基本完成”；
但不能判定为“产品化 fully closed”；
必须先做 YZ4 小修复，然后再最终收口。
```

## 2. Finding 1：Paper portfolio 后端仍硬编码旧模型

严重级别：High

文件：

```text
backend/app/services/tw_stock_paper_portfolio.py
```

问题证据：

```text
MODEL_ID = "e4_frozen_qlib_2023_2025_ltr"
STRATEGY_RULE = "top50_exit_one_worst_sell"
```

并且 `_validate_intent()` 仍然检查：

```text
if str(intent.get("model_id") or "") != MODEL_ID:
    return self._reject("invalid_artifact", "model_id mismatch")
```

这与 final summary 中的判断不一致：

```text
paper portfolio 不再硬编码旧 e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell
```

实际状态是：

```text
前端 pending 时确实禁用了 paper apply；
但后端 paper apply 服务本身仍只接受旧模型 ID；
一旦 next_open ready 且 strict E4 paper decision 生成，后端 apply 可能因为 model_id mismatch 拒绝 strict E4；
或者如果旧 paper artifact 仍存在，latest_decision 仍可能读取旧 paper_portfolio artifact root。
```

这说明 paper portfolio 还没有完全接入 clean registry / YZ clean decision artifact。

收口前必须修复：

```text
1. 移除 tw_stock_paper_portfolio.py 中旧 MODEL_ID 硬编码。
2. paper apply 校验必须读取 configs/tw_modular_registry.yaml / configs/tw_replay_window_policy.yaml。
3. 只允许 production_models.production_selectable 中的两个 E4 model_id。
4. 只允许 strategies.production_selectable 中的策略。
5. latest_decision 必须只读取 YZ clean paper decision artifact，或至少按 clean registry 过滤旧 artifact。
6. pending execution_price 时，后端 POST /paper-portfolio/apply-decision 也必须拒绝，而不能只靠前端禁用按钮。
```

## 3. Finding 2：clean E4 replay artifact 当前为空

严重级别：Medium

报告已承认：

```text
readonly replay window index windows = []
clean 模型 detail = no_audited_replay_artifact_for_window
```

这在安全上是正确的：没有 clean audited artifact 时不 fallback 到旧 artifact。

但从用户功能角度，它意味着：

```text
前端“选模型/策略跑回放”当前并没有完整可用；
目前只是 clean policy 下的安全拒绝/占位；
不能说用户已经可以用前端查看 clean E4 的回放收益、手续费、回撤等结果。
```

这不是安全阻塞，但如果 YZ 的收口目标包含“前端可用回放展示”，则还没完成。

建议处理方式：

```text
不要在 YZ4 里重跑大规模研究矩阵；
只生成并审计 clean E4 两模型 + top50_exit_one_worst_sell + 2026-01-01..2026-05-07 + next_open 口径的 readonly replay artifact；
登记到 readonly replay window index；
前端仍只读展示，不在 API handler 中按需生成回放。
```

如果统筹选择不在 YZ 内完成这一项，final summary 必须把它降级为明确保留项，不能写成“前端回放已完整可用”。

## 4. 已通过项

### 4.1 模型集合收口

`configs/tw_modular_registry.yaml` 中 production selectable 精确为：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

旧模型位于 deprecated：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_adaptive
fresh_qlib_2025_ltr
frozen_qlib_2025_ltr
frozen_qlib_2018_2022
p3_daily_ltr_rerank
o4_controlled_ltr
bridge_ltr
```

这一点通过。

### 4.2 策略集合收口

production selectable：

```text
top50_exit_one_worst_sell
```

research-only：

```text
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

deprecated：

```text
origin
original
top50_exit_all
```

这一点通过。

### 4.3 Strict E4 daily signal

已看到 artifact：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
```

关键字段：

```text
Model A:
model_id = e4_frozen_qlib_2018_2022
row_count = 150
source_model_artifact = phasee1_frozen_qlib_model.pkl

Model B:
model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
row_count = 50
source_model_artifact = phasee3_ltr_model.pkl
source_model_a_manifest = YZ1 Model A manifest
```

这一点通过。

### 4.4 next_open pending 合同

已看到：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/manifest.json
```

关键字段：

```text
execution_price_mode_planned_for_yz3 = next_open
next_open_available_count = 0
missing_next_open_count = 50
no_fallback_to_next_close = true
no_fallback_to_signal_close = true
status = execution_price_unavailable
```

前端 YZ 卡片显示 pending，且 paper apply 按钮禁用。这一点通过。

但注意：后端 apply POST 也必须实现同等阻断，不能只依赖前端。

### 4.5 安全边界

YZ3RR E2E network audit：

```text
forbidden_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
broker_quick_trade_orders_request_count = 0
ops_provider_publish_refresh_accepted_latest_request_count = 0
paper_apply_write_count = 0
paper_reset_write_count = 0
target_position_write_count = 0
```

Console audit：

```text
console_errors = []
page_errors = []
```

当前只读安全边界通过。

## 5. 前端用户第一性审查

前端整体方向是合理的：

```text
用户进入页面能看到 YZ Clean E4 产品化状态；
能看到 execution_price_mode = next_open；
能看到行情未就绪的 pending 文案；
pending 时模拟应用按钮禁用；
模型/策略收敛，不再把一堆历史实验项暴露给用户；
回放窗口明确来自只读索引，不在前端本地回放。
```

但有两个可用性边界需要如实说明：

```text
1. 当前 pending 状态下，用户还不能应用到模拟账户，这是正确行为。
2. 当前 clean E4 replay artifact 未登记，用户还不能实际查看 clean E4 回放收益，这是安全占位，不是完整功能可用。
```

因此前端符合用户第一性原则的“清晰 pending / 不误导 / 不暴露旧项”部分，但还没有完全达到“可选模型策略并查看 clean E4 回放结果”的最终使用状态。

## 6. 建议新增 Phase YZ4：Paper + Replay 最小收口

目标：只修收口缺口，不扩大路线。

### 6.1 执行范围

允许修改：

```text
backend/app/services/tw_stock_paper_portfolio.py
backend/app/routes/tw_stock.py
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
configs/tw_replay_window_policy.yaml
必要的 readonly replay artifact/index 生成脚本
必要的单元测试/E2E 测试
```

禁止：

```text
不得训练模型
不得调参
不得改两个生产模型身份
不得新增 production strategy
不得 provider refresh/publish
不得 accepted latest switch
不得 monitor config/scan/alerts 写入
不得 broker/order/quick-trade
不得把旧 P3/O4/fresh/bridge 模型重新暴露给前端/API
```

### 6.2 必须完成

```text
1. paper portfolio apply 校验改为 clean registry / policy 驱动。
2. 后端 apply-decision 在 execution_price_status != pass 或 paper_apply_allowed != true 时拒绝。
3. latest paper decision 读取必须过滤旧模型 artifact。
4. 生成 clean E4 两模型 + top50_exit_one_worst_sell + 2026-01-01..2026-05-07 + next_open 口径的 readonly replay artifact。
5. replay artifact 必须显式包含 execution_price_mode = next_open。
6. readonly replay index 登记 clean E4 replay windows。
7. 前端回放窗口能展示 clean E4 replay 结果；若 artifact 不存在则显示明确 unavailable，不 fallback。
8. E2E 证明前端不请求旧模型，不展示 origin/original，不触发 forbidden writes。
```

### 6.3 YZ4 验收标准

```text
tw_stock_paper_portfolio.py 不再出现硬编码旧 MODEL_ID = e4_frozen_qlib_2023_2025_ltr；
POST /paper-portfolio/apply-decision 对 pending execution price 后端拒绝；
strict E4 paper decision ready 后可通过 clean registry 校验；
readonly replay window index 至少包含两个 clean E4 model 的 2026-01-01..2026-05-07 窗口；
replay payload 中包含 execution_price_mode = next_open；
network audit forbidden counts = 0；
paper apply/reset 写入仍仅限模拟账户。
```

## 7. 给执行者的 YZ4 prompt

```text
请执行 Phase YZ4 Paper + Replay 最小收口修复。根据 `docs/tw_modular_daily_update_productization/PHASEYZ_FINAL_SUMMARY_REVIEW_AND_REPAIR_SUGGESTION_CN.md`，只修两个缺口：

1. paper portfolio 后端不得再硬编码旧 `e4_frozen_qlib_2023_2025_ltr`，必须改为 clean registry / replay policy 驱动；pending execution_price 时后端 POST apply-decision 必须拒绝；latest decision 必须过滤旧模型 artifact。
2. 生成并登记 clean E4 两模型 + `top50_exit_one_worst_sell` + `2026-01-01..2026-05-07` + `execution_price_mode=next_open` 的 readonly replay artifact，使前端只读回放窗口可以展示 clean E4 回放结果。

不得训练模型、不得新增生产模型/策略、不得使用旧 P3/O4/fresh/bridge、不得 provider refresh/publish、不得 accepted latest switch、不得 monitor/broker/order/quick-trade。完成后提交 `PHASEYZ4_PAPER_REPLAY_FINAL_REPAIR_EXECUTION_REPORT_CN.md`、测试结果、E2E network/console audit 和 artifact 清单。
```

## 8. 给审查者的 YZ4 prompt

```text
请审查 `PHASEYZ4_PAPER_REPLAY_FINAL_REPAIR_EXECUTION_REPORT_CN.md`。重点确认：

1. `tw_stock_paper_portfolio.py` 是否彻底移除旧模型硬编码；
2. paper apply 是否 registry/policy-driven；
3. pending next_open 时后端 POST 是否拒绝，而不是只靠前端禁用；
4. latest paper decision 是否过滤旧模型 artifact；
5. clean E4 两模型的 readonly replay artifact 是否真实生成并登记到 index；
6. replay payload 是否显式 `execution_price_mode=next_open`；
7. 前端是否只展示两个 E4 模型和生产策略，不出现 origin/original/P3/O4/fresh/bridge；
8. network audit 是否无 provider/accepted latest/monitor/broker/order/quick-trade 写入；
9. 是否没有重训、调参或混入新实验。

若任一不满足，停止，不允许 YZ 最终收口。
```

## 9. 最终审查判定

当前判定：

```text
YZ 主链路方向：通过
模型/数据解耦：基本通过
前端 pending 用户态：通过
只保留两个重要模型：配置层通过
paper portfolio 解耦：未通过
clean E4 replay 前端可用性：未完成
最终收口：暂不通过，需 YZ4 小修复
```

一句话结论：

```text
YZ 已经把最危险的旧模型默认请求和数据覆盖问题清掉了，但 paper apply 后端仍有旧模型硬编码，clean E4 回放 artifact 也还没真正接到前端可展示状态；这两个修完后才适合最终收口。
```
