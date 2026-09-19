# TradingAgents Readonly TA7 Final Acceptance 审查报告

生成日期：2026-07-10

## 1. Verdict

PASS

说明：TA7 初次验收后曾发现 `sanitized_report.md/json` 仍保留 TradingAgents 原始策略/动作语义，例如 `续抱`、`追价`、`分批加码`、`新增曝险`、`停损`、`权重` 等。该问题已在修复轮中关闭：`controlled_real_run` 展示 artifact 改为 metadata-only，不再透传外部框架正文；原始输出仅保留在 `raw_untrusted`、`display_allowed=false` 文件中。

## 2. Findings

### Critical

无。

### High

无。

### Medium

- 2026-06-30 controlled real run 仍受 Yahoo chart HTTP 403 阻塞。该问题已被隔离为数据访问分支，不影响 2026-06-01 成功 artifact 对迁移链路的验收。
- controlled real run 的 `quality_status=warning` 合理，因为展示 artifact 不再承载外部正文，只作为人工复核入口；raw 输出不进入 GET/API/frontend 展示面。

### Low

- TA7 artifact 的 `quality_status=warning` 合理，因为 TradingAgents 输出是外部研究线索，仍要求人工复核。
- 已处理审查 Low 项：
  - `forbidden_semantics_audit.forbidden_patterns` 改为从当前 builder 正则名自动生成。
  - GET public payload 的 `manifest` 裁掉 `input_artifacts`，避免 `backend_url` 进入 API/前端展示面。repo 内 artifact manifest/input index 仍保留运行输入，作为审查复现材料。

## 3. Mainline Compliance

通过。

- `third_party/tradingagents` 已在本仓库内。
- 运行时不依赖 `/home/chuliyang/TradingAgents`。
- controlled real run 已使用 repo-local TradingAgents 和本项目 `quantdinger_tw` 行情 provider。
- GET-only loader 返回 public payload，`raw_files_included=false`。
- frontend readonly panel 仅使用 GET helper。
- 未更新 latest。
- 未修改默认模型/策略/accepted latest。
- 未触发 provider publish、monitor write、broker/order/quick-trade。

## 4. Evidence Checked

```text
controlled artifact validator: ok=true, check_count=55
manual sanitized grep for prior leakage terms: no output
backend regression: 56 passed, 1 skipped
frontend static check: tw-stock-tradingagents-readonly-panel-check passed
GET-only loader: True pass ta6_2330_20260601_market_smoke True False / raw path absent / backend_url absent / chat.pku.edu.cn absent / forbidden audit true
vendor clean check: no output
latest/accepted pointer check: no output
```

## 5. Missing Evidence Or Open Questions

- 没有成功生成 2026-06-30 artifact；原因是 Yahoo chart HTTP 403，不是 TradingAgents 迁移链路失败。
- 没有运行完整浏览器 e2e；TA7 本轮以 existing backend tests + frontend static check 验收 readonly panel 合同。

## 6. Forbidden Actions Audit

通过。

未发现：

```text
broker/order/quick-trade
provider publish
accepted latest switch
latest pointer update
default model/strategy change
raw TradingAgents decision semantics exposed through GET loader
raw TradingAgents tactical prose exposed through sanitized_report.md/json
```

## 7. Next Work Document

TradingAgents readonly migration 主线可关闭。

后续可选分支：

1. Yahoo access repair：cookie/crumb/proxy/header/节流，仅处理 Scrapling Yahoo chart 403。
2. Runtime-only fallback data source：补齐 TradingAgents controlled real run 所需行情，但不得 publish provider/latest。
3. 如果要把 TradingAgents analysis 纳入日常 Agent context，必须另开 release gate，并继续保持 sanitized artifact-only。

## 8. Command For Coordinator

关闭本 TradingAgents readonly migration 主线；后续数据补齐作为独立 route 管理。
