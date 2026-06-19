# Phase YZ4 统筹审查结论

生成日期：2026-06-18

审查对象：

```text
docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md
docs/tw_modular_daily_update_productization/PHASEYZ4_PAPER_REPLAY_FINAL_REPAIR_EXECUTION_REPORT_CN.md
backend/app/services/tw_stock_paper_portfolio.py
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
backend/app/services/phase_yz3_productization_status.py
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
data_tw/artifacts/readonly_replay_windows/d7/latest.json
data_tw/artifacts/readonly_replay_windows/d7/manifest.json
data_tw/artifacts/readonly_replay_windows/d6/**
/tmp/quantdinger_tw_phase_yz4_e2e/network_audit.json
/tmp/quantdinger_tw_phase_yz4_e2e/console_audit.json
```

## 1. 总体结论

YZ4 修复方向基本正确，但当前不建议直接最终收尾。

原因不是主功能继续偏离，而是：

```text
既有 paper portfolio API 测试 `backend/tests/test_tw_stock_paper_portfolio_x2r_api.py` 仍有 3 个失败；
测试合同尚未同步 YZ4 的 execution_price_unavailable 后端阻断语义；
因此项目当前不是“测试闭环通过”的收口状态。
```

建议结论：

```text
YZ4 功能实现：基本通过
只读/模拟安全边界：通过
clean registry / 两模型收口：通过
replay artifact/index 安全展示：通过
测试闭环：未通过
最终收口：暂缓，需 YZ4R 小修复后再收口
```

## 2. 已确认通过项

### 2.1 Paper portfolio 旧模型硬编码已移除

`backend/app/services/tw_stock_paper_portfolio.py` 不再保留旧：

```text
MODEL_ID = "e4_frozen_qlib_2023_2025_ltr"
```

当前 `_validate_intent()` 改为：

```text
model_id in clean["models"]
strategy_rule in clean["strategies"]
execution_price_mode == "next_open"
```

`clean["models"]` 来自：

```text
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
```

这一项通过。

### 2.2 Paper apply 后端 gate 在写入前执行

`apply_decision()` 当前流程为：

```text
读取 authoritative intent
校验 request / checksum / clean model / clean strategy
执行 _execution_price_gate(intent)
gate 通过后才 ensure_schema()
之后才进入 DB account / apply_runs / orders / trades 写入逻辑
```

这满足“pending next_open 时不能只靠前端禁用按钮”的要求。

当前 `_execution_price_gate()` 会要求：

```text
execution_price_mode == next_open
execution_price_status == pass
paper_apply_allowed == true
next_open_available_count > 0
missing_next_open_count == 0
no_fallback_to_next_close == true
no_fallback_to_signal_close == true
```

这一项通过。

### 2.3 latest_decision 已过滤非 clean artifact

`latest_decision()` 当前会调用：

```text
_manifest_is_clean_decision(manifest)
```

只接受 clean production model / production strategy / next_open 的 paper decision bundle。

这一项通过。

### 2.4 D7 replay index 已登记两个 clean E4 window

`data_tw/artifacts/readonly_replay_windows/d7/manifest.json` 当前包含两个 window：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

策略均为：

```text
top50_exit_one_worst_sell
```

执行价模式：

```text
execution_price_mode = next_open
```

这一项通过。

### 2.5 Replay artifact 口径没有误当收益证明

两个 D6 replay result 的 `summary.csv` 均为：

```text
action_count = 0
total_return = 0.000000
note = clean_e4_readonly_replay_pending_execution_price_no_trades
```

这说明 YZ4 没有伪造收益，也没有把 pending 状态下的 no-trade artifact 当成策略表现证据。

这一项通过。

### 2.6 安全边界通过

`/tmp/quantdinger_tw_phase_yz4_e2e/network_audit.json`：

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

`console_audit.json`：

```text
console_errors = []
page_errors = []
```

这一项通过。

## 3. 阻塞项：paper API 既有测试仍失败

审查者复跑：

```text
python -m pytest \
  backend/tests/test_tw_stock_paper_portfolio_x2.py \
  backend/tests/test_tw_stock_paper_portfolio_x2r_api.py \
  backend/tests/test_build_tw_paper_portfolio_decision_artifact.py \
  backend/tests/test_tw_stock_readonly_replay_window_api.py -q
```

结果：

```text
38 passed
3 failed
```

失败文件：

```text
backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
```

失败用例：

```text
test_paper_portfolio_apply_route_success_and_error_mapping
test_paper_portfolio_apply_route_rejects_invalid_stale_not_found_and_artifact_abuse
test_paper_portfolio_apply_route_rejects_same_day_different_decision
```

失败原因摘要：

```text
旧测试仍预期 paper apply 可以成功进入 no_actions / stale_epoch 等旧路径；
但 YZ4 新语义是在 execution_price_unavailable 时，后端必须先拒绝 paper apply；
所以实际返回 execution_price_unavailable。
```

这从功能语义上看更接近正确行为，但测试没有同步更新，导致项目测试闭环不完整。

只要这些测试仍失败，就不能说 YZ4 “完善可收尾”。

## 4. 其他轻微注意事项

### 4.1 E2E 默认只请求 Model A

