---
created_at: 2026-07-10T00:00:00+00:00
status: review
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR3_R_CANDIDATE_ONLY_VALIDATOR_LOADER_REPAIR
reviewer: APLR3_R
target_asof: 2026-07-08
verdict: PASS_RECOMMEND_RERUN_APLR3_READONLY_ACCEPTANCE
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
openai_call_allowed: false
production_default_switch_allowed: false
---

# APLR3_R Candidate-only Validator/Loader Repair Review

## Verdict

PASS_RECOMMEND_RERUN_APLR3_READONLY_ACCEPTANCE

允许重新执行 APLR3 readonly acceptance。

本次审查未发现 candidate-only validator/loader compatibility repair 越过 APLR 边界。repair 可接受的前提是：下一步只重跑 APLR3 readonly/no-OpenAI acceptance，不触发 provider/network pull、publish、accepted latest switch、model scoring、strategy replay、OrderIntent、ReplayResult、OpenAI、frontend/config/default switch、monitor/broker/order 行为。

## Review Basis

已阅读并复核：

```text
docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR3_R_CANDIDATE_ONLY_VALIDATOR_LOADER_REPAIR_EXECUTION_REPORT_CN.md
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
data_tw/experiments/agent_prompt_latest_route/aplr3_r_candidate_only_validator_loader_repair/*.json
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
```

同时复核了 backend loader 与 repair evidence builder：

```text
backend/app/services/tw_stock_agent_daily_prompt.py
scripts/build_tw_aplr3_r_candidate_only_validator_loader_repair.py
```

## Findings

### Critical

None.

### High

None.

### Medium

None.

### Low / Residual Risk

- `validate_source_artifacts()` 仍是 source path 存在性校验，且允许绝对路径存在即通过。当前 published APLR artifact 使用固定 repo-relative source paths，protected fingerprint evidence 也证明 artifact/latest/snapshot 未变，因此这不是本次重跑 APLR3 的 blocker。后续可单独收紧为 repo-root allowlist 或禁止绝对路径，避免未来 artifact source citation 指向任意本机文件。

## Scope / Protected Artifacts

未发现本次 repair 修改 Agent prompt artifact/latest、readonly snapshot、backend loader、frontend/config/default 的证据。

repair evidence manifest 只列出 validator 与 validator test 作为 changed files：

```text
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
```

protected fingerprint evidence 全部为 true，覆盖：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
```

关键 protected hashes 仍匹配：

```text
agent latest sha256=f9a5119bf0453299fd50284fdd382936dc107f2bc2ff2f50aa045a707ec70a2f
agent manifest sha256=0dcbc0c01b7caa1ca936a36a8ec0f65352b8c1cbe90531a9435e0d18394eb58a
agent context sha256=6a872c6f6c41c8c0b259d7b973c7df7ed23a42367e5903dc9c36590aeb21ba09
agent prompt sha256=8299c949497e2cd9687673899d16af2814077ce61cb3d41f4107cfe330fbed0a
readonly snapshot latest sha256=74d798f628a45c74959f28e295d71ab2e8f09ea2fdb6f7726a19037d832d4528
controlled signal latest sha256=c58d3e4d88e729eda32b65a9b0a854b827947ba68aec4e8c7bdc76014a152752
```

注：当前 worktree 本身包含大量既有未跟踪/他人改动；本审查未使用全局 git diff 作为唯一 scope 证据，而是以指定文件、repair evidence、protected fingerprints 和本地验证结果为准。

## Validator Compatibility

validator 保留 full-strategy / LTR 分支：

```text
validate_full_strategy_contract()
manifest.model_ids.treatment == e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
manifest.strategy_rule == top50_exit_one_worst_sell
manifest.execution_price_mode == next_open
prompt_context.model_context.ranking_source == ltr_rerank_within_qlib_top50
```

candidate-only 分支不是宽松绕过。`is_candidate_only_mode()` 以任一 candidate marker 触发分支，但 `validate_candidate_only_contract()` 随后强制全部 candidate-only 合同字段：

```text
treatment in (null, "not_applicable")
treatment_status=not_applicable_candidate_only_no_ltr_rerank
strategy_rule=candidate_only_no_strategy_replay
execution_price_mode=not_applicable_candidate_only_no_strategy_replay
execution_price_status=not_built_no_strategy_replay
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
snapshot_candidate_only=true
not_full_strategy_replay=true
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source_lineage=rsppr_candidate_only_readonly_snapshot_latest
```

因此缺 marker 或混合语义会 fail，不会以 candidate-only 名义接受 full-strategy/LTR 伪装。

## Source Path Parsing

source artifact repair 逻辑只接受：

```text
string path
object.path
status=missing_allowed_for_golden_sample only when --allow-golden-missing-sources
```

它不读取 dynamic service payload，不接受内嵌 payload 替代 artifact 文件；production artifact 的 repo-relative paths 当前均存在。golden missing source 仍需显式 `--allow-golden-missing-sources`。

## Score Semantics / Forbidden Terms

published prompt 与 context 中的 “上涨概率” 只出现在否定性 score semantics 解释：

```text
qlib score 是横截面排序分数，不是收益率、胜率、上涨概率或买入概率。
```

validator 的 whitelist 覆盖 `answer_policy.score_semantics_required` 与 prompt line 中的否定/安全语境。未发现把 qlib score 表述为收益率、胜率、上涨概率承诺、买入概率或仓位大小。

## Tests

新增/保留测试覆盖符合要求：

```text
candidate-only published artifact validates in strict mode
candidate-only requires explicit snapshot marker
candidate-only unsafe trade-action terms fail
full-strategy golden pass remains pass
wrong model/strategy/execution-price/checksum/source/forbidden-action samples remain fail
order/submit order/monitor write safety audit remains enforced
```

本地执行结果：

```text
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_validator.py scripts/build_tw_aplr3_r_candidate_only_validator_loader_repair.py
PASS

python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/artifacts/agent_daily_prompt/2026-07-08 --json
ok=true, errors=[], warnings=[]

python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py
13 passed
```

Backend loader local latest load：

```text
loaded=True
signal_asof=2026-07-08
strategy_rule=candidate_only_no_strategy_replay
checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
allowed_citation_count=2
no_openai_call=True
```

第一次 loader command 使用了错误的 `backend.app...` import path 并因 `No module named 'app'` 失败；已按项目实际 backend import path 重跑并通过。

## Forbidden Action Audit

APLR3 原 readonly acceptance evidence 已确认：

```text
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/forbidden_action_audit.json
all_false=true
forbidden_action_audit_pass=true
```

repair evidence:

```text
data_tw/experiments/agent_prompt_latest_route/aplr3_r_candidate_only_validator_loader_repair/forbidden_action_safety_acceptance.json
status=pass
unsafe_candidate_only_rejected=true
forbidden_audit_triggered=true
protected_artifact_not_modified=true
```

未发现 provider/network pull、provider publish、accepted latest switch、model scoring/training、strategy replay、OrderIntent、ReplayResult/NAV、OpenAI call、frontend/config/default switch、monitor write、broker、quick-trade、order path、target position/weight 或 trade sizing 输出。

## Decision

允许重跑 APLR3 readonly acceptance。

重跑必须保持：

```text
readonly/no-OpenAI
no provider/network pull
no publish or accepted latest switch
no model scoring or strategy replay
no frontend/config/default switch
no monitor/broker/order/target output
```
