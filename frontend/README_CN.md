# Clean 台股研究台

`product-clean` 的前端只展示 clean 后端提供的只读研究产物；另有独立的持久化 simulation-only 模拟账户页，使用后端签名令牌和明确的预览/确认门槛。

页面不包含券商、订单、quick-trade、monitor 写入、provider refresh、latest 切换或真实交易入口。

```bash
corepack pnpm install
corepack pnpm dev
corepack pnpm build
```

开发服务器默认将 `/api` 代理到 `http://127.0.0.1:5000`，可用 `TW_CLEAN_API_TARGET` 覆盖。仓库根目录的 `scripts/accept_clean_frontend.py` 提供只读三视口验收。
