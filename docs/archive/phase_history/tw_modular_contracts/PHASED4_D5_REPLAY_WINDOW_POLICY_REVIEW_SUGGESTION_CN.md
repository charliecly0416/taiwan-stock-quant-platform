# Phase D4/D5 用户选择回放窗口意见文档

生成日期：2026-06-17

## 1. 结论

如果 D4/D5 要支持用户在前端选择回放时间段，必须先补 `ReplayWindowPolicy`，并由后端强制校验。

不能只靠前端 date picker 限制，也不能让 API 接收到任意日期后直接回放或读取结果。

建议：

```text
D4 先做 readonly standard artifact index + 固定 2026_ytd 展示；
D5 再做用户可选回放窗口；
D5 前置必须实现 ReplayWindowPolicy。
```

如果执行者坚持 D4 就支持用户选择窗口，则 D4 工作文档必须先扩展为：

```text
D4A ReplayWindowPolicy
D4B readonly replay query API
D4C frontend date-range display
```

不得直接在前端加日期框。

## 2. 为什么需要 ReplayWindowPolicy

不同模型有不同训练窗口。用户选择回放时间段时，必须避免把训练期收益当成策略表现。

例如：

```text
model_id: e4_frozen_qlib_2023_2025_ltr
qlib_train_window: 2018-01-01..2022-12-31
ltr_train_window: 2023-01-01..2025-12-31
allowed_replay_start_min: 2026-01-01
```

因此 E4 不允许用户选择：

```text
2023-01-01..2025-12-31
```

作为策略回放证据。那是 LTR 训练区间。

## 3. ReplayWindowPolicy 最小合同

建议新增配置：

```text
configs/tw_replay_window_policy.yaml
```

示例：

```yaml
policy_version: replay_window_policy_v1
models:
  e4_frozen_qlib_2023_2025_ltr:
    model_family: ltr
    qlib_train_start: 2018-01-01
    qlib_train_end: 2022-12-31
    ltr_train_start: 2023-01-01
    ltr_train_end: 2025-12-31
    allowed_replay_start_min: 2026-01-01
    allowed_replay_end_policy: latest_available_signal_date
    allowed_windows:
      - name: 2026_ytd
        start: 2026-01-01
        end: 2026-05-07
    disallow_training_overlap: true
    disallow_future_beyond_signal: true
  fresh_qlib_adaptive:
    model_family: qlib
    qlib_train_start: 2017-01-10
    qlib_train_end: 2024-12-31
    allowed_replay_start_min: 2025-01-01
    allowed_replay_end_policy: latest_available_signal_date
    disallow_training_overlap: true
    disallow_future_beyond_signal: true
```

注意：具体日期以当前已审计 manifest 为准，执行者不得凭记忆填写。必须从模型/训练报告/manifest 追溯。

## 4. 后端校验规则

新增 validator 或 service：

```text
scripts/validate_tw_replay_window_policy.py
```

或后端 service：

```text
backend/app/services/tw_replay_window_policy.py
```

必须检查：

- `start_date <= end_date`；
- `start_date >= allowed_replay_start_min`；
- `end_date <= latest_available_signal_date`；
- 窗口不得与 qlib train / LTR train 重叠；
- model_id 必须在 policy 中登记；
- strategy_rule 必须在 strategy dependency registry 中登记；
- diagnostic rule 不能作为普通策略展示；
- 返回错误必须清楚说明不允许的原因。

示例错误：

```json
{
  "ok": false,
  "error": "requested window overlaps LTR training window",
  "model_id": "e4_frozen_qlib_2023_2025_ltr",
  "requested_start": "2025-01-01",
  "requested_end": "2025-12-31",
  "allowed_replay_start_min": "2026-01-01"
}
```

## 5. API 设计建议

### 5.1 查询可选窗口

```text
GET /api/tw-stock/modular-replay/windows
```

返回：

```json
{
  "ok": true,
  "readonly_only": true,
  "models": [
    {
      "model_id": "e4_frozen_qlib_2023_2025_ltr",
      "allowed_replay_start_min": "2026-01-01",
      "latest_available_signal_date": "2026-05-07",
      "preset_windows": [
        {
          "name": "2026_ytd",
          "start": "2026-01-01",
          "end": "2026-05-07"
        }
      ]
    }
  ]
}
```

