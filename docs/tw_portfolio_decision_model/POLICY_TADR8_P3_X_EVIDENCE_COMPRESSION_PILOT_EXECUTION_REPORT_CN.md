# TADR8-P3-X Evidence Compression Pilot Execution Report

## Scope

Executed the approved single-packet evidence-only LLM compression pilot for symbol 2454.

## Status

```text
status=SCHEMA_VALIDATION_FAILED
decision=STOP_SCHEMA_VALIDATION_FAILED
api_endpoint_repair=OPENAI_BASE_URL switched from chat.noc.pku.edu.cn to https://chat.pku.edu.cn/v1
```

## What Passed

```text
preflight_packet_schema_validation=PASS
prompt_boundary_validation=PASS
llm_call_audit.status=PASS
forbidden_action_audit=PASS
```

The new platform accepted the original API key:

```text
base_url=https://chat.pku.edu.cn/v1
model=gpt-4.1-mini
api_key_exposed=false
raw_response_stored=false
```

## What Failed

The LLM produced a draft risk summary, but it is not schema-valid:

```text
risk_summary_schema_validation.result=FAIL
schema_error=evidence_coverage_flags: ['complete'] is not of type 'object'
evidence_only_gate_result=EVIDENCE_ONLY_GATE_STOP
```

No trading, order, sizing, performance, OOS, production, or current-best comparison claim is supported.

## Boundary

This run used only the approved 2454 MediaTek evidence packet. It did not use TradingAgents, did not browse or fetch source_ref, did not read new sources, did not read 2330/2317 payloads, did not read prices/provider/latest/accepted latest/qlib/raw/_memory/PCOM/order/target/sizing, did not join current-best rows, did not compute metrics or run replay/backtest/OOS, did not generate order/target/sizing, and did not publish production/default/latest.

## Artifacts

```text
data_tw/experiments/tradingagents_external_evidence_risk_summarizer/tadr8_p3_x_evidence_compression_pilot_execution/
```

## Claim Boundary

This report supports only:

```text
The old proxy URL was the LLM API blocker.
The new URL https://chat.pku.edu.cn/v1 is reachable with the existing key.
The single LLM compression attempt generated a draft JSON but failed strict schema validation.
```

This report does not support收益提升、OOS、生产、交易、current-best comparison、order、target 或 sizing 结论。
