# DNG2_R PriceStore / TWII / Calendar 覆盖修复审查报告

生成日期：2026-06-29

审查者：DNG2_R Reviewer

## 1. 审查结论

Verdict：`PASS_WITH_CONDITIONS_GO_DNG3`

DNG2_R repair 可以带条件进入 DNG3。通过原因是：

1. PriceStore canonical artifact 存在，覆盖目标 asof `2026-06-25`。
2. TWII canonical artifact 覆盖目标 asof `2026-06-25`，但来源是既有本地 isolated bridge，已正确标记为 `PARTIAL_READY_WITH_DECLARED_GAP`，没有伪装成 formal TWII source 或 qlib accepted latest。
3. Readiness matrix 已从单一 `can_continue=false` 拆为 route-level gates：

```text
can_continue_to_model_score=true
can_continue_to_replay=false
can_continue_to_shadow_execution=false
can_continue_to_dng3=true
```

4. latest asof 缺下一本地交易日价格行被标记为 `pending_next_trade_date`，没有再把整条 PriceStore 判死，也没有放行 replay / shadow execution。
5. manifest、lineage、readiness matrix、validator 均显示 forbidden action flags 为 false；本次审查未发现真实抓数、provider refresh/publish、qlib accepted latest switch、readonly latest publish、Agent prompt publish、模型训练/推理/score、策略回放、broker/order/quick-trade、target_position 或 target_weight。

进入 DNG3 的条件：

- DNG3 只能把本轮产物作为 canonical repair artifact / readiness evidence 消费，不得把 `local_twii_bridge` 解释为 formal provider TWII。
- DNG3 不得切 qlib accepted latest、provider latest、readonly latest 或 Agent prompt latest。
- DNG3 不得启动 replay、shadow next-open execution、order intent、broker/order/quick-trade 或任何 target position / target weight 产物。
- 若后续路线要求全历史 calendar 100% TWII 覆盖，必须针对已声明的历史缺口另开补源或 route-level 豁免审查。

## 2. 已审查输入

已阅读必需文件：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_WORK_CN.md`
- `docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_canonical_price_market_calendar.py`
- `scripts/validate_tw_canonical_price_market_calendar.py`
- `data_tw/catalog/dng2_price_market_calendar_validation.json`
- `data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/manifest.json`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/manifest.json`

辅助核对：

- `data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/lineage.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/halt_suspension_audit.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/execution_availability_audit.csv`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/lineage.json`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/coverage_audit.csv`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/twii_local_source_inventory.json`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/twii.csv`

## 3. 本地验证结果

执行：

```bash
python -m py_compile scripts/build_tw_canonical_price_market_calendar.py scripts/validate_tw_canonical_price_market_calendar.py
```

结果：通过，退出码 0。

执行：

```bash
python scripts/validate_tw_canonical_price_market_calendar.py --run-id dng2_r_price_market_calendar_20260625 --asof 2026-06-25 --json
```

结果摘要：

```text
ok=true
status=PARTIAL_READY
errors=0
warnings=0
prices row_count=400205
twii row_count=2795
price_store=PARTIAL_READY
twii=PARTIAL_READY_WITH_DECLARED_GAP
readiness_matrix=PARTIAL_READY
can_continue=false
can_continue_to_model_score=true
can_continue_to_replay=false
can_continue_to_shadow_execution=false
can_continue_to_dng3=true
external_source_repair_required=false
```

审查解释：validator `ok=true` 说明结构、必需文件、必需字段、forbidden fields 和 forbidden action flags 检查通过；业务状态仍是 `PARTIAL_READY`，因此结论不能是无条件 `PASS_GO_DNG3`。

## 4. TWII isolated bridge 审查

本轮最关键问题是：既有 isolated TWII bridge 是否被正确标记为 partial，而不是被提升为正式源。

审查结论：合格。

证据：

```text
formal_normalized_nonempty
path=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
date_max=2026-05-21
fresh_enough_for_target_asof=false
```

```text
rcpt15_r3_t_isolated_twii_bridge
path=data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv
date_max=2026-06-25
fresh_enough_for_target_asof=true
source_type=local_csv_existing_isolated_bridge
```

TWII manifest：

```text
status=PARTIAL_READY_WITH_DECLARED_GAP
asof=2026-06-25
date_min=2015-01-05
date_max=2026-06-25
row_count=2795
source_data_artifact=data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv
external_source_repair_required=false
no_provider_publish=true
no_accepted_latest_switch=true
readonly_only=true
```

TWII coverage audit 明确记录：

```text
coverage_ratio=0.998207
missing_date_count=5
missing_dates_sample=2015-07-10|2015-09-29|2016-07-08|2016-09-27|2016-09-28
status=PARTIAL_READY_WITH_DECLARED_GAP
```

TWII lineage 明确记录：

```text
lineage_type=local_canonicalization_no_fetch
selected_twii_source=data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv
external_source_repair_required=false
```

`twii.csv` 的 `source` 字段为：

```text
local_twii_bridge
```

审查判断：

- DNG2_R 没有伪造 TWII，也没有把 isolated bridge 混写成 formal normalized source。
- DNG2_R 没有宣称 TWII 全历史 READY，而是声明 `PARTIAL_READY_WITH_DECLARED_GAP`。
- 该 bridge 覆盖目标 asof，可满足 DNG3 的基础数据治理继续条件；但它不能作为 formal provider publish / accepted latest 的依据。

