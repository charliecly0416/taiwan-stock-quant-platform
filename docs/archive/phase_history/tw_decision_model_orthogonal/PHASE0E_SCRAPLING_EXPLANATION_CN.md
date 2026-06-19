# Phase 0E 未使用 Scrapling 原因说明

## 1. 说明范围

本说明仅补充 Phase 0E 为什么未使用 Scrapling。

本次不重拉数据、不联网、不新增数据源、不启用月营收、不构建 Phase 1B 样本、不做单因子检验、不训练模型、不进入 Phase 2、不触碰 provider refresh/publish、accepted latest switching、前端/API 或交易路径。

## 2. 为什么 Phase 0E 没有使用 Scrapling

Phase 0E 实际使用的是 FinMind 官方 API endpoint：

- `https://api.finmindtrade.com/api/v4/data`
- `TaiwanStockInstitutionalInvestorsBuySell`
- `TaiwanStockMarginPurchaseShortSale`

该 endpoint 是结构化 JSON API，支持通过 `dataset`、`data_id`、`start_date`、`end_date` 参数直接取得 row-level 数据，并通过 API token 做授权。对这种 API 调用，`requests.get()` 是更直接、更可控的实现方式：

- 可以显式传入 query parameters。
- 可以显式设置 `Authorization` header。
- 返回值是 JSON，不需要浏览器 DOM 解析。
- 更容易控制 timeout、错误类型、row_count、download status 与 token 脱敏。
- 更容易保证不触发登录、验证码、页面脚本或非必要网页访问。

因此，未使用 Scrapling不是因为不知道 Scrapling 是什么，而是当时判断 FinMind API endpoint 不需要浏览器式抓取能力，使用 `requests` 更贴合授权 API 的数据形态。

## 3. 是否检查过 Scrapling 可用性

Phase 0E 执行前没有单独运行 Scrapling 可用性检查。

原因是：

- 工作文档允许使用 Scrapling，也允许使用 FinMind API token 或等价 API token。
- 本次目标数据源已经有明确 API endpoint。
- Phase 0E 的主线目标是扩展 raw archive backfill 与 PIT 审计，不是验证网页抓取框架。
- 使用 `requests` 已满足授权 endpoint、token、download status、manifest、coverage、PIT validation 和 token 脱敏要求。

这点与用户偏好存在偏差：用户提到“使用 Scrapling 和 API token”，我没有在报告中主动解释为什么没有使用 Scrapling，这是本次需要补充说明的缺口。

## 4. 如果未来强制要求 Scrapling，应如何实现

如果后续审查者或用户强制要求 Scrapling 参与同类数据拉取，我会采用以下方式，不改变主线边界：

1. 新增专用脚本或参数，例如 `--transport scrapling`，仍只写 Phase 专用输出目录。
2. token 继续只从运行时输入或环境变量读取，不写入脚本、日志、CSV、JSON、Markdown。
3. 使用 Scrapling 对同一授权 FinMind API URL 发起 GET 请求，而不是新增数据源。
4. 请求参数仍限定为授权 dataset：
   - `TaiwanStockInstitutionalInvestorsBuySell`
   - `TaiwanStockMarginPurchaseShortSale`
5. 不绕过登录、付费墙、验证码或访问控制。
6. 记录与当前一致的审计字段：
   - `source_url`
   - dataset
   - status
   - row_count
   - error_type
   - error_message
   - token_used
7. 输出仍进入 `data_tw/experiments/decision_orthogonal/phase*_...` 专用目录，不写 Qlib bin/provider，不触碰 accepted latest。

也就是说，未来若使用 Scrapling，它应只是 HTTP transport 的替换或 source availability verification 手段，而不是改变数据源、扩大范围或进入后续研究阶段。

## 5. 为什么本次未使用 Scrapling 不影响数据可用性

本次 Phase 0E 数据可用性主要由以下证据支持，而不是由具体 HTTP client 决定：

- download status 显示 300 个授权请求均为 success。
- raw response JSONL 已保留每个 symbol/category 的原始返回证据。
- normalized PIT archive 只保留 `available_at` 非空的 PIT-valid rows。
- 法人筹码 normalized PIT rows：158834。
- 融资融券 normalized PIT rows：156021。
- 两类数据实际 PIT-valid trade date 范围为 2022-01-03 至 2026-05-29。
- 两类各有 1529 raw rows 因无法由本地交易日历生成下一交易日 `available_at` 被排除，没有静默进入 normalized archive。
- manifest、coverage report、PIT validation samples、quality flags summary 均已生成。

FinMind API 返回的 JSON 内容、字段和 row_count 不依赖 Scrapling。Scrapling 与 `requests` 在这里主要是 transport 层差异；只要 endpoint、dataset、参数、token 授权和返回内容一致，当前 archive 仍可作为后续 Phase 1B 审查候选输入。

## 6. Token 未泄露保证

Phase 0E token 处理遵循以下规则：

- token 由用户在聊天框提供后，通过运行时临时输入注入。
- 脚本支持 `--token-stdin`，不要求把 token 写入命令行参数。
- 执行报告中的命令是脱敏命令，不包含 token 原文。
- download status 只记录 `token_used=True`，不记录 token 内容。
- manifest、coverage、PIT validation、quality flags 不包含 token 字段。
- raw response JSONL 中只记录 `token_used` 布尔值，不记录 token 内容。
- 已对 Phase 0E 报告、Phase 0E 产物和脚本做 token 原文/Authorization/Bearer 形式扫描，未发现 token 原文写入。

需要注意：用户曾在聊天框直接贴出 token；这属于对话层面的暴露，不是仓库文件或 Phase 0E 产物泄露。后续若用户希望降低凭证风险，应在数据源侧轮换 token。

## 7. 结论

Phase 0E 未使用 Scrapling的原因是执行者判断 FinMind 结构化 API 用 `requests` 更合适，并非不知道如何使用 Scrapling。

该选择没有改变授权数据源、数据范围、PIT 规则或安全边界，也不影响当前已生成 raw archive 的审查价值。

后续如审查者要求 Scrapling parity 或 Scrapling transport，可在不扩大数据范围、不重定义数据源、不进入 Phase 1B/Phase 2 的前提下实现。
