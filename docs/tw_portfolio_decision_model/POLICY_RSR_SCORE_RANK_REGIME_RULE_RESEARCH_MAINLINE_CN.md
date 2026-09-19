---
created_at: 2026-06-27
status: coordinator_mainline
route: POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH
production_allowed: false
readonly_only: true
model_training_authorized: false
order_or_target_output_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
depends_on_rcpt15: not_blocking
---

# POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN

## 1. 主线目标

本主线开一条新的、轻量的规则研究线：

```text
POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH
```

目标是在不训练新 policy model、不替代 qlib / qlib+LTR ranking、不改 production 默认策略的前提下，系统研究以下可解释规则是否能带来更好的收益/回撤 tradeoff：

1. score 绝对值与 score 分桶；
2. score 分布形态和 score gap；
3. rank momentum / rank reversal；
4. market regime / TWII MA / drawdown / volatility；
5. holding-aware exit / re-entry；
6. 多买多卖但受成本和换手约束的 action budget。

本主线不是复活已关闭的 ML/RL policy 路线，也不是继续在 RAL-FPA 原线调参。它是新的 coordinator-owned route，必须从诊断、预声明、回放、稳健性、closure 分步执行。

## 2. 项目背景

当前项目已有较强信号体系：

```text
baseline = 2018-2022 qlib + 2023-2025 orthogonal LTR
```

此前已经完成：

- ML/RL/free-allocation policy 研究 closure：继续训练独立 policy model 的短期性价比不高；
- RAL/FPA action attribution 研究 closure：oracle 空间存在，但预声明 full-path rule sanity 未通过；
- RCPT 风险控制阈值路线：找到防守型候选 RULE_05，但它不是收益增强策略；
- RCPT7 adaptive-score-aligned closure：存在保留大部分收益并降低回撤的 qlib-only research candidate，但不授权 production；
- RCPT15 daily auto orthogonal batch 生产化接近收尾，剩余 R19B 自动 full cron 观察尾巴，不阻塞本规则研究。

因此，本主线的定位是：

```text
聚焦 policy 层的显式规则，而不是继续训练黑盒 policy。
```

## 3. 研究依据

本主线参考以下研究思想，但必须本地化到台湾股票、现有 qlib/LTR 信号、交易成本和 readonly replay 合同。

### 3.1 技术交易规则与移动平均

经典技术交易规则研究，例如 Brock, Lakonishok, and LeBaron (1992) 对移动平均和 trading-range breakout rules 做统计检验；Lo, Mamaysky, and Wang (2000) 用非参数方法研究技术形态的统计信息。这类工作支持我们把 TWII MA、趋势、回撤、波动作为 market regime 特征，但也提醒必须防止 data-snooping。

### 3.2 Momentum / Contrarian 与 rank change

Jegadeesh and Titman (1993) 的 cross-sectional momentum、Moskowitz/Ooi/Pedersen (2012) 的 time-series momentum，以及后续关于短期 momentum / 长期 contrarian 的研究，支持我们研究：

- rank 连续改善；
- rank 快速恶化；
- score/rank 短期动量；
- 高 score 追涨在不同 regime 下可能失效。

本项目不能直接照搬 long-short momentum，因为台湾股票池、做空、持仓、手续费、交易税和现有 baseline 都不同；只能把 momentum/contrarian 思想映射为 long-only candidate selection / exit gate。

### 3.3 Market regime / market timing

市场状态识别和 market timing 文献说明，移动平均、drawdown、volatility 等规则可能有信息，但容易过拟合。本主线因此要求：

- 先分桶诊断；
- 再冻结规则；
- 再 replay；
- 再跨窗口稳健性；
- 不允许用 replay PnL 反向调阈值。

### 3.4 交易成本与 no-trade zone

交易成本相关研究强调，交易频率和 rebalance threshold 会显著影响净收益。对本项目尤其重要，因为台湾市场有手续费和交易税，且 baseline 已经较强。

因此多买多卖不是默认开放，而是必须通过：

```text
max_buy_count / max_sell_count
turnover budget
min_score_gap
no-trade zone
fee/tax gate
```

来控制。

## 4. 核心假设

本主线只允许围绕以下预设假设研究，不允许执行者临场新增大方向。

### H1 Score Bucket Regime

同一个 score 区间在不同 market regime 下含义不同。

重点验证：

```text
大盘弱势时，score 0.4-0.8 的股票未来收益可能优于 score > 0.8；
大盘强势时，高 score 可能更有效；
score 分布压缩时，Top score 的区分度可能下降。
```

### H2 Rank Momentum / Rank Deterioration

