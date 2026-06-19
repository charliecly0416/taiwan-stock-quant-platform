# Phase R12 审查与 R12R 修复建议

生成日期：2026-06-16

## 1. 审查结论

R12 暂不建议进入 R13，需先做 R12R 修复。

R12 的 shadow runner 主体和安全边界基本正确：

- shadow artifacts 全部写入 `data_tw/artifacts/shadow_modular_daily/2026-06-16/`；
- 未生成 readonly publish artifact；
- 未创建 readonly latest pointer；
- 未修改前端、API、日更脚本或 provider / accepted latest；
- validators 通过；
- forbidden scope audit 通过；
- modular contract regression 通过；
- R12 相关单测通过。

但 R12 明确要求输出 `checksum_manifest.json`，当前 checksum manifest 存在自引用失效问题，并且漏掉两个关键 shadow 输出文件。因此 R12 产物完整性不满足进入 R13 readonly publish writer 的前置要求。

## 2. 阻塞发现

### P1：`checksum_manifest.json` 自引用 hash 失效，且漏掉关键 shadow 输出

位置：

```text
scripts/run_tw_modular_shadow_daily.py
data_tw/artifacts/shadow_modular_daily/2026-06-16/checksum_manifest.json
```

现象：

`checksum_manifest.json` 将自身列入 checksum 清单：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/checksum_manifest.json
```

但记录的 hash 与文件当前实际 hash 不一致。

当前文件实际 hash：

```text
1587c8c8dd1b9136d5079d4dbd0fc10f844c134a0ecde8b527d3a95b5984e247
```

manifest 中记录的自身 hash：

```text
841a6f2ff01869edd49551629a597550dc9bce91b2304672b71c5e01056037e8
```

原因：

runner 在写入新的 `checksum_manifest.json` 前，将已有旧 `checksum_manifest.json` 纳入了 checksum 计算。写入新文件后，该 hash 必然失效。

同时，当前 checksum 清单未包含：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/shadow_summary.json
```

影响：

- R12 shadow gate 虽然通过，但 checksum manifest 不能可靠验证自身目录产物；
- 后续 R13 readonly publish artifact 若依赖该 checksum，会继承错误完整性证据；
- R11/R12 产品化路线要求 checksum / package manifest 作为 publish 前置，因此该问题应阻塞进入 R13。

修复要求：

1. `checksum_manifest.json` 不应包含自身 hash，除非采用明确的 detached / two-pass 自校验设计。
2. `checksum_manifest.json` 必须包含全部关键 source inputs：
   - registry；
   - replay config；
   - replay manifest；
   - signal manifests；
   - full-rank manifests；
   - strategy dependency yaml。
3. `checksum_manifest.json` 必须包含全部 shadow outputs，至少：
   - `manifest.json`；
   - `model_signal_manifest.json`；
   - `full_rank_manifest.json`；
   - `strategy_dependency_snapshot.yaml`；
   - `replay_result_manifest.json`；
   - `validation_report.json`；
   - `forbidden_scope_audit.json`；
   - `shadow_summary.json`。
4. 新增 checksum 校验逻辑或测试，确认清单中每个文件的 `sha256` 与当前文件一致。
5. R12 gate 应增加：

```text
checksum_manifest_valid == true
```

修复后必须重跑：

