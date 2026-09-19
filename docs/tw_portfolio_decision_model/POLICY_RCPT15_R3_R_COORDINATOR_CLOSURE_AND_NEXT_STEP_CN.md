---
created_at: 2026-06-26
status: coordinator_closure
phase: RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR
verdict: PASS_WITH_CONDITIONS_READY_FOR_FRESHNESS_DIAGNOSTIC_OR_RCPT15_CONTINUATION
---

# RCPT15_R3_R 统筹闭环与下一步意见

## 1. 统筹结论

`RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR` 已完成执行与复审，结论为：

```text
PASS_WITH_CONDITIONS
```

本轮修复了 R3 的核心阻塞：

```text
R3 原阻塞 = O4 whitelist 78 特征中缺 22 个技术/市场控制特征
R3_R 结果 = 78/78 特征完整，missing_required_feature_count = 0
```

可以确认：

1. frozen O4 LTR model 可加载；
2. rerank score 经 reviewer 独立复现，来自 frozen O4 predict，`max_abs_pred_diff = 2.22e-16`；
3. `2026-06-19` 正确排除为 no-signal input；
4. O2 institutional_flow / margin_short PIT-safe；
5. 技术/市场特征没有 future leakage；
6. 未写 formal latest、provider accepted latest、qlib accepted latest、order、target、broker；
7. 输出只作为 isolated research/shadow artifact。

## 2. 主要产物

脚本：

```text
scripts/build_tw_policy_rcpt15_r3_r_full_yz2_feature_package_repair.py
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/
```

关键文件：

```text
manifest.json
validator_report.json
feature_package.csv
feature_schema_audit.csv
feature_source_trace.csv
pit_audit.csv
forbidden_scope_audit.csv
rerank_score_snapshot.csv
rerank_top30.csv
rerank_top50.csv
target_date_rerank_status.csv
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_REVIEW_CN.md
```

## 3. 通过证据

`validator_report.json`：

```text
ok = true
feature_whitelist_count = 78
missing_required_feature_count = 0
coverage_pass = true
pit_pass = true
forbidden_pass = true
feature_package_rows = 250
rerank_score_rows = 250
top30_rows = 150
top50_rows = 250
no_fallback_or_fake_rerank = true
no_training_or_tuning = true
no_order_target_quantity_broker = true
```

reviewer 独立验证：

```text
frozen O4 predict max_abs_pred_diff = 2.22e-16
```

## 4. 条件与剩余风险

### 4.1 Matplotlib cache warning

重跑脚本时出现：

```text
/home/chuliyang/.config/matplotlib is not writable
Matplotlib created a temporary cache directory under /tmp
```

这不是业务 artifact，也不触碰 forbidden scope。若要严格做到所有运行写入都只在隔离目录，可在后续命令中设置：

```bash
MPLCONFIGDIR=/tmp/matplotlib-rcpt15-r3-r
```

### 4.2 Price / TWII source freshness 风险

主线程抽查 `pit_audit.csv` 发现：

```text
local_readonly_price latest_used_date_max = 2026-06-01
local_readonly_market latest_used_date_max = 2026-05-21
target signal days = 2026-06-18..2026-06-25
```

这说明 R3_R 特征是 PIT-safe，但技术/市场控制特征使用的本地 readonly price/TWII 源偏旧。

因此本轮可以证明：

```text
完整 78-feature construction + frozen O4 rerank pipeline 已打通
```

但暂不应直接把它解释为“最新市场状态下的生产级 rerank 已充分完成”。若要推进 RCPT15 shadow continuation，应先做一次 source freshness diagnostic，确认 price/TWII 是否需要补到目标 asof 附近。

## 5. 下一步建议

建议下一步：

```text
RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC
```

目标：

1. 审计 `normalized_nonempty` 中 R3_R top50 symbols 与 `TWII` 的最新日期；
2. 判断 `2026-06-18..2026-06-25` 的技术/市场特征为何只用到 `2026-06-01 / 2026-05-21`；
3. 如果存在更近的 R1 candidate normalized 或 staged refresh local files，优先在隔离目录读取，不切 formal provider latest；
4. 若必须补源，必须单独授权 isolated price/TWII source repair；
5. 补齐后重跑 R3_R，并比较 rerank 是否稳定。

若用户接受当前 freshness 风险，也可以进入：

```text
RCPT15_SHADOW_CONTINUATION_RERUN_WITH_R3_R_RERANK
```

但统筹建议优先做 freshness diagnostic，因为 stale 技术/市场特征可能影响 LTR rerank 的可信度。
