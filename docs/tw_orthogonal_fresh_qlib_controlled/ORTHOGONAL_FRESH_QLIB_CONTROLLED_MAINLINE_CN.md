# Orthogonal Fresh Qlib 受控实验主线

生成日期：2026-06-15

## 1. 主线目标

本主线只做一件事：

```text
在严格复刻 fresh qlib baseline 训练/评测合同的前提下，
只把已经通过 PIT 审计的法人筹码与融资融券正交特征加入 qlib 特征层，
训练 Orthogonal Fresh Qlib，
并与原 fresh qlib baseline 做同口径比较。
```

主问题：

```text
正交数据放进 qlib 第一阶段模型后，是否比原 fresh qlib 更好？
```

本主线不是：

- 不训练 LTR；
- 不做 fresh qlib + LTR stacking；
- 不新增月营收 YoY；
- 不新增其他数据源；
- 不做 filter / market gate / turnover rule；
- 不改默认前端策略；
- 不接 provider refresh / publish / accepted latest；
- 不接 monitor / broker / orders / quick-trade。

若执行中发现必须改变训练窗口、标签、模型参数、universe、回放规则或数据源，必须停止并让用户确认。

## 2. 背景

前序结论：

- `fresh qlib / rank_rotate_top50_adaptive_score` 当前继续保留为默认研究基线；
- O4 orthogonal LTR 相对旧 simple LTR 有增益，但与 repaired fresh qlib 同口径比较后差异很小；
- 正交数据在 LTR 中确实被模型使用，说明法人筹码与融资融券可能有信息增量；
- 下一步应验证：这些正交数据是否更适合前移到 qlib 第一阶段模型。

因此本主线必须以 fresh qlib 为 control，而不是以 Phase1C simple LTR 为 control。

## 3. Control：原 fresh qlib baseline 合同

Control 必须复刻原 S2B/S2D fresh qlib baseline。

冻结训练窗口：

```text
train:      2017-01-10..2024-12-31
validation: 2025-01-01..2025-06-30
test:       2025-07-01..2026-05-07
```

冻结 qlib handler / fit：

```text
handler_start: 2015-05-04
handler_end:   2026-05-07
fit_start:     2015-05-04
fit_end:       2024-12-31
```

冻结 provider：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

冻结 universe / post-score filter：

```text
handler instruments = all
post-score filter = tw_liquid_dyn as-of active instrument range
same-day price
>=60 history
trailing 60-day value top150
```

冻结模型家族：

```text
qlib.contrib.model.gbdt.LGBModel
原 S2B fresh qlib model params
线程阶梯 4 -> 2 -> 1
```

冻结回放口径：

```text
strategy: fresh_qlib_top50_adaptive_baseline
window: validation + untouched test
test focus: 2025-07-01..2026-05-07
execution: next-day execution
initial_equity: 1000000
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
candidate_k: 50
```

Control artifact 参考：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/
```

## 4. Treatment：Orthogonal Fresh Qlib 唯一允许变化

Treatment 唯一允许变化：

```text
在 qlib 特征层追加 PIT-safe 法人筹码与融资融券正交特征。
```

允许使用的正交特征来源：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/
```

特别是：

```text
normalized_feature_daily.csv
feature_dictionary.csv
pit_leakage_audit.csv
pit_lineage_audit.csv
```

可用数据族：

```text
TaiwanStockInstitutionalInvestorsBuySell
TaiwanStockMarginPurchaseShortSale
```

禁止：

- 月营收 YoY；
- 估值数据；
- 其他 FinMind dataset；
- 新技术指标；
- 新市场状态指标；
- 改 label；
- 改模型参数；
- 改训练窗口；
- 改 universe；
- 删除样本；
- 因缺失而过滤股票；
- 改 replay 规则。

## 5. PIT 与缺失处理合同

沿用 O1R/O2 已确认合同：

```text
PIT-safe delayed availability
available_at >= next_trading_day(trade_date)
```

Treatment 必须按真实 `available_at` 做 as-of join。

硬约束：

