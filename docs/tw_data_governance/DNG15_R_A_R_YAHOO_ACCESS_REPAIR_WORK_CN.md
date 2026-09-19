# DNG15_R-A-R Yahoo Same-Lineage Access Repair 工作文档

生成日期：2026-06-29

## 1. 背景

DNG15_R-A 已执行并审查，结论为：

```text
STOP_NEEDS_COORDINATOR_DECISION
```

失败点不是模型、qlib dump、score job 或策略层，而是同口径 Yahoo 数据获取层：

```text
proxy http://127.0.0.1:7890 -> connection refused
no-proxy Yahoo chart API -> 150 symbols * .TW/.TWO = 300 attempts all HTTP 403
candidate_normalized symbols_success=0/150
staged_qlib_bin not generated
```

因此不能进入 DNG15_R-B isolated Model A score integration。

统筹授权开：

```text
DNG15_R-A-R Yahoo same-lineage access repair
```

## 2. 目标

在不改变 formal provider、不切 latest、不使用 FinMind fallback 的前提下，修复 Yahoo-only access layer，并重跑 `2026-06-26` same-lineage staged refresh：

```text
Yahoo-only access repair
-> candidate_normalized 150/150
-> staged_qlib_bin
-> provider validation
-> Model A staged smoke
-> optional dry-run-publish audit
```

通过条件：

```text
candidate_normalized symbols_success=150/150
candidate_normalized symbols_with_asof=150/150
staged_qlib_bin calendar_has_asof=true
provider_validation.status=pass
model_smoke.status=pass
prediction_rows=150
finite_prediction_share=1.0
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
production_allowed=false
publish_latest_authorized=false
no FinMind fallback
no mixed provider bridge
```

若不能成功，必须把 blocker 进一步具体化为：

```text
proxy_unavailable
yahoo_access_403_all_clients
yahoo_access_partial_symbols
yahoo_client_schema_mismatch
yahoo_client_drift_validator_failed
candidate_normalized_missing_asof
staged_provider_validation_failed
model_smoke_failed
```

## 3. 数据口径边界

本阶段仍优先使用原始脚本：

```text
qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py
```

但 DNG15_R-A 已证明当前 Scrapling direct chart API 触发 403。因此本 repair 允许在 isolated candidate 内尝试 Yahoo-only access alternatives：

1. `scrapling_with_access_repair`
   - 调整 headers、session、cookie、impersonation、retry/backoff；
   - 数据仍来自 Yahoo chart API；
   - 输出列必须仍为 `symbol,date,open,high,low,close,volume,vwap,factor`。

2. `curl_cffi_yahoo_chart`
   - 使用 `curl_cffi.requests` 的浏览器 impersonation；
   - 数据仍来自 Yahoo chart API；
   - 必须写清 source_client 与 request metadata。

3. `yfinance_yahoo_adjusted_candidate`
   - 只允许作为 Yahoo-only repair candidate；
   - 不得标记为 formal production-ready；
   - 必须对 `2026-06-25` 与 formal `option_c_150_normalized` 做 drift validator；
   - 若 drift validator 不通过，不得进入 staged provider / Model A smoke。

无论使用哪种 access client，都必须满足：

```text
source_provider=Yahoo
finmind_fallback=false
mixed_provider_bridge=false
production_allowed=false
not_published_latest=true
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
```

## 4. Drift Validator 要求

如果使用非原始 Scrapling direct client，例如 `curl_cffi` 或 `yfinance`，必须新增并运行口径漂移验证。

验证对象：

```text
candidate_normalized asof=2026-06-25
vs
formal Option C normalized asof=2026-06-25
```

最低验证字段：

```text
open
high
low
close
volume
vwap
factor
```

最低输出：

```text
data_tw/catalog/dng15_r_a_r_yahoo_access_repair_drift_validator.json
data_tw/catalog/dng15_r_a_r_yahoo_access_repair_drift_validator.csv
```

最低字段：

```text
symbol
field
formal_value
candidate_value
abs_diff
rel_diff
status
```

通过阈值：

- `open/high/low/close/vwap/factor`：
  - `max_abs_diff <= 1e-4` 或 `max_rel_diff <= 1e-6`
- `volume`：
  - 必须完全一致，或若 Yahoo access client 本身返回调整后/原始量差异，必须判定为 `fail_volume_drift`。

如果漂移失败：

```text
candidate_access_status=BLOCKED_DRIFT_VALIDATOR_FAILED
不得生成 staged provider candidate
不得运行 Model A smoke
```

## 5. 授权边界

允许：

- 真实网络访问 Yahoo；
- 使用 proxy 或无 proxy；
- 使用 Yahoo-only access client repair；
- 只写 isolated DNG15_R-A-R job 目录；
- 生成 candidate normalized / staged qlib bin / validator / model smoke；
- 运行 dry-run-publish audit，且只允许 `--mode dry-run-publish`。

禁止：

- formal provider publish；
- 覆盖 formal `option_c_150_normalized`；
- 覆盖 formal `option_c_150_qlib_bin`；
- qlib accepted latest switch；
- 修改 `latest_signal.json`；
- publish readonly latest；
- publish Agent prompt latest；
- production default model/strategy switch；
- broker/order/quick-trade；
- target_position / target_weight；
- FinMind fallback；
- mixed-provider bridge；
- 模型训练或调参。

