# DNG2 PriceStore / TWII / Calendar 审查报告

生成日期：2026-06-29

审查者：DNG2 Reviewer

## 1. 审查结论

Verdict：`FAIL_NEEDS_DNG2_REPAIR`

DNG2 执行结果不能进入 DNG3。原因不是脚本或产物结构失败，而是 DNG2 自己的 readiness gate 明确为：

```text
status=BLOCKED_COVERAGE
can_continue=false
```

关键阻断项：

1. TWII canonical artifact 只到 `2026-05-21`，而本轮 provider calendar / PriceStore asof 为 `2026-06-25`，近期缺口覆盖 `2026-05-22` 至 `2026-06-25` 的多日交易日。
2. PriceStore 为 `PARTIAL_READY`，不是 READY。它虽然覆盖到 `2026-06-25`，但 `halt_flag` 源数据不可得，且 18 个标的没有覆盖完整 provider calendar 历史区间。
3. `next_day_execution_availability` dependency 为 `can_continue=false`。最新 asof 行没有下一交易日价格行，且停牌/暂停交易证据缺失，不能支持下一交易日执行可用性判断。

因此本轮不是 `PASS_WITH_CONDITIONS_GO_DNG3`。DNG3 正交数据规范化依赖一个可用的 price / TWII / calendar 基础层；在 TWII 与 next-day execution readiness 未修复前，继续进入 DNG3 会把下游正交特征、模型输入、策略输入包和回放建立在不完整市场上下文上。

## 2. 已审查输入

已阅读：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_WORK_CN.md`
- `docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_canonical_price_market_calendar.py`
- `scripts/validate_tw_canonical_price_market_calendar.py`
- `data_tw/catalog/dng2_price_market_calendar_validation.json`
- `data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/manifest.json`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_price_market_calendar_20260625/manifest.json`

辅助核对：

- PriceStore `coverage_audit.csv`
- PriceStore `execution_availability_audit.csv`
- TWII `coverage_audit.csv`
- 脚本敏感入口检索结果

## 3. 本地验证结果

执行：

```bash
python -m py_compile scripts/build_tw_canonical_price_market_calendar.py scripts/validate_tw_canonical_price_market_calendar.py
```

结果：通过，退出码 0。

执行：

```bash
python scripts/validate_tw_canonical_price_market_calendar.py --run-id dng2_price_market_calendar_20260625 --asof 2026-06-25 --json
```

结果摘要：

```text
ok=true
status=BLOCKED_COVERAGE
errors=0
warnings=0
prices row_count=400205
twii row_count=2771
price_store=PARTIAL_READY
twii=BLOCKED_COVERAGE
readiness_matrix=BLOCKED_COVERAGE
can_continue=false
```

审查解释：`ok=true` 只说明 validator 能运行且 required files / fields / forbidden flags 等结构检查通过；它不表示业务 readiness 通过。业务 gate 仍然是 `BLOCKED_COVERAGE`。

## 4. 结构与安全边界审查

DNG2 执行已生成工作单要求的基础文件：

- PriceStore manifest / prices / schema / coverage / adjustment / execution availability / lineage
- TWII manifest / twii / schema / coverage / lineage
- readiness matrix
- validation JSON

脚本审查未发现真实抓数、provider refresh/publish、qlib accepted latest switch、readonly latest publish、Agent prompt publish、模型训练/推理、策略回放、broker/order/quick-trade、target_position 或 target_weight 入口调用。脚本中相关命中均为 forbidden fields、forbidden action flags、manifest 标记或状态说明。

manifest、lineage、readiness matrix 与 validator 均记录 forbidden action flags 为 false：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
model_training_triggered=false
model_inference_triggered=false
strategy_replay_triggered=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

结论：DNG2 的执行边界合格；失败点在数据覆盖和 readiness gate，不在越权动作。

## 5. PriceStore 审查

PriceStore manifest：

```text
status=PARTIAL_READY
asof=2026-06-25
date_min=2015-01-05
date_max=2026-06-25
symbol_count=150
row_count=400205
```

正向证据：

- required fields 存在。
- forbidden fields 未发现。
- OHLCV、close、adj_factor、tradable_flag、price_source、adjustment_policy 字段覆盖为 100%。
- mark-to-market close coverage 对 `2026-06-25` 为 READY。
- PriceStore 未发布 latest，也未切 qlib accepted latest。

阻断或风险：

- `halt_flag` 覆盖为 0%，schema 标为 `missing_in_source`，不能当作真实停牌/暂停交易证据。
- 18 个标的未覆盖完整 provider calendar 历史区间。执行报告判断主要是新上市或源历史较短标的；这可以解释 partial，但仍必须由后续 route 明确是否接受该 universe/history 缺口。
- PriceStore 状态是 `PARTIAL_READY`，不能被 DNG3 或后续模型/策略默认解释为 canonical full READY。

审查结论：PriceStore 可以作为 DNG2 repair 的中间产物和证据，但不能作为无条件下游基础层。

## 6. TWII / MarketFeatureStore 审查

TWII manifest：

```text
status=BLOCKED_COVERAGE
asof=2026-05-21
date_min=2015-01-05
date_max=2026-05-21
row_count=2771
```

