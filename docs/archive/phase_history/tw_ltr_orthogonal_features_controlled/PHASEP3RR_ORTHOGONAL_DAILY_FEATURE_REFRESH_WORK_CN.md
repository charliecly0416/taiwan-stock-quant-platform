# Phase P3RR 工作文档：Orthogonal Daily Feature Refresh Repair

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3_REVIEW_AND_P3R_DAILY_CHAIN_REPAIR_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP3R_DAILY_CHAIN_REPAIR_EXECUTION_REPORT_CN.md
```

## 1. 审查结论

P3R 不能最终收尾。

P3R 已完成：

```text
scripts/run_daily_tw_stock_auto_update.py 增加 --run-p3-ltr optional branch；
accepted latest 成功后可调用 scripts/run_tw_ltr_p3_daily_rerank_readonly.py；
P3 failure 不阻塞 fresh qlib 默认链路；
LTR artifact 不写入 qlib accepted latest；
```

但 P3R 未完成用户核心目标中的正交数据日更闭环。

当前 P3R 产物显示：

```text
orthogonal_refresh_status = stale_degraded
institutional_latest_trade_date = 2026-06-10
institutional_latest_available_at = 2026-06-11
margin_latest_trade_date = 2026-06-10
margin_latest_available_at = 2026-06-11
signal_asof = 2026-06-15
```

当前 P3 scoring 仍读取静态 O2 表：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
```

因此当前只能视为：

```text
daily auto script optional LTR rerank hook integrated
```

不能视为：

```text
daily orthogonal data refresh + LTR rerank fully integrated
```

## 2. P3RR 目标

P3RR 只修复正交特征日更闭环。

目标：

```text
每日 auto update 抓到 institutional / margin 数据后，
生成或刷新 P3 inference 可用的 PIT-safe latest orthogonal feature table，
再运行 frozen O4 LTR rerank。
```

目标 gate：

```text
phase_p3rr_orthogonal_daily_feature_refresh_integrated
```

## 3. 必须完成

### 3.1 找到真实正交数据日更来源

执行者必须确认 `backend/scripts/update_tw_stock_daily.py` 或真实日更入口是否已经抓取：

```text
TaiwanStockInstitutionalInvestorsBuySell
TaiwanStockMarginPurchaseShortSale
```

必须输出：

```text
raw institutional latest trade_date
raw margin latest trade_date
raw archive path
row count by family
failed symbols
```

### 3.2 构建 latest orthogonal inference feature table

不得继续只依赖旧 O2 静态表。

必须新增或复用 feature builder，输出一个 P3 专用 latest feature artifact，例如：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_<asof>.csv
```

该表必须满足：

```text
available_at <= signal_asof
feature schema 与 O4 whitelist 对齐
neutral fill + missing flag
不因缺失删除 qlib Top50 行
```

### 3.3 P3 rerank 使用 latest feature table

`scripts/run_tw_ltr_p3_daily_rerank_readonly.py` 必须读取 P3RR 生成的 latest feature artifact，或明确读取一个由每日脚本刚刷新过的 feature table。

summary 必须包含：

```text
orthogonal_refresh_status = current_or_pit_delayed / stale_degraded / failed
latest_feature_table_path
latest_feature_table_created_at
institutional_latest_trade_date
institutional_latest_available_at
margin_latest_trade_date
margin_latest_available_at
stale_feature_families
```

### 3.4 失败隔离

必须保持：

```text
P3RR failure blocks fresh qlib = false
accepted latest mutated by P3RR = false
provider mutated by P3RR = false
monitor/trading mutated by P3RR = false
```

如果正交数据未到齐：

```text
fresh qlib 默认链路继续；
LTR candidate 标记 stale_degraded 或 failed；
不得伪装为 ready。
```

### 3.5 Gate 判定修正

如果 `orthogonal_refresh_status = stale_degraded`，不得给出完整通过 gate。

只能给：

```text
phase_p3rr_degraded_requires_review
```

只有当正交 feature refresh 与 PIT audit 均通过，才能给：

```text
phase_p3rr_orthogonal_daily_feature_refresh_integrated
```

## 4. 禁止事项

P3RR 禁止：

```text
重训 qlib；
重训 LTR；
调参；
改变 O4 model / feature whitelist；
扩大 qlib Top50；
把 LTR artifact 写入 accepted latest；
切换 accepted latest；
provider publish / refresh；
monitor scan/config/alerts 写入；
broker/orders/quick-trade；
target position / target weight；
真实买卖建议；
收益、胜率或上涨概率承诺。
```

## 5. 输出报告

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3RR_ORTHOGONAL_DAILY_FEATURE_REFRESH_EXECUTION_REPORT_CN.md
```

报告必须回答：

```text
1. 正交数据是否真的随每日 auto update 更新？
2. latest feature table 是哪个 artifact？
3. institutional / margin 最新 trade_date 与 available_at 是多少？
4. P3 rerank 是否使用最新 feature table？
5. stale_degraded 时是否不再给完整通过 gate？
6. fresh qlib 默认链路是否不受影响？
7. 是否仍只读且不触发 accepted latest/provider/monitor/trading？
```

## 6. 给执行者的指令

请执行 Phase P3RR：修复 P3R 中正交数据只读取旧 O2 静态表、`orthogonal_refresh_status=stale_degraded` 却给完整 gate 的问题。必须把 institutional/margin 日更数据转成 P3 inference 可用的 PIT-safe latest feature table，并让 frozen O4 LTR rerank 使用该最新表；如果无法做到，则必须保留 degraded gate 并停止等待审查，不得声称日更 LTR 已完整闭环。
