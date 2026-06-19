# Phase P3 审查与 P3R 工作文档：Daily Chain Integration Repair

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3_DAILY_LTR_RERANK_READONLY_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP3_DAILY_LTR_RERANK_READONLY_EXECUTION_REPORT_CN.md
scripts/run_tw_ltr_p3_daily_rerank_readonly.py
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/
```

## 1. 审查结论

P3 当前不允许收尾。

执行者完成了单次 readonly daily LTR rerank artifact 生成：

```text
asof = 2026-06-15
top50 input/scored = 50/50
PIT pass = true
status = ready
```

但 P3 工作文档的核心目标不是只跑一次离线脚本，而是：

```text
每日自动数据更新成功后，
补齐 O4 LTR 所需正交数据，
用 frozen O4 model 重算 qlib Top50 rerank，
形成 fresh qlib 的并列只读候选。
```

当前执行报告没有证明这条链路已经接入每日自动脚本，也没有证明每日正交数据会随自动更新补取。因此只能视为：

```text
single-run readonly scoring proof
```

不能视为：

```text
daily auto-update integrated LTR candidate
```

## 2. 已通过部分

### 2.1 默认策略边界

报告声明默认策略仍为：

```text
fresh qlib / rank_rotate_top50_adaptive_score
```

未发现报告把 LTR 设置为默认。

### 2.2 frozen O4 scoring

新增脚本读取：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl
```

报告声明没有重训 LTR。未发现训练脚本被本轮报告声明执行。

### 2.3 Top50 候选池

报告与 summary 均显示：

```text
top50_input_count = 50
top50_scored_count = 50
top50_missing_score_count = 0
```

当前 asof 没有发现 Top50 外补位证据。

### 2.4 PIT 审计

当前 `daily_ltr_rerank_2026-06-15_pit_audit.json` 显示：

```text
feature_trade_date_max_by_family:
  institutional_flow = 2026-06-10
  margin_short = 2026-06-10

available_at_max_by_family:
  institutional_flow = 2026-06-11
  margin_short = 2026-06-11

available_at_violations = []
future_data_violations = []
pit_pass = true
```

单次 as-of scoring 的 PIT 审计通过。

### 2.5 只读安全

报告声明未触发：

```text
broker / orders / quick-trade / positions
monitor config / scan / alerts
accepted latest switching
provider publish / refresh
```

新增 artifact 写入目录为：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/
```

未发现被写成 qlib accepted latest。

## 3. 阻塞问题

### 3.1 未证明接入每日自动更新脚本

P3 工作文档要求允许并期望：

```text
扩展每日自动脚本，使其在 qlib accepted latest 成功后补取/更新正交数据；
LTR 日更失败时 fresh qlib 默认链路不受影响；
```

当前审查只看到新增：

```text
scripts/run_tw_ltr_p3_daily_rerank_readonly.py
```

但没有看到执行报告说明：

```text
daily auto update script 的调用点；
何时触发 P3 rerank；
如何确保 accepted latest 成功后再运行；
如何确保 P3 失败不会阻塞 fresh qlib 默认更新；
如何记录 optional candidate failure。
```

这是 P3 的核心缺口。

### 3.2 未证明每日正交数据会补取

P3 目标要求每日自动脚本也补齐 LTR 所需正交数据。

当前 P3 脚本读取的是既有 O2 静态日表：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
```

报告风险也写明该表当前只可用到：

```text
trade_date = 2026-06-10
available_at = 2026-06-11
```

但报告没有证明：

```text
每日会新增 institutional / margin raw archive；
每日会刷新 normalized_feature_daily 或生成 latest feature table；
缺失或延迟时如何 degraded；
FinMind/source 拉取失败时如何不阻塞 fresh qlib。
```

因此它还不能满足“每日抓取到新数据后 LTR 也更新”的用户目标。

### 3.3 报告缺少 reader/UI 只读读取验证

P3 工作文档要求：

```text
reader/UI 能只读读取
```

当前报告只列出 artifact，没有说明：

```text
后端是否有 readonly reader；
前端是否有只读展示入口；
或者当前阶段是否明确只到 artifact，不接展示层。
```

如果执行者选择本阶段不接 UI，也必须在报告中明确说：

```text
reader/UI not implemented in P3, requires P3S/P4
```

不能直接以 P3 gate 收尾。

### 3.4 报告未充分列出运行命令和回归验证

P3 工作文档要求报告：

```text
改动文件；
运行命令；
生产构建或相关测试；
fresh qlib 默认 reader 仍可读取 latest_signal.json；
rank_rotate_top50_adaptive_score 默认选择未改变；
LTR 失败不影响 fresh qlib。
```