## 6. 推荐执行顺序

### Step 1：Access diagnostic

检查并记录：

```text
proxy 127.0.0.1:7890 是否可用
Scrapling direct chart API 是否仍 403
curl_cffi Yahoo chart API 是否可行
yfinance 是否可抓单支样本
```

只需要先测少量样本：

```text
2330.TW
1785.TWO
```

### Step 2：Yahoo-only candidate builder

如果原脚本仍失败，允许新增最小脚本：

```text
scripts/build_tw_dng15_r_a_r_yahoo_access_repair_candidate.py
```

职责：

- 从 Option C accepted 150 universe 读取 symbol；
- 使用 Yahoo-only repaired client 抓 `2015-01-01` 到 `2026-06-26`；
- 生成 `candidate_normalized`；
- 跑 normalized validator；
- 如果使用非 Scrapling direct client，跑 6/25 drift validator；
- drift 通过后 dump `staged_qlib_bin`；
- 跑 provider validator；
- 跑 Model A staged smoke；
- 输出 execution summary。

### Step 3：Optional dry-run publish audit

仅在 staged refresh 完整通过后允许：

```bash
python qlib_pipeline/examples/tw/publish_option_c_yahoo_scrapling_refresh.py \
  --job-dir <DNG15_R_A_R_JOB_DIR> \
  --asof 2026-06-26 \
  --mode dry-run-publish \
  --provider-scope option_c_150 \
  --publish-job-id dng15_r_a_r_option_c_dry_run_publish_20260626 \
  --report-path docs/tw_data_governance/DNG15_R_A_R_OPTION_C_DRY_RUN_PUBLISH_REPORT_CN.md
```

不得使用：

```text
--mode publish
```

## 7. 必须生成的产物

执行者必须生成：

```text
docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_EXECUTION_REPORT_CN.md
data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json
data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json
```

如果使用 drift validator，还必须生成：

```text
data_tw/catalog/dng15_r_a_r_yahoo_access_repair_drift_validator.json
data_tw/catalog/dng15_r_a_r_yahoo_access_repair_drift_validator.csv
```

执行 job 目录建议：

```text
data_tw/experiments/dng15_r_a_r_yahoo_access_repair/<job_id>/
  candidate_normalized/
  staged_qlib_bin/
  reports/
```

## 8. 决策 artifact 字段

`dng15_r_a_r_yahoo_access_repair_decision.json` 至少包含：

```text
schema_version
generated_at
asof
route
decision
status
selected_client
job_dir
candidate_normalized_path
staged_provider_path
fetch_status
normalized_validation_status
drift_validator_status
provider_validation_status
model_smoke_status
symbols_expected
symbols_success
symbols_with_asof
calendar_has_asof
prediction_rows
finite_prediction_share
production_allowed=false
publish_latest_authorized=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
finmind_fallback=false
mixed_provider_bridge=false
forbidden_actions
next_recommended_route
```

## 9. 验证要求

至少运行：

```bash
python -m py_compile \
  qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py \
  qlib_pipeline/examples/tw/publish_option_c_yahoo_scrapling_refresh.py \
  qlib_pipeline/scripts/dump_bin.py
```

若新增脚本，也必须 `py_compile`。

必须做 JSON 断言：

```text
production_allowed=false
publish_latest_authorized=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
finmind_fallback=false
mixed_provider_bridge=false
```

## 10. 审查要求

审查者必须生成：

```text
docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_REVIEW_CN.md
```

verdict 只能是：

```text
PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION
PASS_WITH_CONDITIONS_GO_DNG15_R_B
FAIL_NEEDS_DNG15_R_A_R_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

进入 R-B 的最低条件：

- 150/150 candidate normalized 覆盖 `2026-06-26`；
- 若用了非原始 Scrapling direct client，6/25 drift validator 通过；
- staged provider validator 通过；
- Model A staged smoke 通过；
- forbidden actions 全部为 false。

如果只完成 access diagnostic，但没有生成 candidate，不能进入 R-B。

## 11. 执行者命令

```text
请执行 DNG15_R-A-R Yahoo same-lineage access repair。
先读取本工作文档、DNG15_R-A 执行报告和审查意见、DNG15 审查意见、主线文档。
允许真实网络 Yahoo-only access repair，允许 Scrapling/curl_cffi/yfinance Yahoo-only isolated candidate。
如果使用非原始 Scrapling direct client，必须做 6/25 drift validator，失败则停止。
禁止 formal publish、accepted latest switch、latest_signal 更新、readonly/Agent latest publish、生产切换、交易、target_position/target_weight、FinMind fallback、mixed-provider bridge。
完成后写执行报告和 catalog JSON。
```

## 12. 审查者命令

```text
请独立审查 DNG15_R-A-R 执行结果。
重点检查是否真生成 same-lineage/Yahoo-only 2026-06-26 candidate、是否通过 drift validator、是否生成 staged provider、是否通过 Model A smoke、是否没有任何 forbidden action。
给出明确 verdict，并写下一步 R-B 或 repair 建议。
```
