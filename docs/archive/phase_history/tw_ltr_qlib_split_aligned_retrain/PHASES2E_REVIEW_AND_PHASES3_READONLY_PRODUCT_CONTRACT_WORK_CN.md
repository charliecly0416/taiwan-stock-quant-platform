# Phase S2E 审查意见与 Phase S3 Readonly Product Contract 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2E_FRESH_RETRAIN_CONCLUSION_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2D_REVIEW_AND_PHASES2E_FRESH_RETRAIN_CONCLUSION_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2E 通过，S2 gate 接受为 fresh_retrain_qlib_or_top50_default_supported，允许进入 Phase S3 readonly product contract。`

通过理由：

- S2E 正确区分了 S1 与 S2：
  - S1 是旧窗口 split-aligned 方法验证；
  - S2 是 fresh retrain 当前可用性验证；
  - 没有把 S1 的 LTR 方法支持包装成 fresh default 资格。
- S2E 给出的 gate 属于主线允许范围：

```text
fresh_retrain_qlib_or_top50_default_supported
```

- 结论没有支持 LTR 默认化；
- `fresh_ltr_simple` 被定位为不支持默认；
- `fresh_ltr_turnover_controlled` 被定位为低动作研究候选，不自动选择；
- 没有把低动作优势包装成收益更优、回撤更优或未来更稳；
- 未训练、未回放、未调参、未新增策略变体；
- 未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

允许进入：

```text
Phase S3 readonly product contract
```

不允许直接进入：

```text
frontend/API implementation
provider refresh/publish
accepted latest switching
monitor
trading chain
default strategy product switch without contract review
```

---

## 2. 关键结论

### 2.1 当前 S2 gate

接受 gate：

```text
fresh_retrain_qlib_or_top50_default_supported
```

含义：

- 当前 fresh retrain 证据支持默认研究方向留在 qlib/top50 家族；
- 不是交易建议；
- 不是收益承诺；
- 不是 accepted latest / provider / 前端默认值切换。

### 2.2 qlib/top50 家族定位

S2E 证据支持：

```text
fresh_qlib_top50_adaptive_baseline: default_research_candidate
fresh_confirmed_exit: same_family_research_candidate
fresh_rank_rotate_top50: secondary_baseline_only
```

说明：

- `fresh_confirmed_exit` full test 略优于 top50，但 validation 低于 top50；
- 因此它可以作为同家族研究候选，不应在 S3 自动替代 top50 adaptive；
- S3 可以设计成默认展示 top50 adaptive，同时允许同家族候选作为只读对照。

### 2.3 LTR 定位

S2E 证据支持：

```text
fresh_ltr_simple: research_only_not_default
fresh_ltr_turnover_controlled: low_action_research_candidate_only
```

禁止表述：

```text
LTR 收益更优
LTR 更稳
LTR 默认策略成立
LTR 未来表现更好
```

允许表述：

```text
低动作研究候选
历史模拟中动作更少
收益/回撤相对 top50 有取舍
仅供研究对照
```

---

## 3. Findings

### Low 1：S2E 报告正文未列出 forbidden audit，但产物齐全

已核查：

```text
phase_s2e_forbidden_action_audit.json
phase_s2e_gate_summary.json
phase_s2e_ltr_positioning_note.json
phase_s2e_default_candidate_decision_matrix.csv
phase_s2e_s1_s2_evidence_summary.json
```

安全边界与 gate 均满足要求，不要求重写 S2E。

### Low 2：S3 必须防止“默认研究候选”被 UI 文案误读为买卖建议

`default_research_candidate` 只能表示研究页默认展示或优先对照，不得写成：

```text
建议使用
建议买入
推荐持有
目标仓位
未来收益更好
```

S3 必须先冻结产品展示合同，再决定是否允许实现。

---

## 4. Gate

S2E gate 接受：

```text
fresh_retrain_qlib_or_top50_default_supported
```

下一轮执行：

```text
Phase S3 readonly product contract
```

---

## 5. Phase S3 工作目标

S3 只回答一个问题：

```text
如何把 S1/S2 研究结论转成用户第一性、只读、安全、清晰的产品展示合同？
```

