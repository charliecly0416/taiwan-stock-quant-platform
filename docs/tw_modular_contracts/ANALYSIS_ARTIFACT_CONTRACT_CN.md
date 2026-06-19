# AnalysisArtifact 合同

生成日期：2026-06-17

## 1. 目的

`AnalysisArtifact` 承载研究分析、审计、诊断和报告输出。它可以解释标准 artifact，但不得直接成为默认策略切换、生产上线、前端交易建议或日更发布依据。

## 2. Artifact 结构

```text
data_tw/artifacts/analysis/{analysis_name}/{run_id}/
manifest.json
report.md 或 report.json
input_artifact_index.json
claim_support_audit.json
forbidden_semantics_audit.json
```

## 3. Required Fields

```text
artifact_type=analysis_artifact
analysis_name
run_id
input_artifacts
output_report
quality_status
no_replay
no_strategy_return_conclusion
not_valid_strategy_evidence
claim_support_audit
```

## 4. Forbidden Fields / Semantics

```text
production_ready=true
default_strategy_selected=true
target_position
target_weight
buy_now
sell_now
guaranteed_return
win_rate_promise
broker_order_id
```

## 5. 特殊边界

Diagnostic-only artifact 必须标记 `not_valid_strategy_evidence=true`，不得作为默认策略或产品展示证据。

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
