---
created_at: 2026-08-22
status: ready_for_independent_review
phase: NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ
verdict: READY_FOR_INDEPENDENT_REVIEW
code_data_config_cron_changed: false
real_payload_bytes_read: false
nmrpa3_u_entered: false
---

# NMRPA3 T_R-D 三项 Runtime Blocker 当前状态静态预检执行报告

## 1. 执行结论

```text
READY_FOR_INDEPENDENT_REVIEW
THREE_RUNTIME_BLOCKERS_OPEN
NEXT=NMRPA3_T_R_E_FIVE_ROOT_IMMUTABLE_BINDING_WRITER_ADAPTER_IMPLEMENTATION_NO_PAYLOAD_READ
T_R_SUBSTRATE_UNCHANGED
NMRPA3_U_NOT_AUTHORIZED_NOT_ENTERED
```

三项 blocker 均真实存在。T_R bootstrap 已解决“可信 storage/locator 放在哪里”的前置问题，但尚未解决“谁以何种 committed transition 写入”和“真实 payload 如何形成 immutable root/binding”。full cron 的短路也被最近两个自然 full-job status metadata 直接复现。

确定顺序是：**先实现 immutable binding writer/adapter 的 no-payload 版本，不先修改 full cron**。原因是 full cron 当前即使可达，也只会更新 mutable/ops source 和 checkpoint；在 writer、post-genesis transition 与 immutable root seal 可验证之前，调度修复不能产生 NMRPA 可接受证据。

## 2. 已冻结设计与 Runtime 缺失

### 2.1 已冻结且不得重复设计

| area | frozen result | source |
| --- | --- | --- |
| 五 root 与 locator | `sealed_calendar`、`formal_instruments`、`adjusted_price`、`twii`、`modela_signal`，固定顺序、ID、token、base | NMRPA3_R_R_R；NMRPA3_S；T_R bootstrap/schema |
| Price/TWII binding | inventory/object selector、calendar prefix、121 日 Price/TWII、60 日 volume/vwap、formal-active/Model A cross-binding、PIT evidence、external anchor | NMRPA3_R 至 R_R_R_R |
| trust governance | 六 fixed logs、commit DAG、identity/credential/role、registration rotation、principal uniqueness | NMRPA3_R_R_R_R 至 R_R_R_R_R_R_R |
| adapter validator | recursive exact types、raw bytes/object cross-binding、row PIT、registration variants | NMRPA3_S 至 S_R_R_R |
| institutional/margin feature input | exact present 十日 grid；same-day source/cutoff；confirmed-absent request、response、returned/absent set 与 checksum | NMRPA1_R；NMRPA2 repair series |
| bootstrap substrate | 五 reserved-empty roots、六 genesis-only fixed logs、九 caller-pinned stores、project-root marker | NMRPA3_T_R-B/T_R-C |

### 2.2 仅 Runtime 缺失

```text
real immutable source snapshot producer
post-genesis append-only transition writer/validator
real root reservation -> activation -> seal lifecycle
real binding/anchor/head writer
real credential/authorization/consumption records
institutional/margin trusted immutable payload locator/root mapping
full-scope branch在latest已推进后的独立可达控制流
daily/full orchestration到上述writer的接线
```

`scripts/tw_policy_nmrpa3_source_adapter.py` 仍为 `synthetic_injected_only`。T_R config 的 capabilities 仍为 `create_storage=false`、`read_payload=false`、`issue_authorization=false`、`record_trust=false`、`run_real_date=false`。这两项是正确的 fail-closed 状态，不应通过 env/CLI override 放宽。

## 3. Blocker A：PriceStore/TWII Immutable Daily Binding

### CURRENT_FACT

```text
OPEN
canonical PriceStore/TWII 一级 run 仍只有 2026-06-25 两组；
NMRPA adjusted_price/twii reserved roots 仍为空；
不存在 real immutable daily binding writer 或 committed binding record。
```

### EVIDENCE

- `data_tw/canonical/price_store/tw_equity_daily/` 仅有 `dng2_price_market_calendar_20260625` 与 `dng2_r_price_market_calendar_20260625`。
- `data_tw/canonical/market_feature_store/twii_daily/` 同样仅有上述两组 `20260625` run。
- pathname/lstat inventory 确认 NMRPA `adjusted_price/...` 与 `twii/...` root 目录存在但无子项。
- `scripts/build_tw_canonical_price_market_calendar.py` 可构建旧 canonical Price/TWII run，但 daily orchestrator 不调用它，也不调用 NMRPA writer。
- `scripts/tw_policy_nmrpa3_source_adapter.py` 只接受 injected synthetic bytes；T_R bootstrap module 没有 real source snapshot/binding write entrypoint。

