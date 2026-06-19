# Phase D3 审查与 Phase D3R 修复工作文档

生成日期：2026-06-17

## 1. D3 审查结论

D3 不能通过，必须进入 D3R。

结论：

```text
D3 parity CSV validation: pass
D3 stated decoupling objective: fail
next phase: D3R source-proof repair
```

当前 D3 的 validator、单测、contract regression 和 readonly snapshot validator 都能通过；但 D3 产物没有证明 `OrderIntentArtifact -> ReplayExecutionEngine -> ReplayResultArtifact` 的五规则全窗口路径。当前实现把旧 `formal_replay_manifest.json` 同时作为 baseline 和所谓 `order_intent_replay_manifest`，实际比较的是旧 modular replay artifact 与 baseline windowed replay artifact，而不是独立 OrderIntent replay 结果与旧 baseline 的 parity。

这是 D3 目标层面的阻塞问题。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED3_FIVE_RULE_FULL_WINDOW_PARITY_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED3_FIVE_RULE_FULL_WINDOW_PARITY_EXECUTION_REPORT_CN.md
```

新增实现：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

D3 artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/manifest.json
```

## 3. Findings

### Critical: D3 没有生成或消费真正的 OrderIntent replay result

位置：

```text
scripts/run_tw_modular_order_intent_replay_parity.py:219-240
scripts/run_tw_modular_order_intent_replay_parity.py:311-316
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/manifest.json:9-14
```

当前 runner：

```text
source_manifest = load_json(baseline_manifest_path)
baseline_dir = source_manifest["baseline_windowed_dir"]
replay = read_artifact_frame(source_manifest, "summary/daily_nav/actions/snapshots")
```

也就是说：

- baseline 侧读取 `formal_replay_matrix_windowed`；
- replay 侧读取 `formal_replay_manifest.json` 中的旧 modular replay 输出；
- 没有调用 `scripts/build_tw_modular_order_intent_artifact.py` 生成全窗口五规则 OrderIntentArtifact；
- 没有调用或扩展 `scripts/run_tw_modular_order_intent_replay.py` 用 OrderIntentArtifact 进行全窗口 replay；
- 没有新的 OrderIntent replay result manifest。

D3 manifest 也显示：

```text
baseline_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
order_intent_replay_manifest=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

这两个字段完全相同。该 manifest 不能作为 `OrderIntentArtifact -> ReplayExecutionEngine` parity 证据。

目录实证：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/
```

该目录下只有：

```text
summary_parity.csv
daily_nav_parity.csv
actions_parity.csv
action_key_parity.csv
position_snapshot_parity.csv
coverage_audit.csv
forbidden_scope_audit.csv
decision_source_audit.csv
manifest.json
```

未发现五规则全窗口 `OrderIntentArtifact`，也未发现五规则全窗口 `ReplayResultArtifact`。

影响：

- 当前 `parity_status=pass` 只能说明旧 modular replay 与旧 baseline windowed replay 仍能对齐；
- 不能证明 D1/D2/D2R 抽出的 `OrderIntentArtifact` 与 replay execution 在全窗口、五规则下行为等价；
- 不能进入产品化接入标准 `OrderIntentArtifact` / `ReplayResultArtifact`；
- 后续 API/前端若接入当前 D3 产物，会绕开新合同链路，回到旧 replay artifact。

### High: D3 validator 没有验证 replay source 与 baseline source 不同且类型正确

位置：

```text
scripts/validate_tw_modular_order_intent_replay_parity.py:67-72
scripts/validate_tw_modular_order_intent_replay_parity.py:84-104
```

当前 validator 只检查：

```text
baseline_manifest_exists
order_intent_replay_manifest_exists
parity CSV status all pass
row counts match
coverage / forbidden / decision audit pass
```

缺失检查：

