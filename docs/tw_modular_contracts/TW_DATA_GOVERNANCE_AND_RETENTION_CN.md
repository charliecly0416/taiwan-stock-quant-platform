# 台股研究数据治理与保留策略

## 目标

训练、测试和回测应从同一套可追溯的日更资产读取，不再依赖某次实验目录或人工记忆。治理层保留 event date、真实 acquisition lineage、decision cutoff、validator 和 SHA256；特征与未来标签分开管理，避免未来信息泄漏。

## 每日自动维护

当前已落地的第一阶段是轻量 research history：

1. Model A inference input 和 signal 已是 canonical artifact，治理层只登记路径、哈希和血缘，不复制数据。
2. B19R2R 只有通过 research-only 合同后，才把 78F、signal、schema 和审计文件从临时 job 目录固化到 append-only canonical history。
3. `index.json` 提供按日期解析入口，`latest.json` 只指向已验证且含 Model A 的最新日期。
4. 失败保留 previous-good，并且不阻断 Model A 主线。

后续 price、TWII、机构、融资融券、估值、月营收和公司行动应按各自自然频率写 immutable 分区。每日任务只增量写新日期或新的 revision；训练 DatasetSnapshot、成熟标签和回测结果按需构建并以内容哈希缓存，不做每日全量重建。

## PIT 要求

- `event_date` 与 `available_at/acquired_at` 分开记录。
- 特征只允许读取 `available_at <= decision_cutoff` 的版本。
- 修订数据追加新 vintage，不覆盖旧值。
- label 在 horizon 到期后才成熟，并记录 `label_available_at`。
- DatasetSnapshot 必须冻结日期范围、universe、feature/label version、source manifest SHA、费用和执行价。

Model A 现有 manifest 中部分 `available_at` 仍是交易日占位语义，不能单独作为严格 PIT 证明。治理索引保留真实 `source_acquisition_run_id` 和 `decision_cutoff`，后续 canonical facts 分区仍需补齐来源的真实 UTC availability。

## 保留与删除

引用关系优先于年龄。active baseline、registry/latest、训练冻结、已发布 signal/snapshot、回测 lineage、未结算 prospective event、pending/running job 引用的对象一律保护。

自动删除当前关闭。任何物理删除必须依次完成：

```text
reference closure -> external backup -> SHA256 manifest -> credential scan
-> isolated restore verification -> quarantine -> delete
```

默认期限记录在 `configs/tw_data_governance.yaml`。这些期限只能产生候选，不能绕过引用扫描。当前大型 `option_c_ops`、daily ops 和旧实验目录在备份闭包与引用图未补齐前不得删除。

## 消费方式

训练、测试和交互式回测应先按日期范围和模型解析 research history index，再生成不可变 DatasetSnapshot 或 ReplayResult。API handler 只创建只读 simulation job 或读取已生成结果，不在请求内训练模型、抓取 provider、改 latest 或执行交易。
