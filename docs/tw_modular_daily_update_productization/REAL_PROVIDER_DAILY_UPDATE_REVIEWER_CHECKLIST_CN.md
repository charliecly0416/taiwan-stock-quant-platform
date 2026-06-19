# Real Provider Daily Update Reviewer Checklist

生成时间：2026-06-17

## 必查项

- `data_readiness_manifest.json` 的 `updates_readonly_latest=false`，`actual_readonly_latest_updated=false`。
- 只有 V2 registry 的 success 且 U 链 validator 通过时，才允许 `readonly_latest_updated=true`。
- 非 ready / no data / partial / failed / deadline missed 均保持 previous readonly latest。
- `provider_accepted_latest_changed=false` 且 `qlib_accepted_latest_changed=false`。
- `forbidden_action_audit.actions.*` 不得出现 true。
- `model_strategy_availability_matrix.json` 覆盖全部 5 个模型和 7 个策略。
- diagnostic/smoke strategy 不得 `production_selectable=true`。
- 前端/API 只有 `/api/tw-stock/readonly-daily-update-runs` 一个受控 POST。
- provider readiness、run list、run detail、latest readonly result 均为 GET。
- 模型/策略切换不得触发 provider refetch。

## 建议复跑

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
python -m py_compile scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
```
