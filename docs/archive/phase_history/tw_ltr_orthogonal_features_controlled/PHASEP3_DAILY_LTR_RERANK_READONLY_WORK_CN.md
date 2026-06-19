# Phase P3 工作文档：Daily Orthogonal LTR Rerank Readonly Candidate

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP2_DEFAULT_STRATEGY_DISCUSSION_EXECUTION_REPORT_CN.md
docs/tw_fresh_top50_coverage_repair/PHASEC5_FRONTEND_DEFAULT_SWITCH_EXECUTION_REPORT_CN.md
```

## 1. P3 目标

P3 目标是新增一条只读的 LTR 日更并列候选链路：

```text
每日自动数据更新成功后，
在 fresh qlib Top50 候选上，
补齐 O4 orthogonal LTR 需要的正交数据，
使用已冻结 O4 LTR 模型每日重算分数并重排序，
输出一个与 fresh qlib 默认策略并列展示的 readonly LTR candidate。
```

P3 不改变当前默认策略：

```text
默认策略仍为 fresh qlib / rank_rotate_top50_adaptive_score
LTR 日更结果仅为并列研究候选
```

目标 gate：

```text
phase_p3_daily_ltr_rerank_readonly_candidate_ready_for_review
```

## 2. 用户确认的产品语义

用户已确认本阶段只需要：

```text
每日重算 LTR 分数；
不每日重训 LTR 模型；
不默认展示为主策略；
作为 fresh qlib 的并列候选；
只展示策略研究结论，不做真实操作。
```

本文件中的“只读”含义固定为：

```text
允许读取数据、抓取必要正交数据、生成本地研究 artifact、计算排名、做历史/当日研究展示；
禁止连接券商、提交订单、写真实持仓、生成实际 target position、触发 quick-trade 或自动交易。
```

## 3. 固定模型与输入合同

P3 必须复用 O4 已冻结 treatment LTR 模型，不得重训。

固定模型：

```text
model artifact:
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl

score semantics:
orthogonal LTR rerank score
```

固定训练身份：

```text
base = Phase1C simple LTR contract
treatment = Phase1C 原始特征 + PIT-safe 法人筹码/融资融券正交特征
model type / hyperparameters / label / split 均来自 O4
```

P3 只允许做 inference / scoring：

```text
load frozen O4 model
build latest as-of features
score qlib Top50 rows
rerank qlib Top50 rows by LTR score
write readonly candidate artifact
```

## 4. 日更数据范围

P3 需要接入每日自动脚本的数据更新链路，但只允许补齐 LTR inference 所需数据。

必须覆盖：

```text
fresh qlib accepted latest Top50
本地日线/技术特征
O4 使用的法人筹码正交特征
O4 使用的融资融券正交特征
```

正交数据范围沿用 O1/O2/O4：

```text
TaiwanStockInstitutionalInvestorsBuySell
TaiwanStockMarginPurchaseShortSale
```

暂不纳入：

```text
月营收；
新数据源；
新特征族；
新闻/情绪/基本面；
任何未在 O4 白名单中的 feature。
```

## 5. PIT / available_at 合同

P3 必须沿用 O1R/O2 已确认的 delayed availability 合同。

默认规则：

```text
正交数据 trade_date 不得同日用于 inference；
只能在 available_at <= signal_asof 时使用；
不得用未来数据补当日 ranking；
不得用回测后或当日之后才知道的数据修正当日候选。
```

执行者必须输出当日 as-of 审计：

```text
signal_asof
feature_trade_date_max_by_family
available_at_max_by_family
available_at_violations
future_data_violations
missing_feature_count_by_family
```

若发现 exact T+1 无法保证、必须使用更晚可得性，必须停止并提交用户确认，不得自行放宽。

## 6. 候选池与轮动规则

P3 的候选池固定为每日 fresh qlib accepted latest 的 Top50。

输入来源：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
对应 run_dir 下的 top50 signal artifact
```

LTR 不得扩大股票池：

```text
不得从 Top50 外 top-up；
不得用全市场股票补位；
不得因为缺正交特征删除股票后再补其他股票；
不得加入新的 universe filter。
```

轮动规则固定为用户指定语义：

```text
在 qlib Top50 内按 LTR score 重排序；
若当前模拟持有标的跌出 qlib Top50，则历史模拟中移除排名最低的一支；
从 LTR 重排序后的最高排名候选补入一支；
保持与 fresh qlib Top50 adaptive 相同的只读历史模拟/研究展示语义。
```

执行者必须注意：

```text
这里的“卖掉/买入”只能出现在 historical simulation / readonly replay 语义中；
产品文案不得写成真实交易指令；
不得生成可被交易链路消费的 target position / target weight。
```

## 7. 与 fresh qlib 默认策略的关系

P3 不改变默认策略。

固定关系：

```text
default_strategy = fresh qlib / rank_rotate_top50_adaptive_score
parallel_candidate = daily orthogonal LTR rerank on fresh qlib Top50
legacy_static_candidate = frozen O4 historical evidence
```

允许展示：

```text
fresh qlib 默认策略；
daily orthogonal LTR rerank 并列候选；
两者当日 Top50 / Top10 差异；
只读历史模拟对照；
PIT / coverage / missing 审计。
```

禁止展示：

```text
LTR 已替代默认；
LTR 是当前默认策略；
LTR 给出真实买卖建议；
LTR 保证收益、胜率或上涨概率；
LTR 输出真实仓位目标。
```

## 8. 允许改动范围

P3 允许执行者做最小必要实现：

```text
1. 扩展每日自动脚本，使其在 qlib accepted latest 成功后补取/更新正交数据；
2. 新增或复用 PIT-safe latest feature builder；
3. 新增 O4 frozen model inference / scoring 脚本；
4. 新增 readonly daily LTR artifact 输出；
5. 新增后端只读 reader 或前端只读展示入口；
6. 新增测试、审计报告和文档。
```

