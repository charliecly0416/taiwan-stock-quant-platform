# Phase M3 审查与 Phase M3R 修复工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M3 暂不通过，不得进入 Phase M4。

M3 的 dry-run golden samples、latest pointer 状态机样例、validator 接入和单元测试本身成立；但本阶段最关键的验收目标是把既有两小时自动更新脚本纳入 `DailyOrchestrator` / `RunRegistry` / `AutoUpdateOrchestrator` 合同边界，并证明 M3 路径不会触发真实 provider refresh / publish、不会切 provider 或 qlib accepted latest。

当前实现没有关闭这一点：`scripts/run_daily_tw_stock_auto_update.py` 仍在默认可达路径中保留 Yahoo/Scrapling refresh、provider publish 和 accepted latest 切换；`scripts/validate_tw_daily_orchestrator_m3.py --audit-script` 只把这些路径标记为 warning，仍返回 `ok=true`。这与 Phase M3 的安全门槛冲突，因此需要进入 Phase M3R 修复。

## 2. 已通过部分

### 2.1 M3 dry-run 合同样例

M3 执行报告声明新增 16 个 golden samples，覆盖：

```text
daily_orchestrator: 7
run_registry: 3
auto_update: 6
```

审查复跑结果：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
```

结果：

```text
ok=true
sample_count=16
```

### 2.2 Latest pointer 状态机

样例覆盖了以下关键状态：

```text
no_new_data -> committed_latest 保留 previous_latest
fresh_data_success + validators passed -> committed_latest 更新为 proposed readonly latest
validator_failed -> committed_latest 保留 previous_latest
module_failed -> committed_latest 保留 previous_latest
run_registry success -> 记录 previous/proposed/committed/checksum
```

这部分符合 M3 对 readonly latest pointer 的抽象要求。

### 2.3 禁止交易与 monitor 写入边界

脚本静态审计结果显示：

```text
broker_order_patterns_present=[]
monitor_write_patterns_present=[]
```

审查未发现 broker、quick-trade、order action、monitor config save、monitor scan 或 alert write 的新增路径。M3R 不应扩大这些边界。

### 2.4 回归接入

审查复跑结果：

```bash
python -m py_compile scripts/validate_tw_daily_orchestrator_m3.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m3_daily_orchestrator.py
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py tests/unit/test_tw_modular_m3_daily_orchestrator.py -q
```

结果：

```text
py_compile: pass
pytest: 12 passed
```

## 3. 阻塞问题

### M3-BLOCKER-1：既有两小时脚本仍有默认可达 provider refresh / publish / accepted latest 路径

严重级别：High

证据：

`scripts/run_daily_tw_stock_auto_update.py` 的 `--skip-qlib` 是可选参数，默认不跳过 qlib：

```text
scripts/run_daily_tw_stock_auto_update.py:390
parser.add_argument("--skip-qlib", action="store_true")
```

在未传 `--skip-qlib` 时，脚本进入真实 qlib 更新分支：

```text
scripts/run_daily_tw_stock_auto_update.py:492
if not args.skip_qlib:
```

该分支会构造并运行 Yahoo/Scrapling refresh：

```text
scripts/run_daily_tw_stock_auto_update.py:493-525
examples/tw/run_option_c_yahoo_scrapling_refresh.py
```

该分支随后会构造并运行 provider publish：

```text
scripts/run_daily_tw_stock_auto_update.py:537-558
examples/tw/publish_option_c_yahoo_scrapling_refresh.py
provider_publish_triggered = True
```

provider publish 后还会调用 accepted latest 切换：

```text
scripts/run_daily_tw_stock_auto_update.py:570
accepted = publish_accepted_latest(asof)
```

并写入 latest signal 更新结果：

```text
scripts/run_daily_tw_stock_auto_update.py:588-589
job["accepted_latest"] = accepted
job["latest_signal_updated"] = bool(accepted.get("latest_signal_updated"))
```

这不是“只读 latest pointer”的 M3 合同路径，而是 legacy production publish/latest 路径。即使审查过程没有实际执行这些命令，只要默认可达路径仍存在，M3 就不能证明既有两小时脚本已经被映射到安全的 orchestrator contract。

### M3-BLOCKER-2：M3 script audit 将发布与 accepted latest 降级为 warning，仍返回通过

严重级别：High

证据：

`scripts/validate_tw_daily_orchestrator_m3.py` 能识别 production provider publish 与 accepted latest 路径：

```text
scripts/validate_tw_daily_orchestrator_m3.py:183-184
production_provider_publish_path_present
production_accepted_latest_path_present
```

但 validator 只把它们加入 warnings：

```text
scripts/validate_tw_daily_orchestrator_m3.py:196-199
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

真正会导致 `ok=false` 的只有 broker/order 与 monitor write pattern：

```text
scripts/validate_tw_daily_orchestrator_m3.py:200-205
errors = []
...
return {"ok": not errors, ...}
```

这导致下面的审计命令在存在 publish/latest 路径时仍返回 `ok=true`：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

审查复跑结果：

```text
ok=true
warnings=legacy_provider_publish_path_present|legacy_accepted_latest_path_present
production_provider_publish_path_present=true
production_accepted_latest_path_present=true
```

M3 的验收门槛不是“记录 legacy 风险即可”，而是现有两小时脚本必须被审计并映射到不会触发真实 provider refresh / publish、不会切 accepted latest 的 orchestrator contract。当前 validator 的通过条件过宽。

