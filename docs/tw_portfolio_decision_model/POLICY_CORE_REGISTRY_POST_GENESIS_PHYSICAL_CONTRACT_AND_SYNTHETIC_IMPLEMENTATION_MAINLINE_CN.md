# Core Registry Post-Genesis Physical Contract And Synthetic Implementation 主线

## 1. 目标

为现有 NMRPA core trust bootstrap 的六条 fixed registry logs 冻结并实现一套与 actual sequence-0 文件兼容的 post-genesis 物理提交协议，只在 `/tmp` synthetic root 中证明：

```text
principal -> identity -> credential -> trusted service / publication authority / capture recorder
```

每个 committed record 必须能由 config-pinned fixed log、registry store、signed record、journal、marker、history entry 和 head 双向解析，最终输出唯一 `CoreRegistryCommitRef`，供 optional-source route 后续只读引用。

## 2. 非目标

```text
actual core substrate mutation
真实 principal / identity / credential / registration issuance
authorization / anchor / optional binding
真实 institutional / margin payload read
provider / qlib / latest / cron / frontend / backend
training / labels / metrics / NMRPA3_U
bootstrap/config migration
```

## 3. 权威现状

- config：`configs/tw_policy_nmrpa3_real_trust_bootstrap.json`；
- root：`data_tw/artifacts/research/nmrpa/trust_bootstrap_v1/`；
- 六条 fixed logs 均已有 `genesis.json`、V1 `head.json`、bare-array `historical_heads.json`、空 `journals/` 与 `commit_markers/`；
- principal/identity/credential records 只能写入 config-pinned `principal_identity_credential_registry_stores`；
- trusted service/publication authority/capture recorder records 只能写入 config-pinned `trusted_actor_registry_stores`；
- 不新增目录，不修改 config，不使用抽象 `<log_kind>/<log_id>/records/` layout。

## 4. 唯一物理模型

每次 synthetic registry commit 只写一个 domain object，并使用对应 fixed log：

```text
domain object                         immutable, pinned registry store
journals/{sequence20}--{tx}.record.json   immutable signed record
journals/{sequence20}--{tx}.journal.json  immutable journal
commit_markers/{sequence20}--{tx}.commit.json immutable marker
historical_heads.json                mutable bare-array append
head.json                            mutable activate last
```

sequence-0 head 保持 actual `nmrpa.log_head.v1` exact bytes/shape。sequence>=1 使用新的 tagged committed-head schema；history 仍是 bare array，允许 sequence-0 V1 entry 与后续 committed entries的 exact tagged union。禁止 wrapper migration。

## 5. Phase Plan

### CRPG0 Contract Freeze

冻结：

- 六条 log mapping、两个 store mapping与所有 basename grammar；
- six transition payload exact schemas；
- signed record、signature、journal、marker、committed head、mixed history和 `CoreRegistryCommitRef`；
- digest domains/order、CAS、one-shot transaction/replay、orphan、cross-log prerequisite closure；
- intent/plan public APIs、recursive exact types、full manifest、fault/rollback matrix；
- CRPG1 exact allowed files与测试矩阵。

结果必须经独立 reviewer 返回 `PASS_WITH_CONDITIONS` 才可进入 CRPG1。

### CRPG1 Synthetic Implementation

只允许实现独立 core registry adapter、两份 schema、dedicated tests 和阶段文档。所有 commits只发生在 pytest/tempfile `/tmp` 的 bootstrap-compatible copy。CRPG0_R 审查确认既有 generic writer 缺少 immutable-final 原子 no-clobber；因此 CRPG1 可对 `commit_schema_driven_transaction()` 增加一个默认关闭的具名 opt-in，并只为该能力扩展既有 T_R-E tests。既有 callers 默认行为与 five-root 语义不得变化，actual files仍禁止修改。

### CRPG2 Integration Closure

独立验证六 transition chain、`CoreRegistryCommitRef` 物理解析、fault rollback、five-root/optional non-regression、protected baseline，并输出 optional route 可复用 handoff。CRPG2 不执行 actual bootstrap或 optional binding。

## 6. Public API Boundary

CRPG1 目标 API：

```text
validate_intent(intent, descriptor, descriptor_sha256, project_root, capability)
plan(intent, descriptor, descriptor_sha256, project_root, capability)
validate_plan(plan, descriptor, descriptor_sha256)
commit(plan, descriptor, descriptor_sha256, project_root, capability,
       *, synthetic_fail_after_step=None)
resolve_commit_ref(ref, descriptor, descriptor_sha256, project_root, capability)
```

`validate_plan` 只表示 self-contained logical validity；physical acceptance只能由带 root/capability 的入口完成。schema-only 永不构成业务 acceptance。

## 7. Hard Boundaries

- actual project root、actual core/optional identity marker必须硬拒绝；
- caller不得传 payload path/bytes/file handles、checkpoint/cache/latest；
- exact types拒绝 bool/float/Decimal/numpy scalar及 subclasses；
- no-follow、regular-file、root-fd/inode capability、CAS、O_EXCL、fsync、same-parent replace、reverse rollback、terminal taint沿用 T_R-E；
- repository dirty state不得被清理或回滚。

## 8. Closure Criteria

```text
CRPG0 independent contract review PASS
CRPG1 dedicated + T_R-E + core bootstrap + optional non-regression PASS
all six transition nominal chains PASS
CoreRegistryCommitRef unbacked/resealed/path-alias attacks REJECT
every commit stage fault rollback PASS
actual roots/protected entries unchanged
real payload/network/DB/OpenAI access = 0
```

任一无法由 actual config/bootstrap 唯一导出的 locator/schema必须 STOP，不得再由 optional route补合同。