```text
order_intent_replay_manifest != baseline_manifest
order_intent_replay_manifest.artifact_type == replay_result 或 d3_order_intent_replay_result
order_intent_replay_manifest.decision_source == order_intent_artifact / order_intent_artifacts
order_intent_replay_manifest 不得指向 old formal_replay_manifest
OrderIntentArtifact manifests exist
OrderIntentArtifact count covers five rules x five methods x 2026_ytd signal dates
Replay actions reference OrderIntentArtifact source
decision_source_audit details 指向真实 order-intent replay manifest，而非 baseline manifest
```

因此，当前 validator 会接受“baseline 和 replay manifest 是同一个旧文件”的伪通过。

### Medium: D3 单测只 mutate parity CSV 状态，没有覆盖 source-proof

位置：

```text
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

当前测试能覆盖：

- 五规则字段存在；
- parity CSV status fail 会被拒绝；
- diagnostic flag 被改坏会被拒绝。

但缺失负面测试：

```text
test_d3_rejects_order_intent_replay_manifest_equal_to_baseline_manifest
test_d3_rejects_order_intent_replay_manifest_with_legacy_replay_result_type
test_d3_rejects_missing_order_intent_artifact_manifests
test_d3_rejects_replay_actions_without_order_intent_artifact_reference
test_d3_rejects_decision_source_audit_pointing_to_baseline_manifest
```

这就是当前缺陷没有被测试捕获的原因。

## 4. 已通过但不能覆盖 D3 目标的检查

已复核并通过：

```text
py_compile: pass
D3 parity validator: ok=true
unit tests: 22 passed
contract regression: ok=true
readonly snapshot validator: ok=true
targeted static boundary audit: no matches
```

这些结果说明：

- 当前脚本语法正确；
- 当前 parity CSV 自洽；
- 当前测试覆盖了 CSV status 与部分 manifest flags；
- 未发现前端/API/daily/provider/accepted latest/monitor/broker/order 边界越界。

但它们不能证明 D3 的核心目标：五规则全窗口 OrderIntent replay parity。

## 5. 只读安全边界

未发现 D3 新增文件包含：

```text
target_position
target_weight
broker
quick_trade
provider_publish
accepted_latest
monitor/scan
monitor/config
monitor/alerts
POST /api
PUT /api
PATCH /api
DELETE /api
```

readonly snapshot validator 仍通过：

```text
ok=true
no_provider_publish=pass
no_accepted_latest_switch=pass
no_monitor_broker_order=pass
latest_pointer_points_to_readonly_snapshot_only=pass
```

因此 D3 的问题不是只读越界，而是 parity 证据源错误。

## 6. D3R 修复目标

D3R 目标：

```text
生成真实五规则、五方法、2026_ytd 全窗口 OrderIntentArtifact 与 OrderIntent ReplayResultArtifact，
再用这些新产物与旧 baseline 做 parity。
```

D3R 通过前，不得进入产品化 API/前端接入。

## 7. D3R 必做项

### 7.1 生成全窗口 OrderIntentArtifact

必须生成覆盖：

```text
methods:
  e4_frozen_qlib_2023_2025_ltr
  fresh_qlib_2025_ltr
  fresh_qlib_adaptive
  frozen_qlib_2018_2022
  frozen_qlib_2025_ltr

rules:
  original
  top50_exit_all
  top50_exit_one_worst_sell
  one_sell_one_buy_correct
  one_sell_one_buy_buggy_e8r

window:
  2026_ytd, 2026-01-01 -> 2026-05-07
