# Phase 2C Risk-off-only 诊断审查与 Stage 3 收尾文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE2C_RISK_OFF_ONLY_DIAGNOSIS_REPORT_CN.md`

---

## 1. 审查结论

Phase2C 执行者工作符合本轮边界。

本轮只做了 `risk_off-only` 最终诊断，没有发现：

- 进入 Phase3；
- turnover portfolio layer；
- 组合净值、动作次数、换手、成本回放；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- frontend / API / monitor / database 改动；
- LTR 重新训练；
- `trend_score` 或 forbidden features；
- 白名单外 regime 特征；
- 买入、卖出、持有、仓位、target position / target weight；
- 收益承诺、胜率、上涨概率语义。

审查接受执行者最终结论：

```text
risk_off_gating_not_supported_final
```

因此 Stage 3：Regime-aware gating 正式收尾为：

```text
证据不足，不作为已通过主线层放行。
```

---

## 2. 关键证据

Phase2C 复用 Phase2B aggregate 产物与 Phase1 样本，只使用 5 个 regime 白名单字段：

```text
TWII_ret20
TWII_ret60
market_drawdown60
market_volatility20
market_breadth20
```

Phase2B selected definition：

```text
balanced_drawdown_breadth
```

在 independent_test 的 `risk_off` 样本为：

```text
15 dates / 2245 rows
```

该子样本中 Phase1C 已显著优于 qlib：

```text
qlib ndcg@30      = 0.511355
Phase1C ndcg@30   = 0.558694

qlib top30 future excess rank     = 0.529059
Phase1C top30 future excess rank  = 0.553244
```

这说明问题不是 Phase1C 在 `risk_off` 完全失效，而是进一步 risk_scope 收缩缺乏稳定收益。

---

## 3. risk_scope 诊断

Phase2C 使用已有 Phase2B aggregate 结果进行只读 sensitivity：

```text
risk_scope=50:
  risk_off 无变化

risk_scope=40:
  independent_test changed_ratio = 0.1067
  top30 future excess delta = -0.005785

risk_scope=30:
  independent_test changed_ratio = 0.2244
  top30 future excess delta = -0.024185

risk_scope=20:
  independent_test changed_ratio = 0.2244
  top30 future excess delta = -0.024185
```

结论：

```text
更严格 risk_scope 可以制造 risk_off 过滤变化，
但会伤害 independent_test 的 risk_off Top30 future excess rank。
```

`risk_scope=45/35` 没有补算。审查接受该限制，原因是：

- Phase2B 没有物化这两个 exact scope；
- 当前目录没有保存可直接复用的行级 Phase1C score；
- Phase2C 工作文档明确禁止重新训练 LTR 或重建 Phase1C 行级 score；
- 本轮目标是最终诊断，不是继续参数搜索。

---

## 4. Findings

### High：Stage 3 不成立，不能作为 Phase3 前提

Phase2 / Phase2B / Phase2C 连续证明：

- no-op gate 不能作为有效 regime layer；
- selected non-noop gate 只在 `caution` 下有轻微效果；
- `risk_off` 下 selected gate 无效；
- 更严格 risk_scope 会牺牲核心 TopK；
- risk_off 样本偏少，且不存在稳定证据支持“收缩后不伤害 Phase1C”。

因此不能把 Stage 3 包装成已通过层。

### Medium：Phase2C 的诊断粒度受已保存产物限制

45/35 scope 无法补算，但这不是执行者越界或漏做，而是本轮“禁止重训 / 禁止重建行级 Phase1C”的合理后果。

### Low：报告措辞基本合格

报告明确写出：

```text
risk_off_gating_not_supported_final
```

没有试图用局部指标改善来强推 Phase3。

---

## 5. 安全边界审查

本轮为离线只读诊断。

未发现：

- broker / quick-trade / orders；
- target position / target weight；
- monitor config save / monitor scan / alerts write；
- provider refresh / publish；
- accepted latest switching；
- frontend/API 写入；
- 买卖建议、仓位建议、收益承诺、上涨概率、胜率语义。

安全边界通过。

---

## 6. 验证

已执行：

```text
python -m py_compile scripts/diagnose_tw_ltr_phase2c_risk_off_only.py
```

结果：通过。

普通沙箱下执行：

```text
python scripts/diagnose_tw_ltr_phase2c_risk_off_only.py
```

遇到环境限制：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

按环境规则提升权限复跑同一只读脚本：

```text
python scripts/diagnose_tw_ltr_phase2c_risk_off_only.py
```

结果：通过，输出：

```text
ok = true
final_gate = risk_off_gating_not_supported_final
```

---

## 7. 主线状态

当前主线状态如下：

```text
Stage 1 qlib baseline:
  保留

Stage 2 qlib-preserving LTR rerank:
  Phase1C 成立，作为当前可用 rerank 成果保留

Stage 3 regime-aware gating:
  Phase2 / Phase2B / Phase2C 均未给出充分证据
  正式收尾为证据不足

Stage 4 turnover-controlled portfolio layer:
  不能以“已通过 regime gate”为前提自动进入
```

---

## 8. 下一步给执行者的工作文档

在没有用户进一步确认前，执行者不得继续写 Phase3。

给执行者的下一步是收尾文档化，而不是继续探索：

```text
请撰写 Stage 3 收尾归档，不新增代码：

目标：
  把 Phase2 / Phase2B / Phase2C 的 regime-aware gating 结论归档为证据不足，
  明确当前主线可保留的是 Phase1C qlib-preserving LTR rerank，
  明确 Stage 3 不作为已通过前提进入 Phase4。

允许：
  - 汇总现有报告与产物；
  - 写一个 Stage3 closure markdown；
  - 列出已验证失败原因；
  - 列出后续若用户显式选择 tradeoff 时的边界。

禁止：
  - 新增脚本；
  - 新增数据；
  - 重训模型；
  - 重新调参；
  - 进入 Phase3/Phase4 实现；
  - 改 frontend / API / monitor / database；
  - provider refresh / publish；
  - accepted latest switching；
  - 任何买卖、仓位、收益、概率语义。

必须交付：
  docs/tw_ltr_rerank_regime_turnover/STAGE3_REGIME_GATING_CLOSURE_CN.md

验收：
  - 明确写出 Stage 3 gating 不成立；
  - 明确 Phase1C 仍是保留成果；
  - 明确后续如进入 turnover，必须由用户显式接受“绕过已失败 regime gate”的 tradeoff；
  - 不新增任何代码或实验产物。
```

---

## 9. 审查者建议

建议先让执行者完成 `STAGE3_REGIME_GATING_CLOSURE_CN.md` 归档。

归档完成后，如果用户仍希望继续完成主文档实用闭环，应单独确认一个 tradeoff：

```text
是否允许 Stage4 turnover layer 只以 Phase1C qlib-preserving LTR rerank 为输入，
并把 regime 仅作为只读诊断字段，而不是已验证 gating 层？
```

在这个确认前，不应继续 Phase4。

