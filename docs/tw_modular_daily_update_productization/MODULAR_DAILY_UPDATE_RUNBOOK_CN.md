# 模块化台股日更只读运行手册

## 日常执行

```bash
python scripts/run_tw_modular_daily_readonly_update.py --scenario all --update-latest
```

## 验证

```bash
python scripts/validate_tw_modular_daily_readonly_update.py --json
```

## 读取接口

- `GET /api/tw-stock/readonly-daily-latest`
- `GET /api/tw-stock/readonly-daily-run-registry`

## 运行约束

- 仅允许本地 staging 读取
- 仅允许 GET 读取
- success/no_new_data/validator_failed/module_failed 都必须保留可追溯 registry
- success 需要 validator-gated 后更新 readonly latest

## 故障处理

- 若 latest 校验失败，先检查 `data_tw/artifacts/daily_readonly_latest/latest.json`
- 若 registry 失败，检查对应 `data_tw/artifacts/daily_run_registry/<run_id>/manifest.json`
- 若前端未显示，先验证 API 再验证浏览器 network audit
