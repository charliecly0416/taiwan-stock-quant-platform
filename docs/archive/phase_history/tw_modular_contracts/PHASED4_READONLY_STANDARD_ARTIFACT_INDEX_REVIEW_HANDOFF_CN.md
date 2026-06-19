# Phase D4 Readonly Standard Artifact Index 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

执行侧建议：D4 可进入审查。D4 已将 D3RR 标准产物整理为只读标准 artifact index，并补 ReplayWindowPolicy metadata；本阶段未开启用户自选 date range，也未新增 API/前端。

```text
readonly standard artifact index: pass
ReplayWindowPolicy metadata: pass
fixed_window_only=true
user_selectable_range_enabled=false
D3RR parity validator: pass
contract regression: pass
readonly snapshot validator: pass
```

## 2. 审查对象

新增实现：

```text
configs/tw_replay_window_policy.yaml
scripts/build_tw_modular_readonly_standard_artifact_index.py
scripts/validate_tw_modular_readonly_standard_artifact_index.py
scripts/validate_tw_replay_window_policy.py
tests/unit/test_tw_modular_readonly_standard_artifact_index.py
```

执行报告：

```text
docs/tw_modular_contracts/PHASED4_READONLY_STANDARD_ARTIFACT_INDEX_EXECUTION_REPORT_CN.md
```

D4 产物：

```text
data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json
data_tw/artifacts/readonly_standard_artifact_index/d4/latest.json
data_tw/artifacts/readonly_standard_artifact_index/d4/checksum_manifest.json
```

## 3. 审查重点

请重点确认：

```text
1. D4 index 只读消费 D3RR 标准 artifact，不覆盖 D3RR 原始产物。
2. order_intent_replay_result_manifest != baseline_manifest。
3. ReplayResult 仍声明 generated_by=replay_execution_engine。
4. fixed_window_only=true 且 user_selectable_range_enabled=false。
5. ReplayWindowPolicy 已记录训练窗口和 allowed replay min date。
6. one_sell_one_buy_buggy_e8r 仍只作为 diagnostic，不作为有效策略证据。
```

## 4. 本阶段未做事项

D4 没有做：

```text
API route
frontend display
date range picker
按用户请求即时 replay 生成
provider refresh / publish
accepted latest switch
monitor 写入
broker / quick-trade / order
```

这符合 D3RR review 文档中“D4 固定 2026_ytd，D5 再做用户可选 date range replay”的建议。

## 5. 验证命令

建议审查者复跑：

```bash
python scripts/validate_tw_replay_window_policy.py --json
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
python -m pytest tests/unit/test_tw_modular_readonly_standard_artifact_index.py
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 6. D5 前置提醒

若下一阶段要支持用户自选回放窗口，必须新增后端窗口 validator 和非法训练窗口拒绝测试。不得只靠前端 date picker 限制窗口。