本步没有打开上述 CSV/JSON payload，也没有对其计算 checksum；日期事实来自 immutable run pathname 与既有已审查合同。

### GAP

缺少对现有 daily source 的只读输入描述、五 root snapshot plan、object inventory、PIT evidence、root seal、binding/anchor/head commit 的 real writer；也没有 post-genesis log/head transition 实现。目录本身不是 lineage。

### 最小修复边界

先实现独立的五 root immutable binding writer/adapter library：仅在 synthetic/`tmp_path` 输入上生成 plan、验证 transaction DAG、atomic commit order 和 rollback；复用 NMRPA3_R/S exact schema，不修改 synthetic adapter，不接 cron，不触碰 actual substrate。

### 是否需要真实 payload 授权

```text
no-payload implementation: 不需要
actual snapshot/binding: 需要 exact target、五 source roots、允许读取的 payload manifest、输出路径、authorization/credential 与写入记录范围的独立授权
```

### 是否可先做 no-payload implementation

可以，且这是当前唯一下一步。

### STOP 条件

- 需要从 mutable `latest` 自动推导 source/path/head；
- 需要修改现有 NMRPA3_S synthetic contract；
- 无法在 `tmp_path` 证明 root seal、binding、anchor、head 的 commit/rollback 顺序；
- 需要读取真实 payload 或写 actual T_R substrate；
- 发现五 root 合同仍有 schema 歧义。

## 4. Blocker B：Institutional/Margin Same-Day Immutable Binding

### CURRENT_FACT

```text
OPEN
最新 institutional_margin ops checkpoint pathname 为 2026-08-11；
2026-08-12 至 2026-08-21 segment cache 只有 daily_price；
ops checkpoint/cache 不是 same-day immutable payload binding。
```

### EVIDENCE

- `finmind_orthogonal_batch_state` 的 pathname/lstat inventory 最后为 `2026-08-11_institutional_margin.json`。
- `finmind_segment_cache` 文件名 inventory 显示 `2026-08-12` 至 `2026-08-21` 只有 `*_daily_price.json`，没有同日 institutional/margin cache。
- orchestrator 的 orthogonal state 仅维护 `done_symbols`、`failed_symbols`、cursor、provider status 与 cache path；`merge_finmind_segment_payloads()` 只把 count/date-range 状态合并到 job stdout。
- NMRPA1_R/NMRPA2 已冻结 present/confirmed-absent exact input，但仓库没有 producer 把 FinMind raw archive 封存为 request/response/returned-row-set/available-at/checksum-bound immutable object。
- T_R 五个 source root 不包含 institutional 或 margin root。

本步未打开 checkpoint、segment stdout、archive 或 DB row。

### GAP

存在两层缺口：

1. 缺少 institutional/margin immutable payload locator/root 与 seal 生命周期；
2. 缺少把 same-day present 或 confirmed-absent 证据转换为 NMRPA2 exact input 的 writer/adapter。

T_R 的 `binding_store`/`anchor_ledger` 可承载未来 record，但不能替代 payload root；当前五 root catalog 不能直接定位 institutional/margin bytes。

### 最小修复边界

在五 root writer no-payload 实现通过后，单独冻结并实现 institutional/margin immutable source locator extension 与 exact adapter；先仅 synthetic/`tmp_path`，不得把 ops checkpoint 或 `done=150` 认作 payload。

### 是否需要真实 payload 授权

```text
locator/schema/adapter no-payload implementation: 不需要
actual request/response/archive read、checksum、seal与binding: 需要 exact authorization
```

### 是否可先做 no-payload implementation

可以，但依赖下一步五 root writer 的 transaction/commit primitives，不应并行发明第二套 writer。

### STOP 条件

- 使用 ops checkpoint、cursor、count、空 CSV 或 cache status 证明 present/absence；
- 缺少 authoritative request scope、returned rows/set 或 trusted available-at；
- 需要读取 DB/network/真实 archive；
- 试图把 institutional/margin payload 放进 `binding_store` 规避 source-root locator；
- 未经独立合同审查扩展 T_R root catalog。