如需要改动 `scripts/run_daily_tw_stock_auto_update.py` 或同类 daily auto update 脚本，必须保证：

```text
不会改变既有 fresh qlib accepted latest 发布语义；
不会让 LTR 失败阻塞 fresh qlib 默认策略更新，除非明确标记为 optional candidate failure；
不会在 LTR 分支中触发 provider publish / accepted latest switching；
不会把 LTR artifact 写成 accepted latest qlib signal。
```

## 9. 输出 artifact 合同

P3 必须新增独立 readonly artifact root，建议：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/
```

每个 asof 至少输出：

```text
daily_ltr_rerank_<asof>_top50.csv
daily_ltr_rerank_<asof>_summary.json
daily_ltr_rerank_<asof>_feature_audit.csv
daily_ltr_rerank_<asof>_pit_audit.json
daily_ltr_rerank_latest.json
```

Top50 CSV 至少包含：

```text
asof
symbol
instrument
qlib_rank
qlib_score
ltr_score
ltr_rank
score_model_id
feature_available_at_max
missing_feature_family_count
research_signal_not_order
```

summary JSON 至少包含：

```text
asof
source_qlib_run_id
source_latest_signal_path
model_artifact
model_hash
feature_schema_hash
top50_input_count
top50_scored_count
top50_missing_score_count
pit_pass
available_at_violations
future_data_violations
status
trading_disabled_flags
```

## 10. 验证要求

P3 执行报告必须完成以下验证。

### 10.1 功能验证

```text
读取当前 accepted latest；
取到 qlib Top50；
构建 Top50 的 O4 inference 特征；
载入 frozen O4 model；
输出 LTR score 和 ltr_rank；
生成 latest pointer；
reader/UI 能只读读取。
```

### 10.2 PIT / Coverage 验证

```text
available_at_violations == 0
future_data_violations == 0
top50_input_count == 50
top50_scored_count 尽量为 50
缺失不得导致股票被静默删除
缺失必须通过 neutral fill + missing flag 或明确 degraded status 处理
```

若 `top50_scored_count < 50`，执行者必须解释原因，并明确是否仍可作为 degraded readonly candidate。不得自动补入 Top50 外股票。

### 10.3 只读安全验证

必须证明：

```text
不连接 broker；
不提交 orders；
不触发 quick-trade；
不写真实 positions；
不写 monitor config；
不触发 monitor scan；
不写 alerts；
不切 accepted latest；
不触发 provider publish；
不改变 fresh qlib 默认策略。
```

### 10.4 回归验证

必须证明：

```text
fresh qlib 默认页面/reader 仍可正常读取 latest_signal.json；
rank_rotate_top50_adaptive_score 默认选择未改变；
LTR 日更失败时 fresh qlib 默认链路不受影响；
生产构建或相关测试通过。
```

## 11. 禁止事项

P3 禁止：

```text
重训 qlib；
重训 LTR；
调参；
改变 O4 模型；
改变 O4 feature 白名单；
改变 Phase1C / O4 历史结论；
扩大 LTR 候选池到 qlib Top50 之外；
新增 filter / threshold / market gate / stop loss / take profit / turnover rule；
把 LTR artifact 发布成 qlib accepted latest；
切换 accepted latest；
provider publish / refresh；
monitor scan / config / alerts 写入；
broker / orders / quick-trade；
target position / target weight；
真实买卖建议；
收益、胜率或上涨概率承诺。
```

## 12. 停止条件

出现以下任一情况，执行者必须停止并提交问题，不得自行继续：

```text
需要每日重训 LTR 才能完成；
需要改变 O4 feature schema；
需要改变 available_at 合同；
需要引入新数据源或新特征族；
需要把 LTR 写入 accepted latest；
需要改 fresh qlib 默认策略；
LTR 分支会阻塞 fresh qlib 日更；
出现 PIT / future data violation；
需要接入真实交易或 monitor 写链路；
产品文案无法避免真实买卖/仓位语义。
```

## 13. 执行报告要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3_DAILY_LTR_RERANK_READONLY_EXECUTION_REPORT_CN.md
```

报告必须回答：

```text
1. 是否仍保持 fresh qlib 为默认策略？
2. 是否只做 frozen O4 model daily scoring，没有重训？
3. 每日自动脚本如何补取正交数据？
4. LTR candidate 是否只使用 qlib Top50？
5. PIT / available_at 审计是否通过？
6. 缺失数据如何处理，是否有静默删股或 Top50 外补位？
7. 输出了哪些 artifact？
8. LTR 日更失败时 fresh qlib 默认链路是否不受影响？
9. 是否触发 provider / accepted latest / monitor / trading 链路？
10. 是否可以进入只读展示/E2E 验收？
```

报告必须列出：

```text
改动文件；
运行命令；
输入 artifact；
输出 artifact；
当前 asof 测试结果；
Top50 input/scored/missing 统计；
PIT audit 结果；
只读安全审计结果；
剩余风险。
```

## 14. 给执行者的指令

请按本文执行 Phase P3：新增 daily orthogonal LTR rerank readonly candidate。只允许在每日数据更新成功后，为 qlib accepted latest Top50 补齐 O4 所需正交特征，并用 frozen O4 LTR 模型重算分数和重排序；不得重训模型、不得扩大股票池、不得改变 fresh qlib 默认策略、不得发布 LTR 为 accepted latest、不得触发 provider/monitor/交易链路。完成后提交 `PHASEP3_DAILY_LTR_RERANK_READONLY_EXECUTION_REPORT_CN.md` 等待审查。
