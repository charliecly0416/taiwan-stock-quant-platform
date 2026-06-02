# 最大生产闭环说明

## 目标

本项目的最大闭环目标是把原来分散在以下项目中的台股研究链路收敛到单个独立项目：

- QuantDinger backend
- QuantDinger-Vue frontend
- qlib 台股 Option C 量化研究与预测脚本
- Scrapling/Yahoo 数据拉取 handoff
- FinMind/TWSE 台股归档、补数、校验脚本

闭环范围：

```text
FinMind/TWSE/Yahoo/Scrapling 拉取与补数
-> normalized CSV, 150 股票 2015 至今
-> qlib provider/bin
-> Alpha158 + LightGBM frozen model / daily signal
-> accepted latest artifact
-> QuantDinger backend qlib reader / trend / cross-analysis / Agent
-> QuantDinger-Vue frontend 展示
-> human review
```

## 已迁入仓库的生产代码

- `backend/`：QuantDinger 台股后端服务、API、Agent、cross-analysis、qlib signal reader、EOD ops wrapper。
- `frontend/`：QuantDinger-Vue 台股监控前端。
- `backend/scripts/`：FinMind/TWSE 台股 daily/archive/update/validate/export 等脚本。
- `crawler/yahoo_scrapling/`：内置 Yahoo/Scrapling 基础 crawler 和 validator。
- `crawler/scrapling_handoff/`：原 Scrapling handoff 脚本、数据契约、source playbook、FinMind supplement 脚本。
- `qlib_pipeline/examples/tw/`：原 qlib 台股 examples/tw 研究、因子、Option C daily prediction/signal、Yahoo/Scrapling refresh/publish 脚本。
- `qlib_pipeline/configs/`：原 qlib 台股 Alpha158/LightGBM 配置。
- `qlib_pipeline/scripts/`：`dump_bin.py`、`export_tw_qlib_normalized.py`。
- `qlib_pipeline/qlib_extensions/`：台股 qlib handler/strategy 扩展代码备份。

## 数据与模型资产策略

不把大数据和模型文件直接提交到 Git：

- `qlib_pipeline/data_tw/`：ignored，本地生成或 bootstrap。
- `qlib_pipeline/mlruns/`：ignored，本地生成或 bootstrap。
- `data_tw/`：ignored，本地 demo/验证输出。

原因：

- 原 qlib `data_tw` 约 6.7G。
- Yahoo primary full normalized 约 604M。
- frozen model `mlruns` 约 316M。
- 这些内容更适合作为 GitHub Release artifact、对象存储、或由脚本重新生成。

## 本机复刻原效果

如果机器上保留原 `/home/chuliyang/qlib`，运行：

```bash
python scripts/bootstrap_full_production_assets.py --replace
python scripts/verify_full_production_loop.py
```

当前验证结果：

- Option C 150 normalized：150 支股票。
- 最新日期：`2026-06-01`。
- accepted latest：`option_c_daily_signal_20260601_20260602T090715Z`。
- 后端 reader：latest/top30/top50/health 通过。
- qlib Option C provider dry-run：通过。

后端运行时建议设置：

```bash
export QLIB_TW_OPTION_C_ROOT=/path/to/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/option_c_daily_signal
export TW_QLIB_OPTION_C_CWD=/path/to/taiwan-stock-quant-platform/qlib_pipeline
export TW_QLIB_OPTION_C_PROVIDER_CALENDAR=/path/to/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

## GitHub 发布方式

仓库提交代码、配置、脚本、文档、测试，不提交 generated market data 或 model artifacts。

建议发布资产：

1. `option_c_150_normalized.tar.zst`
2. `option_c_150_qlib_bin.tar.zst`
3. `option_c_daily_signal.tar.zst`
4. `frozen_mlruns_recorder_950741cfd5f14ee5a05464fec3e12e0a.tar.zst`

用户 clone 后有两条路径：

- 使用 release artifacts 解压到 `qlib_pipeline/data_tw/` 和 `qlib_pipeline/mlruns/`。
- 使用仓库内 crawler/export/dump/signal 脚本从头生成。

## 当前判定

本机独立项目已经达到最大闭环的核心效果：真实 150 股票、2015 至今数据资产、qlib frozen model、accepted latest、后端读取、前端代码、FinMind/TWSE/Yahoo/Scrapling 脚本都已纳入或可 bootstrap 到独立项目。

剩余不是功能缺口，而是发布形态问题：GitHub 仓库应保持轻量，生产数据和模型用 release artifact 或外部存储交付。