rank 改善/恶化可能比单日 rank 更能解释买卖决策。

重点验证：

```text
rank_1d_delta / rank_3d_delta / rank_5d_delta
连续 N 日改善
高 rank 但 rank_delta 恶化
中等 score 但 rank 持续上升
```

### H3 Market Regime Gating

baseline 在 risk-off 仍机械买卖，因此下跌年暴露过高。market regime 可用于调整参与度、买入阈值和卖出优先级。

重点 regime：

```text
risk_on
risk_neutral
risk_off
crash
```

### H4 Multi-buy / Multi-sell With Cost Gate

baseline 每日最多一买一卖可能限制收益捕捉；但无约束多交易会提升手续费和交易税。

本主线允许研究多买多卖，但必须满足：

```text
每日 max_buy_count / max_sell_count 固定；
只在 score/rank evidence 强时扩大 action budget；
risk_off 自动收缩 action budget；
fee/tax-adjusted return gate 必须通过；
turnover 不能成为伪提升来源。
```

### H5 Holding-aware Rules

策略不应只看今日候选，还应看当前持仓状态：

- 已持有且 rank 恶化；
- 已持有但仍处于 score support 区间；
- 未持有但 rank/score 同步改善；
- 跌出 candidate boundary 的持仓是否一次性卖出或分批退出。

## 5. 非目标

本主线明确不做：

- 不训练 ML/RL/DL policy；
- 不重训 qlib；
- 不重训 LTR；
- 不修改 daily auto update；
- 不等待 RCPT15 全量覆盖才开始 qlib-only 诊断；
- 不直接使用 2023-2025 LTR 训练集数据做最终 strict test；
- 不输出真实订单；
- 不输出 target_position / target_weight / quantity instruction；
- 不接 broker / quick-trade；
- 不 provider publish；
- 不 accepted latest switch；
- 不修改前端默认策略；
- 不把 diagnostic/smoke 结果包装为生产收益结论。

## 6. 数据与窗口原则

### 6.1 第一阶段使用 qlib-only

第一轮使用 qlib-only frozen signal，理由：

- 避免 2023-2025 LTR 训练集复用争议；
- 与 RCPT 风险控制路线保持可比；
- 更适合先验证规则机制是否存在；
- 若 qlib-only 都无机制，再上 qlib+LTR 没意义。

### 6.2 后续 qlib+LTR 适配

仅当 qlib-only 规则通过机制和稳健性 gate，才允许开 qlib+LTR adaptation 子阶段。

qlib+LTR 适配必须另行冻结：

- signal lineage；
- train/valid/test 边界；
- 是否只做 shadow/diagnostic；
- 是否存在 LTR 训练集复用；
- 是否允许 strict OOS。

### 6.3 窗口语义

建议窗口：

```text
2022 = downturn validation diagnostic，不是 strict OOS
2021 = pre-2022 sanity diagnostic
2023-2025 qlib-only = strict OOS candidate if lineage permits
```

执行者不得把 2022 说成 strict OOS，也不得把 2023-2025 qlib-only 结果偷换成 qlib+LTR 结果。

## 7. 合同与边界

必须遵守：

- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

策略实现如进入 OrderIntent 阶段，必须通过：

```text
ModelSignalArtifact + PortfolioState + StrategyRuleConfig
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
```

不得直接在 replay 脚本里偷偷实现规则并跳过 OrderIntentArtifact。

## 8. Phase Plan

### RSR0 Contract And Data Readiness

目标：

- 冻结本主线；
- 确认可用 qlib-only signal、baseline replay、price、TWII/market features、portfolio state；
- 确认可构造 score bucket、rank delta、market regime、holding state；
- 不跑收益规则，不调阈值。

输出：

- `POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md`
- `POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md`
- data readiness manifest
- feature availability audit

通过条件：

- 关键输入可追溯；
- PIT / available_at 可解释；
- 不能读取 future return 做决策；
- 可以构造诊断 dataset。

### RSR1 Score / Rank / Regime Attribution Diagnostic

目标：

构造只读 attribution dataset，观察但不下结论：

- score buckets；
- rank delta buckets；
- market regime buckets；
- holding / non-holding；
- forward return 仅作为标签/诊断输出，不得作为策略输入；
- action opportunities；
- fee/tax/turnover context。

输出：

- attribution dataset；
- bucket summary；
- regime summary；
- monotonicity / stability report；
- missingness / PIT audit；
- `POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md`
- review + RSR2 work doc。

通过条件：

- 至少能回答 H1/H2/H3 是否有可观察机制；
- 若没有机制，主线应 closure，不得硬造规则；
- 若有机制，只允许进入 RSR2 预声明规则冻结。

