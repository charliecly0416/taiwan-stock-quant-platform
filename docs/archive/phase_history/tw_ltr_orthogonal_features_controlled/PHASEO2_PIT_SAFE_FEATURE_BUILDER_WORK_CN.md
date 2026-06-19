# Phase O2 工作文档：PIT-safe Raw Archive 与 Feature Builder

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_REVIEW_CN.md
用户确认：接受 PIT-safe delayed availability，允许进入 O2
```

## 1. O2 启动条件

Phase O1R 已完成审查：

```text
覆盖补齐：通过，150/150 control symbols 均有数据
PIT 禁止性提前可见：未发现
exact T+1 合同：不通过
PIT-safe delayed availability：用户已确认接受
```

O2 允许启动。

O2 的 gate 目标：

```text
phase_o2_pit_safe_feature_builder_passed
```

## 2. O2 合同变更记录

主线原始合同：

```text
available_at = next_trading_day(trade_date)
```

经 O1R 审查与用户确认，O2 起采用：

```text
available_at >= next_trading_day(trade_date)
PIT-safe delayed availability
```

含义：

```text
数据只能在真实 available_at 及之后使用；
允许来源延迟可见；
不得人工提前 available_at；
不得把 delayed rows 静默当作 exact T+1；
不得用未来数据补历史特征。
```

每行必须保留：

```text
trade_date
available_at
next_trading_day
delay_days
delay_reason
available_at_contract
raw_snapshot_id
fetched_at
raw_payload_hash 或 raw checksum
raw_snapshot_path
```

## 3. O2 目标

O2 只做一件事：

```text
把 O1R 审查通过的法人筹码与融资融券数据构造成可复现、可追溯、PIT-safe 的特征构建器。
```

O2 不训练模型，不拼接最终 treatment LTR sample，不做收益率回放。

## 4. 输入范围

只允许使用：

```text
TaiwanStockInstitutionalInvestorsBuySell
TaiwanStockMarginPurchaseShortSale
```

输入产物：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/
```

允许读取 Phase1C control sample，仅用于取得：

```text
symbol
sample_date
control row universe
```

不得改写 control sample。

## 5. 允许构建的特征族

### 5.1 法人筹码

允许：

```text
foreign_net_buy
investment_trust_net_buy
dealer_net_buy
institutional_total_net_buy
1/3/5/10 日 rolling net buy
连续买超/卖超天数
买卖超占成交量比例，如成交量字段可在 PIT-safe as-of 下取得
missing flag
delay flag / delay_days
```

### 5.2 融资融券

允许：

```text
margin_balance
margin_balance_change
short_balance
short_balance_change
融资余额变化 rolling
融券余额变化 rolling
融资/融券方向 proxy
missing flag
delay flag / delay_days
```

如某个派生特征需要额外数据源或非 O1R 审查字段，必须停止并说明，不得静默加入。

## 6. PIT Join 规则

所有特征必须按 as-of 方式构建：

```text
对每个 control row 的 sample_date，
只能使用 available_at <= sample_date 的最新或历史记录。
```

禁止：

```text
用 trade_date <= sample_date 但 available_at > sample_date 的记录；
用未来记录回填早期样本；
为了提高覆盖率提前 available_at；
用窗口后数据修正窗口内特征；
同日使用 trade_date 数据，除非该行 available_at 已经 <= sample_date。
```

## 7. 缺失值规则

缺失不得导致样本行删除。

默认处理：

```text
数值特征 neutral fill：优先 0；如使用横截面中位数，必须记录字段和日期；
每个特征族必须有 missing flag；
低覆盖股票必须保留 missing report；
treatment 后续拼接时必须保持 control rows 完全一致。
```

O1R 已知低覆盖风险必须在 O2 报告中单独列出：

```text
institutional_flow low coverage < 0.95: 4 symbols
margin_short low coverage < 0.95: 9 symbols
```

重点包括：

```text
TW7769
TW6919
TW3131
TW6683
TW4749
```

## 8. 必须输出的审计

O2 报告必须至少包含：

```text
使用脚本
输入 artifact
输出 artifact
feature dictionary
raw archive / normalized table lineage
row count
symbol count
date range
available_at 合同统计
delay_days / delay_reason 分布
missing ratio by feature family
missing ratio by symbol
missing ratio by date
PIT leakage audit
是否出现 available_at > sample_date 被使用
是否出现 available_at <= trade_date
是否改变 control rows / symbol / sample_date
是否触发停止条件
```

推荐输出产物：

```text
feature_dictionary.csv
normalized_feature_daily.csv
feature_builder_manifest.json
pit_lineage_audit.csv
pit_leakage_audit.csv
missing_by_feature_family.csv
missing_by_symbol.csv
missing_by_date.csv
delay_distribution.csv
phaseo2_summary.json
```

## 9. O2 禁止事项

严格禁止：

```text
训练 qlib
训练 LTR
构建并训练最终 treatment sample
做收益率回放
改变 Phase1C control
改变 control rows / label / original features
改变训练窗口 / 验证窗口 / 测试窗口
新增月营收 YoY
新增 O1R 未审查的数据源
新增 filter / threshold / market gate / turnover rule
改 frontend/API/provider/accepted latest/monitor/交易链路
```

## 10. O2 停止条件

如出现以下任一情况，执行者必须停止并提交问题说明：

```text
需要用未来数据补特征；
feature 无法追溯 raw archive；
as-of join 发现 available_at > sample_date 被使用；
发现 available_at <= trade_date 的禁止性提前可见；
feature builder 会导致后续 treatment rows 少于 control rows；
需要改变 control sample_date 或 symbol 集合；
需要新增数据源或新增未审查字段；
缺失值处理需要删行。
```

## 11. 给执行者的一句话

```text
请按本 O2 工作文档执行，只基于 O1R 已确认的法人筹码与融资融券数据，采用 PIT-safe delayed availability 合同构建 raw archive / normalized daily table / feature builder，并输出 lineage、missing、delay 与 PIT leakage 审计；不得训练、回放、构建最终 treatment sample、改 control 或触发任何前端/API/provider/accepted latest/monitor/交易链路。
```