## 5. Blocker C：Full Cron `already_up_to_date` Short-Circuit

### CURRENT_FACT

```text
OPEN_AND_NATURALLY_REPRODUCED
installed cron 与 actual crontab 均有 weekday 14:45 UTC full line；
但 main() 在 FinMind branch 前按 product latest 全局 return。
```

### EVIDENCE

- installed cron 与 actual crontab 一致：高频 job 使用 `TW_DAILY_AUTO_FINMIND_SCOPE=daily`；weekday `14:45 UTC` job 使用 `TW_DAILY_AUTO_FINMIND_SCOPE=full`。
- `scripts/run_daily_tw_stock_auto_update.py:6017-6033` 在 `latest_before == asof and not force` 时写 `already_up_to_date`、执行只读 gates、finalize 后 `return 0`。
- FinMind/full branch 从 `:6068` 后才开始，因此 full env 不能改变前置 return。
- 自然 full jobs：

```text
2026-08-20T14:45:01Z: status=already_up_to_date, latest_before=2026-08-20,
  finmind_update_triggered=false, finmind_orthogonal_batch_update_triggered=false
2026-08-21T14:45:01Z: status=already_up_to_date, latest_before=2026-08-21,
  finmind_update_triggered=false, finmind_orthogonal_batch_update_triggered=false
```

这证明 blocker 不只是“可能”，而是当前自然调度的稳定行为。

### GAP

`latest_before` 是产品 latest freshness，不是 orthogonal source completeness。控制流没有把 product no-op 与 full-source maintenance 分离，也没有 source-specific completion gate。

### 最小修复边界

未来应把 full-source maintenance 放到 product-latest early return 之前，或把 early return 改为按 source-specific completeness 决策；必须保留 product publish gates、flock、cooldown、daily/full 隔离与 fail-closed accounting。修复后 full branch 只在其独立 source gate 下执行，不能使用 `--force` 作为 cron 常态绕过。

### 是否需要真实 payload 授权

```text
control-flow implementation与unit test: 不需要
manual cron run/network/provider payload read: 需要单独授权
actual crontab修改: 需要单独精确授权
```

### 是否可先做 no-payload implementation

技术上可以，但当前不应先做。它依赖 immutable writer/adapter 定义“full branch 成功后必须提交什么”；否则只修可达性，不能关闭 A/B。

### STOP 条件

- 以 `--force` 永久绕过所有 freshness gates；
- 修改 actual crontab、发起 manual run、DB/network/provider pull；
- full branch 可改写 product/latest 而无现有 gates；
- source-specific completion 仍由 product latest 或 ops count 代替。

## 6. T_R Bootstrap Future Binding 承载审查

| capability | current fact | verdict |
| --- | --- | --- |
| fixed root identity | 五个 reserved-empty roots 已物化 | READY_LOCATION_ONLY |
| binding/anchor/head storage | `binding_store`、`anchor_ledger`、`immutable_historical_head_storage` 已物化且为空 | READY_LOCATION_ONLY |
| governance logs | 六 log 只有 genesis/head/history；journals/markers 为空 | GENESIS_ONLY |
| post-genesis validation | `validate_storage_layout()` 要求 history 长度 1，并拒绝 journal/marker orphan；无 append transition writer | MISSING |
| real authorization | config capability false；authorization validator只接受 synthetic fixture | MISSING_AND_NOT_AUTHORIZED |
| Price/TWII payload root | reserved path 存在但为空 | MISSING_PAYLOAD_AND_SEAL |
| institutional/margin payload root | 不在五 root catalog | MISSING_LOCATOR_CONTRACT |

结论：bootstrap **可以承载未来 binding 的固定位置与身份**，但当前不能承载合法 post-genesis lifecycle。不能向空 stores 写 record；首先需要 no-payload writer/validator implementation 与 synthetic transition tests。

## 7. 严格顺序与唯一下一步

严格顺序：

1. `NMRPA3_T_R_E_FIVE_ROOT_IMMUTABLE_BINDING_WRITER_ADAPTER_IMPLEMENTATION_NO_PAYLOAD_READ`；
2. 独立审查后，才设计 institutional/margin locator/root extension 与 adapter；
3. 两类 immutable artifact producer 合同通过后，才修 full-cron source-specific control flow 并接线；
4. 真实 payload read、actual record/anchor/binding、cron install/run 各自另行精确授权；
5. 三项自然 evidence 均闭合后才可重新申请 NMRPA3_U。

