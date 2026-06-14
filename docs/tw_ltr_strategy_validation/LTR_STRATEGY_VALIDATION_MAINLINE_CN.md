# LTR 候选策略稳定性验证主线文档

生成日期：2026-06-14

## 1. 背景

LTR rerank + regime + turnover 主线已经完成最终收口，当前状态为：

```text
保留 LTR readonly explanation 最小只读接入；
不恢复 manual review explanation；
不继续扩展推荐/交易/写入链路；
不再围绕原 LTR 收口主线新增功能分支。
```

但 Phase3A2C 的完整日频同口径回放显示，LTR 候选策略具有继续验证的价值：

| 策略 | common full range 费用后收益 | 最大回撤 | 动作数 | 说明 |
| --- | ---: | ---: | ---: | --- |
| `rank_rotate_top50_adaptive_score` | `15.963677` | `-0.402422` | `1932` | 当前最强稳定基线 |
| `phase1c_ltr_simple_daily` | `40.018220` | `-0.387816` | `1978` | 收益最高，但高动作/高换手 |
| `phase1c_ltr_turnover_controlled_daily` | `4.652725` | `-0.199269` | `315` | 防守、低动作、低回撤，但收益牺牲明显 |

分段上：

- 2022 熊市：`phase1c_ltr_turnover_controlled_daily` 为正收益，明显优于 Top50 自适应。
- 2025 / 2026 强势区间：`phase1c_ltr_simple_daily` 收益更强。
- `rank_rotate_top50_adaptive_score` 仍是当前主产品里更成熟、更稳定、更容易解释的基线。

因此，本新主线不继续扩展原 LTR 只读解释，而是单独验证：

```text
LTR simple daily / LTR turnover-controlled daily 是否具备跨年份、滚动窗口、不同市况下的稳定性，
是否有资格在未来成为“可选模拟策略”候选。
```

## 2. 本主线不是做什么

本主线不是：

- 继续扩展原 LTR readonly explanation 收口主线；
- 立即把 LTR 设为默认策略；
- 立即接入前端主推荐；
- 重新训练 LTR；
- 继续调参寻找最好结果；
- 引入法人筹码、融资融券、月营收等新数据；
- 写 provider；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 输出真实买入、卖出、持有、仓位建议；
- 输出收益承诺、胜率承诺或上涨概率。

本主线只做只读研究验证。

## 3. 用户第一性原则

本主线必须始终符合：

1. **简单**：最终只回答“LTR 是否稳定值得作为候选策略”，不要堆复杂模型解释。
2. **准确**：所有比较必须同口径、同日期集合、同价格执行、同费用税费、无 lookahead。
3. **清晰**：区分收益最高、低回撤、低换手、稳定性，不混成一个模糊结论。
4. **实用**：若 LTR 只在部分窗口强，就保留为研究候选；若不稳定，不强行产品化。

## 4. 候选策略与 baseline

### 4.1 必须验证的候选策略

候选策略冻结为：

