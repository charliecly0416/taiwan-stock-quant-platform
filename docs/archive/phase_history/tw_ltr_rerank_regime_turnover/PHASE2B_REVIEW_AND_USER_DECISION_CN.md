# Phase 2B Regime Gating 修复审查意见与用户决策文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE2B_REGIME_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

本轮执行者的 Phase2B 修复工作没有发现主线越界：

- 未进入 Stage 4 turnover-controlled portfolio layer；
- 未新增数据源；
- 未新增白名单外 regime 特征；
- 未引入 `trend_score`；
- 未引入 forbidden features；
- 未改 frontend / API / monitor / database；
- 未做 provider refresh / publish；
- 未做 accepted latest switching；
- 未生成真实交易、broker、quick-trade、orders、target position / target weight 语义；
- 未把 regime 输出包装成买卖、仓位、收益承诺、上涨概率或胜率。

但是，Phase2B 没有达到放行 Phase3 的证据门槛。

因此审查结论是：

```text
接受 Phase2B 的停止结论。
不放行 Phase3。
需要回到用户确认下一步方向。
```

---

## 2. 关键证据

执行者最终选中的候选为：

```text
definition_id = balanced_drawdown_breadth
gate_id       = caution_only_c40_r50
score_column  = score_balanced_drawdown_breadth_caution_only_c40_r50
```

该候选是非 no-op，并且 validation selection 没有使用 independent_test 反选参数。

independent_test 总体对照显示：

```text
Phase1C ndcg@30              = 0.541729
Phase2B selected ndcg@30     = 0.542685

Phase1C top30 future rank    = 0.527890
Phase2B selected top30 rank  = 0.528888
```

从总体数字看，Phase2B 没有破坏 Phase1C 的核心 TopK 质量。

但分状态证据显示，selected gate 实际只在 `caution` 生效：

```text
caution:
  date_count = 52
  top30_changed_ratio = 0.0891
  gated_top30_median_qlib_rank: 17 -> 16
  top30_future_excess_delta = +0.0040

risk_off:
  date_count = 15
  top30_changed_ratio = 0.0
  gated_top30_median_qlib_rank: 17 -> 17
  top30_future_excess_delta = 0.0
```

也就是说，当前 gate 没有证明它能在 `risk_off` 状态下产生有效保守过滤。

执行者自己的 `phase2b_gate_summary.json` 也给出：

```text
recommended_gate = stop_regime_gating_insufficient_evidence
not_single_regime_only = false
```

这与审查判断一致。

---

## 3. 对主线的影响

主文档要求 Stage 3 的目标是：

```text
正常环境可以更积极参考 rerank；
差市况时应提高动作门槛，降低错误补仓和追高概率。
```

当前 Phase2B 只证明了 `caution` 下有轻微保守过滤，尚未证明 `risk_off` 下成立。

如果现在直接进入 Phase3，等于把一个仍未成立的 regime layer 当成已完成前提，会造成后续 turnover layer 的解释基础不稳：

```text
用户看到的“不动作原因”可能被解释为 regime gate，
但当前证据并不能支持 risk_off gate 的有效性。
```

因此不能按正常流程放行 Phase3。

---

## 4. 审查者复现

已执行：

```text
python -m py_compile scripts/repair_tw_ltr_phase2b_regime_gating.py
```

结果：通过。

普通沙箱下执行：

```text
python scripts/repair_tw_ltr_phase2b_regime_gating.py
```

遇到环境限制：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

按环境规则提升权限后复跑同一离线脚本，结果通过，输出为：

```text
ok = true
recommended_gate = stop_regime_gating_insufficient_evidence
selected_definition_id = balanced_drawdown_breadth
selected_gate_id = caution_only_c40_r50
```

复现结果与执行报告一致。

---

## 5. Findings

### High：不能放行 Phase3

Phase2B selected gate 虽是非 no-op，但保守过滤证据集中在 `caution`，`risk_off` 下没有实际过滤变化。

这不满足此前 Phase2B 工作文档中“结果不是只靠单一 regime 成立”的放行条件。

### Medium：risk_off 样本仍然偏小

selected definition 在 independent_test 的 `risk_off` 只有 15 个日期，且 selected gate 为 `caution_only_c40_r50`，对 `risk_off` scope 保持 50，实际等同 no-op。

这不能作为差市况 gating 已经有效的证据。

### Low：执行者报告结论清楚

执行者没有强行把轻微总体提升包装成 Phase3 放行理由，而是正确给出：

```text
stop_regime_gating_insufficient_evidence
```

这一点符合主线“证据不足时停止”的原则。

---

## 6. 当前可选方向

因为主文档要求证据不足时回到用户确认，审查者不能直接为执行者下发 Phase3 工作。

用户需要在以下方向中选择一个：

### 方向 A：接受 Phase2/Phase2B 失败收尾

含义：

- 承认当前数据与约束下，Stage 3 regime-aware gating 没有足够证据成立；
- 保留 Phase1C `qlib-preserving LTR rerank` 作为已通过的主线成果；
- 不进入 Phase3；
- 将 regime 结论沉淀为研究失败报告。

这是最严格、最稳健的选择。

### 方向 B：显式放宽 tradeoff 后进入 Phase3

含义：

- 用户明确接受：Stage 3 没有充分成立；
- Phase3 turnover layer 只基于 Phase1C rerank + baseline rule 做组合层回放；
- regime 只能作为诊断字段或解释候选，不得作为已验证 gating 前提；
- 后续不得声称“regime-aware gating 已通过”。

这属于用户显式 tradeoff，不是审查者自动放行。

### 方向 C：再做一次更窄的 risk_off-only 诊断

含义：

- 不进入 Phase3；
- 只检查 risk_off 样本为什么 gate 难以成立；
- 不再新增大搜索、不再调模型、不再引入新数据；
- 输出 risk_off insufficient evidence 的最终收尾依据。

这可以作为 Phase2C，但必须非常窄，避免无限探索。

---

## 7. 给执行者的下一步状态

在用户确认前，执行者不得继续实现 Phase3。

当前给执行者的状态是：

```text
Phase2B 审查通过其停止结论，但不通过 Phase3 放行。
请等待用户选择：
A. Phase2 收尾；
B. 用户显式绕过 regime，以 Phase1C 为基础进入 Phase3；
C. 做一次 risk_off-only 最终诊断。
```

---

## 8. 审查者建议

建议选择方向 B 或 A。

如果目标是继续完成主文档的实用闭环，可以选择方向 B，但文档必须明确：

```text
Phase3 不以已验证 regime gate 为前提，
只以 Phase1C qlib-preserving LTR rerank 为排序输入，
regime 字段只做只读解释/诊断，不作为通过验收的 gating 层。
```

如果目标是严格按证据推进，则选择方向 A。

