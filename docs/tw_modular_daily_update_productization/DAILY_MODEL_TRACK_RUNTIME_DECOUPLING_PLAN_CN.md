# 每日模型轨道运行时解耦计划

状态：已实现并通过独立审查。

## 目标

把每日完整数据批次改造成配置驱动的模型轨道 fan-out：`model_a_only` 与
`model_a_plus_b_b19r2r` 在编排层地位相同，各自读取同一批次的数据快照，并各自输出
标准 `ModelSignalArtifact`。A+B 的 adapter 必须在自己的隔离目录中重新运行 Model A，
不得消费 `model_a_only` 轨道的输出。

## 保持不变

- Model A 仍是唯一 active baseline 和产品默认模型。
- A+B 仍是 nonblocking research shadow，`production_allowed=false`。
- 模拟账户 allowlist 仍只有 `model_a_only`。
- 现有每两小时 Model A 快速更新、产品 latest 发布和只读 API 不改变语义。
- 不训练模型，不改模型参数，不改策略，不触发真实订单。

## 实现步骤

1. 保持 `configs/readonly_model_tracks.yaml` 的冻结治理 checksum 不变，在 `configs/daily_model_tracks.yaml` 为每条轨道声明运行时 adapter 和数据依赖。
2. 新增单一 daily model-track runner，负责加载配置、检查依赖、独立调用 adapter、汇总统一结果。
3. Model A adapter 复用冻结 Qlib scorer；A+B adapter 在隔离目录中先重跑 Model A，再调用 B19R2R。
4. 完整数据批次就绪后运行两条轨道；required 失败阻塞该批次，nonblocking 失败只记录。
5. 每条轨道只写自己的 job-local artifact；A+B 继续追加本轨既有的 prospective research ledger，用于跨日只读观察，不读取或修改 A 轨 artifact。本轮不新增产品 latest，不改变默认前端或模拟账户。

## 统一结果

每条轨道至少返回：

```json
{
  "track_id": "model_a_plus_b_b19r2r",
  "runtime_adapter_id": "daily_model_a_plus_b_b19r2r_v1",
  "workflow_policy": "nonblocking",
  "status": "READY_RESEARCH_SHADOW",
  "artifact_type": "ModelSignalArtifact",
  "artifact_dir": "...",
  "source_snapshot_id": "...",
  "production_allowed": false
}
```

## 验收标准

- 两条轨道没有 workflow dependency 边；A+B 不读取 A 轨道 Artifact。
- A+B 的内部 Model A 与 B 输出绑定同一 `asof`、source run 和 decision cutoff。
- 未知 adapter、缺数据、PIT 不完整均 fail closed。
- A+B 失败不改变 Model A、provider、accepted latest、产品 latest 或 pending 状态。
- focused tests、M3 daily orchestrator validator、模块合同回归和 `git diff --check` 通过。
- 独立 reviewer 检查配置身份、Artifact 合同、主线回归和安全边界。
