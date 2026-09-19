# MBCDS3-5C_R 审查条件状态与关闭记录

日期：2026-09-06

## 1. 结论

`IMPLEMENTABLE_CONDITIONS_CLOSED / WAITING_EXTERNAL_EVIDENCE`

MBCDS3-5A_R 审查提出的 signal-time PIT-safe regime 实现条件已经关闭。该结论只允许继续 isolated、no-publish prospective shadow accumulation，不证明 Model A+Model B 优于 Model A，也不授权 baseline/default/latest/cron/provider/publish 变更。

## 2. 已关闭条件

| 条件 | 状态 | 关闭证据 |
|---|---|---|
| 冻结 signal-time regime 合同 | CLOSED | `MBCDS3_5_SIGNAL_TIME_PIT_SAFE_REGIME_CONTRACT_V1.json`，SHA256 `74e50aecda4353e74e9f34e8bbcd934a356738e1e8d8ced2c74751ef905d3ffe` |
| outcome 未见前冻结的 RSR2-derived existing-feature-frame adaptation | CLOSED | 明确不是逐字复用 RSR2 MA20/MA5；沿用其 crash/risk-off 阈值与优先级，并以 frozen Model B 已有 MA60/ret20 字段定义 risk-on；crash -> risk_off -> risk_on -> neutral，边界测试覆盖 |
| missing/non-finite fail closed | CLOSED | 不分类、不填补、不生成可评分 manifest |
| feature artifact 生成 signal-time regime | CLOSED | `signal_time_regime.json` 绑定 asof、cutoff、source run、feature frame 和 contract checksum |
| scorer 继承并独立重算 | CLOSED | scorer 校验合同、artifact、source、frame checksum，并从 150 行一致 TWII 字段重算 |
| SIGNAL_REGISTERED 封存 regime | CLOSED | event 写入 regime、artifact checksum、contract checksum |
| outcome 无权提供 regime | CLOSED | outcome builder 已删除 regime；settlement 对任意 outcome-manifest regime key fail closed |
| regime stability 使用 signal-time regime | CLOSED | `daily_comparison.csv` 和 grouped stability 读取 signal event，而非 outcome event |
| Model A non-blocking | CLOSED | feature/scorer failure 继续返回 isolated nonblocking status；既有 daily wiring 测试通过 |

## 3. 冻结分类合同

只消费 feature frame 中、来源可用时间不晚于 signal decision cutoff 的字段：

```text
TWII_close_vs_MA60
TWII_ret20
market_drawdown60
```

优先级：

1. `crash`: `market_drawdown60 <= -0.15`
2. `risk_off`: `TWII_close_vs_MA60 < 0` 或 `market_drawdown60 <= -0.08`
3. `risk_on`: `TWII_close_vs_MA60 >= 0` 且 `TWII_ret20 >= 0`
4. `neutral`: 其余有限、完整输入

任一字段缺失、非有限，或 150 行 cross-section 中 TWII 值不一致时，整日 fail closed。禁止使用 outcome、未来收益、entry/exit open 或 post-signal market data 分类。

## 4. 外部证据条件

以下条件依赖未来真实交易日和独立审查，不能由代码或 synthetic fixture 伪造完成：

| 条件 | 状态 | 完成门槛 |
|---|---|---|
| natural valid input accumulation | WAITING_EXTERNAL_EVIDENCE | 20 个真实 accepted prospective input days |
| first live end-to-end | WAITING_EXTERNAL_EVIDENCE | 首个真实 feature -> scorer -> SIGNAL_REGISTERED -> 后续 OUTCOME_SETTLED 全链路通过 |
| preliminary OOS comparison | WAITING_EXTERNAL_EVIDENCE | 60 个 settled paired OOS days |
| baseline review sample | WAITING_EXTERNAL_EVIDENCE | 120 个 settled paired OOS days，regime 全部来自 signal-time contract |
| exact strategy replay | WAITING_EXTERNAL_EVIDENCE | 120 日后单独执行相同费用、日历、持仓和成交语义 replay，并独立审查 |
| baseline switch decision | WAITING_REVIEW_NOT_AUTHORIZED | OOS 与 exact replay 均通过后仍须人工明确授权，不自动切换 |

## 5. 安全边界

本轮未修改 installed/actual cron、任何 latest pointer、provider、Qlib accepted latest、frontend/backend default 或 publish 配置；未训练、未调用 DB/OpenAI、未触发 broker/order/target。Model B 保持 shadow-only，失败不得阻塞 Model A。
