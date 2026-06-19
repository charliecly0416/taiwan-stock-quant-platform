# Phase M3R Daily Orchestrator Gate 修复执行报告

生成日期：2026-06-17

## 1. 执行结论

Phase M3R 已关闭 M3 审查指出的默认可达 legacy provider refresh / provider publish / accepted latest 缺口。

`scripts/run_daily_tw_stock_auto_update.py` 现在默认进入 M3 readonly orchestrator contract mode；Yahoo/Scrapling refresh、provider publish 和 accepted latest 切换仍保留为 legacy 代码，但必须显式传入非默认 gate `--enable-legacy-provider-publish`，或显式设置 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true`，才会进入 legacy 分支。默认命令不会进入这些路径。

本轮没有训练新模型、没有新增正式策略、没有运行新收益结论、没有切默认策略、没有触发 provider publish / refresh、没有切 accepted latest、没有改 monitor / broker / quick-trade / order，也没有修改前端 Agent 行为、prompt、tool 权限或 action 入口。

## 2. 修复内容

### 2.1 两小时脚本默认路径修复

修改文件：

```text
scripts/run_daily_tw_stock_auto_update.py
```

新增显式 legacy gate：

```text
--enable-legacy-provider-publish
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=false
```

默认 M3 contract mode：

```text
readonly_orchestrator_default
```

默认路径行为：

```text
不调用 examples/tw/run_option_c_yahoo_scrapling_refresh.py
不调用 examples/tw/publish_option_c_yahoo_scrapling_refresh.py
不调用 publish_accepted_latest(asof)
不调用 accepted latest scheduler
继续记录 noop / retry / pending 状态
继续走 readonly snapshot dry-run/latest pointer 逻辑
```

### 2.2 M3 validator 修复

修改文件：

```text
scripts/validate_tw_daily_orchestrator_m3.py
```

`--audit-script` 现在区分：

```text
production_provider_refresh_path_present
production_provider_publish_path_present
production_accepted_latest_path_present
legacy_provider_gate_present
legacy_provider_gate_default_disabled
legacy_provider_block_guarded
default_provider_refresh_reachable
default_provider_publish_reachable
default_accepted_latest_reachable
```

判定规则：

```text
legacy 代码存在但受显式非默认 gate 保护 -> ok=true + warning
default provider refresh 可达 -> ok=false
default provider publish 可达 -> ok=false
default accepted latest 可达 -> ok=false
legacy gate 缺失 / 默认开启 / 未包住 legacy block -> ok=false
broker/order pattern 或 monitor write pattern -> ok=false
```

### 2.3 测试修复

修改文件：

```text
tests/unit/test_tw_modular_m3_daily_orchestrator.py
```

新增/更新覆盖：

```text
实际两小时脚本必须 legacy gate present/default disabled/block guarded
实际两小时脚本 default_provider_refresh_reachable=false
实际两小时脚本 default_provider_publish_reachable=false
实际两小时脚本 default_accepted_latest_reachable=false
构造 unsafe 默认可达 provider refresh/publish/accepted latest 脚本必须失败
```

## 3. 审计结果

命令：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：

```text
ok=true
status=passed
production_provider_refresh_path_present=true
production_provider_publish_path_present=true
production_accepted_latest_path_present=true
legacy_provider_gate_present=true
legacy_provider_gate_default_disabled=true
legacy_provider_block_guarded=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
broker_order_patterns_present=[]
monitor_write_patterns_present=[]
```

保留 warning：

```text
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

解释：warning 只表示 legacy 代码仍存在，不能表示默认路径可触达。M3R 后，validator 只有在证明默认路径不可达且 legacy gate 非默认关闭时才返回 `ok=true`。

## 4. 验证命令

已执行：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m3_daily_orchestrator.py
python scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py tests/unit/test_tw_modular_m3_daily_orchestrator.py -q
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
py_compile: pass
M3 golden validator: ok=true, sample_count=16
M3 script audit: ok=true, default provider/latest reachable=false
pytest: 13 passed
contract regression: ok=true
```

说明：两个 validator 命令在普通沙箱中被 bwrap 限制拦截，提升权限只读复跑通过。

## 5. 残余风险

Legacy provider refresh / publish / accepted latest 代码仍保留在脚本中，用于显式生产 gate。后续 M4/M5 前应决定是否进一步拆出独立生产 entrypoint、独立 approval gate 或完全迁移到 contract registry 管理。

在完成后续生产治理前，M3R 结论只表示默认 M3 合同路径安全，不表示 legacy provider publish / accepted latest 路径已获得生产发布放行。
