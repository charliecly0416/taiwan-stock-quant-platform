# PortfolioStateArtifact 合同

生成日期：2026-09-19

## 1. 目的与阶段边界

`PortfolioStateArtifact` 是策略与回放共享的只读组合状态接口。它只描述某个决策时点之前已经确认的模拟持仓和尚未结算的意图投影，不生成买卖决定，不计算成交、价格、现金、费用、净值或收益。

WF-5B 只准入：

```text
state_kind = owner_independent_replay_simulation
production_allowed = false
```

本阶段不选择、不生成任何正式 portfolio，不接 daily/workflow/latest。`per_user_paper` 需要独立隐私投影与 owner binding 设计，当前 validator 必须拒绝；未来 paper adapter 是把私有状态投影为本合同的 producer，不是当前 template 的 consumer，也不能把账户、用户或 broker 身份写入标准 artifact。

PortfolioState 与 ModelSignal 是策略的两个并列输入，registry 不允许 state 依赖具体模型。当前首版状态只能通过 checksum 绑定的 replay execution 或 verified-empty replay lineage 建立来源，不能从模型分数反推持仓。prior-state adapter 留到 producer 阶段再扩展，WF-5B 不预先放行。

## 2. 文件结构

每个 artifact 是不可变目录，至少包含：

```text
manifest.json
portfolio_state.csv
pending_intents.csv
schema.json
source_lineage.json
forbidden_field_audit.json
forbidden_action_audit.json
checksum_manifest.json
```

空组合还必须包含 `empty_state_evidence.json`。空状态用只有 header 的 `portfolio_state.csv` 表达，不得伪造 quantity=0 的占位行。

除 `source_artifacts[].manifest_path` 外，所有声明文件必须位于当前 artifact 目录内，不能使用绝对路径、`..` 或 symlink。外部 source manifest 只能引用 repository 内标准 `data_tw/artifacts/` 路径；golden sample 可引用版本化 golden 根目录内、由固定 admission registry 明确准入的 source proof。

## 3. Manifest 身份与 PIT

必需身份：

```text
artifact_type = portfolio_state
schema_version = m1.0.0
artifact_id = portfolio_state:{portfolio_id}:{asof}:{run_id}
run_id
portfolio_id
state_kind = owner_independent_replay_simulation
status = READY
state_status = complete
asof = YYYY-MM-DD
available_at = timezone-aware ISO-8601
decision_cutoff = timezone-aware ISO-8601
```

`portfolio_id` 必须是稳定、不透明的 `ps_` 加 32 位小写十六进制 ID，不能携带 user/account/broker/email/phone 语义。`available_at` 与 `decision_cutoff` 必须明确使用台湾 `+08:00` offset，满足 `available_at <= decision_cutoff`，且 `available_at` 不得早于 `asof`；`decision_cutoff` 的本地日期必须等于 `asof`。

## 4. Position Rows

`portfolio_state.csv` 固定且只允许以下列：

| field | type | rule |
| --- | --- | --- |
| `asof_date` | date | 必须等于 manifest `asof` |
| `instrument` | string | `TW...` 标准代码，行间唯一 |
| `quantity` | integer | 严格正整数 |
| `cost_basis` | number | 有限且严格为正，只作为状态，不参与策略排序；未知成本不得用 0 代替 |
| `current_holding_flag` | boolean | 严格小写 `true` |

`max_holding_policy` 必须声明 `mode=hard_cap` 和 1..100 的 `max_holding_count`；实际持仓不得超过该上限。

## 5. Pending Projection

缺少 pending 证据不等于没有 pending。每个 artifact 都必须提供 `pending_intents.csv`，即使为空也必须保留 header：

```text
instrument
action
source_signal_date
source_intent_id
```

manifest 必须声明 `pending_state.status=complete`、精确 `row_count`、`captured_after_due_execution=true` 和 `captured_before_decision=true`。pending projection 只描述未结意图身份，不得包含执行价格、数量、现金或成交结果。

`source_signal_date` 必须早于本状态 `asof`，因为状态冻结在本日策略决策之前；`source_intent_id` 必须是 `oi_` 加 32 位小写十六进制 ID。同一 instrument 最多只能有一个未结 intent，语义元组与 intent ID 均不得重复；pending sell 必须仍在持仓中，pending buy 必须尚未持有。

WF-5B 尚未定义 `OrderIntentArtifact` 到 pending projection 的可信绑定，所以当前准入要求 pending CSV 为空。非空行即使字段和持仓关系正确也会以 `portfolio_pending_source_unbound` 失败。下一阶段必须先增加 source intent identity、checksum 和 validator 绑定，再开放非空 pending；不能靠 producer 自报跳过。

