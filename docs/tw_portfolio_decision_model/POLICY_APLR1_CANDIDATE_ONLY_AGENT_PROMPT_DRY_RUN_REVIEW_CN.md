---
created_at: 2026-07-10T08:23:03+00:00
status: review_opinion
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN
reviewer: APLR1_REVIEWER
target_asof: 2026-07-08
verdict: PASS_RECOMMEND_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH
allow_aplr2_agent_prompt_artifact_publish: true
agent_prompt_artifact_write_allowed_for_aplr2: true
agent_prompt_latest_write_allowed_for_aplr2: true
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

# APLR1 Candidate-only Agent Prompt Dry-run Review

## 1. Verdict

```text
PASS_RECOMMEND_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH
```

APLR1 dry-run evidence 满足 candidate-only Agent prompt 发布前审查要求。允许进入独立
APLR2 Agent prompt artifact publish。

本结论只授权 APLR2 在其 work doc 限定路径内写
`data_tw/artifacts/agent_daily_prompt/2026-07-08/` 与
`data_tw/artifacts/agent_daily_prompt/latest.json`。不授权 provider/model/strategy/
replay/OpenAI/order/target/default/frontend/backend/config 变更。

## 2. Reviewed Inputs

已独立阅读或核对：

```text
docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_WORK_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py
data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run/*
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
```

## 3. Production Write Boundary

APLR1 未创建生产 Agent prompt artifact/latest：

```text
data_tw/artifacts/agent_daily_prompt exists=false
data_tw/artifacts/agent_daily_prompt/2026-07-08 exists=false
data_tw/artifacts/agent_daily_prompt/latest.json exists=false
```

`source_gate_check.json` 与 `forbidden_action_audit.json` 均记录：

```text
agent_prompt_asof_dir_absent=true
agent_prompt_latest_absent_or_fingerprint_only=true
created_agent_prompt_asof_dir=false
wrote_agent_prompt_latest=false
modified_readonly_snapshot_latest=false
```

审查意见：APLR1 保持 dry-run only，没有提前发布生产 Agent prompt artifact/latest。

## 4. Source Gate

`source_gate_check.json`：

```text
status=pass
all checks=true
aplr0_reviewer_pass=true
readonly_strategy_snapshot/latest -> data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
source_lineage=clpr_controlled_model_signal_latest
source_signal_latest_sha256=c58d3e4d88e729eda32b65a9b0a854b827947ba68aec4e8c7bdc76014a152752
```

readonly snapshot latest 当前仍指向 2026-07-08 manifest，且 2026-07-08 manifest 与
strategy snapshot 均为 candidate-only readonly source。

## 5. Candidate-only Context

`candidate_only_prompt_context_dry_run.json` 与 source snapshot 语义一致：

```text
candidate_only=true
top_candidates_count=50
len(top_candidates)=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
strategy_rule=candidate_only_no_strategy_replay
treatment_model_id=null
treatment_model_status=not_applicable_candidate_only_no_ltr_rerank
```

该 context 明确 `not_full_strategy_replay=true`，没有把 candidate-only snapshot
伪装成 full strategy replay 或 LTR rerank artifact。

## 6. Prompt Text Safety

`candidate_only_prompt_text_dry_run.md` 满足只读研究边界：

```text
research-only / 只读研究助手
不能执行交易行为
不能给出真实执行指令
不能承诺收益
不能输出交易规模、仓位目标、股数或张数
qlib score 是横截面排序分数，不是收益率、胜率、上涨概率或买入概率
不是 full strategy replay，不包含 exit/hold replay context
```

审查意见：prompt_text 没有交易执行或交易规模语义；对 qlib score 的语义限制足够明确。

## 7. Checksum And Manifest Hashes

独立复算结果：

```text
checksum_rule=sha256(prompt_context raw bytes + newline + prompt_text raw bytes)
context_sha256=6a872c6f6c41c8c0b259d7b973c7df7ed23a42367e5903dc9c36590aeb21ba09
prompt_text_sha256=8299c949497e2cd9687673899d16af2814077ce61cb3d41f4107cfe330fbed0a
planned_manifest_checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
recomputed_manifest_checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
checksum_match=true
```