当前执行报告只给了简短结论，没有覆盖这些审查项。

## 4. Verdict

```text
不通过 / 需要 P3R 修复
```

当前可以保留为：

```text
P3 single-run readonly scoring proof passed
```

但不得声明：

```text
daily LTR auto-update chain completed
```

不得进入最终收尾或默认策略讨论。

## 5. Phase P3R 目标

P3R 只修复 P3 的日更链路闭环，不扩大策略范围。

目标：

```text
把 P3 readonly LTR rerank 接入每日自动更新链路，
并证明正交数据更新、frozen O4 scoring、artifact 输出、失败隔离和只读安全均闭环。
```

目标 gate：

```text
phase_p3r_daily_ltr_rerank_chain_integrated_and_audited
```

## 6. P3R 必须完成

### 6.1 Daily chain integration

执行者必须明确找到并审计每日自动脚本，例如：

```text
scripts/run_daily_tw_stock_auto_update.py
```

如果实际日更入口不是该脚本，必须说明真实入口。

必须实现或证明：

```text
fresh qlib accepted latest 成功后才运行 P3 LTR rerank；
P3 LTR rerank 是 optional candidate branch；
P3 失败不得阻塞 fresh qlib 默认链路；
P3 不得修改 latest_signal.json；
P3 不得触发 accepted latest switching；
P3 不得触发 provider publish / refresh。
```

### 6.2 Orthogonal data refresh

执行者必须完成以下之一：

```text
A. 接入每日正交数据补取与 PIT-safe feature 更新；
B. 如果当前数据源尚不能日更，明确标记 P3 candidate 为 stale/degraded，并停止请求用户确认。
```

不能只读取 O2 历史静态表后宣称已完成日更。

必须输出：

```text
orthogonal_refresh_status
institutional_latest_trade_date
institutional_latest_available_at
margin_latest_trade_date
margin_latest_available_at
refresh_failed_symbols
stale_feature_families
```

### 6.3 Frozen model scoring contract

必须继续保持：

```text
只 load O4 model；
不重训；
不调参；
不改 feature whitelist；
只 score qlib Top50；
不得 Top50 外补位。
```

### 6.4 Failure isolation

必须新增或输出失败隔离审计：

```text
fresh_qlib_default_chain_status
p3_ltr_candidate_status
p3_failure_blocks_fresh_qlib = false
accepted_latest_mutated_by_p3 = false
provider_mutated_by_p3 = false
```

### 6.5 Readonly reader/UI boundary

P3R 至少要二选一：

```text
A. 新增后端 readonly reader，并用 GET-only 或 local artifact test 验证可读；
B. 明确本阶段只产 artifact，不接 UI，并另开后续展示工作文档。
```

无论选择 A 或 B，都不得接交易、monitor 写入或 accepted latest 切换。

### 6.6 Report completeness

P3R 报告必须列出：

```text
改动文件；
运行命令；
日更入口；
P3 调用点；
输入 artifact；
输出 artifact；
当前 asof；
Top50 input/scored/missing；
正交数据最新 trade_date / available_at；
PIT audit；
failure isolation audit；
fresh qlib 默认链路回归；
只读安全审计；
剩余风险。
```

## 7. P3R 禁止事项

P3R 禁止：

```text
重训 qlib；
重训 LTR；
调参；
改变 O4 model；
改变 O4 feature whitelist；
扩大到 qlib Top50 外；
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

## 8. P3R 停止条件

出现以下任一情况必须停止：

```text
需要让 LTR 分支写 accepted latest；
需要让 LTR 失败阻塞 fresh qlib；
需要放宽 available_at 合同；
需要新数据源或新特征族；
无法每日补齐正交数据；
无法避免交易/monitor/accepted latest/provider 写链路；
无法证明 default fresh qlib 未改变。
```

## 9. 给执行者的指令

请执行 Phase P3R：修复 P3 只完成单次 readonly scoring、未闭环日更链路的问题。必须把 frozen O4 LTR rerank 作为 optional readonly candidate 接到每日自动更新流程中，或明确证明当前不能接入并停止；必须补齐或审计每日正交数据刷新、PIT available_at、失败隔离、fresh qlib 默认链路不受影响和只读安全边界。不得重训、不得改默认、不得写 accepted latest、不得触发 provider/monitor/交易链路。完成后提交：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3R_DAILY_CHAIN_REPAIR_EXECUTION_REPORT_CN.md
```
