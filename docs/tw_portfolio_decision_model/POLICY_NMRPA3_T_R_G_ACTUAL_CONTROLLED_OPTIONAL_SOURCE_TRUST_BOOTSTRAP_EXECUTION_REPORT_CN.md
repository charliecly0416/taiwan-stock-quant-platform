---
phase: NMRPA3_T_R_G_ACTUAL_CONTROLLED_OPTIONAL_SOURCE_TRUST_BOOTSTRAP
status: IMPLEMENTATION_COMPLETE_PENDING_INDEPENDENT_REVIEW
work_order_sha256: 16927001884834e9aa0e453ee927ee5187fe5d63f1bc6e19abf1b35e3615de6c
real_payload_read: 0
---

# NMRPA3 T_R-G 执行报告

## 范围与结果
严格按 R3 manifest 创建 15 个目录和 5 个 JSON；5 个 named staging 全部清除。未创建或替换 anchors。

## 逐路径 before/after（仅 lstat metadata）
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/journals`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/commit_markers`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/optional_source_profile_registry`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/authorization_ledger`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/anchor_ledger`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/binding_store`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/immutable_historical_head_storage`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/capture_attempt_store`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/response_evidence_store`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/sealed_object_store`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/sealed_object_store/sha256`: before=ABSENT; after=PRESENT; type=drwxr-x---; mode=0o750
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/descriptor.json`: before=ABSENT; after=PRESENT; type=-rw-r-----; mode=0o640
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/genesis.json`: before=ABSENT; after=PRESENT; type=-rw-r-----; mode=0o640
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/head.json`: before=ABSENT; after=PRESENT; type=-rw-r-----; mode=0o640
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/historical_heads.json`: before=ABSENT; after=PRESENT; type=-rw-r-----; mode=0o640
- `configs/tw_policy_nmrpa3_optional_source_trust.json`: before=ABSENT; after=PRESENT; type=-rw-r-----; mode=0o640
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/.descriptor.json.nmrpa3-tr-stage-v1`: before=ABSENT; after=ABSENT; type=; mode=
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/.genesis.json.nmrpa3-tr-stage-v1`: before=ABSENT; after=ABSENT; type=; mode=
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/.head.json.nmrpa3-tr-stage-v1`: before=ABSENT; after=ABSENT; type=; mode=
- `data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/.historical_heads.json.nmrpa3-tr-stage-v1`: before=ABSENT; after=ABSENT; type=; mode=
- `configs/.tw_policy_nmrpa3_optional_source_trust.json.nmrpa3-tr-stage-v1`: before=ABSENT; after=ABSENT; type=; mode=

## 内容摘要
JSON 使用 canonical UTF-8；descriptor/genesis/head/history 均为 genesis-only、`payload_evidence_state=not_bound`，未包含真实 target/date 或 payload。各 JSON content SHA256 已由 canonical payload 生成并通过结构检查。

## 保护对象与禁止边界
protected metadata before/after unchanged: `True`。未读取真实 institutional/margin/price/TWII/provider payload bytes；未写 credential、authorization、anchor、binding、capture、sealed evidence、post-genesis record、latest、cron、provider、qlib、DB、OpenAI、frontend/backend；未进入 T_R-H 或 NMRPA3_U。

## 验证
layout、owner/group、mode、staging absence、descriptor hash、genesis/head/history linkage、`py_compile`、`git diff --check` 由本执行步骤完成或随后复核。

## Post-write protected evidence appendix

## Documentation Output Scope

本报告是 coordinator/reviewer 流程的 documentation output，不属于 R3 的 20 个 final paths 或 5 个
staging paths，也不属于 bootstrap data/config creation authorization。该报告的写入由后续修复工作单单独授权。

写后独立复核结果：`15` 个 companion directories、`5` 个 final JSON、`5` 个 named staging paths 均符合 R3 状态；staging 为 `ABSENT`。所有新建目录为 `0750`、文件为 `0640`、owner/group 为 `chuliyang:chuliyang`。leaf stores、journals、commit_markers 均为空。

八个 protected regular files 与 R2 冻结 baseline SHA-256 完全一致（`8/8`）：

```text
scripts/tw_policy_nmrpa2.py = ddfccffa20c79f427409314627a8e1a30e1416c2862c640ed99d0c6e7ed79dfc
scripts/tw_policy_nmrpa3_source_adapter.py = 3d131035c8a14b374af3d1c55f602a6f3cad3e837a783c6e609438f09c001fa1
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron = 6ae5ec28ad71e63959fee0327d6162ee99caec5b8a98e1e5ae937bb68bc8c620
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json = 477ec76da67d0afd60b234279717bb8eb28286db9d07936e4b53c667d3003b02
data_tw/experiments/option_c_daily_signal/latest_signal.json = 7ee18951d8115ed808d7630775eb5dbc230c8c8071ca42868373b996710bc131
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json = ce403d972fcad52277dcaa149aaafde2bed1cfd37e93f6e31f49fd570e56630c
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json = ec2019a7475a85f34299e0734b488d5119b8154d7eb095be375e194fba41ee4b
data_tw/artifacts/agent_daily_prompt/latest.json = df69bb717c85b742040e2ac763c05f9d0f43522267898417dbc71e4500c5eb0a
```

Formal provider R2 metadata-v1 的无 payload 重放为 `1206` records；仅 pathname 与 no-follow `lstat`，未 open/read/mmap/checksum provider payload bytes。现有 protected/latest、cron、provider metadata 未被本步修改。该 appendix 是写后复核证据，不替代后续独立审查。