### 5.2 查询回放结果

```text
GET /api/tw-stock/modular-replay/result?model_id=...&strategy_rule=...&start=...&end=...
```

后端必须先调用 ReplayWindowPolicy validator。

如果窗口已经有标准 `ReplayResultArtifact`，API 只读返回现有结果。

如果没有现成 artifact，D4/D5 必须先决定是否允许“按标准 OrderIntent + ReplayExecution 生成新的 readonly replay artifact”。如果允许，必须：

- 只生成到只读研究 artifact 目录；
- 不写 provider / accepted latest；
- 不改默认策略；
- 不改前端状态；
- 不触发交易链路；
- 生成 manifest / validator / checksum；
- 返回 artifact 路径和审计状态。

## 6. 前端设计建议

前端应分为两个区域：

### 6.1 当日策略意图区

输入：

```text
OrderIntentArtifact API
```

交互：

- 策略下拉框；
- 模型下拉框；
- 日期选择 latest / 指定 signal_date；
- 展示候选买入、候选卖出、继续观察、跳过。

### 6.2 回放结果区

输入：

```text
ReplayResultArtifact API
ReplayWindowPolicy API
```

交互：

- 模型下拉框；
- 策略下拉框；
- preset window；
- date range picker。

前端必须显示：

- 允许回放最早日期；
- 当前选择是否 OOS；
- 若窗口非法，展示后端错误，不自己绕过；
- 收益、回撤、手续费、税费、交易次数、skipped actions；
- daily nav；
- action table；
- coverage/integrity audit。

文案要求：

```text
只读回放
研究结果
候选意图
非交易指令
不构成投资建议
```

禁止：

```text
下单
买入指令
卖出指令
目标仓位
自动交易
一键交易
保证收益
胜率承诺
```

## 7. D4/D5 分工建议

推荐拆分：

### D4：只读标准产物索引与固定窗口展示

- 建立 D3RR artifact index；
- API / 前端展示固定 `2026_ytd`；
- 不提供用户自选窗口；
- 为 D5 暴露 window policy metadata。

### D5：用户自选回放窗口

- 实现 `ReplayWindowPolicy`；
- 实现窗口 validator；
- 实现 replay result 查询 API；
- 前端 date range picker；
- 后端拒绝训练期窗口；
- 必须有 E2E 证明非法窗口不能查询。

如果用户坚持 D4 就做 date range，必须把 D5 的 ReplayWindowPolicy 前置到 D4。

## 8. 审查硬 Gate

支持用户选择回放窗口前，必须满足：

```text
replay_window_policy_exists == true
model_training_windows_traceable == true
backend_window_validator_exists == true
frontend_date_picker_not_only_guard == true
illegal_training_window_rejected_by_api == true
diagnostic_rule_not_valid_strategy_evidence == true
readonly_only == true
no_provider_publish == true
no_accepted_latest_switch == true
no_monitor_broker_order == true
```

## 9. 给执行者的 Prompt

请按：

```text
docs/tw_modular_contracts/PHASED4_D5_REPLAY_WINDOW_POLICY_REVIEW_SUGGESTION_CN.md
```

在 D4/D5 工作中补充用户可选回放窗口设计。若 D4 只展示固定 D3RR `2026_ytd` 标准产物，可以暂不实现 date range；若 D4/D5 任一阶段要允许用户选择日期范围，必须先实现 `ReplayWindowPolicy`、后端 validator 和非法训练窗口拒绝测试。

不得只靠前端 date picker 限制。不得允许 E4 选择 2023-2025 训练区间作为回放结果。不得触发 provider publish、accepted latest、monitor、broker、quick-trade、order。

## 10. 给审查者的 Prompt

请审查 D4/D5 报告时重点确认：

- 是否支持用户选择回放窗口；
- 如果支持，是否有 `ReplayWindowPolicy`；
- E4 是否只允许 2026 及之后的 OOS 窗口；
- 是否由后端拒绝训练期窗口；
- 前端是否只展示 API 返回结果，不自行回放；
- diagnostic rule 是否没有进入有效策略对比；
- 是否没有 provider / accepted latest / monitor / broker / order 越界。

若没有后端窗口校验，不能放行用户自选回放窗口。
