---
created_at: 2026-08-22
status: frozen_manifest_ready_for_independent_review
phase: NMRPA3_T_R_F_R3_WORK_ORDER_SHA_RECONCILIATION_AND_FINAL_MANIFEST_LOCK_NO_PAYLOAD_READ
scope: docs_only_evidence_lock
real_payload_read_allowed: false
code_data_config_cron_write_allowed: false
nmrpa3_u_authorized: false
---

# NMRPA3 T_R-F R3 工作单：稳定哈希与最终 manifest 锁定

## 1. 目标与禁止边界

本工作单仅解决 R2 工作单与执行报告的 SHA-256 不一致。R2 当前实际 SHA 为
`063c5962d9f1551348866f751cfcf913e86aadbaeb955ce8205bd2a881da8044`；旧的
`367cba9e70821f281aba6d7119d48d201abc4868772dfdf65976051848ee5628` 不再是有效锁。

本文件是新的最终 manifest/authorization handoff。其内容在 hash capture 后冻结，禁止再修改；执行报告与后续审查只能引用本文件 capture 后得到的稳定 SHA。不得修改代码、schema、fixture、data、config、cron、provider、qlib/latest、frontend/backend，不得创建 companion，不得读取真实 institutional/margin payload，不得进入 T_R-G 或 NMRPA3_U。

## 2. 最终路径 manifest（固定、不增不减）

最终清单固定为 `20 = 15 directories + 5 JSON files`。以下顺序是唯一顺序，全部为 repository-relative ASCII 字面量：

```text
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/descriptor.json
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/genesis.json
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/head.json
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/historical_heads.json
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/journals/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/commit_markers/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/optional_source_profile_registry/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/authorization_ledger/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/anchor_ledger/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/binding_store/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/immutable_historical_head_storage/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/capture_attempt_store/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/response_evidence_store/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/sealed_object_store/
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/stores/sealed_object_store/sha256/
configs/tw_policy_nmrpa3_optional_source_trust.json
```

5 个 JSON 为 `descriptor.json`、`genesis.json`、`head.json`、`historical_heads.json` 和外置 companion config；它们写前必须为 `ABSENT`。

## 3. 祖先闭包与 staging manifest

目录作用域固定为 `20 = 15` 个 companion directories、`4` 个既有 data anchors、`1` 个既有 `configs/` anchor。既有 anchors 只验证，不创建或替换：

```text
data_tw/
data_tw/artifacts/
data_tw/artifacts/research/
data_tw/artifacts/research/nmrpa/
configs/
```

15 个 companion directories 是最终清单中除 JSON 外的全部目录项。任何缺失 anchor、额外 parent、路径别名或 symlink 都必须 STOP，禁止隐含授权。

5 个 named staging paths 与 final 的固定映射如下：

```text
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/descriptor.json
 -> data_tw/artifacts/research/nmrpa/optional_source_trust_v1/.descriptor.json.nmrpa3-tr-stage-v1
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/genesis.json
 -> data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/.genesis.json.nmrpa3-tr-stage-v1
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/head.json
 -> data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/.head.json.nmrpa3-tr-stage-v1
data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/historical_heads.json
 -> data_tw/artifacts/research/nmrpa/optional_source_trust_v1/fixed_logs/optional_source_binding_log/.historical_heads.json.nmrpa3-tr-stage-v1
configs/tw_policy_nmrpa3_optional_source_trust.json
 -> configs/.tw_policy_nmrpa3_optional_source_trust.json.nmrpa3-tr-stage-v1
```

All 5 staging paths must be `ABSENT`, regular-file-only when staged, non-symlink, fixed-name, and used only for their mapped JSON. final/staging intersection is empty.

## 4. Creation, commit and rollback contract

Before any future authorized bootstrap, perform per-path no-follow `lstat`, protected fingerprints, and verify all 20 final paths and 5 staging paths are `ABSENT` while the 5 anchors are valid existing directories. Use directories `0750`, files `0640`, owner/group `chuliyang:chuliyang`, exclusive creation, `fsync(file)`, same-parent `os.replace`, and parent `fsync`.

Commit order is fixed: validate closure; create 15 companion directories in ancestor order; stage and replace `descriptor.json`, `genesis.json`, `historical_heads.json`, then `head.json`; fsync each parent; stage and replace companion config last; fsync `configs/`; validate layout, checksums, activation edge, and protected pointers. Only paths that were `ABSENT` in this round may be rolled back. Rollback failure is terminal-taint and STOP; pre-existing paths are never deleted or overwritten.

Future post-genesis transactions remain outside this bootstrap: principal/issuer/recorder, profile, authorization, capture attempts, sealed evidence, classification, binding, anchor, journal, commit marker, historical head, head, and any latest/config pointer require separate exact authorization. The optional source is a child binding and must never mutate the five-root binding.

## 5. R3 evidence lock

Hash procedure: after this document is complete, run `sha256sum` on this file once; record UTC capture time in the separate execution report; do not modify this file afterward. The R3 work document itself is the sole hash-locked contract. The execution report must reference only that final SHA and must not treat either R2 SHA as valid.

```text
R3 work document hash: captured after freeze and recorded only in execution report
R2 old hash 367c...ee5628: INVALID
R2 current hash 063c...8044: historical evidence only, not the final lock
```

## 6. Required verification and handoff

Run only `git diff --check`, SHA capture, and pathname-state checks for the 20 final and 5 staging paths. Confirm T_R substrate, protected files, provider metadata, config and cron are unchanged. Do not read payload bytes/content/checksums. Required result:

```text
READY_FOR_INDEPENDENT_REVIEW
T_R_G_NOT_AUTHORIZED
ACTUAL_COMPANION_BOOTSTRAP_NOT_EXECUTED
REAL_PAYLOAD_READ_ZERO
```
