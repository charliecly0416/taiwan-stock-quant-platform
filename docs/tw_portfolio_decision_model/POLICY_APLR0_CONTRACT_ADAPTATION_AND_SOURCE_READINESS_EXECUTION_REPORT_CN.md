---
created_at: 2026-07-10T00:00:00+00:00
status: execution_report
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS
target_asof: 2026-07-08
verdict: PASS_RECOMMEND_APLR0_REVIEWER
agent_prompt_artifact_write_allowed: false
agent_prompt_latest_write_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_sizing_output_allowed: false
production_default_switch_allowed: false
---

# APLR0 Contract Adaptation And Source Readiness Execution Report

## 1. 范围

APLR0 只执行合同适配与源 readiness。执行期间未创建
`data_tw/artifacts/agent_daily_prompt/2026-07-08/`，未写
`data_tw/artifacts/agent_daily_prompt/latest.json`，未修改
`readonly_strategy_snapshot/latest.json` 或 2026-07-08 snapshot artifact。

## 2. 已读取输入

已读取 APLR mainline、APLR0 work、RSPPR final closure、项目宪法、
DailyAgentPromptArtifact 合同、OpenAI rebuild design、Phase0-6 final summary、
现有 Agent prompt builder/validator，以及 RSPPR 发布的 2026-07-08
readonly strategy snapshot latest、manifest、snapshot、validation report 与
checksum manifest。

## 3. Evidence

Evidence 输出目录：

```text
data_tw/experiments/agent_prompt_latest_route/aplr0_contract_adaptation_and_source_readiness
```

生成文件：

```text
rsppr_gate_check.json
source_inventory.json
candidate_only_prompt_contract_extension.json
builder_validator_compatibility.json
publish_plan.json
rollback_plan.json
forbidden_action_audit.json
artifact_manifest.json
```

全部 evidence `status=pass`，`artifact_manifest.json` 记录的 evidence checksum
已复算通过。

## 4. 关键检查结果

RSPPR final closure verdict 为：

```text
PASS_CLOSE_RSPPR_AND_OPEN_SEPARATE_AGENT_PROMPT_LATEST_ROUTE
```

Readonly snapshot latest 仍指向：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
```

2026-07-08 snapshot readiness：

```text
candidate_only=true
top_candidates_count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source_lineage=clpr_controlled_model_signal_latest
source_signal_latest=data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
controlled_signal_latest_sha256=c58d3e4d88e729eda32b65a9b0a854b827947ba68aec4e8c7bdc76014a152752
```

Agent prompt latest 当前状态：

```text
data_tw/artifacts/agent_daily_prompt/latest.json absent
data_tw/artifacts/agent_daily_prompt/2026-07-08/ absent
```

## 5. Builder / Validator 兼容性

现有 `scripts/build_tw_agent_daily_prompt_artifact.py` 和
`scripts/validate_tw_agent_daily_prompt_artifact.py` 不能静默用于 APLR2 发布。
已在 `builder_validator_compatibility.json` 记录：

- builder 要求 `current_strategy_context` 与 readonly snapshot source JSON。
- builder/validator 仍强制既有 LTR treatment model、`top50_exit_one_worst_sell`
  与 `ltr_rerank_within_qlib_top50`。
- candidate-only snapshot 的语义是 `candidate_only_no_strategy_replay`，
  treatment model 不适用，且 exit/hold context 未构建。
- APLR1 必须做 candidate-only dry-run 适配证据，不能把 candidate-only source
  伪装成 full-strategy/LTR source。

## 6. Forbidden Action Audit

`forbidden_action_audit.json`：

```text
all_false=true
status=pass
```

APLR0 未触发 provider/network pull、provider publish、accepted latest switch、
legacy option_c switch、model scoring/training、strategy replay、OrderIntent、
ReplayResult/NAV、OpenAI call、frontend/API/default switch、monitor/broker/order/
quick-trade，也未输出交易执行或交易规模字段。

## 7. Commands

```bash
python -m py_compile scripts/build_tw_aplr0_contract_adaptation_and_source_readiness.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python scripts/build_tw_aplr0_contract_adaptation_and_source_readiness.py --json
python -c 'exec("... artifact_manifest checksum and JSON status self-check ...")'
ls -la data_tw/artifacts/agent_daily_prompt data_tw/artifacts/agent_daily_prompt/latest.json data_tw/artifacts/agent_daily_prompt/2026-07-08
```

结果：

```text
py_compile passed
APLR0 evidence status=pass
artifact_manifest checksum self-check overall=True
Agent prompt artifact directory/latest pointer remain absent
```

## 8. Verdict

```text
PASS_RECOMMEND_APLR0_REVIEWER
```

建议进入 APLR0 reviewer。进入 APLR1 的前提是 reviewer PASS；APLR1 只能做
candidate-only Agent prompt dry-run evidence，不能发布 latest。