唯一下一步只执行第 1 项。其最窄允许范围应为新 library/schema/tests/docs，在 synthetic/`tmp_path` 中实现：

```text
five-root snapshot plan
post-genesis transaction intent
reservation -> activation -> seal
binding -> anchor -> historical-head commit order
atomic staging/fsync/replace abstraction
failed-before-activation rollback与post-activation quarantine
recursive exact validation与negative matrix
```

不得读取真实 payload，不得修改 actual T_R substrate，不得写 cron，不得进入 NMRPA3_U。

## 8. 只读命令记录

本步执行的全部只读命令逐字记录如下；`apply_patch` 只新增本工作单与执行报告：

```text
sed -n '1,240p' /home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
rg --files docs/tw_portfolio_decision_model | rg 'POLICY_NMRPA3_(R|S|T)|NMRPA3'
rg -n "2026-06-25|institutional|margin|already_up_to_date|full cron|full_cron|immutable|binding|冻结|runtime|synthetic_injected_only|PriceStore|TWII" docs/tw_portfolio_decision_model/POLICY_NMRPA3_R* docs/tw_portfolio_decision_model/POLICY_NMRPA3_S* docs/tw_portfolio_decision_model/POLICY_NMRPA3_T*
rg -n --glob '!data_tw/**' --glob '!qlib_pipeline/data_tw/**' "already_up_to_date|FinMind|institutional|margin|PriceStore|TWII|ENABLE_TW_QALD|daily_auto" scripts tests backend_api_python docs/tw_portfolio_decision_model | head -1200
sed -n '1,360p' tests/unit/test_tw_modular_m3_daily_orchestrator.py
rg -n "already_up_to_date|finmind_scope|run_finmind_segmented_update|attach_fpala|full" scripts/run_daily_tw_stock_auto_update.py data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
sed -n '5860,6135p' scripts/run_daily_tw_stock_auto_update.py
sed -n '1,90p' data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
crontab -l
sed -n '1,260p' docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_REAL_SOURCE_EXACT_INPUT_READINESS_PREFLIGHT_NO_RUN_EXECUTION_REPORT_CN.md
rg -n "BASE_PATH|ROOT_KINDS|FIXED_LOGS|TRUST_STORE_KINDS|storage|binding|locator|authorization|anchor|history|genesis|head|project_root" scripts/tw_policy_nmrpa3_real_trust_bootstrap.py scripts/schemas/tw_policy_nmrpa3_real_trust_bootstrap.schema.json tests/unit/test_tw_policy_nmrpa3_real_trust_bootstrap.py
rg --files data_tw | rg 'dng2_.*20260625|pricestore|price_store|twii|finmind_orthogonal_batch_state|institutional_margin' | head -400
find data_tw -maxdepth 7 \( -iname '*dng2*' -o -iname '*pricestore*' -o -iname '*price_store*' -o -iname '*twii*' -o -iname '*institutional_margin*' \) -printf '%y %m %u:%g %s %TY-%Tm-%TdT%TH:%TM:%TS %p\n'
find data_tw/artifacts/research/nmrpa -mindepth 1 -maxdepth 7 -printf '%y %m %u:%g %s %TY-%Tm-%TdT%TH:%TM:%TS %p\n'
rg -n "institutional|margin|source_state|immutable_response|absence|capture|binding|ROOT_KINDS|synthetic_injected_only" scripts/tw_policy_nmrpa3_source_adapter.py scripts/schemas/tw_policy_nmrpa3_source_adapter.schema.json docs/tw_portfolio_decision_model/POLICY_NMRPA3_S_PRICESTORE_TWII_ISOLATED_REAL_SOURCE_ADAPTER_SCHEMA_IMPLEMENTATION_NO_RUN_EXECUTION_REPORT_CN.md
rg -n "institutional|margin|immutable response|same-day|absence evidence|source_state" docs/tw_portfolio_decision_model/POLICY_NMRPA3_R* docs/tw_portfolio_decision_model/POLICY_NMRPA3_S* docs/tw_portfolio_decision_model/POLICY_NMRPA2* docs/tw_portfolio_decision_model/POLICY_NMRPA1* | head -600
sed -n '4420,5365p' scripts/run_daily_tw_stock_auto_update.py
git status --short
find data_tw/ops/daily_auto_update -maxdepth 1 -type d -name 'daily_tw_stock_auto_update_*' -printf '%f\n' | sort | tail -30
rg -n '"(status|asof|latest_before|latest_after|finmind_update_triggered|finmind_orthogonal_batch_update_triggered|finmind_scope_overridden_for_strict_e4|pending_asof_cleared)"' data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260821_20260821T144501Z/job.json data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260820_20260820T144501Z/job.json
find data_tw/ops/daily_auto_update/finmind_segment_cache -maxdepth 1 -type f -printf '%f\n' | sort | tail -50
find data_tw/canonical/price_store/tw_equity_daily data_tw/canonical/market_feature_store/twii_daily -mindepth 1 -maxdepth 2 -printf '%y %m %u:%g %s %TY-%Tm-%TdT%TH:%TM:%TS %p\n'
rg -n "build_tw_canonical_price_market_calendar|canonical/price_store|market_feature_store/twii_daily|immutable_source_roots|binding_store|anchor_ledger|nmrpa3_real_trust" scripts tests configs data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron --glob '!**/*.csv' --glob '!**/*.bin' --glob '!**/features/**'
sed -n '1,220p' docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_C_POST_BOOTSTRAP_LIFECYCLE_TEST_REPAIR_NO_DATA_CONFIG_MUTATION_WORK_CN.md
find data_tw/artifacts/research/nmrpa -mindepth 1 -type d -printf 'D\n' -o -type f -printf 'F\n' | sort | uniq -c
find data_tw/artifacts/research/nmrpa/immutable_source_roots/sealed_calendar/nmrpa_sealed_calendar_root_v1 data_tw/artifacts/research/nmrpa/immutable_source_roots/formal_instruments/nmrpa_formal_instruments_root_v1 data_tw/artifacts/research/nmrpa/immutable_source_roots/adjusted_price/nmrpa_adjusted_price_root_v1 data_tw/artifacts/research/nmrpa/immutable_source_roots/twii/nmrpa_twii_root_v1 data_tw/artifacts/research/nmrpa/immutable_source_roots/modela_signal/nmrpa_modela_signal_root_v1 data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/root_locator_registry data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/authorization_ledger data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/anchor_ledger data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/binding_store data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/stores/immutable_historical_head_storage -mindepth 1 -printf '%y %p\n'
find data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/fixed_logs \( -path '*/journals/*' -o -path '*/commit_markers/*' \) -printf '%y %p\n'
sed -n '1,260p' docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_EXECUTION_REPORT_CN.md
sed -n '260,520p' docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_EXECUTION_REPORT_CN.md
nl -ba docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_EXECUTION_REPORT_CN.md | sed -n '235,330p'
git diff --no-index --check /dev/null docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_WORK_CN.md
git diff --no-index --check /dev/null docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_EXECUTION_REPORT_CN.md
```