- 不得人工提前 `available_at`；
- 不得把 delayed rows 当作 exact T+1；
- 不得用 test 后数据修正 test 内特征；
- 每行保留 `delay_days` / `delay_reason` / lineage；
- 缺失值 neutral fill；
- 每个正交特征族保留 missing flag；
- 不得因为正交特征缺失删除原 fresh qlib 样本或股票。

## 6. 为什么不是直接做 LTR stacking

本主线不做：

```text
fresh qlib + orthogonal LTR
```

原因：

- 当前问题是验证正交数据是否应进入第一阶段 qlib；
- 若同时训练 qlib 与 LTR，会无法判断增益来源；
- LTR stacking 涉及时序错开、OOS score provenance 和二阶段泄漏审计，应该作为后续独立主线。

## 7. 阶段设计

### Phase Q0：Control 与 Orthogonal Feature 合同冻结

目标：

```text
冻结原 fresh qlib control 合同，并确认 O2 正交特征可用于 qlib 训练样本。
```

执行内容：

- 读取 S2B/S2D fresh qlib control artifact；
- 复核 train/validation/test；
- 复核 qlib config / provider / model params；
- 复核 O2 正交特征字典；
- 复核 PIT-safe delayed availability 合同；
- 输出 treatment 允许新增列白名单；
- 输出禁止变化清单。

输出：

```text
PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_q0_control_and_orthogonal_feature_contract_frozen
```

停止条件：

- 找不到原 fresh qlib control artifact；
- 训练窗口或模型参数无法确认；
- O2 正交特征 lineage / PIT 审计不完整；
- 需要新增数据源或新特征族。

### Phase Q1：Qlib 正交特征接入方案与样本对齐

目标：

```text
在不改 fresh qlib 原有 Alpha158 特征、label、split、universe 的前提下，
把正交特征拼接成 qlib 可训练数据。
```

执行内容：

- 设计 qlib handler / dataset 接入方式；
- 保留原 Alpha158 feature；
- 追加正交 feature；
- 对齐 `instrument + datetime`；
- 输出 schema diff；
- 输出 row alignment audit；
- 输出 missing report；
- 输出 PIT leakage audit；
- 不训练模型。

输出：

```text
PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_q1_orthogonal_qlib_feature_join_passed
```

硬性要求：

```text
control_label == treatment_label
control_split == treatment_split
control_universe_policy == treatment_universe_policy
only_added_columns == approved_orthogonal_features_and_missing_flags
```

停止条件：

- qlib handler 无法安全接入外部特征；
- 需要改 label 或 split；
- 需要删行；
- 特征 join 出现未来函数风险；
- 原 Alpha158 特征被改动。

### Phase Q2：Orthogonal Fresh Qlib 训练

目标：

```text
用原 fresh qlib 训练合同训练 Orthogonal Fresh Qlib。
```

执行内容：

- 使用原 S2B 模型家族；
- 使用原 S2B 模型参数；
- 使用同 train/validation/test；
- 使用同 provider / universe / post-score filter；
- 只新增 Q1 通过的正交特征；
- 输出 raw score rank；
- 输出 post-filter score rank；
- 输出 feature importance；
- 输出 resource / leakage / forbidden action audit。

输出：

```text
PHASEQ2_ORTHOGONAL_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_q2_orthogonal_fresh_qlib_training_completed
```

停止条件：

- OOM 后不能在 4 -> 2 -> 1 线程阶梯完成；
- 必须改模型参数才能跑通；
- 必须缩小 universe；
- 必须改变 split / label / feature family；
- feature importance 显示正交特征完全未进入或全部为常量，需报告但不一定阻塞。

### Phase Q3：同口径回放对比

目标：

```text
用同一回放引擎比较 Orthogonal Fresh Qlib 与原 Fresh Qlib。
```

必须比较：

```text
fresh_qlib_top50_adaptive_baseline
orthogonal_fresh_qlib_top50_adaptive
```

建议保留审计参考：

```text
O4 orthogonal LTR
Phase1C simple LTR
```

但主结论只基于：

```text
Orthogonal Fresh Qlib vs 原 Fresh Qlib
```

输出指标：

