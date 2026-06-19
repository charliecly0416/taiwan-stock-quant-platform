# Phase S2D 审查意见与 Phase S2E Fresh Retrain Conclusion 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2D_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2C_REVIEW_AND_PHASES2D_FULL_DAILY_REPLAY_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2D 通过，允许进入 Phase S2E fresh retrain conclusion review。`

通过理由：

- S2D 已完成 validation 与 untouched test 的完整日频历史回放；
- validation 与 test 分开报告，未混写；
- 五个候选策略齐全：
  - `fresh_qlib_top50_adaptive_baseline`
  - `fresh_rank_rotate_top50`
  - `fresh_confirmed_exit`
  - `fresh_ltr_simple`
  - `fresh_ltr_turnover_controlled`
- 指标包含收益、回撤、动作、买卖次数、费用、换手、相对收益、相对回撤、相对动作；
- S1B6R next-day accounting 已保持；
- turnover-controlled config 复用冻结配置，未在 validation/test 上重选；
- coverage 差异已披露；
- 未训练、未调参、未新增策略变体、未决定默认策略；
- 未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

允许进入：

```text
Phase S2E fresh retrain conclusion review
```

不允许直接进入：

```text
frontend/API integration
default strategy product switch
provider refresh/publish
accepted latest switching
monitor
trading chain
```

---

## 2. 关键结果

### 2.1 Full validation

| method | net_return | max_drawdown | actions | relative_return_vs_top50 |
| --- | ---: | ---: | ---: | ---: |
| fresh_qlib_top50_adaptive_baseline | 0.038270 | -0.151349 | 226 | 0.000000 |
| fresh_rank_rotate_top50 | -0.010622 | -0.167158 | 226 | -0.048892 |
| fresh_confirmed_exit | -0.001010 | -0.167158 | 226 | -0.039280 |
| fresh_ltr_simple | -0.057453 | -0.310589 | 226 | -0.095723 |
| fresh_ltr_turnover_controlled | -0.023366 | -0.285770 | 36 | -0.061636 |

解释：

- validation 不支持 fresh LTR 优于 top50 baseline；
- turnover-controlled 的动作数显著更低，但收益和回撤都不支持默认化。

### 2.2 Full test

| method | net_return | max_drawdown | actions | relative_return_vs_top50 |
| --- | ---: | ---: | ---: | ---: |
| fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 | 0.000000 |
| fresh_rank_rotate_top50 | 0.637989 | -0.080952 | 409 | -0.024468 |
| fresh_confirmed_exit | 0.668523 | -0.081340 | 409 | 0.006066 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 | -0.118076 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 | -0.047398 |

解释：

- untouched test 中 `fresh_confirmed_exit` 略高于 top50 adaptive；
- `fresh_qlib_top50_adaptive_baseline` 本身表现强；
- `fresh_ltr_simple` 明显低于 top50，且回撤更差；
- `fresh_ltr_turnover_controlled` 动作数和换手显著低，但 full test 收益低于 top50，回撤也更差。

### 2.3 Rolling / segment caveat

rolling 6m 中，turnover-controlled LTR 有部分窗口优于 top50，但 full validation 与 full test 不支持把 LTR 作为 fresh default。

regime 分段中部分小样本段标记为 `sample_too_small`，S2E 结论不得过度解释这些小段。

---

## 3. Findings

### Medium 1：S2 fresh retrain 不支持 LTR default candidate

S1 旧窗口验证支持 LTR 方法继续进入 S2，但 S2 fresh retrain full validation/test 结果没有支持 LTR 默认化：

- validation：LTR simple / turnover-controlled 都低于 top50；
- test：LTR simple / turnover-controlled 都低于 top50；
- turnover-controlled 的低动作优势真实存在，但不足以覆盖收益与回撤劣势。

S2E 不得写：

```text
fresh_retrain_ltr_default_candidate_supported
```

除非用户明确接受“牺牲收益换低动作”的产品 tradeoff；这属于用户取舍，不能由执行者自动决定。

### Low 1：S2D 报告正文未展示 relative_drawdown/actions，但产物已包含

`phase_s2d_replay_metrics_by_strategy.csv` 已包含：

```text
relative_drawdown_vs_fresh_top50_adaptive
relative_actions_vs_fresh_top50_adaptive
```