`artifact_manifest.json` 中所有 evidence file checksum 已复算：

```text
artifact_manifest_hashes_all_match=true
artifact_manifest_hash_mismatches=[]
artifact_manifest_self_checksum_rule=excludes itself from evidence_files
```

## 8. Validator Adaptation

`validator_adaptation_plan.json` 明确旧 validator 的 full-strategy/LTR 假设：

```text
requires previous LTR treatment model id
requires strategy_rule top50_exit_one_worst_sell
requires ranking_source ltr_rerank_within_qlib_top50
expects full strategy context rather than candidate-only snapshot
```

同时明确 APLR2 必须采用 candidate-only validator evidence 或受控适配：

```text
accept model_ids.treatment as null or not_applicable when candidate_only is true
accept strategy_rule candidate_only_no_strategy_replay
accept ranking_source qlib_rank_controlled_signal and candidate_boundary qlib_top50
require top_candidates_count=50 and empty exit/hold candidate lists
require exit_hold_context_status=not_built_no_strategy_replay
validate qlib score semantics text in prompt_text
validate checksum with prompt_context bytes plus newline plus prompt_text bytes
block production publish unless candidate-only validator evidence is pass
```

审查意见：APLR2 不能静默复用旧 full-strategy/LTR validator 常量；publish 前必须产出
candidate-only validator pass evidence。

## 9. Forbidden Action Audit

`forbidden_action_audit.json`：

```text
status=pass
all_false=true
provider_or_network_pull=false
provider_publish=false
provider_accepted_latest_switch=false
qlib_accepted_latest_switch=false
legacy_option_c_latest_signal_switch=false
model_scoring_or_training=false
strategy_replay=false
order_intent_generation=false
replay_result_or_nav_generation=false
openai_call=false
frontend_api_or_default_switch=false
monitor_broker_order_or_quick_trade=false
trade_execution_or_sizing_output=false
```

未发现 provider/network/model/replay/OpenAI/frontend/monitor/broker/order path 调用。

## 10. APLR2 Boundary Review

`POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_WORK_CN.md` 仅允许写：

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/*.json
docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_EXECUTION_REPORT_CN.md
```

APLR2 work doc 明确禁止：

```text
provider/network pull
model scoring/training
strategy replay
OrderIntent
ReplayResult/NAV
OpenAI call
frontend/API/default switch
monitor
broker/order path
readonly snapshot latest modification
trade execution/sizing output
```

审查意见：APLR2 scope 足够窄，只允许 Agent prompt artifact/latest 发布，不允许
provider/model/strategy/replay/OpenAI/order/target/default/frontend/backend/config 变更。

## 11. Review Commands

本 review 使用的只读复核命令包括：

```bash
sed -n '1,280p' docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_WORK_CN.md
sed -n '1,980p' scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py
cat data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run/*.json
cat data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run/candidate_only_prompt_text_dry_run.md
cat data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
cat data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
cat data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
ls -la data_tw/artifacts/agent_daily_prompt
python -c '... independent APLR1 checksum/context/manifest/source-gate self-check ...'
```

`ls` 对 `data_tw/artifacts/agent_daily_prompt` 返回不存在，符合 APLR1 禁写生产路径要求。

## 12. Final Decision

```text
allow_aplr2_agent_prompt_artifact_publish=true
allow_agent_prompt_artifact_latest_publish=true
allow_provider_or_qlib_latest_modification=false
allow_model_scoring_or_strategy_replay=false
allow_openai_call=false
allow_frontend_backend_config_default_switch=false
allow_order_or_trade_target_output=false
```

APLR2 可启动，但必须继续满足 candidate-only validator pass、checksum 复算、rollback
state capture、forbidden action audit pass，并保持只读 Agent prompt artifact/latest
发布边界。