### M3-BLOCKER-3：测试把阻断项固化为预期通过

严重级别：Medium

证据：

`tests/unit/test_tw_modular_m3_daily_orchestrator.py` 明确期待脚本审计在存在 legacy provider publish 与 accepted latest 时仍然通过：

```text
tests/unit/test_tw_modular_m3_daily_orchestrator.py:76-84
test_m3_daily_auto_update_script_audit_records_legacy_warnings_only
assert code == 0
assert result["ok"] is True
warning_codes == legacy_provider_publish_path_present|legacy_accepted_latest_path_present
```

并进一步确认这两个 production 路径存在：

```text
tests/unit/test_tw_modular_m3_daily_orchestrator.py:91-92
production_provider_publish_path_present is True
production_accepted_latest_path_present is True
```

这会把错误的 M3 验收语义写入回归测试，后续执行者即使保留默认可达发布路径也能持续通过 M3 gate。

## 4. 对执行报告的修正意见

M3 执行报告第 9 行称本阶段“没有触发 provider publish / refresh、没有切 accepted latest”。这句话只能解释为审查命令没有实际运行这些生产动作，不能解释为既有两小时脚本的默认路径已经安全。

同一报告第 11 行、第 115-122 行已经承认脚本仍保留 legacy provider publish 与 accepted latest 路径，并把它们标记为 warning。审查结论是：这些不应在 M3 审计中作为 warning 放行，而应作为 M3R 阻断项处理。

## 5. Phase M3R 修复范围

M3R 目标：关闭既有两小时自动更新入口的 M3 安全边界缺口，使自动更新脚本在 M3 合同路径下只做调度、状态记录、retry/noop、RunRegistry 和 readonly latest pointer，不触发 provider refresh / publish，不切 provider 或 qlib accepted latest。

必须完成：

1. 明确定义 M3 auto-update readonly/dry-run 模式。
   - 该模式必须是 M3 审计和回归使用的默认合同模式。
   - 该模式不得调用 `examples/tw/run_option_c_yahoo_scrapling_refresh.py`。
   - 该模式不得调用 `examples/tw/publish_option_c_yahoo_scrapling_refresh.py`。
   - 该模式不得调用 `publish_accepted_latest(asof)` 或 accepted latest scheduler。

2. 修复 `scripts/run_daily_tw_stock_auto_update.py` 的默认可达路径。
   - 推荐方案：新增显式非默认 flag，例如 `--enable-legacy-provider-publish` 或等价生产确认 gate，只有显式确认时才允许 legacy refresh/publish/latest 路径。
   - M3 默认路径必须保留 previous latest 或只更新独立 readonly latest pointer。
   - 如果执行者认为 legacy 两小时脚本不属于 M3 合同，应另建被审计的 M3 entrypoint，并在文档中明确旧脚本已退出 M3 验收范围；但这必须同时修改主线要求，否则不能满足“既有两小时脚本已映射”的目标。

3. 修复 `scripts/validate_tw_daily_orchestrator_m3.py --audit-script`。
   - 对默认可达 provider refresh / provider publish / accepted latest path 返回 `ok=false`。
   - 只有当 validator 能证明这些路径受显式非默认 gate 保护，且 M3 默认模式不会进入时，才允许审计通过。
   - warning 可以保留用于迁移提示，但不能覆盖 M3 阻断错误。

4. 修复测试。
   - 删除或改写“legacy warnings only 仍通过”的预期。
   - 增加负例：默认可达 provider publish、provider refresh、accepted latest 必须失败。
   - 增加正例：显式 legacy gate 存在但默认关闭、M3 readonly/dry-run 模式可验证时才通过。

5. 更新执行报告。
   - 不再把“未实际触发”写成“脚本边界已安全”。
   - 明确 M3R 修复后的默认模式、legacy 模式、validator 判定规则和残余风险。

## 6. M3R 验收门槛

M3R 完成后，审查者至少复跑以下命令：

```bash
python -m py_compile scripts/validate_tw_daily_orchestrator_m3.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m3_daily_orchestrator.py
python scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py tests/unit/test_tw_modular_m3_daily_orchestrator.py -q
```

必须满足：

```text
M3 golden validator: ok=true
M3 script audit: ok=true only when default M3 path has no provider refresh/publish/accepted latest
pytest: pass
broker/order/quick-trade: no new path
monitor config/scan/alert writes: no new path
Agent prompt/tool/action: no expansion
```

如果 `--audit-script scripts/run_daily_tw_stock_auto_update.py --json` 仍报告：

```text
production_provider_publish_path_present=true
production_accepted_latest_path_present=true
```

则必须同时证明这些路径不可由 M3 默认模式到达；否则 M3R 不通过。

## 7. M4 前置条件

只有 M3R 通过后，才允许进入 M4。进入 M4 前必须具备：

```text
既有两小时脚本的 M3 默认路径已冻结为 readonly/dry-run orchestrator contract
provider refresh / publish 与 accepted latest 已被移出 M3 默认路径或受显式非默认 gate 保护
validator 对默认可达 forbidden path 会失败
测试不再把 legacy publish/latest warning 固化为通过
RunRegistry / readonly latest pointer 状态机仍保持 M3 golden 覆盖
```

M4 不得基于当前 M3 报告继续推进前端或 Agent 读取链路；否则会把未关闭的生产 publish/latest 风险带入展示层和 Agent context。