```text
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

候选策略必须复用已冻结的 Phase1C score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

禁止：

- 重训 LTR；
- 改 Phase1C score；
- 改 Phase1C candidate；
- 用新窗口重新选 LTR 参数；
- 用测试集反向调参。

### 4.2 必须比较的 baseline

至少比较：

```text
rank_rotate_top50_adaptive_score
rank_rotate_top50
rank_rotate_top30
confirmed_exit
```

其中 `rank_rotate_top50_adaptive_score` 是本主线的主基线。

## 5. 回放口径

必须沿用 Phase3A2C 已修复的完整日频组合回放口径：

- 使用产品侧 `TWStockPortfolioReplayService` / `_replay_variant()` 权威路径；
- 使用本地真实日线价格；
- 交易价使用 asof 后第一个真实交易日 close；
- 同一 accepted signal days；
- 与 Phase1C frozen score 日期取交集；
- 所有方法使用共同日期集合；
- 同一初始资金；
- 同一手续费 / 交易税；
- 同一买卖单位；
- 同一最大持仓；
- 同一缺价处理；
- 同一净收益字段：`fee_tax_adjusted_net_return`；
- `gross_return` 若当前引擎不可用，必须明确写 `not_available_in_current_engine`，不得伪造。

必须保留：

- price execution audit；
- data quality report；
- common replay days；
- excluded dates；
- missing price count；
- action count；
- notional turnover proxy。

## 6. 必须验证的时间切片

### 6.1 分年验证

必须按年度输出：

```text
2022
2023
2024
2025
2026 YTD
```

如果某年没有足够 accepted runs 或 Phase1C score，应明确标记：

```text
insufficient_data
```

不得静默跳过。

### 6.2 Rolling window 验证

必须做：

```text
rolling 6 months
rolling 12 months
```

每个窗口输出：

- 窗口起止日期；
- 方法；
- 费用后收益；
- 最大回撤；
- 动作数；
- notional turnover proxy；
- 相对 `rank_rotate_top50_adaptive_score` 的收益差；
- 相对 `rank_rotate_top50_adaptive_score` 的回撤差；
- 相对 `rank_rotate_top50_adaptive_score` 的动作数差；
- 数据状态。

### 6.3 市况分段验证

至少按本地可用 TWII 或既有 market regime 规则分为：

```text
bull / normal / bear
```

如果沿用既有 `normal / caution / risk_off`，必须解释映射关系。

重点回答：

- LTR simple 是否只在牛市强；
- turnover-controlled LTR 是否真的在熊市更抗跌；
- Top50 自适应是否在平稳市更稳定；
- confirmed_exit 是否只是低动作低收益参考。

## 7. 指标

每个方法、每个窗口至少输出：

- `fee_tax_adjusted_net_return`
- `final_equity`
- `max_drawdown`
- `action_count`
- `buy_count`
- `sell_count`
- `fee_and_tax`
- `turnover_proxy_by_notional_over_avg_equity`
- `missing_price_count`
- `trading_days_used`
- `relative_return_vs_top50_adaptive`
- `relative_drawdown_vs_top50_adaptive`
- `relative_actions_vs_top50_adaptive`

不得只报告收益率。

## 8. 稳定性判定

本主线不能因为单一窗口收益高就判定 LTR 胜出。

建议分三类结论：

### 8.1 可以进入可选模拟策略设计

条件建议：

- LTR simple 或 turnover-controlled 在多数 rolling 窗口优于 Top50 自适应；
- 或者收益接近但回撤/动作显著更好；
- 2022 / bear 或 risk_off 分段不显著失效；
- 没有只靠 2025/2026 牛市拉高；
- 动作和换手符合用户可接受范围。

### 8.2 只保留只读研究解释

条件：

- 全区间或部分年份很强，但 rolling 稳定性不足；
- 或者收益强但换手过高；
- 或者低回撤策略收益牺牲过大；
- 仍有价值解释“为什么现在不动”或“激进/防守取舍”。

### 8.3 归档为研究失败/暂缓

条件：

- 大多数 rolling 窗口不如 Top50 自适应；
- 熊市/震荡市明显失效；
- 收益优势来自少数窗口；
- 回撤/换手/费用不可接受。

## 9. 阶段计划

### Phase V0：冻结验证合同

目标：

- 冻结候选策略；
- 冻结 baseline；
- 冻结回放口径；
- 冻结年度、rolling、市况分段；
- 冻结指标；
- 冻结禁止事项；
- 盘点 Phase3A2C 可复用脚本与产物。

Phase V0 不允许：

- 跑新回放；
- 改代码；
- 重训模型；
- 调参；
- 改前端/API；
- 联网或新数据；
- provider / accepted latest / monitor / trading。

产物：

```text
docs/tw_ltr_strategy_validation/PHASEV0_EXECUTION_REPORT_CN.md
```

Gate：

```text
request_phase_v1_yearly_replay_validation
```

或：

```text
stop_strategy_validation_contract_incomplete
```

### Phase V1：分年完整日频回放

目标：

- 按 2022 / 2023 / 2024 / 2025 / 2026 YTD 分年回放；
- 使用 Phase V0 冻结口径；
- 输出同口径表格和审计。

禁止：

- 用结果调参；
- 改候选策略；
- 静默跳过缺数据年份；
- 前端/API 产品化。

Gate：

```text
request_phase_v2_comprehensive_stability_validation
```

或：

```text
stop_ltr_candidate_not_yearly_robust
```

### Phase V2：综合稳定性验证

目标：

- 合并完成 rolling 6M / 12M 与市况分段验证；
- 检查 LTR 是否跨窗口稳定；
- 判断是否只靠少数牛市窗口；
- 检查 bull / normal / bear 或 normal / caution / risk_off 下的稳定性；
- 特别检验 2022 熊市与后续强势行情的差异；
- 明确 LTR simple、LTR turnover-controlled 与 Top50 自适应主基线之间的稳定性取舍。

必须包含：

- rolling 6 months；
- rolling 12 months；
- bull / normal / bear 或 normal / caution / risk_off 市况分段；
- 每个窗口/分段的收益、回撤、动作数、换手、费用后指标；
- 相对 `rank_rotate_top50_adaptive_score` 的 return / drawdown / action delta；
- 数据状态和样本天数；
- 是否只靠少数年份或牛市窗口贡献结果。

禁止：

- 重训 LTR；
- 调参；
- 改候选策略；
- 改 Phase1C score；
- 改 replay 口径；
- 新增数据源或联网；
- provider / accepted latest / monitor / trading；
- 前端/API 产品化。

Gate：

```text
request_phase_v3_user_first_product_design
```

或：

```text
archive_ltr_candidate_as_research_only
```

### Phase V3：用户第一性产品化设计

目标：

- 仅在 Phase V2 综合稳定性验证通过后启动；
- 判断 LTR 候选是否适合作为“可选模拟策略”；
- 设计用户第一性产品契约；
- 明确 LTR 策略与 Top50 自适应主基线的关系；
- 明确前端是否、在哪里、以什么文字展示；
- 明确只读 API / 前端最小接入范围；
- 明确验收和回退条件。

产品设计必须保持：

- 可选：用户主动选择，不自动启用；
- 模拟：只进入模拟/历史验证语境；
- 只读：不写 provider、accepted latest、monitor、交易或仓位；
- 非默认：不替代 `rank_rotate_top50_adaptive_score` 当前主基线；
- 非交易：不输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

Phase V3 不直接实现代码，只冻结产品化契约和下一轮最小实现范围。

Gate：

```text
request_phase_v4_min_optional_sim_strategy_implementation
```

或：

```text
keep_readonly_explanation_only
```

或：

```text
archive_strategy_validation
```

### Phase V4：最小可选模拟策略实现与只读验收

目标：

- 仅在 Phase V3 产品契约通过后启动；
- 按 Phase V3 契约做最小可选模拟策略接入；
- 完成只读 API / 前端 / E2E 验收；
- 确认不会改变默认主基线；
- 确认不会进入交易链路或写入链路；
- 归档最终结论。

允许范围：

- 只读模拟策略选择；
- 只读历史验证展示；
- 明确“可选 / 模拟 / 只读 / 非默认 / 非交易”文案；
- 静态检查和只读 E2E；
- 最终归档文档。

禁止：

- 默认启用 LTR；
- 替换 Top50 自适应主基线；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖、持有、仓位建议；
- 收益承诺、胜率承诺或上涨概率；
- 新数据源、联网、重训或调参。

最终可能结论：

```text
optional_sim_strategy_accepted_readonly_non_default
rollback_to_readonly_explanation_only
archive_strategy_validation
```

## 10. 和现有产品的关系

在本主线完成前：

- `rank_rotate_top50_adaptive_score` 继续是当前稳定主基线；
- LTR readonly explanation 继续保持最小只读接入；
- 不改变首页、台股研究页、模拟账户默认推荐；
- 不新增用户可操作的 LTR 策略按钮；
- 不新增交易动作。

Phase V2 综合稳定性验证通过之前：

- 不允许进入产品化设计；
- 不允许修改前端/API；
- 不允许新增用户可操作策略入口。

Phase V2 通过后，可以在本主线内进入 Phase V3 / V4，但必须继续满足：

- LTR 只能作为可选模拟策略；
- LTR 不得成为默认策略；
- LTR 不得替代 `rank_rotate_top50_adaptive_score` 主基线；
- LTR 不得进入真实交易、仓位、broker、quick-trade、orders、provider、accepted latest 或 monitor 写入链路；
- 页面文案必须明确“只读研究 / 历史模拟 / 不构成投资建议 / 不产生真实执行动作”。

## 11. 执行者第一轮指令

```text
请按 docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md 执行 Phase V0：冻结验证合同。只允许盘点 Phase3A2C 产物与脚本、冻结候选策略、baseline、完整日频回放口径、年度/rolling/市况分段、指标和禁止事项；不得跑新回放、不得重训 LTR、不得调参、不得改前端/API、不得联网或新增数据源、不得触发 provider/accepted latest/monitor/交易链路。执行完提交 docs/tw_ltr_strategy_validation/PHASEV0_EXECUTION_REPORT_CN.md，等待审查。
```

## 12. 审查者第一轮指令

```text
请审查执行者的 docs/tw_ltr_strategy_validation/PHASEV0_EXECUTION_REPORT_CN.md，依据 docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md 确认候选策略、Top50 自适应主基线、完整日频回放口径、年度/rolling/市况分段、指标和安全边界是否冻结清楚，是否避免重训、调参、前端/API、联网、新数据、provider、accepted latest、monitor、交易链路；若通过，请撰写 Phase V1 分年完整日频回放验证工作文档，若不通过，请给出必须修复项并停止。
```

