# Phase O1 审查结论：正交数据 PIT 可得性

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO0_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO1_ORTHOGONAL_DATA_PIT_AVAILABILITY_EXECUTION_REPORT_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/
```

## 1. 审查结论

结论：

```text
需要用户确认 / 暂不通过 O1 passed gate
```

执行者没有越界。本轮只读取既有 Phase0E/Phase0D 本地产物做 PIT 可得性审计，没有请求 FinMind 网络，没有训练 qlib/LTR，没有构建 treatment 样本，没有回放收益率，也没有触发 frontend/API/provider/accepted latest/monitor/交易链路。

但 O1 目标是确认法人筹码、融资融券能按 Phase1C control 股票池和目标时间段稳定获取，并可形成 PIT raw archive。当前报告主动给出的 gate 是：

```text
phase_o1_blocked_requires_data_coverage_decision
```

这个判断是合理的，不能改判为通过。

## 2. 通过项

### 2.1 执行边界合规

O1 遵守 O0 审查约束：

```text
未训练 qlib
未训练 LTR
未构建 treatment sample
未做回放或收益率优劣证明
未改 control sample / label / original features
未改 frontend/API/provider/accepted latest/monitor/交易链路
```

### 2.2 数据源和字段 schema 可识别

本轮审计的数据族符合主线范围：

```text
institutional_flow: FinMind TaiwanStockInstitutionalInvestorsBuySell
margin_short: FinMind TaiwanStockMarginPurchaseShortSale
```

两个 normalized table 都包含主线需要的基础字段：

```text
symbol
stock_id
trade_date
available_at
source / snapshot / fetched_at / quality_flags
```

字段层面没有发现缺 required columns。

### 2.3 未发现同日可见 PIT 违规

PIT audit 显示：

```text
institutional_flow available_at_not_after_trade_date_rows: 0
margin_short available_at_not_after_trade_date_rows: 0
```

也就是说，当前没有发现 `available_at <= trade_date` 的明显未来函数/同日使用问题。

## 3. 阻塞问题

### 3.1 严格 T+1 PIT 规则未通过

主线 O1 要验证：

```text
available_at = next_trading_day(trade_date)
```

但 O1 结果为：

| category | row_count | mismatch rows | pit_rule_pass |
| --- | ---: | ---: | --- |
| institutional_flow | 158834 | 398 | no |
| margin_short | 156021 | 5 | no |

其中大部分不是提前可见，而是延迟可见或日历/上市状态导致的 mismatch。延迟可见本身是 PIT-safe 的，但它已经不是主线写死的 exact T+1 合同。

因此这里必须做合同选择：

```text
A. 坚持 exact T+1：先修正 available_at / 日历 / 上市状态，再审 O1R；
B. 放宽为 conservative delayed availability：允许 available_at >= next_trading_day，但 O2/O3 必须按真实 available_at 做 as-of join。
```

不能静默把 exact T+1 改成 delayed availability。

### 3.2 Phase0E 本地 archive 未覆盖全部 Phase1C control symbols

O1 覆盖结果：

| category | control symbols | symbols with data | absent symbols |
| --- | ---: | ---: | ---: |
| institutional_flow | 150 | 103 | 47 |
| margin_short | 150 | 103 | 47 |

这不是小缺口。47/150 个 control symbol 没有本地 Phase0E 数据，若直接进入 O2/O3，这些股票的正交特征会长期依赖 neutral fill + missing flag。

这不会导致样本删行，但会让 treatment 的新增信息在相当一部分股票上实际缺失，影响后续增益解释。

### 3.3 部分已有股票覆盖也偏低

低覆盖样例：

```text
institutional_flow:
TW4749 coverage 0.7865

margin_short:
TW3131 coverage 0.1117
TW4749 coverage 0.1962
TW6446 coverage 0.6441
TW6805 coverage 0.7328
TW6770 coverage 0.9033
```

这意味着即使在 103 个有数据的股票里，也存在个别股票的历史覆盖不足。

## 4. 是否偏离主线

没有发现执行者偏离主线。

执行者没有把问题掩盖成通过，而是正确停在：

```text
phase_o1_blocked_requires_data_coverage_decision
```

这个 gate 符合主线“有问题停下来讨论”的要求。

## 5. 审查决定

当前不能进入常规 O2。

允许的下一步只有二选一：

### 方案 A：O1R 覆盖与 available_at 合同修复

目标：

```text
尽量补齐 150 个 Phase1C control symbols 的法人筹码/融资融券本地 raw archive；
重新审计 available_at；
明确 exact T+1 或 delayed availability 合同。
```

适用条件：

```text
用户希望正交数据覆盖尽量完整，再进入 O2。
```

注意：

```text
可以拉取 FinMind，但仍禁止训练、禁止回放、禁止改 control、禁止前端/交易链路。
```

### 方案 B：接受当前覆盖，进入“缺失显式化 O2”

目标：

```text
不补数据；
用现有 103/150 覆盖进入 feature builder；
47 个 absent symbols 和低覆盖区间全部 neutral fill + missing flag；
在后续 O5/O6 把覆盖不足作为解释风险。
```

适用条件：

```text
用户接受 treatment 的新增正交信息不是全股票覆盖。
```

风险：

```text
后续若 treatment 没有增益，无法明确区分是正交数据无效，还是覆盖不足导致信号不足；
若 treatment 有增益，也必须审计增益是否只来自少数有高覆盖的股票。
```

## 6. 推荐

推荐先走方案 A，做一个很小的 O1R：

```text
Phase O1R：Coverage / available_at Contract Repair
```

O1R 只解决两个问题：

```text
1. 47 个 absent control symbols 是否能用同一 FinMind dataset 补齐；
2. available_at 合同到底采用 exact T+1，还是 PIT-safe delayed availability。
```

O1R 禁止事项：

```text
不得训练 qlib/LTR
不得构建 treatment sample
不得做收益率回放
不得改 Phase1C control
不得新增月营收 YoY 或其他数据源
不得新增过滤器/阈值/market gate/turnover rule
不得改 frontend/API/provider/accepted latest/monitor/交易链路
```

如果 O1R 仍无法补齐覆盖，则再由用户决定是否接受“缺失显式化 O2”。

## 7. 最终判断

```text
O1 执行合规；
O1 数据可得性未通过；
需要用户确认下一步；
暂不允许进入常规 O2。
```