## 6. Empty State

空组合只有同时满足以下条件才有效：

- `row_count=0`、`empty_state=true`、`state_status=complete`；
- `empty_reason=verified_no_positions`；
- `empty_state_evidence.json` 精确绑定 portfolio/asof，并声明 `no_synthetic_row=true` 与 `source_proof_required=true`；
- `source_artifacts` 精确绑定一个通过正式 validator 的 `ReplayResultArtifact`；
- replay 的 checksum closure 完整有效，且 `asof` 当日 `position_snapshots.csv` 为零行；
- source lineage 的 `lineage_kind=verified_empty_source`。

非空组合必须使用 `empty_state=false`，并将 `empty_reason`、`empty_state_evidence` 设为 `null`。

## 7. Lineage 与 Checksum

每个 `source_artifacts` 条目固定包含：

```text
admission_id
artifact_type
run_id
manifest_path
sha256
bytes
```

`source_lineage.json` 必须绑定相同的 `portfolio_id/state_kind/asof/source_artifacts`。生产 artifact 的 source manifest 只能位于 repository 的标准 `data_tw/artifacts/` root；fixture source 只允许出现在版本化 golden 根目录内。WF-5B 精确要求一个 `replay_result` source，并通过 repository 固定的 `configs/tw_portfolio_state_replay_source_admissions.yaml` 同时 pin source manifest 与 source checksum manifest 的路径、SHA256、run ID、asof、schema/contract version 和 validator profile。artifact 自己不能指定或替换 admission registry；未知或重复 admission、path swap、重签后的新 run 都必须失败。

ReplayResult 使用 `portfolio_state_source_v1` 严格 profile：summary、daily NAV、actions、9 列 position snapshots、coverage、position integrity、forbidden field、execution、forbidden action、decision source、forbidden scope、action lineage 与 source identity 共 13 类证据，并由独立 replay checksum manifest 精确覆盖。强 validator 还会重算 NAV、snapshot 和 summary 会计关系，并核对 producer/source-input lineage。PortfolioState 的 `(instrument, quantity, cost_basis)` 必须与 source 在 `asof` 当日的 snapshot 逐项一致；空组合必须由同日 daily NAV 和零行 snapshot 共同证明。只重算 PortfolioState 自身哈希，或同时重签 replay manifest/checksum，都不能绕过 admission pin。

PortfolioState checksum closure 必须精确覆盖 positions、pending projection、schema、lineage、两类 forbidden audit、source manifest，以及空组合的 empty evidence；ReplayResult 的 13 类证据文件由 source 自己的 checksum closure 覆盖。多报、少报、重复、SHA/bytes 不符均失败。`manifest.json` 与 `checksum_manifest.json` 不纳入 PortfolioState closure，以避免 manifest 引用 checksum 时形成循环哈希；manifest 字段由 validator 直接验证。`forbidden_field_audit.json` 必须列出除自身外实际扫描的完整 PortfolioState 文件集合。

## 8. 安全边界

manifest 必须严格声明：

```text
readonly_only=true
simulation_only=true
not_order=true
not_target_position=true
not_target_weight=true
not_investment_advice=true
no_broker=true
production_allowed=false
contains_account_identifier=false
contains_pii=false
contains_credentials=false
no_provider_publish=true
no_accepted_latest_switch=true
```

manifest、lineage、source proof、schema 和 audit 使用严格字段白名单，未知字段一律失败；CSV 也必须精确列数。由此禁止账户、用户、broker、密钥、PII、future/label、execution/price、cash、PnL、target position/weight 和订单字段。当前允许的 consumer 仅为 `strategy_rule` 与 `replay_execution`；禁止 frontend direct、paper account direct、broker、order、provider/latest。

## 9. 验证

```bash
python scripts/validate_tw_modular_m_contracts.py \
  --contract portfolio_state --artifact-path <artifact-dir> --json

python scripts/validate_tw_modular_m_contracts.py \
  --run-golden --contract portfolio_state --json
```

固定 admission 只是 PortfolioState validator 消费 golden source 的准入，不是 runtime 或产品准入；registry 顶层及每项均固定 `runtime_admission=false`、`production_allowed=false`。当前没有正式生产 source entry，D7 discovery 也不是信任根。

合同通过只表示 artifact 形状与安全边界合格，不表示 runtime admission、正式组合选择、daily 接入、paper apply 或 baseline 变更。runtime 继续 HOLD。