```bash
python scripts/run_tw_modular_shadow_daily.py --asof 2026-06-16 --json
python scripts/run_tw_modular_contract_regression.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

并提供 R12R execution report / review handoff。

## 3. 其他复核结果

### 3.1 Shadow runner 边界正确

R12 新增：

```text
scripts/run_tw_modular_shadow_daily.py
data_tw/artifacts/shadow_modular_daily/2026-06-16/
```

Shadow 输出文件齐全：

```text
manifest.json
model_signal_manifest.json
full_rank_manifest.json
strategy_dependency_snapshot.yaml
replay_result_manifest.json
validation_report.json
forbidden_scope_audit.json
checksum_manifest.json
shadow_summary.json
```

除 checksum manifest 缺陷外，其余 shadow artifact 路径符合 R12 隔离目录要求。

### 3.2 Gate 结果通过但需补 checksum gate

`manifest.json` 当前 gate：

```text
all_validators_pass: true
forbidden_scope_audit_status: pass
artifact_output_under_shadow_dir_only: true
no_frontend_change: true
no_api_change: true
no_daily_orchestrator_change: true
no_provider_publish: true
no_accepted_latest_switch: true
no_broker_order: true
```

这些 gate 均通过。

但当前 gate 未覆盖：

```text
checksum_manifest_valid
```

R12R 应补上。

### 3.3 Validation report 通过

`validation_report.json` 显示：

```text
registry_validation.ok: true
replay_result_validation.ok: true
model_signal_validation: true / skipped only
full_rank_validation: true
all_validators_pass: true
```

`sector_extension_analysis_smoke` 对 canonical signal artifacts 仍为 skipped，符合 R7-R12 既有 registry 适用范围设计。

### 3.4 Forbidden scope audit 通过

`forbidden_scope_audit.json` 显示：

```text
status: pass
no_frontend_change: true
no_api_change: true
no_daily_orchestrator_change: true
no_provider_publish: true
no_accepted_latest_switch: true
no_broker_order: true
artifact_output_under_shadow_dir_only: true
```

`README.md` 中已有 `broker` 字样被记录为 informational keyword finding，不作为 gate 失败。这是合理的，因为实际禁止路径无 tracked diff，且 shadow 输出位于隔离目录。

### 3.5 Regression / tests

复核命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

全量 pytest 在执行者报告中因当前环境缺少 `ccxt` 于 crypto backend 测试收集阶段失败。该失败与 R12 shadow runner 无直接关系，但正式产品化阶段若要使用全量 pytest 作为 gate，需要补齐测试依赖或拆分测试 profile。

### 3.6 生产链路未触碰

Targeted diff 复核对象：

```text
frontend
src
backend
backend_api_python
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish
```

结果：无 tracked diff。

未发现：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/
readonly latest pointer
provider accepted latest change
frontend/API 接入
daily orchestrator 接入
monitor / broker / quick-trade / order
```

## 4. R12R 修复指令

请执行 R12R：Shadow checksum manifest repair。

只允许修改：

```text
scripts/run_tw_modular_shadow_daily.py
data_tw/artifacts/shadow_modular_daily/2026-06-16/
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_REVIEW_HANDOFF_CN.md
```

建议实现：

1. 先写除 `checksum_manifest.json` 以外的全部 shadow outputs；
2. 对 source inputs + shadow outputs 计算 checksum；
3. 明确排除 `checksum_manifest.json` 自身，或采用稳定可验证的 detached checksum 方案；
4. 写入 `checksum_manifest.json`；
5. 运行 checksum self-validation，但不是校验自身 hash，而是校验清单列出的所有文件当前 hash；
6. 将结果写入 `manifest.gate.checksum_manifest_valid` 和 `shadow_summary`。

建议 checksum manifest 至少包含：

```text
registry
replay_config
replay_manifest
signal manifests
full-rank manifests
strategy dependency yaml
model_signal_manifest.json
full_rank_manifest.json
strategy_dependency_snapshot.yaml
replay_result_manifest.json
validation_report.json
forbidden_scope_audit.json
shadow_summary.json
manifest.json
```

不得包含：

```text
checksum_manifest.json
```

除非额外设计 self-checksum 占位算法并写清楚验证方式。

## 5. R12R 禁止事项

R12R 禁止：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- readonly publish writer；
- readonly latest pointer；
- API wrapper；
- frontend change；
- daily orchestrator change；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order；
- 修改 R1/R9/R10 canonical artifacts；
- 修改默认策略。

## 6. R13 前置条件

只有 R12R 审查通过后，才允许进入 R13。

R13 仍只能按产品化工作文档执行：

```text
Readonly Publish Artifact Contract / Writer / Validator
```

R13 也不允许：

- 前端/API 接入；
- daily orchestrator 接入；
- provider publish；
- accepted latest 切换；
- monitor / broker / order。

## 7. 最终结论

R12 主体方向正确，但 `checksum_manifest.json` 是 R12 必需产物，当前存在自引用失效和关键输出漏记问题。

结论：

```text
R12 需 R12R 修复后再进入 R13。
```