TWII coverage audit：

```text
expected_calendar_count=2789
calendar_covered_count=2760
coverage_ratio=0.989602
missing_date_count=29
status=BLOCKED_COVERAGE
```

关键缺口包括：

```text
2026-05-22
2026-05-25 至 2026-06-18
2026-06-22 至 2026-06-25
```

这不是可忽略的历史早期滚动窗口空值，而是目标 asof 前的近期市场指数缺口。DNG3 正交数据规范化通常需要市场状态、指数收益、滚动均线、趋势状态或至少完整 market context；在 TWII 只到 `2026-05-21` 时，不能宣称 `2026-06-25` 的基础市场特征已 ready。

审查结论：TWII 是 DNG2 阻断项，必须 repair。

## 7. Calendar 与 next-day execution 审查

Calendar evidence：

```text
source=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
date_min=2015-01-05
date_max=2026-06-25
```

审查解释：该 calendar 是 provider calendar evidence，不等于 qlib accepted latest，也不构成 publish/latest switch。

Readiness matrix dependency：

| dependency | status | can_continue | 审查判断 |
| --- | --- | --- | --- |
| `price_coverage` | `PARTIAL_READY` / coverage READY | true | 价格到 asof，但仍是 partial |
| `twii_coverage` | `BLOCKED_COVERAGE` | false | 阻断 |
| `calendar_coverage` | READY evidence | true | 可作为 calendar evidence |
| `next_day_execution_availability` | `PARTIAL_READY` | false | 阻断 |
| `mark_to_market_close_coverage` | READY | true | 同日 close 可用于 MTM |
| `holiday_or_no_data_evidence` | READY | true | 非交易日证据存在 |

`next_day_execution_availability` 的 blocker 明确写为：

```text
halt_flag unavailable in source; latest asof rows have next_day_execution_availability=false until next trading row exists
```

因此，DNG2 不能为 `2026-06-25` 生成可信的下一交易日执行可用性。该问题会直接阻断 replay execution、strategy order intent 可执行性审计、shadow/readonly 的执行价语义，也会污染 DNG3 之后的 route readiness。

## 8. 是否需要 DNG2 repair

需要 DNG2 repair。

repair 不应做：

- 不应切 qlib accepted latest。
- 不应 publish readonly latest 或 Agent prompt latest。
- 不应训练、推理、生成模型 score。
- 不应策略回放、生成 order intent、broker/order/quick-trade。
- 不应生成 target_position 或 target_weight。
- 不应为了绕过 gate 把 `twii_coverage` 或 `next_day_execution_availability` 改成 optional。

repair 应做：

1. 补齐本地可审计 TWII normalized / canonical 来源，使 `twii_daily` 覆盖 provider calendar 到 `2026-06-25`，并重新生成 TWII manifest、coverage、lineage。
2. 引入或 catalog 权威 halt/suspension 来源，修复 `halt_flag` 覆盖。若来源仍不可得，必须在 readiness 中把依赖保持 blocked 或明确降级范围，不能伪装 READY。
3. 在下一交易日价格行可用后重建 `next_day_execution_availability`，确保最新 asof 的执行可用性不只是“没有下一行所以 false”的占位结果。
4. 复核 18 个 partial history 标的：区分新上市导致的可接受历史不足与源缺失。若 DNG3 或后续路线要求完整历史窗口，应在 readiness matrix 写出是否阻断。
5. 重新运行 builder 与 validator，目标是 `readiness_matrix.status=READY` 且 `can_continue=true`；如果仍为 partial，则必须给出 route-level 降级说明和 reviewer approval。

## 9. 为什么不是协调者裁决

本轮不需要 `STOP_COORDINATOR_DECISION_REQUIRED`。

阻断项已经由 DNG2 artifact 和 readiness matrix 明确给出，repair 路径也明确：补 TWII 覆盖、补 halt/suspension 证据、补下一交易日执行可用性。没有出现 contract 冲突、授权边界冲突或需要协调者在多个不可兼容政策之间裁决的情况。

## 10. 后续边界

DNG2 repair 通过前，不得进入：

- DNG3 OrthogonalData 规范化；
- ModelInferenceInput / ScoreJob / ModelSignalArtifact；
- StrategyInputBundle / ReplayInputBundle；
- readonly snapshot publish；
- Agent DailyAgentPromptArtifact publish；
- qlib accepted latest switch；
- production/default latest switch。

repair 通过后，DNG3 的重点约束应是：

1. 正交数据必须沿用 DNG1/DNG2 的 catalog、manifest、schema、coverage、lineage、validator 口径。
2. institutional flow、margin short、monthly revenue、valuation、corporate actions 等必须区分 `available`、`not_published_yet`、`provider_quota_blocked`、`provider_permission_blocked`、`holiday_no_data` 与 `not_required_for_route`。
3. DNG3 只能建立 canonical orthogonal feature store，不得默认触发模型训练/推理、LTR rerank、策略回放、publish 或 latest switch。
4. 如果正交数据缺失，只能显式阻断或按合同 fallback；不得把 qlib-only、旧 LTR、experiment feature 或 temporary bridge 冒充 full canonical ready。