## 5. PriceStore 与 halt/suspension 审查

PriceStore manifest：

```text
status=PARTIAL_READY
asof=2026-06-25
date_min=2015-01-05
date_max=2026-06-25
symbol_count=150
row_count=400205
```

字段覆盖：

```text
open/high/low/close/volume/adj_factor/tradable_flag/halt_flag/halt_flag_source/next_day_execution_availability/next_day_execution_status coverage_ratio=1.0
```

halt/suspension evidence：

```text
halt_suspension_policy=conservative_derived_from_price_presence
halt_flag_source=derived_from_price_presence
authoritative_halt_suspension_source_available=false
```

审查判断：

- DNG2_R 没有伪造权威 halt/suspension source。
- 使用 `derived_from_price_presence` 是 DNG2_R 工作单允许的保守派生，且已写入 `halt_suspension_audit.json`。
- PriceStore 仍是 `PARTIAL_READY`，原因是一个或多个标的不完整覆盖 provider calendar；该 partial 状态被保留，没有被误标为 full READY。

## 6. next-day execution 与分层 can_continue 审查

`execution_availability_audit.csv` 显示各标的最新行：

```text
last_row_next_day_execution_availability=false
last_row_next_day_execution_status=pending_next_trade_date
historical_execution_ready=true
latest_next_day_execution_pending=true
```

Readiness matrix 对 `next_day_execution_availability` 的解释为：

```text
latest asof has pending_next_trade_date because no next local trading row exists;
this blocks replay/shadow next-open semantics but not same-day model score or DNG3 base data normalization
```

整体 gate：

| Gate | 值 | 审查判断 |
| --- | --- | --- |
| `can_continue` | false | 严格全路线汇总仍为 false，合理 |
| `can_continue_to_model_score` | true | 价格、calendar、同日 MTM close 可支持模型 score 输入准备 |
| `can_continue_to_replay` | false | latest next-day pending，不能进入 replay |
| `can_continue_to_shadow_execution` | false | latest next-day pending，不能进入 next-open shadow |
| `can_continue_to_dng3` | true | DNG3 基础数据治理可继续 |

审查判断：分层 `can_continue` 合理。DNG2_R 没有用 `can_continue_to_dng3=true` 偷渡 replay 或 shadow execution。

## 7. Forbidden action 审查

脚本、manifest、lineage、readiness matrix、validator 报告中均记录：

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

脚本审查要点：

- `build_tw_canonical_price_market_calendar.py` 只读取本地 `qlib_pipeline/data_tw/**` 与 `data_tw/**` 文件，输出 canonical artifact、lineage、readiness。
- `discover_twii_source()` 只在两个本地 TWII 候选中选择覆盖 target asof 的本地文件。
- `build_lineage()` 明确写入 `local_canonicalization_no_fetch`。
- `validate_tw_canonical_price_market_calendar.py` 检查 forbidden fields 与 forbidden action flags，不触发 publish、refresh、推理、回放或交易动作。

审查判断：未发现 forbidden action 触发证据。

## 8. 条件与剩余风险

DNG3 允许继续的范围：

- 继续做 canonical feature / orthogonal feature / catalog / readiness / strategy input bundle 前置治理设计。
- 消费本轮 PriceStore 与 TWII artifact 的 manifest、lineage、coverage、readiness 作为输入证据。
- 在 DNG3 readiness 中保留 TWII `PARTIAL_READY_WITH_DECLARED_GAP` 与 PriceStore `PARTIAL_READY` 的事实。

DNG3 不允许继续的范围：

- 不得把 `local_twii_bridge` 作为 formal provider TWII、qlib accepted provider 或 production latest。
- 不得因 `can_continue_to_dng3=true` 放行 replay、shadow next-open execution、broker/order/quick-trade。
- 不得 publish provider / readonly / Agent latest。
- 不得训练、推理、生成 model score。
- 不得生成 order intent、target_position、target_weight。

剩余风险：

1. TWII 存在 5 个历史 calendar 缺口；如果 DNG3 或后续模型路线要求完整历史 TWII calendar 覆盖，必须单独补源或记录 route-level 豁免。
2. TWII bridge 有 11 个 extra dates；本轮 DNG2_R 已声明为 partial artifact，但后续若做严格 provider-calendar 对齐，需要再次审查 extra-date policy。
3. PriceStore 仍为 `PARTIAL_READY`；后续依赖全历史完整 universe 的路线不能默认复用为 full READY。
4. latest next-day execution 仍 pending；任何 replay / shadow / execution-price 语义必须等下一本地交易日价格行存在后重建并重审。

## 9. 最终判定

最终结论：

```text
PASS_WITH_CONDITIONS_GO_DNG3
```

理由：DNG2_R 修复了 DNG2 的目标 asof TWII blocker，并用本地既有 isolated bridge 生成 canonical TWII store；该 bridge 被正确标记为 `PARTIAL_READY_WITH_DECLARED_GAP`，没有伪造成正式源。Readiness matrix 的分层 gate 合理，validator 通过，forbidden action 边界未被破坏。因此可以进入 DNG3，但只能在上述条件下继续，不能放行 replay、shadow execution、formal latest/publish 或交易相关产物。
