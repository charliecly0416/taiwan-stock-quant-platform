# 独立项目闭环验证报告

## 结论

当前 `taiwan-stock-quant-platform` 已经可以作为一个“QuantDinger 后端 + QuantDinger-Vue 前端 + 外部 qlib/Scrapling 生产链路”的组合研究平台运行，但还不是单仓库完全自足闭环。

可以闭环的部分：

- QuantDinger 后端台股 API、趋势分析、监控、cross-analysis、Agent context/chat、qlib accepted latest 读取链路存在并通过测试。
- QuantDinger-Vue 前端台股监控页、qlib 排名展示、cross-analysis 展示、Agent panel 和 dry-run ops 展示通过静态/契约检查。
- FinMind/TWSE 口径的台股补数、归档、校验和 normalized CSV 导出脚本存在。
- qlib Option C 的 accepted latest artifact 读取、health、runs、run detail、ops dry-run、scheduler、EOD automation wrapper 存在并通过核心测试。
- 安全边界保持 research-only，不默认连接 broker、不下单。

尚未自足闭环的部分：

- 仓库内没有可执行 Scrapling Yahoo crawler。Scrapling/Yahoo 拉数目前主要是文档 handoff，指向外部 `/home/chuliyang/Scrapling/qlib_scrapling_handoff` 方法。
- 仓库内没有 qlib 侧完整训练/预测脚本，例如 `examples/tw/run_option_c_daily_signal_option_c_provider.py`、`examples/tw/run_option_c_yahoo_scrapling_refresh.py`、`examples/tw/publish_option_c_yahoo_scrapling_refresh.py`。
- EOD pipeline 当前通过环境变量/默认路径调用外部 `/home/chuliyang/qlib` 项目。因此它能对接外部 qlib，但不是单仓库内独立完成训练、预测和 accepted artifact 发布。
- 默认配置下 EOD automation、accepted latest scheduler、normal publish gate 都是 disabled-by-default，需要显式环境变量、外部 qlib 路径和人工 review gate。

## 验证结果

已通过：

```bash
cd backend
python -m pytest tests/test_tw_stock_qlib_option_c_ops.py -q
# 54 passed
```

```bash
cd backend
python -m pytest tests/test_tw_stock_agent_context.py tests/test_tw_stock_agent_chat.py tests/test_tw_stock_cross_analysis_service.py tests/test_tw_stock_cross_analysis_api.py tests/test_tw_stock_qlib_option_c_signals.py tests/test_tw_stock_quant_signal_api.py -q
# 97 passed
```

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
# all passed
```

发现并修复：

- `backend/scripts/verify_tw_stock_research_stack.py` 在独立仓库中从 `backend/` 目录执行时仍使用旧 `backend/tests/...` 相对路径，已改成基于仓库根目录解析。
- `backend/tests/test_tw_stock_research_workflow.py` 仍检查旧 workflow 名称 `tw-stock-research.yml`，已改为 `backend-tw-stock-research.yml`。

## 闭环分级

### 组合闭环：基本成立

在同一机器或部署环境中同时准备：

1. 本仓库后端和前端。
2. PostgreSQL 数据库。
3. 外部 qlib 项目及 Option C scripts。
4. 外部 Scrapling/Yahoo crawler 或已生成的 qlib provider/artifacts。
5. 环境变量指向 qlib artifact root。

此时可以形成：

```text
Scrapling/Yahoo or FinMind/TWSE data
-> qlib provider / accepted latest artifacts
-> QuantDinger backend qlib reader + trend + cross-analysis + Agent
-> QuantDinger-Vue tw-stock-monitor frontend
-> human review
```

### 单仓库自足闭环：尚未成立

缺口是生产端：Scrapling crawler 和 qlib Option C 训练/预测/发布脚本没有被纳入本仓库。

## 建议补齐方向

如果目标是上传 GitHub 后别人 clone 本仓库即可完整跑通，建议增加 Phase Package-A：

1. 新增 `crawler/yahoo_scrapling/`：放入可执行 Scrapling Yahoo chart API crawler、validator、symbols 输入、输出 contract。
2. 新增 `qlib_pipeline/option_c/`：放入 qlib provider dump、Alpha158/LightGBM config、daily signal wrapper、refresh/publish wrapper。
3. 改造后端 EOD pipeline 默认路径：从 `/home/chuliyang/qlib/...` 改为仓库内 `qlib_pipeline/...` 或环境变量必填。
4. 新增端到端 dry-run fixture：用 3-5 支台股 mock/cached CSV 跑 crawler validate -> normalized -> accepted artifact -> API -> frontend static check。
5. README 明确两种模式：`integrated-with-external-qlib` 和 `self-contained-demo`。

## 当前发布建议

当前版本可以发布，但 README 应描述为“打包版研究平台 + 外部 qlib/Scrapling 生产链路集成”，不要描述为“单仓库内置 Scrapling 拉数和 qlib 训练预测全闭环”。
