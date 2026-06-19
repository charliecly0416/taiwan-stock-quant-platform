# Phase C5 执行报告：前端默认研究基线切换

生成日期：2026-06-15

## 1. 执行目标

将台股页面的默认研究基线从 `phase1c_ltr_simple_daily` 切换为：

```text
rank_rotate_top50_adaptive_score
Fresh qlib Top50 滚动默认基线
```

本阶段只改只读产品视图和前端默认选择，不训练模型、不重跑回测、不触发数据刷新、不切换 accepted latest、不触发交易链路。

## 2. 后端改动

文件：

```text
backend/app/services/tw_ltr_optional_sim_strategy.py
```

改动：

- `default_method_key` 改为 `rank_rotate_top50_adaptive_score`。
- `phase1c_ltr_simple_daily` 改为 LTR 研究参考，不再是默认主策略。
- `rank_rotate_top50_adaptive_score` 展示为 Fresh qlib Top50 滚动默认基线。
- 新增 `daily_update_contract`，明确默认基线读取每日 accepted qlib Top30/Top50 signal artifacts。
- 明确每日自动化入口：`scripts/run_daily_tw_stock_auto_update.py`。
- 明确 accepted latest 来源：`qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`。
- 明确只读边界：不触发刷新、不下单、不写仓位。

## 3. 前端改动

文件：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

改动：

- 页面初始选择从 `phase1c_ltr_simple_daily` 改为 `rank_rotate_top50_adaptive_score`。
- 面板标题改为“默认研究基线与可选模拟策略”。
- 标签从“默认主策略”改为“默认基线”。
- 提示文案说明默认基线读取每日 accepted qlib Top50 排名。
- 策略回放卡片顺序将 Top50 adaptive 放在第一位。
- Top50 adaptive 简述改为“默认基线”。

## 4. 自动化适配确认

当前每日自动化脚本已经包含完整链路：

```text
FinMind raw update
-> Yahoo/Scrapling Option C 150 provider refresh
-> provider publish
-> publish_accepted_latest(asof)
-> qlib option_c_daily_signal/latest_signal.json
```

关键代码位置：

```text
scripts/run_daily_tw_stock_auto_update.py
```

`publish_accepted_latest(asof)` 成功后，后端 readonly reader `QlibOptionCSignalReader` 会读取最新 accepted signal：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

因此每日成功拉到新数据并发布 accepted latest 后，Top30/Top50 排名会自动更新；基于 Top50 的默认研究基线会读取最新排名产物。C5 不需要新增定时任务。

## 5. 边界

未执行：

- qlib 训练；
- LTR 训练；
- 数据拉取；
- provider refresh / publish；
- accepted latest switching；
- monitor scan；
- broker / orders / quick-trade / target position；
- 任何真实买卖或仓位建议。

## 6. 结论

C5 完成默认研究基线切换：

```text
默认：Fresh qlib Top50 滚动 / rank_rotate_top50_adaptive_score
保留：LTR simple 作为可选研究参考
```

该默认基线已适配原有 daily auto update 链路：每日 accepted latest 更新后，页面读取最新 qlib signal artifacts。
