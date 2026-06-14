# Manual Review 浏览器只读验收入口方案

- 阶段：Phase R6
- 日期：2026-06-12
- 结论：推荐 R7 采用“测试专用 query flag / test-only mode 挂载 manual-review 最小区块 + Playwright 严格网络计数审计”的方案。

## 1. 背景问题

R5 没有直接执行浏览器 smoke，原因不是 manual-review 模块本身需要写入，而是现有 `/tw-stock-monitor` 整页挂载链路会触发既有：

- `POST /api/tw-stock/rank-tech-cross/portfolio-replay`

该请求来自既有历史模拟面板，不是 manual-review 新增能力，也不是人工复盘解释模块的必要请求。但它会污染“浏览器只读验收”的网络审计结果，使验收无法证明 manual-review 本身只走只读路径。

因此 R6 需要先设计一个干净、可审计、只覆盖 manual-review 的浏览器验收入口，供 R7 实现。

## 2. 目标

R7 浏览器验收入口只验证：

- manual-review 区块能在浏览器中渲染。
- 用户能看到 `复盘线索` 相关只读内容。
- 页面发起 `GET /api/tw-stock/manual-review/explanation`。
- 浏览器运行过程中没有台股业务写请求。
- 页面文案不出现买卖、仓位、收益、概率或胜率语义。

验收应能输出可审查的 network 计数，而不是只用人工观察说明。

## 3. 非目标

本方案不做：

- 字段映射增强。
- 新数据源。
- 联网或 token。
- 模型训练。
- qlib provider 写入。
- provider refresh/publish。
- accepted latest switching。
- monitor config 保存。
- monitor scan 或 scan-all。
- alerts 写入。
- broker、quick-trade、orders。
- target position 或 target weight。
- 买入、卖出、持有建议。
- 仓位建议、收益承诺、上涨概率或胜率承诺。
- 新产品页或复杂调试台。

## 4. 候选方案对比

| 方案 | 变更面 | 用户可见性 | 网络请求面 | 安全风险 | 前端改动 | 后端改动 | 能否证明只测 manual-review | 是否适合 R7 |
|---|---|---|---|---|---|---|---|---|
| A. Query flag / test-only mode 最小挂载 | 小。只在测试参数存在时让页面进入 manual-review-only 渲染路径，或挂载同一组件的最小容器 | 不进入导航，不作为用户入口宣传；只由测试 URL 使用 | 只允许 manual-review GET、静态资源、必要只读 bootstrap/auth GET | 风险低，但必须保证不改变真实页面默认行为 | 需要小改动 | 不需要 | 能。因为不挂载整页历史模拟链路，且 Playwright 记录所有请求 | 推荐 |
| B. 专用只读测试 route | 中。新增一个测试专用 route，只承载 manual-review 区块 | 若路由可直接访问，需要清楚标记为测试/开发态，不能变成产品入口 | 可做到只请求 manual-review GET | 风险中。新增 route 容易被误解为新页面或调试产品 | 需要新增 route/页面 | 不需要 | 能，但新增入口面比 A 大 | 可备选，不优先 |
| C. Playwright route mock/intercept | 小到中。主要改测试，用拦截处理非 manual-review 请求 | 用户不可见 | 可以拦截 portfolio replay POST，但仍可能说明页面曾主动发出危险请求 | 风险中高。若只拦截并放行测试，会掩盖真实整页触发了 POST 的事实 | 通常不需要，或很少 | 不需要 | 弱。必须区分“发出后被拦截”和“根本未发出” | 不推荐作为主方案 |

## 5. 推荐方案

推荐 R7 采用方案 A：

> 在现有前端中增加测试专用 query flag / test-only mode，使 Playwright 可以打开一个 manual-review-only 的最小渲染路径；该路径只挂载人工复盘解释区块或最小容器，不挂载会触发 portfolio replay 的整页链路。同时，Playwright 记录所有浏览器请求，并用 allowlist/denylist 计数审计。

推荐理由：

