# Phase 0 样本 / 特征 / 标签 / Baseline 口径冻结合同

生成时间：2026-06-13T15:10:46+00:00

唯一主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

## 1. 样本范围冻结

- Phase 0 不构建训练样本，只冻结后续样本口径。
- 后续 Phase 1 只能从本地既有 qlib prediction / top30 / top50、既有本地 OHLCV、既有本地 TWII 数据派生。
- 本轮发现 qlib prediction 文件数：1379。
- 本轮发现 top30 文件数：1379，top50 文件数：1379。
- 本轮发现本地价格文件数：1986，TWII 文件存在：True。
- 不允许新增数据源、联网、token、provider refresh/publish、accepted latest switching。

## 2. Input Feature 白名单冻结

- 允许输入只限 `phase0_feature_whitelist_inventory.csv` 中 `input_feature_allowed=true` 且来自主文档白名单的字段。
- qlib 层字段只能表达横截面排序与历史排名变化，不能解释成收益率、上涨概率、胜率或仓位。
- 技术、流动性、市场状态字段只能使用当前日及历史可得数据滚动派生。
- `trend_score` 在 Phase 0 标记为需复用既有稳定口径；若 Phase 1 找不到稳定定义，应继续排除。

## 3. 禁止特征冻结

以下字段不得进入输入特征、训练、回放或解释主线：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- 任意没有 `available_at` / `announcement_date` 的 PIT 不安全字段

本轮禁止特征输入扫描结论：`forbidden_feature_scan_passed=True`。

## 4. 标签候选与隔离口径

Phase 0 只提出候选，不训练模型。

候选标签必须服务横截面排序，不做点预测回归：

- `future_excess_return_rank_5d`：未来 5 个交易日相对横截面表现排序标签候选。
- `future_excess_return_rank_10d`：未来 10 个交易日相对横截面表现排序标签候选。
- `future_excess_return_rank_20d`：未来 20 个交易日相对横截面表现排序标签候选。
- `topk_forward_bucket`：面向 TopK / rank quality 的分桶标签候选。

隔离规则：

- input columns：只能来自白名单特征。
- label columns：未来收益、未来相对排名、未来 TopK 分桶，只能用于训练目标/评估，不能进入 input。
- audit columns：未来原始收益、成本、净值、动作次数、回撤等只用于审计。
- grouping columns：`date`、`instrument`、`year`、`regime_segment` 等只用于分组/切分，不作为普通输入特征。
- 任何 future return / future rank / label / audit 字段混入 input，都必须停止。

## 5. 数据切分冻结

Phase 1 构建真实样本后必须按实际覆盖日期复核最终边界。Phase 0 先冻结原则：

- train：历史较早区间，用于 LTR baseline 拟合。
- validation：晚于 train，用于模型和参数选择。
- independent test：晚于 validation，用于独立检验。
- regime segment：基于 `TWII_ret20`、`TWII_ret60`、`market_drawdown60`、`market_volatility20`、`market_breadth20` 做差市况 / 非差市况分段审计。

切分要求：

- 时间顺序不能交叉。
- 同一天横截面作为 LTR group。
- label 只能来自未来窗口，且不能回流到 input。
- 若实际本地覆盖不足以支持 train / validation / independent test，Phase 1 必须停止并报告。

## 6. Baseline 对照冻结

后续至少必须对照：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

Phase 0 只冻结名称、口径和未来指标要求；旧 replay 不能被重新解释为本 LTR 主线增益。

## 7. Phase 1 前置 Gate

- 白名单字段数：35。
- 可本地派生或已有字段数：34。
- 禁止特征输入命中数：0。
- baseline 覆盖数：4。
- 推荐 gate：`request_phase1_ltr_baseline_work`。