```

可以选择：

- 一个全局 OrderIntentArtifact manifest；
- 或每个 method/rule 一个 OrderIntentArtifact manifest，再由 D3R replay manifest 汇总。

必须在 manifest 中明确：

```text
artifact_type=order_intent
artifact_stage=d3_full_window_replay_input
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
not_parity_evidence=false
diagnostic rule only for parity
source ModelSignalArtifact / FullRankArtifact / PortfolioState
row counts by method/rule/date/action
```

### 7.2 生成真实 OrderIntent ReplayResultArtifact

必须由 replay execution 消费 OrderIntentArtifact，而不是读取旧 formal replay artifact 作为 replay side。

ReplayResultArtifact manifest 必须包含：

```text
artifact_type=replay_result
schema_version=d3_order_intent_replay_result_v1 或兼容明确版本
decision_source=order_intent_artifact
order_intent_artifacts=[...]
baseline_manifest=<old formal_replay_manifest only for parity, not replay source>
window=2026_ytd
rules_present=五规则
methods_present=五方法
summary/daily_nav/actions/position_snapshots artifacts
decision_source_audit
forbidden_scope_audit
```

actions 必须能追踪到 OrderIntent 来源：

```text
order_intent_artifact
order_intent_row_id 或等价 key
signal_date
instrument
strategy_rule
model_name
```

### 7.3 D3 parity runner 必须比较两个不同来源

D3R parity manifest 必须满足：

```text
baseline_manifest != order_intent_replay_manifest
baseline_manifest.artifact_type == replay_result_r10_action_window_cleanup 或旧 replay result
order_intent_replay_manifest.artifact_type == replay_result
order_intent_replay_manifest.decision_source == order_intent_artifact
```

parity 比较对象：

```text
baseline side:
  old formal replay matrix / windowed baseline

replay side:
  newly generated OrderIntent ReplayResultArtifact
```

不得把 `formal_replay_manifest.json` 作为 `order_intent_replay_manifest`。

### 7.4 D3 validator 必须补 source-proof hard gates

`scripts/validate_tw_modular_order_intent_replay_parity.py` 必须新增：

```text
order_intent_replay_manifest_not_equal_baseline_manifest
order_intent_replay_manifest_artifact_type
order_intent_replay_manifest_decision_source_order_intent
order_intent_artifacts_exist
order_intent_artifacts_cover_five_rules
order_intent_artifacts_cover_five_methods
order_intent_artifacts_cover_2026_ytd
replay_actions_reference_order_intent_artifact
decision_source_audit_points_to_order_intent_replay_manifest
reject_legacy_formal_replay_manifest_as_replay_source
```

### 7.5 D3 tests 必须补负例

新增或修改测试，至少覆盖：

```text
test_d3_rejects_order_intent_replay_manifest_equal_to_baseline_manifest
test_d3_rejects_legacy_formal_replay_manifest_as_order_intent_replay_source
test_d3_rejects_missing_order_intent_artifact
test_d3_rejects_replay_manifest_without_order_intent_decision_source
test_d3_rejects_actions_without_order_intent_artifact_reference
test_d3_rejects_decision_source_audit_pointing_to_baseline_manifest
```

保留现有 CSV mismatch 负例。

## 8. D3R 允许修改范围

允许修改：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
docs/tw_modular_contracts/PHASED3R_*.md
```

禁止修改：

```text
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

旧 replay baseline：

```text
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

只能作为 baseline 读取或复跑，不得静默修改。

## 9. D3R 验证命令

D3R 执行者必须提供：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_order_intent_replay_parity.py --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact <d3r_parity_manifest> --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

并提供定向 source audit：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path("<d3r_parity_manifest>")
m = json.loads(p.read_text())
print("baseline_manifest", m.get("baseline_manifest"))
print("order_intent_replay_manifest", m.get("order_intent_replay_manifest"))
assert m.get("baseline_manifest") != m.get("order_intent_replay_manifest")
PY
```

以及只读边界扫描：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py tests/unit/test_tw_modular_order_intent_replay_parity.py
```

预期：

```text
all validators ok=true
unit tests pass
contract regression ok=true
readonly snapshot validator ok=true
baseline_manifest != order_intent_replay_manifest
order_intent_replay_manifest decision_source=order_intent_artifact
five rules / five methods / 2026_ytd covered by real OrderIntent artifacts
all parity CSV pass
no production write / trading / monitor / provider boundary hit
```

## 10. D3R 通过后

D3R 通过后，才允许进入下一阶段：只读产品接入标准 `OrderIntentArtifact` / `ReplayResultArtifact`。

产品接入阶段仍必须单独审查：

```text
API 只读
frontend 只展示不计算
diagnostic rule 不作为有效策略或收益证据
no provider publish / accepted latest switch
no monitor / broker / quick-trade / order
```