### RSR2 Predeclared Rule Contract

目标：

基于 RSR1 的稳定机制，冻结少量规则，不超过 5 个。

允许规则族：

1. score bucket gate；
2. rank momentum buy gate；
3. rank deterioration sell gate；
4. market regime action budget；
5. score/rank/regime interaction。

必须冻结：

- strategy_rule name；
- required fields；
- score bucket thresholds；
- rank delta thresholds；
- market regime definition；
- max_buy_count / max_sell_count；
- sell boundary；
- buy ordering；
- no-trade zone；
- diagnostic_only flag；
- expected tradeoff；
- pass/fail gates。

输出：

- `configs/strategy_dependencies/{rule}.yaml` 草案或合同表；
- predeclared rule spec；
- reviewer checklist；
- `POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md`
- `POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md`

通过条件：

- 规则数量有限；
- 阈值来自 RSR1 机制，不来自 replay PnL 搜索；
- 无未来数据；
- 无 production/default 切换。

### RSR3 OrderIntent Builder And Parity Smoke

目标：

实现或生成规则的 `OrderIntentArtifact`，先不做正式收益结论。

要求：

- 每个 rule 输出标准 OrderIntentArtifact；
- forbidden field audit pass；
- max buy/sell count 生效；
- diagnostic/smoke 标记正确；
- baseline parity smoke 能复现既有 baseline action 边界。

输出：

- OrderIntentArtifact samples；
- strategy decision audit；
- forbidden action audit；
- validator output；
- `POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md`
- review + RSR4 work doc。

通过条件：

- 合同通过；
- 不含 broker/order/target/quantity；
- replay 尚不作为收益结论。

### RSR4 Predeclared Readonly Replay

目标：

对 RSR2 冻结规则跑 readonly replay。

要求：

- 使用统一 replay engine；
- 使用同一 baseline；
- next-day execution；
- fee/tax gate；
- turnover gate；
- cash / concentration audit；
- missing price audit；
- no future leakage audit。

输出：

- ReplayResultArtifact；
- candidate vs baseline summary；
- action attribution；
- fee/tax/turnover summary；
- `POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md`
- review + RSR5 work doc。

通过 gate：

规则必须至少满足一个明确可接受类型：

```text
Type A: 收益增强
net_return_after_fee_tax > baseline + material_margin
max_drawdown 不显著恶化
turnover / fee_tax 不失控

Type B: 防守 tradeoff
net_return_after_fee_tax 不低很多
max_drawdown 明显改善
cash/no-trade 不是主要伪改善来源

Type C: regime-specific candidate
只在预声明 regime 生效
整体不伤害太大
机制稳定且 action count 足够
```

不得接受：

- baseline clone；
- all-cash/no-trade；
- 高 turnover 伪收益；
- 只在单一窗口有效；
- fee/tax 漏算；
- 使用 replay PnL 后验调参。

### RSR5 Robustness And Ablation

目标：

对 RSR4 通过候选做窄稳健性：

- 2021 sanity；
- 2022 downturn diagnostic；
- 2023-2025 qlib-only strict candidate；
- parameter neighborhood stability；
- action-level attribution；
- market regime ablation；
- multi-buy/multi-sell ablation；
- transaction cost sensitivity。

输出：

- robustness summary；
- ablation matrix；
- pass/fail classification；
- `POLICY_RSR5_ROBUSTNESS_AND_ABLATION_EXECUTION_REPORT_CN.md`
- review + closure work doc。

通过条件：

- 不是单点阈值偶然；
- 不是 baseline equivalent；
- 不是纯 cash；
- 不是只靠降低参与度；
- 明确收益/回撤/成本 tradeoff。

### RSR6 Closure

目标：

最终 closure：

- 若无候选通过，关闭主线；
- 若有 qlib-only research candidate，通过 research closure；
- 若候选足够强，才允许另开 qlib+LTR adaptation design；
- 不允许直接 production。

输出：

- `POLICY_RSR6_SCORE_RANK_REGIME_RULE_RESEARCH_CLOSURE_REVIEW_CN.md`
- final candidate table；
- deployment boundary；
- future route recommendation。

## 9. Gate Definitions

### 9.1 Material Margin

执行者不得自行定义。RSR2 必须冻结。

建议初始定义：

```text
收益增强：net_return_after_fee_tax 至少高于 baseline 2-3 个百分点，且跨窗口方向一致。
防守 tradeoff：收益损失不超过 baseline 的 10-15% 相对收益，同时 max_drawdown 改善至少 20% 相对幅度。
```

若项目已有更严格 gate，以既有 gate 为准。

### 9.2 Participation Gate