第一次 sandbox 内 `crontab -l` 因权限被拒；随后仅经授权在 sandbox 外只读执行，未修改 crontab。

## 9. Forbidden Audit

| action | performed |
| --- | --- |
| Price/TWII/institutional/margin/provider payload open/read/checksum | false |
| DB/network/OpenAI | false |
| 真实 target/date/authorization/credential/anchor/binding/event | false |
| 向 reserved roots/stores/logs 写 record | false |
| code/schema/test/fixture/data/config/cron 修改 | false |
| daily-auto/manual cron run | false |
| candidate/metric/outcome/training/inference/replay | false |
| provider/qlib/latest/product/backend/frontend/Agent 写入 | false |
| NMRPA3_U | not entered |

## 10. Substrate Unchanged 与 Files Changed

写文档前 inventory：

```text
data_tw/artifacts/research/nmrpa/** = 41 directories + 19 files
five reserved roots = empty
root_locator_registry/authorization_ledger/anchor_ledger/binding_store/
immutable_historical_head_storage = empty
all six fixed-log journals and commit_markers = empty
```

完成后已用同一命令复核：计数仍为 `41 directories + 19 files`；完整 pathname/type/mode/uid/gid/size/mtime 与写前相同；全部指定空 root/store/journal/marker 仍无输出。唯一允许新增并实际新增的文件为：

```text
docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_NMRPA3_T_R_D_THREE_RUNTIME_BLOCKER_CURRENT_STATE_PREFLIGHT_NO_PAYLOAD_READ_EXECUTION_REPORT_CN.md
```

本报告等待独立 reviewer；它不授权下一路线实现或任何 runtime 写入。
