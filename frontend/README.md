# Clean 台股研究台

这是 `product-clean` 的唯一前端。它只读取 clean 后端的研究产物，提供：

- 今日候选榜单与策略意图
- Top30/Top50 排名和进入/离开变化
- Model A 与 Model A+B 的同日排名比较和可选历史回放指标
- 行情、MA20、RSI14、收益和量能背景
- 持久化 simulation-only 模拟账户（独立令牌、预览/确认/重置）
- 本地产物解释，不调用浏览器端 LLM

页面不包含券商、订单、quick-trade、monitor 写入、provider refresh、latest 切换或真实交易入口。

```bash
corepack pnpm install
corepack pnpm dev
corepack pnpm build
```

开发服务器默认把 `/api` 代理到 `http://127.0.0.1:5000`；可用 `TW_CLEAN_API_TARGET` 覆盖。只读前端验收由仓库根目录的 `scripts/accept_clean_frontend.py` 执行。

在仓库根目录执行 `node --test frontend/tests/*.test.js` 检查缺失数值显示；构建后执行 `python scripts/accept_clean_frontend.py --serve-build`，即可在自动分配的本地端口完成七页、三视口验收。浏览器批量验收使用 fixture 验证 paper 确认门槛；另有独立 owner 的正式端口模拟账本验收。本机 paper 路由已启用且需要签名令牌。脚本自动关闭临时服务；只允许同源本地 GET 和精确匹配 `/api/tw-stock/agent/simple-chat` 的只读 POST，其他请求发送前阻断。业务资料不足时仍返回失败，不能把 `ui_passed=true` 解读为正式资料已上线。

正式部署由 clean Gunicorn 同源提供 dist 与 API，入口为 `http://localhost:8000`。部署验收使用 `TW_CLEAN_FRONTEND_URL=http://127.0.0.1:8000 python scripts/accept_clean_frontend.py`；`--serve-build` 仅用于开发隔离验证。面试展示见 [演示路线](../docs/INTERVIEW_DEMO_CN.md)。
