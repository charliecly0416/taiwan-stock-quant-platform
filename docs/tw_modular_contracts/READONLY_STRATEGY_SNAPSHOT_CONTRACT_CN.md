# Readonly Strategy Snapshot Contract

版本：readonly_strategy_snapshot_r13_v1

生成日期：2026-06-16

## 1. 目的

`ReadonlyStrategySnapshot` 是 R13 引入的只读发布产物，用于把已通过 R12/R12R shadow gate 的 modular artifact 固化为 API/前端未来可读取的只读候选快照。

该 artifact 不是交易指令，不是目标仓位，不是投资建议，不触发 broker、quick-trade、order、monitor、provider publish 或 provider accepted latest 切换。

## 2. 目录结构

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/
  manifest.json
  strategy_snapshot.json
  validation_report.json
  forbidden_scope_audit.json
  checksum_manifest.json

data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

`latest.json` 只允许指向 readonly snapshot，不得命名为 accepted latest，不得修改 provider / qlib accepted latest。

## 3. manifest.json 必需字段

```json
{
  "artifact_type": "readonly_strategy_snapshot",
  "schema_version": "readonly_strategy_snapshot_r13_v1",
  "asof": "YYYY-MM-DD",
  "created_at": "ISO-8601",
  "created_by": "scripts/publish_tw_modular_readonly_snapshot.py",
  "readonly_only": true,
  "production_trade_enabled": false,
  "no_order_action": true,
  "not_target_position": true,
  "not_investment_advice": true,
  "display_role": "primary_readonly_candidate",
  "is_primary_readonly_candidate": true,
  "is_production_trading_default": false,
  "source_shadow_manifest": "data_tw/artifacts/shadow_modular_daily/{asof}/manifest.json",
  "source_signal_manifest": "...",
  "source_full_rank_manifest": "...",
  "source_strategy_dependency": "...",
  "snapshot": "strategy_snapshot.json",
  "validation_report": "validation_report.json",
  "forbidden_scope_audit": "forbidden_scope_audit.json",
  "checksum_manifest": "checksum_manifest.json",
  "quality_status": "pass"
}
```

## 4. strategy_snapshot.json 必需字段

```json
{
  "asof": "YYYY-MM-DD",
  "data_asof": "YYYY-MM-DD",
  "signal_asof": "YYYY-MM-DD",
  "model_id": "e4_frozen_qlib_2023_2025_ltr",
  "base_model_id": "frozen_qlib_2018_2022",
  "strategy_rule": "top50_exit_one_worst_sell",
  "candidate_boundary": "qlib_top50",
  "ranking_source": "ltr_rerank_within_qlib_top50",
  "display_role": "primary_readonly_candidate",
  "is_primary_readonly_candidate": true,
  "is_production_trading_default": false,
  "top_candidates": [],
  "exit_candidates": [],
  "hold_candidates": [],
  "explanations": [],
  "available_at_policy": "current_or_pit_delayed",
  "readonly_only": true,
  "not_order": true,
  "no_order_action": true,
  "not_target_position": true,
  "not_investment_advice": true
}
```

## 5. 安全边界

允许：

- 从 R12/R12R shadow manifest 读取 source artifact；
- 生成 readonly snapshot；
- 生成 readonly snapshot latest pointer；
- 运行 readonly snapshot validator；
- 写入 `data_tw/artifacts/publish/readonly_strategy_snapshot/`。

禁止：

- 训练、调参、score recompute、replay recompute；
- 修改 R1/R9/R10/R12 canonical artifacts；
- 修改默认策略；
- 接入前端、API、daily orchestrator；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade、order；
- 读取真实券商持仓；
- 输出生产 target position / target weight；
- 将候选解释为交易建议。

## 6. Validator Gate

R13 validator 必须确认：

```text
readonly_snapshot_validator_ok == true
checksum_ok == true
latest_pointer_points_to_readonly_snapshot_only == true
forbidden_scope_audit.status == pass
```