- validation；
- untouched test；
- 2025H2；
- 2026YTD；
- rolling 6m；
- market regime；
- fee/tax adjusted net return；
- max drawdown；
- action_count；
- turnover_proxy；
- fee_and_tax；
- next-day accounting；
- coverage；
- PnL contribution；
- feature importance summary。

输出：

```text
PHASEQ3_ORTHOGONAL_FRESH_QLIB_REPLAY_EXECUTION_REPORT_CN.md
```

Gate：

```text
phase_q3_orthogonal_fresh_qlib_replay_completed
```

停止条件：

- 回放引擎口径不一致；
- 原 fresh qlib 指标无法复现；
- coverage 不公平且无法解释；
- next-day accounting 违规；
- 只报告收益不报告回撤/动作/换手。

### Phase Q4：审查与决策

目标：

```text
判断 Orthogonal Fresh Qlib 是否值得进入只读产品设计或默认策略讨论。
```

推荐通过标准：

必须至少满足：

- validation 不明显劣于原 fresh qlib；
- untouched test 收益高于原 fresh qlib，或收益相近但回撤/动作/换手明显更优；
- max drawdown 不明显恶化；
- action_count / turnover 不明显恶化；
- 增益不是单一股票或单一日期贡献；
- PIT / feature join / accounting 无阻断；
- 正交特征确实有可解释贡献。

如果通过：

```text
进入只读产品化设计，不直接改默认。
```

如果不通过：

```text
收尾为研究结论，保留 feature builder 与实验产物，不进入默认策略。
```

输出：

```text
PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_REVIEW_CN.md
```

Gate 示例：

```text
orthogonal_fresh_qlib_supported_for_readonly_candidate
orthogonal_fresh_qlib_not_supported_vs_fresh_qlib
orthogonal_fresh_qlib_blocked_by_data_or_contract
```

## 8. 用户第一性原则

本主线必须服务于一个简单问题：

```text
加入法人筹码和融资融券后，fresh qlib 是否真的更有用？
```

不得把结果包装成：

- 真实交易建议；
- 收益承诺；
- 胜率；
- 上涨概率；
- 自动买卖；
- 目标仓位；
- 目标权重。

最终若产品化，只能展示：

```text
历史只读对比；
默认策略是否保持；
新增正交数据是否带来改善；
收益、回撤、动作次数、换手的取舍；
为什么这不是交易建议。
```

## 9. 执行者报告要求

每个 Phase 必须输出报告到：

```text
docs/tw_orthogonal_fresh_qlib_controlled/
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- 输入/输出路径；
- row count；
- 日期范围；
- symbol 覆盖；
- schema diff；
- PIT 审计；
- 是否改变 control 合同；
- 是否触发停止条件；
- 下一步建议。

## 10. 审查者报告要求

审查者每轮必须检查：

- 是否只改变正交特征；
- 是否保持原 fresh qlib 训练窗口；
- 是否保持原 qlib 模型参数；
- 是否保持原 label / split / universe；
- 是否没有引入 LTR；
- 是否没有新增 filter / market gate / turnover rule；
- 是否没有改前端/API/provider/accepted latest/monitor/交易链路；
- 是否符合用户第一性原则。

审查结论只能是：

```text
通过，允许进入下一 Phase
不通过，指出问题
需要用户确认
```

## 11. 给执行者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/ORTHOGONAL_FRESH_QLIB_CONTROLLED_MAINLINE_CN.md 执行 Phase Q0：冻结原 fresh qlib baseline 训练/回放合同，并确认 O2 PIT-safe 法人筹码与融资融券特征可作为唯一新增变量；不得训练、调参、改 split/label/universe/model、引入 LTR、改前端/API/provider/accepted latest/monitor 或触发交易链路。
```

## 12. 给审查者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/ORTHOGONAL_FRESH_QLIB_CONTROLLED_MAINLINE_CN.md 审查执行者 Phase Q0 报告，重点确认原 fresh qlib control 合同是否完整冻结、O2 正交特征是否 PIT-safe 且为唯一新增变量、是否没有引入 LTR 或任何额外规则，并判断是否允许进入 Phase Q1。
```