必须避免：

```text
candidate 只是不交易；
candidate 只在极少数日期交易；
candidate action 与 baseline 几乎完全一样。
```

RSR2 必须冻结：

- min_action_change_rate；
- min_active_days；
- max_cash_rate；
- max_cash_gt_90pct_day_share。

### 9.3 Turnover / Cost Gate

多买多卖候选必须报告：

- buy_count；
- sell_count；
- turnover proxy；
- fee；
- tax；
- fee_tax_delta；
- net vs gross gap。

高 turnover 候选必须在 net after fee/tax 上通过，不接受 gross-only。

## 10. Executor Rules

执行者必须：

- 每阶段只执行当前 work doc；
- 先读 mainline 和合同；
- 保留 artifact manifest；
- 报告输入 lineage；
- 报告 forbidden action audit；
- 不新增未授权规则族；
- 不使用 future return 做策略输入；
- 不把 diagnostic 结果说成 production；
- 写 execution report。

执行者不得：

- 训练模型；
- 调参到 replay 过关；
- 改 daily auto；
- 改 accepted latest；
- 改 provider publish；
- 改 frontend default；
- 输出订单/仓位/权重/数量。

## 11. Reviewer Rules

审查者必须：

- 独立检查执行报告；
- 抽查 artifact；
- 检查 PIT / leakage；
- 检查 threshold 是否预声明；
- 检查是否 baseline equivalent；
- 检查 fee/tax；
- 检查 cash/no-trade；
- 检查 forbidden action；
- 给出 PASS / PASS_WITH_CONDITIONS / FAIL_NEEDS_REPAIR / STOP；
- 写下一阶段 work doc。

审查者不得：

- 因为方向有趣就放行；
- 允许执行者在 review 中追加新规则；
- 把 2022 diagnostic 当 strict OOS；
- 把 qlib-only 结果说成 qlib+LTR；
- 授权 production。

## 12. Stop Conditions

以下情况必须 STOP：

- 找不到可追溯 qlib-only signal；
- 无法构造 PIT-safe market regime；
- 需要读取 future return 才能决策；
- 执行者使用 replay PnL 调阈值；
- 规则数量失控；
- 输出 target_weight / target_position / order / broker；
- provider publish / accepted latest switch 被触发；
- reviewer 无法验证 artifact。

## 13. Closure Criteria

主线可 closure 的条件：

- RSR0-RSR5 均有执行报告和审查报告；
- 或 RSR1/RSR2 发现机制不足并 STOP closure；
- final candidate 只作为 research candidate；
- 所有 forbidden action audit clean；
- 明确说明是否值得开 qlib+LTR adaptation；
- 明确说明是否不再继续。

## 14. First Executor Command

```text
请执行 POLICY_RSR0_CONTRACT_AND_DATA_READINESS。

必须先读取：
- docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
- docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
- docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md
- docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
- docs/tw_portfolio_decision_model/POLICY_RCPT6_RESEARCH_CLOSURE_PACKAGE_CN.md
- docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_REVIEW_CN.md

只做 contract/data readiness，不跑规则收益 replay，不新增策略默认，不训练模型。
输出 POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md。
```

## 15. First Reviewer Brief

```text
请审查 POLICY_RSR0_CONTRACT_AND_DATA_READINESS。

重点检查：
1. 是否真的只做 readiness；
2. 是否可追溯 qlib-only signal / baseline / price / TWII / portfolio state；
3. 是否能 PIT-safe 构造 score bucket、rank delta、market regime、holding state；
4. 是否没有 future leakage；
5. 是否没有 provider publish / accepted latest switch / production/default 改动；
6. 是否可以进入 RSR1 attribution diagnostic。

若通过，请写 POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md。
```

## 16. 参考来源

- Brock, Lakonishok, and LeBaron, “Simple Technical Trading Rules and the Stochastic Properties of Stock Returns,” Journal of Finance, 1992. DOI: https://doi.org/10.2307/2328994
- Lo, Mamaysky, and Wang, “Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation,” Journal of Finance, 2000.
- Jegadeesh and Titman, “Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency,” Journal of Finance, 1993.
- Moskowitz, Ooi, and Pedersen, “Time Series Momentum,” Journal of Financial Economics, 2012.
- Shi and Zhou, “Time series momentum and contrarian effects in the Chinese stock market,” arXiv:1702.07374.
- Fan, Medeiros, Yang, and Yang, “Cost-aware Portfolios in a Large Universe of Assets,” arXiv:2412.11575.
- Ma and Smith, “Optimal two-parameter portfolio management strategy with transaction costs,” arXiv:2411.07949.
