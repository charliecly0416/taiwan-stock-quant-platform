# MBCDS3-4 执行报告

## 1. 范围

- 路线：MBCDS3-4 Source Availability Timestamp Contract and Same-Run Ledger
- 目标：让 future Model A + Model B shadow 输入具备可审计的 source availability、same-run 和 checksum 绑定。
- 非目标：不训练/评分 Model B，不切换 baseline，不写 provider/latest，不改 frontend/backend production default。

## 2. 变更

- `scripts/run_tw_model_score_job.py`
  - ModelSignalArtifact schema/manifest 增加 `source_acquisition_run_id`、`decision_cutoff`。
  - ScoreJob manifest 同步写入两个字段。
  - 增加 `--decision-cutoff` CLI 参数；缺省空值表示 PIT cutoff 未证明，不自动放行。
- `scripts/run_daily_tw_stock_auto_update.py`
  - 标准 Model A score 调用传入 daily runner 在评分前捕获的 `mbcds3_decision_cutoff`。
  - 既有 ledger/bridge 继续要求 acquisition ID、asof、时间戳和 artifact checksum 一致。
- `backend/scripts/update_tw_stock_daily.py`
  - 修复 HSA8 capture 适配器：从本次响应解析出的目标交易日记录计算 `returned_scope`。
  - 只在全部 expected symbols 都有目标日记录时标记 `validator_status=PASS` 和 `pit_status=PASS`；缺失项保持 `unknown_scope`。
  - TWII 在 schema 和目标日期校验通过时填充 `returned_scope=[TWII]`，否则继续 BLOCKED。
- `backend/tests/test_update_tw_stock_daily.py`
  - 更新测试合同，确保 scope 只按目标日计算，不把历史记录误当作目标日证据。

## 3. 验证证据

- `python -m py_compile scripts/run_tw_model_score_job.py scripts/run_daily_tw_stock_auto_update.py`：通过。
- `python -m pytest tests/unit/test_tw_model_score_job_cron_python.py tests/unit/test_tw_daily_readonly_snapshot_integration.py -q`：18 passed。
- `python -m pytest backend/tests/test_update_tw_stock_daily.py backend/tests/test_archive_tw_stock_daily.py tests/unit/test_tw_model_score_job_cron_python.py tests/unit/test_tw_daily_readonly_snapshot_integration.py -q`：47 passed。
- `python scripts/build_tw_mbcds3_shadow_accumulator.py --self-test`：通过。
- 正向 ledger fixture：`PASS`，正确计算 combined availability/fetched time。
- 逆序时间 fixture：`BLOCKED_SOURCE_AVAILABILITY`。
- checksum 变更 fixture：`BLOCKED_SOURCE_AVAILABILITY`，拒绝错误 artifact。
- `python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json`：`passed`；仅保留既有 legacy provider/accepted-latest 显式 gate warnings。

## 4. 边界审计

- 未使用文件 mtime、score 完成时间或 cron 时间冒充 source availability。
- 未把历史缺失字段推断为 PIT 合法。
- 未修改 Model A latest、Model B production、provider、cron、frontend/backend default。
- Model B 仍为 shadow-only；有效日不足时不得进入 baseline。

## 5. 剩余工作

继续自然工作日累积完整 HSA8 source evidence；至少达到 20 日才考虑 shadow score，60 日才做 OOS comparison，120 日后才可进入 baseline review。