因此不要求重写 S2D，但 S2E 结论必须引用完整指标，不只看收益率。

### Low 2：安全边界通过

未发现以下越权：

- frontend/API 修改；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 真实买卖建议、收益承诺、胜率承诺或上涨概率承诺；
- 新数据源或联网。

---

## 4. Gate

S2D gate 接受：

```text
s2d_full_daily_replay_pass_request_s2e_fresh_retrain_conclusion_review
```

下一轮执行：

```text
Phase S2E fresh retrain conclusion review
```

---

## 5. Phase S2E 工作目标

S2E 只回答一个问题：

```text
结合 S1 split-aligned 公平验证与 S2 fresh retrain validation/test，当前主线应给出哪个研究结论 gate？
```

S2E 是研究结论轮，不是产品实现轮。

审查者可接受的 S2 gate 只能来自主线：

```text
fresh_retrain_ltr_default_candidate_supported
fresh_retrain_qlib_or_top50_default_supported
fresh_retrain_inconclusive
fresh_retrain_data_or_leakage_blocked
```

---

## 6. Phase S2E 必须完成

执行者必须：

1. 汇总 S1 与 S2 的关系：
   - S1 旧窗口公平验证支持 LTR 方法继续验证；
   - S2 fresh retrain 是当前可用性验证；
   - 不得把 S1 旧窗口胜出包装成 fresh 当前默认。

2. 汇总 S2D full validation/test：
   - full validation；
   - full test；
   - 2025H2；
   - 2026YTD；
   - rolling 6m；
   - regime caveat。

3. 判断默认候选：
   - 若按完整证据，当前更合理的研究结论应倾向 `fresh_retrain_qlib_or_top50_default_supported`；
   - 若执行者认为应支持 LTR default，必须明确指出这是牺牲收益/回撤换低动作的 tradeoff，并停止等待用户确认；
   - 若发现数据、accounting、coverage 或泄漏问题，必须改为 blocked，不得继续。

4. 写清楚 LTR 的合理定位：
   - `fresh_ltr_simple` 不支持默认；
   - `fresh_ltr_turnover_controlled` 可保留为低动作研究候选；
   - 不得称其收益更优或更稳。

5. 写清楚下一步建议：
   - 如果结论为 qlib/top50 默认支持，可进入 S3 只读产品决策设计；
   - S3 仍不得直接改前端/API，必须先写产品展示合同；
   - LTR 可以作为研究候选保留，不作为默认。

---

## 7. Phase S2E 禁止事项

本轮禁止：

- 训练 qlib；
- 训练 LTR；
- 跑新回放；
- 调参或参数搜索；
- 重选 turnover config；
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

## 8. Phase S2E 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion/
```

必须产物：

```text
phase_s2e_s1_s2_evidence_summary.json
phase_s2e_default_candidate_decision_matrix.csv
phase_s2e_ltr_positioning_note.json
phase_s2e_forbidden_action_audit.json
phase_s2e_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2E_FRESH_RETRAIN_CONCLUSION_EXECUTION_REPORT_CN.md
```

---

## 9. Phase S2E 通过条件

只有全部满足时，才允许进入 S3：

```text
s1_s2_relationship_explained = true
validation_and_test_evidence_summarized = true
default_candidate_gate_is_one_of_mainline_allowed_gates = true
ltr_not_overclaimed = true
low_turnover_tradeoff_not_auto_selected = true
no_new_training_or_replay = true
no_parameter_search = true
no_new_strategy_variant = true
no_provider_refresh_publish = true
no_accepted_latest_switching = true
no_frontend_or_api = true
no_monitor_or_trading_chain = true
```

通过 gate 之一：

```text
fresh_retrain_qlib_or_top50_default_supported
fresh_retrain_inconclusive
fresh_retrain_data_or_leakage_blocked
```

若执行者给出：

```text
fresh_retrain_ltr_default_candidate_supported
```

必须同时提供用户 tradeoff 确认请求，不得自动进入 S3。

---

## 10. 给执行者的一句话

请执行 Phase S2E：只基于 S1 与 S2D 既有证据做 fresh retrain 结论审查，明确当前是否应给出 `fresh_retrain_qlib_or_top50_default_supported`、`fresh_retrain_inconclusive` 或 blocked；不得训练、回放、调参、重选 turnover config、改前端/API 或把 LTR 低动作优势包装成收益更优。
