# 单仓库自包含闭环说明

## 目标

本项目支持两种闭环模式：

1. `self_contained_demo`：clone 单个仓库后，不依赖外部 `/home/chuliyang/qlib` 或 `/home/chuliyang/Scrapling`，用仓库内脚本和本地 fixture 跑通最小闭环。
2. `production_integrated`：真实每日市场结束后，用 Yahoo/Scrapling 或其他生产数据源补数，再进入 qlib Option C 训练/预测/accepted latest 发布，最后由 QuantDinger 后端和 QuantDinger-Vue 前端展示。

## 已内置的自包含闭环

仓库内新增：

- `crawler/yahoo_scrapling/crawl_yahoo_scrapling.py`
- `crawler/yahoo_scrapling/validate_output.py`
- `qlib_pipeline/option_c/build_self_contained_option_c_signal.py`
- `scripts/verify_self_contained_closed_loop.py`

验证链路：

```text
本地 150 支台股 fixture normalized CSV
-> qlib_pipeline/option_c/build_self_contained_option_c_signal.py
-> data_tw/experiments/option_c_daily_signal/latest_signal.json
-> QuantDinger backend QlibOptionCSignalReader latest/top30/top50/health
```

执行：

```bash
python scripts/verify_self_contained_closed_loop.py
```

通过后会生成：

- `data_tw/self_contained_demo/normalized/TW*.csv`
- `data_tw/experiments/option_c_daily_signal/latest_signal.json`
- `data_tw/experiments/option_c_daily_signal/<run_id>/top30_signals.csv`
- `data_tw/experiments/option_c_daily_signal/<run_id>/top50_signals.csv`
- `docs/SELF_CONTAINED_CLOSED_LOOP_REPORT_CN.json`

这些 `data_tw/` 文件属于本地生成数据，不应提交到 Git。

## 生产闭环仍需补齐或接入的部分

当前内置的 `build_self_contained_option_c_signal.py` 是 demo artifact 生成器，目的是验证单仓库闭环和后端契约。它不是生产级 qlib LightGBM/Alpha158 训练替代品。

生产模式建议继续补齐：

1. 将 qlib 侧正式脚本迁入 `qlib_pipeline/option_c/`，至少包括：
   - provider dump/build
   - Alpha158/LightGBM config
   - daily prediction/signal
   - Yahoo/Scrapling refresh
   - reviewed publish/rollback metadata
2. 将后端 EOD pipeline 默认路径从 `/home/chuliyang/qlib` 改为 repo-local 默认或环境变量必填。
3. 增加 live-data smoke：小股票池 Yahoo/Scrapling 拉数、validate、生成 accepted latest、后端 API、前端静态或 Playwright 检查。
4. 保持 research-only 边界：不接 broker、不下单、不自动生成交易指令。

## 判定

现在项目已经具备“单仓库最小自包含闭环验证能力”。

如果目标是公开 GitHub 后让别人 clone 即可验证项目形态，当前方向成立。如果目标是 clone 后直接跑真实市场每日全量 qlib 训练预测，则还需要继续做生产 qlib pipeline 内迁和真实 Yahoo/Scrapling smoke。
