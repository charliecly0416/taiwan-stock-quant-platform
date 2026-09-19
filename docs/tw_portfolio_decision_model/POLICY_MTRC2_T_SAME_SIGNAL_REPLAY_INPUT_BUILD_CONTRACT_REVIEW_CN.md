# POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_WITH_PRICESTORE_BRIDGE_REQUIRED_READY_FOR_MTRC2_T_R
```

审查接受 MTRC2_T 作为 replay input contract/readiness 阶段产物。`scripts/build_tw_policy_mtrc2_t_same_signal_replay_input_build_contract.py` 只生成 same-signal replay input contract、execution config contract、PriceStore/readiness inventory、missing price policy、old replay non-reuse audit、forbidden audit 和 validator/report；未生成 ReplayResult、ledger、收益 replay 或生产接入产物。

本 PASS 不放行 `MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD`。原因是未发现标准 PriceStore manifest，且现有 bridge/local source 对 MTRC2_S OrderIntent 覆盖不完整。下一步只能开：

```text
MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR
```

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. PriceStore/readiness 尚未达到直接 replay build 条件。`data_tw/artifacts/price_store` 不存在标准 `artifact_type=price_store` manifest；local bridge source 仅覆盖 `103/142` 个 OrderIntent instrument，并有 `763` 行缺失 price file。MTRC2_T 正确给出 `PRICESTORE_BRIDGE_REQUIRED_BEFORE_MTRC2_U`，没有伪装为正式 PriceStore，也没有放行 MTRC2_U。

### Low

1. `price_store_inventory.csv` 同时记录了历史 YZ/YZ2R readiness manifest，其中部分 readiness 曾为 pass，但它们不是标准 PriceStore manifest，也不覆盖本阶段 MTRC2_S OrderIntent 全量 replay 输入。因此只能作为后续 bridge/build repair 输入，不能作为当前直接 replay readiness。
2. 仓库已有大量 dirty/untracked 文件。本审查未归因、未回退、未覆盖他人修改；本次只新增本 review 文档。

## 3. Evidence Checked

已读取并核对必读文档：

- `docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_REVIEW_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

已审查脚本：

- `scripts/build_tw_policy_mtrc2_t_same_signal_replay_input_build_contract.py`

已审查 MTRC2_T 输出目录全部 16 个产物：

- `manifest.json`
- `same_signal_replay_input_contract.csv`
- `order_intent_lineage_audit.csv`
- `order_intent_schema_audit.csv`
- `candidate_parameter_audit.csv`
- `execution_config_contract.json`
- `execution_config_contract.csv`
- `price_store_inventory.csv`
- `price_store_readiness_audit.csv`
- `missing_price_policy_contract.csv`
- `old_mtr2r_replay_non_reuse_audit.csv`
- `forbidden_scope_audit.csv`
- `forbidden_action_audit.json`
- `validator_report.json`
- `diagnostic_findings.md`
- `mtrc2_u_replay_build_work_recommendation.md`

辅助核对输入：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/order_intents.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json`

## 4. Independent Recompute/Audit 摘要

输出边界复核：

```text
OUT_DIR = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_same_signal_replay_input_build_contract
REPORT_PATH = docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md
```

脚本中的 `write_csv`、`write_json`、`write_text` 写入均指向 MTRC2_T 输出目录或 MTRC2_T execution report；未发现写入正式 PriceStore、registry/config、provider/latest/default/frontend/API/Agent/daily/production、broker/order 或 replay result 目录的代码路径。

MTRC2_S OrderIntent 独立复算结果：

```text
row_count = 2378
buy_intent_count = 1194
sell_intent_count = 1184
date_range = 2017-01-10..2026-05-07
date_count = 1194
instrument_count = 142
max_daily_buy_count = 1
max_daily_sell_count = 1
non_top50_buy_intent_count = 0
```

唯一 decision source / signal lineage 复核通过：

```text
order_intent_artifact = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json
row_signal_artifacts = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
MTRC2_S validator verdict = PASS_READY_FOR_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT
old_mtr2r_replay_reused = false
```

冻结参数复核通过：

```text
strategy_rule = mechanism_transfer_top50_cost_aware_v1
candidate_id = M2_hold_rank_buffer_100
mechanism = hold_rank_buffer
rank_buffer = 100
target_holding_count = 10
candidate_k = 50
max_buy_count = 1
max_sell_count = 1
```

execution config 复核通过：

```text
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
initial_equity = 1000000
target_holdings = 10
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
missing_price_policy = skip_or_audit_no_silent_fill
cash_policy = no_negative_cash_unless_explicitly_allowed_and_audited
```

PriceStore/readiness 独立复算结果：

```text
standard_price_store_manifest_count = 0
local_bridge_csv_count = 106
order_instrument_bridge_overlap = 103/142
bridge_available_next_open_count = 1615
bridge_missing_price_file_count = 763
bridge_missing_next_open_count = 0
price_store_verdict = PRICESTORE_BRIDGE_REQUIRED_BEFORE_MTRC2_U
```

结论：Price bridge required 判断合理。当前没有标准 PriceStore manifest，且 bridge/local source 覆盖不完整；后续必须先构建或桥接可审计 PriceStore/readiness，再重新过 gate。

旧 MTR2_R/E3 replay non-reuse 复核通过。MTRC2_T 仅读取旧 replay manifest 作为 non-reuse audit 参考，没有把旧 replay 的 summary/actions/daily_nav/snapshots 或旧 OrderIntent 作为本阶段输出或后续合法输入。

## 5. Forbidden Actions Audit

输出目录禁用文件名检查结果为空，未发现以下文件：

```text
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
execution_audit.csv
skipped_actions.csv
daily_cash_audit.csv
ledger.csv
trade_ledger.csv
action_ledger.csv
```

`forbidden_action_audit.json` status 为 `pass`，所有禁止动作均 `performed=false`。独立静态审查与产物审查未发现：

- 生成 ReplayResultArtifact、ledger、summary/actions/daily_nav/position snapshots。
- 运行收益 replay，计算收益、回撤、集中度、rolling window 或 risk-off 诊断。
- 生成或修改 ModelSignalArtifact / OrderIntentArtifact。
- 复用旧 MTR2_R/E3 replay 作为当前输出或合法 replay 输入。
- 写入 provider/latest/default/frontend/API/Agent/daily/production。
- 写入 registry/config 或正式 PriceStore 目录。
- broker、quick-trade、real order。
- target_weight、target_position、quantity instruction。
- fallback 到 close 或 same-day open 的 missing price policy。

## 6. Next Work Document

下一步只能建议：

```text
MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR
```

MTRC2_T_R 必须只修复/桥接 MTRC2_S same-signal OrderIntent rows 所需的 PriceStore/readiness 输入，并继续保持：

- 只消费 `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json`；
- `signal_artifact` 严格等于 MTRC1D broad full-rank signal manifest；
- `M2_hold_rank_buffer_100`、`hold_rank_buffer`、`rank_buffer=100`、`target_holding_count=10`、`candidate_k=50`、`max_buy/max_sell=1/1` 不变；
- execution config 固定为 `next_open`、下一可交易日、`initial_equity=1000000`、`target_holdings=10`、`fee_rate=0.001425`、`sell_tax_rate=0.003`、`lot_size=10`；
- missing price 只能 skip/audit，不得 silent fill、close fallback 或 same-day open fallback；
- 不得 provider refresh/publish、accepted latest switch、生产/default/frontend/API/Agent/daily 改动、broker/order、target/quantity。

在 PriceStore/readiness 重新通过之前，不得进入 `MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD`。
