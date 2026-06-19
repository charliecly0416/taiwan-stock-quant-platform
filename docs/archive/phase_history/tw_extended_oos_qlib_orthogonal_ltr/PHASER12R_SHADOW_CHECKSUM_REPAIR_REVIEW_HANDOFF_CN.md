# Phase R12R Shadow Checksum Repair 审查交接

生成日期：2026-06-16

## 1. 审查目标

请审查 R12R 是否修复 R12 checksum manifest 阻塞问题：

```text
checksum_manifest.json 自引用失效
manifest.json / shadow_summary.json 漏记
manifest gate 缺少 checksum_manifest_valid
```

## 2. 审查对象

修改代码：

```text
scripts/run_tw_modular_shadow_daily.py
```

更新 artifact：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/
```

新增报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_REVIEW_HANDOFF_CN.md
```

## 3. 必审点

请确认：

1. `checksum_manifest.json` 不包含自身；
2. `checksum_manifest.json` 包含 `manifest.json`；
3. `checksum_manifest.json` 包含 `shadow_summary.json`；
4. 清单中 24 个文件 hash 均与当前文件一致；
5. `checksum_manifest.validation.ok == true`；
6. `manifest.gate.checksum_manifest_valid == true`；
7. `shadow_summary.checksum_manifest_valid == true`；
8. 未修改前端、API、daily、publish、provider/latest、monitor/broker/order。

## 4. 执行命令

```bash
python -m py_compile scripts/run_tw_modular_shadow_daily.py
python scripts/run_tw_modular_shadow_daily.py --asof 2026-06-16 --json
python scripts/run_tw_modular_contract_regression.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果摘要：

```text
py_compile: pass
R12 shadow runner: ok=true
checksum self-validation: ok=true, checked_file_count=24
modular contract regression: ok=true
R12 related unit tests: 13 passed
```

## 5. 边界确认

R12R 未触碰：

```text
frontend/
backend_api_python/
src/api/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish/
```

R12R 未执行：

- training；
- tuning；
- score recompute；
- replay recompute；
- readonly publish writer；
- readonly latest pointer；
- API / frontend / daily integration；
- provider publish；
- accepted latest switch；
- monitor / broker / quick-trade / order。

## 6. 建议结论

若以上确认无误，建议 R12R 通过。

R12R 通过后，才允许按产品化工作文档进入 R13；R13 仍只能做 readonly publish artifact contract / writer / validator，不得接入前端、API、daily orchestrator、provider accepted latest 或交易链路。
