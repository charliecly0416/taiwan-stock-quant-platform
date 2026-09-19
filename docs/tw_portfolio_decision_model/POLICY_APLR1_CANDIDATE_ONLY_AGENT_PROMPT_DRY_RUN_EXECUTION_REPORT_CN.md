---
created_at: 2026-07-10T08:19:43+00:00
status: execution_report
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN
target_asof: 2026-07-08
verdict: PASS_RECOMMEND_APLR1_REVIEWER
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

# APLR1 Candidate-only Agent Prompt Dry-run Execution Report

## 1. 范围

APLR1 只基于 APLR0 PASS evidence 与 RSPPR candidate-only readonly snapshot latest
生成 Agent prompt dry-run evidence。未写生产 Agent prompt artifact 目录，未写 Agent
prompt latest pointer，未修改 readonly strategy snapshot latest 或 2026-07-08 snapshot
artifact。

## 2. Evidence

Evidence 输出目录：

```text
data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run
```

生成文件：

```text
source_gate_check.json
candidate_only_prompt_context_dry_run.json
candidate_only_prompt_text_dry_run.md
dry_run_manifest_plan.json
latest_pointer_payload_plan.json
validator_adaptation_plan.json
checksum_plan.json
forbidden_action_audit.json
artifact_manifest.json
```

## 3. 关键检查

```text
APLR0 reviewer PASS=true
readonly_strategy_snapshot/latest -> data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source_lineage=clpr_controlled_model_signal_latest
strategy_rule=candidate_only_no_strategy_replay
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
treatment_model=null/not_applicable
```

Prompt text 保持 research-only / readonly 边界，并明确 qlib score 是横截面排序分数，
不是收益率、胜率、上涨概率或买入概率。

## 4. Checksum

```text
rule=sha256(prompt_context raw bytes + newline + prompt_text raw bytes)
context_sha256=6a872c6f6c41c8c0b259d7b973c7df7ed23a42367e5903dc9c36590aeb21ba09
prompt_text_sha256=8299c949497e2cd9687673899d16af2814077ce61cb3d41f4107cfe330fbed0a
planned_manifest_checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
```

## 5. Validator

旧 validator 仍带 full-strategy/LTR 假设。APLR1 已在
`validator_adaptation_plan.json` 显式记录 APLR2 前必须适配 candidate-only
validator，不能静默复用旧 validator 发布。

## 6. Forbidden Action Audit

```text
all_false=true
provider/network/model/replay/OpenAI/frontend/monitor/broker/order paths invoked=false
production Agent prompt artifact write=false
Agent prompt latest write=false
readonly snapshot modification=false
```

Agent prompt latest 当前仍为 absent 或仅 fingerprint 状态；本阶段没有发布 latest。

## 7. Commands

```bash
python -m py_compile scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py --json
python -c '... APLR1 evidence JSON/checksum self-check ...'
```

## 8. Verdict

```text
PASS_RECOMMEND_APLR1_REVIEWER
```

建议进入 APLR1 reviewer。只有 APLR1 reviewer PASS 后，才允许进入独立 APLR2
Agent prompt artifact publish；APLR1 本身不发布。
