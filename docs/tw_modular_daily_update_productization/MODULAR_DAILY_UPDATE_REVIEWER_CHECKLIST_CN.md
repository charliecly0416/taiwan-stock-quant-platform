# 模块化台股日更只读审查清单

- [ ] U1/U2/U3 的 golden 全部通过
- [ ] `scripts/run_tw_modular_daily_readonly_update.py --scenario all --update-latest` 通过
- [ ] `scripts/validate_tw_modular_daily_readonly_update.py --json` 通过
- [ ] `GET /api/tw-stock/readonly-daily-latest` 可读
- [ ] `GET /api/tw-stock/readonly-daily-run-registry` 可读
- [ ] 前端只展示 readonly daily latest，不本地计算策略/replay
- [ ] network audit 结果 `forbidden_request_count=0`
- [ ] `ops_dry_run_post_count=0`
- [ ] 未发现 provider publish / accepted latest / monitor write / broker order
- [ ] 未发现 Agent prompt/tool/action 扩权
