# Phase O1R 覆盖与 available_at 合同修复工作文档

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO1_REVIEW_CN.md
```

## 1. 为什么需要 O1R

Phase O1 执行合规，但没有通过 O1 gate。

阻塞点有两个：

```text
1. Phase0E 本地 archive 只覆盖 103/150 个 Phase1C control symbols；
2. available_at 并不完全等于 next_trading_day(trade_date)，存在 delayed availability / 日历 / 上市状态 mismatch。
```

因此不能直接进入常规 O2 feature builder。

O1R 的目的不是改变主线，而是把进入 O2 前必须澄清的数据合同补齐。

## 2. O1R 目标

O1R 只解决两个问题：

```text
1. 47 个 absent control symbols 是否能用同一 FinMind dataset 补齐；
2. available_at 合同到底采用 exact T+1，还是 PIT-safe delayed availability。
```

本阶段不训练、不回放、不构建 treatment LTR 样本。

## 3. 不变合同

O1R 必须保持以下合同不变：

- Control 仍为第一版 simple LTR / Phase1C anchor；
- 冻结旧 qlib 输入不变；
- LTR 样本、标签、训练窗口、模型参数不变；
- 正交数据范围仍只包含：
  - `TaiwanStockInstitutionalInvestorsBuySell`
  - `TaiwanStockMarginPurchaseShortSale`
- 月营收 YoY 仍不纳入；
- 不新增 filter；
- 不新增 market gate；
- 不新增 turnover rule；
- 不改 frontend/API/provider/accepted latest/monitor/交易链路。

## 4. 执行内容

### 4.1 覆盖补齐审计

执行者需要：

- 列出 47 个 absent control symbols；
- 使用同一 FinMind dataset 尝试补齐：
  - 法人筹码；
  - 融资融券；
- 优先使用项目既有 FinMind token；
- 必要时使用 scrapling + token；
- 只写本地主线实验目录，不写 provider，不发布 accepted latest。

输出：

```text
absent_symbol_fetch_attempts.csv
coverage_before_after.csv
fetch_error_summary.csv
raw_archive_manifest.csv
```

### 4.2 available_at 合同审计

执行者需要对所有可用 raw/normalized 行重新审计：

- `trade_date`
- `next_trading_day`
- `available_at`
- `available_at < next_trading_day`
- `available_at == next_trading_day`
- `available_at > next_trading_day`
- mismatch 原因分类：
  - delayed_source
  - calendar_gap
  - listing_status_gap
  - missing_calendar
  - data_quality_unknown

核心判断：

```text
提前可见不可接受；
延迟可见 PIT-safe，但必须显式入合同。
```

### 4.3 合同二选一

O1R 结束时必须给出明确建议：

#### 方案 A：Exact T+1

```text
available_at = next_trading_day(trade_date)
```

适用条件：

- mismatch 可由日历或上市状态修复；
- 修复后不存在大面积延迟；
- 不需要猜测数据可见时间。

#### 方案 B：PIT-safe delayed availability

```text
available_at >= next_trading_day(trade_date)
```

适用条件：

- 数据确实存在延迟可见；
- 延迟不是未来函数；
- O2/O3 能严格按真实 available_at 做 as-of join；
- 所有延迟行必须保留 delay_days 和 delay_reason。

禁止：

```text
不得把 delayed availability 静默当作 exact T+1；
不得为了覆盖率把 available_at 人工提前；
不得用未来数据补历史特征。
```

## 5. 输出报告要求

执行者必须输出：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_COVERAGE_AVAILABLE_AT_REPAIR_EXECUTION_REPORT_CN.md
```

报告至少包含：

- 执行摘要；
- 是否联网拉取；
- 使用的数据集；
- token/scrapling 使用情况；
- 150 个 control symbols 覆盖前后对比；
- absent symbols 补齐结果；
- 低覆盖 symbols 列表；
- available_at mismatch 分类；
- 是否存在提前可见行；
- 推荐采用 exact T+1 还是 delayed availability；
- 是否允许进入 O2；
- 是否触发用户确认。

## 6. 审查者检查点

审查者必须检查：

- 是否仍符合主线控制变量原则；
- 是否只处理覆盖和 available_at；
- 是否没有训练 qlib/LTR；
- 是否没有构建 treatment sample；
- 是否没有做收益率回放；
- 是否没有改 Phase1C control；
- 是否没有新增月营收或其他数据源；
- 是否没有 provider/accepted latest/frontend/API/monitor/交易链路写入；
- 是否给出清晰的合同选择。

审查结论只能是：

```text
通过，允许进入 O2
不通过，继续 O1R 修复
需要用户确认
```

## 7. 用户第一性原则

O1R 不是为了追求“看起来数据更多”，而是为了保证后续模型结论可信。

用户真正需要的是：

```text
如果正交数据有效，要能相信它不是未来函数；
如果正交数据无效，要能区分是数据本身无效，还是覆盖不足导致无效。
```

因此本阶段宁愿停下来，也不能把 103/150 覆盖静默包装成完整正交数据实验。

## 8. 给执行者的一句话

```text
请按 docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_COVERAGE_AVAILABLE_AT_REPAIR_WORK_CN.md 执行 O1R，只修复/审计 Phase1C control 150 股的法人筹码与融资融券覆盖，以及 exact T+1 vs PIT-safe delayed availability 合同，不得训练、回放、构建 treatment sample、改 control 或触发任何前端/API/provider/accepted latest/monitor/交易链路。
```

## 9. 给审查者的一句话

```text
请按 docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_COVERAGE_AVAILABLE_AT_REPAIR_WORK_CN.md 审查 O1R 执行报告，重点确认覆盖补齐、available_at 合同、PIT 安全、控制变量边界和是否允许进入 O2；如合同需要从 exact T+1 改为 delayed availability，必须明确要求用户确认。
```