S3 是产品合同设计轮，不是实现轮。

---

## 6. Phase S3 必须冻结

执行者必须冻结：

1. 默认研究展示策略：
   - 建议默认展示：`fresh_qlib_top50_adaptive_baseline`；
   - `fresh_confirmed_exit` 可作为 qlib/top50 同家族候选；
   - 不得自动把 confirmed_exit 替代为产品默认，除非后续用户确认。

2. 策略列表与用户可读标签：
   - `fresh_qlib_top50_adaptive_baseline`：默认研究候选；
   - `fresh_confirmed_exit`：同家族研究候选；
   - `fresh_rank_rotate_top50`：规则基线对照；
   - `fresh_ltr_simple`：LTR 研究候选，不默认；
   - `fresh_ltr_turnover_controlled`：低动作研究候选，不默认。

3. 用户第一性文案：
   - 简单：普通用户能理解；
   - 准确：区分历史模拟、研究候选、低动作取舍；
   - 清晰：默认看哪个、其他策略为什么存在；
   - 实用：不要堆训练细节，不要隐藏 caveat。

4. 指标展示范围：
   - `fee_tax_adjusted_net_return` 可显示为历史模拟收益；
   - `max_drawdown`；
   - `action_count`；
   - `fee_and_tax`；
   - `turnover_proxy_by_notional_over_avg_equity`；
   - validation/test 区间说明；
   - caveat：历史模拟不代表未来结果。

5. 禁用语义：
   - 买入/卖出建议；
   - 持有建议；
   - 目标仓位；
   - 目标权重；
   - 未来收益；
   - 胜率；
   - 上涨概率；
   - 自动交易；
   - broker / quick-trade / orders。

6. 数据/系统边界：
   - 不改 provider；
   - 不切换 accepted latest；
   - 不触发 monitor；
   - 不接交易链路；
   - 不改前端/API 实现。

---

## 7. Phase S3 禁止事项

本轮禁止：

- 训练 qlib；
- 训练 LTR；
- 跑新回放；
- 调参或参数搜索；
- 新增策略变体；
- 改 split；
- 改 feature / label；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改前端/API；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、收益承诺、胜率承诺、上涨概率承诺。

---

## 8. Phase S3 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s3_readonly_product_contract/
```

必须产物：

```text
phase_s3_strategy_display_contract.json
phase_s3_user_facing_copy_contract.json
phase_s3_metric_display_contract.json
phase_s3_safety_semantics_audit.json
phase_s3_forbidden_action_audit.json
phase_s3_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES3_READONLY_PRODUCT_CONTRACT_EXECUTION_REPORT_CN.md
```

---

## 9. Phase S3 通过条件

只有全部满足时，才允许进入后续只读实现评估：

```text
default_research_display_strategy_frozen = true
fresh_qlib_top50_adaptive_baseline_default_display = true
fresh_confirmed_exit_not_auto_promoted_to_default = true
ltr_candidates_not_default = true
low_action_tradeoff_disclosed = true
user_facing_copy_safe = true
historical_simulation_not_future_promise = true
no_buy_sell_hold_position_weight_language = true
no_frontend_or_api_implementation = true
no_provider_refresh_publish = true
no_accepted_latest_switching = true
no_monitor_or_trading_chain = true
```

通过 gate：

```text
s3_readonly_product_contract_pass_request_s3b_readonly_implementation_plan
```

失败 gate：

```text
s3_blocked_by_unsafe_product_semantics
s3_blocked_by_default_strategy_tradeoff
s3_blocked_by_scope_violation
s3_blocked_by_user_tradeoff_required
```

---

## 10. 给执行者的一句话

请执行 Phase S3：只把 S2E 的 `fresh_retrain_qlib_or_top50_default_supported` 结论转成只读产品展示合同，默认研究展示冻结为 `fresh_qlib_top50_adaptive_baseline`，confirmed_exit 仅作同家族候选，LTR 仅作研究/低动作候选；不得实现前端/API、不得改 provider/accepted latest/monitor/交易链路，也不得使用买卖、仓位、收益承诺、胜率或上涨概率语义。