- 最小：只为验收绕开整页挂载噪音，不新增后端 API、不接新数据源、不改 manual-review 业务语义。
- 清晰：测试 URL 能明确表达“只验收 manual-review 区块”。
- 准确：network 审计能证明没有危险请求，而不是把危险请求拦截后当作通过。
- 实用：R7 执行者可以直接实现 Playwright smoke，并输出固定计数字段。

不优先选择方案 B 的原因：

- 新增专用 route 的变更面更大，容易被误解为新增用户入口或调试产品。
- 当前目标只是验收入口，不需要创建新的产品路径。

不选择方案 C 作为主方案的原因：

- 纯拦截可以让测试通过，但无法证明页面没有主动发出危险请求。
- R7 若使用拦截，也只能用于“计数并失败”，不能用于隐藏危险请求。

## 6. Network Allowlist

R7 浏览器验收建议只允许：

- `GET /api/tw-stock/manual-review/explanation`
- 前端静态资源请求，例如 JS、CSS、图片、字体、source map。
- 必要的应用启动只读 GET，例如本地开发服务的页面 HTML、健康检查、只读 auth/bootstrap GET。若实际出现，R7 报告必须逐项列出 URL、方法、用途，并说明为什么不属于台股业务写入。

allowlist 不应包含任何台股业务 POST/PUT/PATCH/DELETE。

## 7. Dangerous Request Denylist

R7 浏览器验收必须把以下请求计为 forbidden，并在出现时失败：

- 任意台股业务 `POST`、`PUT`、`PATCH`、`DELETE`。
- `POST /api/tw-stock/rank-tech-cross/portfolio-replay`
- `POST /api/tw-stock/monitor/config`
- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`
- `POST /api/tw-stock/monitor/alerts`
- `PUT /api/tw-stock/monitor/alerts/*`
- `PATCH /api/tw-stock/monitor/alerts/*`
- `DELETE /api/tw-stock/monitor/alerts/*`
- `POST /api/tw-stock/quant/ops/**`
- 任意 provider refresh/publish 相关请求。
- 任意 accepted latest switching 相关请求。
- `POST /api/quick-trade/**`
- 任意 `/api/broker/**`
- 任意包含 `order` 的业务请求。
- 任意包含 `target-position` 的业务请求。
- 任意包含 `target_weight` 的业务请求。

R7 不应通过 abort/fulfill 将这些请求“静默处理”为成功。只要浏览器发出，就应计数并失败。

## 8. R7 实现边界

R7 可以实现：

- 一个测试专用 query flag / test-only mode。
- 一个 Playwright readonly smoke。
- 一个只读 network 审计 summary artifact。
- 必要的 fixture 或 mock response，仅用于 manual-review GET 的浏览器展示稳定性。

R7 不应实现：

- 新后端 route。
- 新业务 API。
- 新数据源。
- 字段映射增强。
- 真实数据刷新。
- provider refresh/publish。
- accepted latest switching。
- monitor 写入或扫描。
- broker、quick-trade、orders。
- 交易语义文案。

如果 R7 发现必须新增专用 route、修改真实页面默认挂载逻辑、禁用既有业务功能，或必须触发任何写请求，应停止并回到审查者。

## 9. R7 验收 Gate

R7 产物必须报告并满足：

- `forbidden_request_count=0`
- `manual_review_get_count>=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

建议 R7 同时保留：

- 浏览器页面截图或文本摘要。
- network 请求清单。
- console error/warning 摘要。
- Playwright 退出码。

## 10. 必须停下来讨论的情况

出现以下情况时，R7 不应继续实现或扩大范围：

- 需要联网、token 或拉取数据。
- 需要新增数据源。
- 需要训练模型。
- 需要改 qlib provider 或 materialize 数据。
- 需要 provider refresh/publish。
- 需要 accepted latest switching。
- 需要 monitor config 保存、monitor scan、scan-all 或 alerts 写入。
- 需要 broker、quick-trade、orders。
- 需要 target position 或 target weight。
- 需要买入、卖出、持有、仓位、收益、上涨概率或胜率语义。
- 需要把验收入口变成用户可见的新产品页。
- 需要同时实现完整上下文字段映射。

## 11. 推荐 Gate

建议进入：

`request_phaser7_browser_readonly_acceptance_implementation`

