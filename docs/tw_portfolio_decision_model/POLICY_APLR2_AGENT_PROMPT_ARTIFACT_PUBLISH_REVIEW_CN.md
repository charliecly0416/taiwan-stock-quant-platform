---
created_at: 2026-07-10T00:00:00+00:00
status: review_opinion
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH
reviewer: APLR2_REVIEWER
target_asof: 2026-07-08
verdict: PASS_RECOMMEND_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE
allow_aplr3_agent_prompt_readonly_acceptance: true
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
frontend_backend_default_switch_allowed: false
---

# APLR2 Agent Prompt Artifact Publish Review

## 1. Verdict

```text
PASS_RECOMMEND_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE
```

APLR2 执行结果满足 Agent prompt artifact publish 审查要求。允许进入 APLR3
readonly acceptance。

本结论只授权 APLR3 按
`POLICY_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE_WORK_CN.md` 做只读验收；不授权
provider/network pull、provider/qlib accepted latest 切换、model scoring/training、
strategy replay、OrderIntent、ReplayResult/NAV、OpenAI call、frontend/backend/config/default
切换、monitor、broker/order/quick-trade 或任何交易规模/目标仓位输出。

## 2. Reviewed Inputs

已独立阅读或核对：

```text
docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE_WORK_CN.md
scripts/build_tw_aplr2_agent_prompt_artifact_publish.py
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/*.json
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
```

同时按 Agent Daily Prompt 与只读安全边界审查要求，复核了 DailyAgentPromptArtifact
合同、OpenAI 简化路线设计、Phase0-6 总结与 forbidden action 参考。

## 3. Latest Pointer

`data_tw/artifacts/agent_daily_prompt/latest.json` 只指向本次 Agent prompt artifact：

```text
manifest=data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
readonly_only=true
production_trade_enabled=false
```

`latest_pointer_write.json` 通过：

```text
manifest_field_exact=true
latest_pointer_scoped_to_agent_prompt_only=true
not_provider_or_qlib_accepted_latest=true
rollback_captured_before_write=true
```

审查意见：latest pointer 范围正确，没有混同 provider accepted latest、qlib accepted
latest 或 readonly strategy snapshot latest。

## 4. APLR1 Dry-run Consistency And Checksum

独立复算：

```text
checksum_rule=sha256(prompt_context raw bytes + newline + prompt_text raw bytes)
computed_checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
manifest_checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
latest_checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
context_matches_aplr1=true
prompt_matches_aplr1=true
```

`checksum_verify.json` 同步记录：

```text
computed_checksum_matches_expected=true
manifest_checksum_matches_expected=true
context_bytes_match_aplr1=true
prompt_text_bytes_match_aplr1=true
```

审查意见：manifest、prompt_context、prompt_text 与 APLR1 dry-run payload/checksum 一致。

## 5. Candidate-only Semantics

实际 `prompt_context.json` 与 `manifest.json` 保留 candidate-only 语义：

```text
candidate_only=true
top_candidates_count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
strategy_rule=candidate_only_no_strategy_replay
treatment_model_id=null
treatment_model_status=not_applicable_candidate_only_no_ltr_rerank
not_full_strategy_replay=true
```

`candidate_only_validator_publish.json` 通过：

```text
status=pass
validator_type=candidate_only_agent_prompt_validator_publish
old_ltr_full_strategy_validator_reused=false
old_ltr_full_strategy_constants_required=false
candidate_only_no_strategy_replay=true
```

审查意见：APLR2 明确使用 candidate-only validator publish evidence，没有静默复用旧
full-strategy/LTR validator 常量。

## 6. Prompt Text And Safety Boundary

`prompt_text.md` 明确：

```text
research-only / 只读研究助手
只能解释给定上下文
不能执行交易行为
不能给出真实执行指令
不能承诺收益
不能输出交易规模、仓位目标、股数或张数
qlib score 不是收益率、胜率、上涨概率或买入概率
不是 full strategy replay，不包含 exit/hold replay context
```

审查意见：prompt_text 保持只读研究边界，没有真实交易执行、交易规模、目标仓位或收益承诺语义。

## 7. Rollback And Snapshot Protection

`rollback_package.json`：

```text
captured_before_latest_pointer_write=true
latest_pointer_before.exists=false
latest_pointer_before.status=absent_rollback
rollback_instruction=delete latest.json when status is absent_rollback
```

`readonly_strategy_snapshot/latest.json` 当前仍为：

```text
snapshot_manifest=data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
candidate_only=true
sha256=74d798f628a45c74959f28e295d71ab2e8f09ea2fdb6f7726a19037d832d4528
```

`forbidden_action_audit.json` 中 protected path 指纹显示 readonly snapshot latest、
2026-07-08 manifest、strategy_snapshot 与 pre-publish 指纹一致。

审查意见：rollback 记录了 prior latest absent，readonly strategy snapshot latest 未被修改。

## 8. Forbidden Action Audit

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
modified_readonly_snapshot_latest=false
modified_readonly_snapshot_artifact=false
```

脚本审查结论：

```text
写路径限于 Agent prompt artifact/latest、APLR2 evidence、APLR2 report、APLR3 work doc
未发现 provider/model/strategy/replay/OpenAI/order/target/default/frontend/backend/config 写路径
```

危险关键词检索命中均处于 forbidden lists、blocked question types、只读状态字段、报告文本或
APLR3 stop conditions 中；未发现真实 action API、交易执行 payload 或默认切换路径。

## 9. APLR3 Work Doc Boundary

`POLICY_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE_WORK_CN.md` 仅要求：

```text
latest pointer manifest check
manifest/context/text checksum check
candidate-only validator publish evidence check
readonly_strategy_snapshot/latest remains pointed at 2026-07-08
source citations exist and remain readonly
backend loader compatibility may be checked only without OpenAI calls
forbidden action audit remains pass
```

Stop conditions 明确阻断 provider/network pull、provider publish、accepted latest switch、
model scoring/training、strategy replay、OrderIntent、ReplayResult/NAV、OpenAI call、
frontend/API/default switch、monitor、broker、order path 和 production default switch。

审查意见：APLR3 work doc 仅做 readonly acceptance，不调用 OpenAI，不改 frontend/backend/default。

## 10. Final Decision

```text
allow_aplr3_agent_prompt_readonly_acceptance=true
allow_openai_call=false
allow_frontend_backend_config_default_switch=false
allow_provider_or_qlib_latest_modification=false
allow_model_scoring_or_strategy_replay=false
allow_order_or_trade_target_output=false
```

APLR2 可关闭为 reviewer PASS。APLR3 可以启动，但必须保持 readonly/no-OpenAI 验收边界。
