# Full Orthogonal Current-Asof Refresh Repair 执行报告

## 1. 范围

- 目标：产品 latest 已等于目标交易日时，weekday 14:45 UTC `full` cron 仍刷新 institutional/margin 研究源。
- 非目标：不安装 cron，不运行真实网络抓取，不发布 provider/accepted latest/product latest，不训练或评分 Model A/B。

## 2. 实现

- `scripts/run_daily_tw_stock_auto_update.py`
  - 新增 exact-scope 判定 `should_run_full_orthogonal_refresh`。
  - `daily` scope 保持 `already_up_to_date`；`full` scope 绕过该产品 noop。
  - 完整 segmented acquisition 后直接完成研究源验收并返回，位于 HSA8 handoff、provider、模型和产品发布之前。
  - full segmented acquisition 已覆盖全 universe institutional/margin，不再追加 quota-aware orthogonal batch，避免重复 provider 请求。
  - evidence 增加 segment command/capture、logical acquisition、batch skip reason 和五个 protected latest fingerprint。
- `tests/unit/test_tw_modular_m3_daily_orchestrator.py`
  - 覆盖 exact mode、daily noop、full acquisition branch、scope incomplete 和 protected latest mutation fail-closed。
- `docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md`
  - 补充两个 full refresh 状态及 segmented acquisition 单次采集语义。

## 3. 验证

```text
targeted full orthogonal tests: 6 passed
orchestrator regression: 39 passed, 1 deselected
py_compile: PASS
M3 static validator: PASS, only two expected gated-legacy warnings
git diff --check: PASS
```

Deselected test 是既有 cron 合同冲突：它要求 legacy provider publish flag 不存在，但当前 installed cron 已按更早授权启用。此次未修改 installed cron 或 actual crontab。

## 4. 禁止动作审计

- real FinMind/Yahoo pull：未执行
- installed/actual cron：未修改
- provider/accepted/product latest：未写入
- Model A/B scoring/training：未执行
- frontend/backend、DB、OpenAI、broker/order/target：未触发

## 5. 结论

实现与静态回归通过。尚不能声称自然 cron 验收完成；需要下一次 weekday 14:45 UTC 自然 full job 提供运行证据。