YZ4 network audit 中 readonly replay 请求只看到：

```text
model_id=e4_frozen_qlib_2018_2022
```

D7 index 已登记 Model A 和 Model B 两个窗口，所以功能上不是阻塞项。但如果要更严谨，YZ4R 可补一个 E2E 或 API smoke，显式请求 Model B：

```text
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

### 4.2 STRATEGY_RULE 常量仍存在但不构成旧模型风险

`tw_stock_paper_portfolio.py` 仍有：

```text
STRATEGY_RULE = "top50_exit_one_worst_sell"
```

当前 `_validate_intent()` 已从 clean registry 校验 strategy，因此该常量如果没有参与强制绑定可以接受。但后续最好也统一由 registry/policy 默认读取，减少长期维护歧义。

## 5. 建议新增 Phase YZ4R：测试合同同步与最终验收

YZ4R 不应改主功能，只做最小测试/验收修复。

允许范围：

```text
backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
必要的 paper portfolio fixture / helper
必要的 readonly replay API smoke test
docs/tw_modular_daily_update_productization/PHASEYZ4R_TEST_CONTRACT_SYNC_EXECUTION_REPORT_CN.md
```

禁止：

```text
不得训练模型
不得改生产模型集合
不得改生产策略集合
不得重新引入旧模型
不得 provider refresh/publish
不得 accepted latest switch
不得 monitor/broker/order/quick-trade
不得把 pending 状态绕过成可 apply
```

必须完成：

```text
1. 更新 paper API 测试，使 pending next_open 时 POST apply-decision 预期返回 execution_price_unavailable。
2. 保留或新增 ready-state 单元测试：mock productization_status_loader 返回 pass，证明 clean strict E4 intent 可以进入原有 apply 路径。
3. 保留 invalid artifact / path traversal / checksum mismatch 测试，确保这些仍先于或独立于 gate 被拒绝。
4. 复跑 paper/replay 测试组合必须全绿。
5. 补一个 Model B readonly replay API smoke，确认 D7 index 的第二个 clean window 可查。
```

建议复跑命令：

```text
python -m pytest \
  backend/tests/test_phase_yz0_clean_registry.py \
  backend/tests/test_phase_yz1_strict_e4_model_adapters.py \
  backend/tests/test_phase_yz2_orthogonal_package.py \
  backend/tests/test_phase_yz2r_execution_price_readiness.py \
  backend/tests/test_phase_yz3_productization_status.py \
  backend/tests/test_tw_stock_paper_portfolio_x2.py \
  backend/tests/test_tw_stock_paper_portfolio_x2r_api.py \
  backend/tests/test_build_tw_paper_portfolio_decision_artifact.py \
  backend/tests/test_tw_stock_readonly_replay_window_api.py -q
```

## 6. 给执行者的 YZ4R prompt

```text
请执行 Phase YZ4R 测试合同同步与最终验收。不要改模型、策略、provider、latest、monitor、broker/order。当前 YZ4 功能方向基本正确，但 `backend/tests/test_tw_stock_paper_portfolio_x2r_api.py` 仍有 3 个旧测试失败，因为旧测试期待 pending 状态下 paper apply 成功，而 YZ4 合同要求 execution_price_unavailable 时后端先拒绝。

请更新/补充 paper API 测试：
1. pending next_open 时 POST /paper-portfolio/apply-decision 应返回 execution_price_unavailable，且无 schema/apply_runs/orders/trades 写入；
2. mock ready status 时，clean strict E4 intent 应能进入原有 apply 成功路径；
3. path traversal / checksum mismatch / invalid artifact 仍应正确拒绝；
4. 补 Model B readonly replay API smoke，确认 D7 第二个 clean window 可查；
5. 复跑 YZ + paper/replay 相关 pytest 全绿。

完成后提交 `docs/tw_modular_daily_update_productization/PHASEYZ4R_TEST_CONTRACT_SYNC_EXECUTION_REPORT_CN.md`。
```

## 7. 给审查者的 YZ4R prompt

```text
请审查 `PHASEYZ4R_TEST_CONTRACT_SYNC_EXECUTION_REPORT_CN.md`。重点确认：
1. paper API 既有失败测试是否已同步 YZ4 pending gate 合同；
2. pending execution_price_unavailable 是否后端拒绝且无写入；
3. mock ready status 是否证明 clean strict E4 paper intent 可以应用到模拟账户路径；
4. invalid artifact/path traversal/checksum mismatch 是否仍被拒绝；
5. Model B readonly replay API 是否可查；
6. 复跑 YZ + paper/replay 相关 pytest 是否全绿；
7. 是否没有训练、调参、provider/accepted latest/monitor/broker/order/quick-trade。

若全部满足，YZ 路线可以最终收口。
```

## 8. 最终判定

当前判定：

```text
YZ4 实现本身：基本通过
YZ 路线最终收口：暂不通过
需要：YZ4R 测试合同同步
```

一句话结论：

```text
YZ4 把之前的关键功能缺口补上了，但测试套件还没跟上新的 next_open pending gate 合同；为了避免带着失败测试收口，建议先做一个很小的 YZ4R，再最终关闭 YZ。
```
