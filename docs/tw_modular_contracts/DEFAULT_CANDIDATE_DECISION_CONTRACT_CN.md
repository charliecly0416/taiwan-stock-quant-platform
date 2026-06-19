# DefaultCandidateDecision 合同

生成日期：2026-06-17

## 1. 目的

`DefaultCandidateDecision` 定义未来候选模型/策略如何被比较、标记、回滚和人工确认。它不是 M0 的默认策略切换许可；任何默认切换必须另开阶段并由用户确认。

## 2. Required Fields

```text
candidate_id
model_name
strategy_rule
comparison_window
required_oos_evidence
risk_metrics
diagnostic_only
not_valid_strategy_evidence
current_default_preserved=true
rollback_policy
user_confirmation_required=true
```

## 3. 必须使用的 OOS 证据

```text
fixed OOS window
same-window baseline comparison
validator status
coverage audit
turnover / drawdown / missing execution audit
diagnostic-only exclusion audit
review handoff and reviewer conclusion
```

## 4. 必须展示的风险指标

```text
max_drawdown
turnover
missing_execution_count
halt_or_untradable_count
coverage_gap_count
window_sensitivity
baseline_delta
```

## 5. 禁止事项

不得根据单次收益自动切默认；不得把 diagnostic-only 当有效策略证据；不得绕过用户确认、validator 或 review。

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
