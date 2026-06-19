# Phase R14 Readonly API 审查交接

生成日期：2026-06-16

## 1. 审查目标

请审查 R14 是否只完成：

```text
Readonly API 接入
```

R14 不应包含前端、daily orchestrator、provider accepted latest、monitor 或交易链路接入。

## 2. 审查对象

新增：

```text
backend/app/services/readonly_strategy_snapshot.py
backend/app/routes/readonly_strategy_snapshot.py
backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_REVIEW_HANDOFF_CN.md
```

修改：

```text
backend/app/routes/__init__.py
scripts/validate_tw_modular_readonly_snapshot.py
```

## 3. API Endpoint

```text
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-strategy-snapshot/<asof>
```

只读取：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/checksum_manifest.json
```

## 4. 执行命令

```bash
python -m py_compile backend/app/services/readonly_strategy_snapshot.py backend/app/routes/readonly_strategy_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
python scripts/run_tw_modular_contract_regression.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果摘要：

```text
py_compile: pass
R14 API tests: 4 passed
readonly snapshot validator: ok=true
modular contract regression: ok=true
modular contract unit tests: 13 passed
```

## 5. 审查重点

请确认：

1. API routes 仅为 GET；
2. POST / PUT / PATCH / DELETE 均 405；
3. API 只读取 R13 readonly snapshot artifact；
4. API 返回 readonly flags；
5. API 返回 validation / checksum / sources；
6. API 不触发 provider publish / accepted latest switch；
7. API 不触发 monitor scan / config save / alerts write；
8. API 不触发 broker / quick-trade / order；
9. API 不输出 target position / target weight；
10. 未接入前端或 daily orchestrator。

## 6. 边界确认

R14 未触碰：

```text
frontend/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

R14 未执行：

- training；
- tuning；
- score recompute；
- replay recompute；
- frontend integration；
- daily integration；
- provider publish；
- accepted latest switch；
- monitor / broker / quick-trade / order。

## 7. 建议结论

若以上确认无误，建议 R14 通过。

R14 通过后，才允许按产品化工作文档进入 R15 frontend readonly display；R15 仍不得接 daily orchestrator、provider accepted latest 或交易链路。
