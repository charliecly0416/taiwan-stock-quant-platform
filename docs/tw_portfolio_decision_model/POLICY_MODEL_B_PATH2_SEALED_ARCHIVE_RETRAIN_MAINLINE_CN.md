# Model B 路径二：原 78 特征历史封存归档与合规重训主线

生成日期：2026-08-25
状态：`P2-0R_PASS_STOP_ARCHIVE_NOT_SEALED`

## 1. 目标

在不破坏既有 Model A、旧 Model B、前端、daily auto、latest 或生产只读链路的前提下，验证并建设原 Model B 78 特征的历史 sealed source archive。只有当每一条训练/评测样本同时具备可验证的 `asof`、`available_at`、source snapshot、lineage、标签 maturity 和 purge 证据后，才允许重新训练原 78 特征 Model B。

路径二的含义是：保留原 Model B 的 78 特征语义和顺序，重新建立当前合同下的输入与训练边界；不是把旧模型、旧分数或旧收益报告直接升级为合规结果。

## 2. 当前基线

- 旧 Model B 是 `LightGBM.LGBMRanker`，固定 78 特征。
- 现有历史资料包含 `phase_o1/o1r/o2/o3/o4` 以及 E1/E2/E3 研究样本和 raw archive。
- 2026-01-02..2026-05-07 有 79 个 score dates、3,950 条 Qlib Top50 行。
- 其中 37 条 Top50 行缺少 `margin_short_trade_date`、`margin_short_available_at`、source snapshot、source path 和 lineage。
- 旧训练窗口为 2023-01-03..2025-12-31；对 2026-01-02 首个 OOS 日，按 10 个交易日 purge 的合法训练截止日应为 2025-12-17，旧训练边界未证明满足该要求。
- 现有 Model B 结果继续标记为 `legacy_exploratory` / `readonly comparison`，不进入生产默认或正式 OOS 结论。

## 3. 非目标与禁止事项

- 不修改 Model A、旧 Model B、ModelSignal latest、qlib accepted latest、provider、cron、daily auto、frontend/backend 默认值。
- 不连接网络、DB、OpenAI 或 broker；不补抓、不猜测、不用 later data 倒灌历史。
- 不零填补、neutral-fill、静默删除缺口或以同股票其他日期代替目标日期的 PIT 事实。
- P2-0/P2-1/P2-2 不训练、不评分、不 replay、不生成生产 artifact。

## 4. 阶段路线

### P2-0：sealed archive inventory（当前阶段）

盘点 78 特征、原始 source archive、字段 schema、snapshot identity、fetch time、availability、label maturity 和训练/评测边界；形成 manifest、gap matrix、protected-scope audit 和独立审查。

### P2-1：archive contract closure（仅在 P2-0 通过后）

为每个 source family 冻结 immutable snapshot manifest、逐行 lineage、可用时间规则、缺失/未知表示和标签 maturity contract。若 37 条缺口或训练 purge 无法闭合，输出 STOP，不进入训练。

### P2-2：sealed archive build（仅允许 isolated archive）

在明确授权和完整来源存在时，以 staging + checksum + atomic rename 构建隔离的 78-feature archive；不触碰 canonical provider、accepted latest 或产品链路。

### P2-3：合规训练/评测 preflight（默认不训练）

冻结共同窗口、purge、fold、feature hash、模型配置和输入 manifest。只有用户另行授权训练，且审查者 PASS，才可进入 P2-4。

### P2-4：controlled retrain/scoring（需单独授权）

训练新版本 Model B，生成标准 ModelSignalArtifact 候选和只读比较报告；新版本独立命名，不能覆盖旧 Model B。

### P2-5：readonly comparison/closure

与 Model A、旧 Model B 做同窗口、同策略、同执行价口径的只读比较；不自动接入前端默认、daily auto 或 latest。

## 5. P2-0 执行者职责

1. 读取本主线及当前模型/数据合同。
2. 只读盘点 78 特征 hash、源 archive、E1/E2/E3、phase O1/O1R/O2/O3/O4 和 MB26F0/MB26R0 证据。
3. 对每个 source family 判断是否具备 sealed identity、PIT availability、lineage 和缺失闭合。
4. 生成隔离 evidence/report，不改任何既有 artifact。
5. 发现任一未知缺口时标记 `unknown/quarantine`，不得自行修复。

## 6. P2-0 审查者职责

独立检查 archive 证据是否逐行绑定目标日期、是否误把研究样本当 sealed archive、是否发生 later-data 倒灌、是否满足 78 特征 hash、是否越过禁止边界。结论只能是 `PASS_WITH_CONDITIONS`、`STOP_ARCHIVE_NOT_SEALED` 或 `FAIL_NEEDS_REPAIR`，并写出下一阶段工作单。

## 7. 统一停止条件

- 任一特征缺少可验证 source lineage 或 available_at。
- 任一 label 缺少 maturity/availability binding。
- 训练截止日未满足 purge，或训练/评测窗口重叠。
- source archive 只是当前导出、未保存 immutable snapshot identity。
- 需要网络、DB、用户猜测路径或后来的数据才能补齐历史事实。

## 8. 完成条件

P2-4 完成不代表生产可用。只有新版本通过 ModelSignalArtifact、validator、同窗口 OOS、策略只读回放和独立审查，才可讨论研究候选；生产默认仍需另行路线和授权。

## 9. 首个执行命令

执行 `P2-0_SEALED_ARCHIVE_INVENTORY_NO_TRAINING`，随后由独立审查者执行 `P2-0R_ARCHIVE_INVENTORY_REVIEW_OR_STOP`。

## 10. 当前审查结果

P2-0 执行和 P2-0R 独立审查已完成，结论为 `PASS_STOP_ARCHIVE_NOT_SEALED`。当前不能进入 P2-1 的实际 archive 构建，也不能训练、评分或 replay。重启条件见 P2-0 执行报告和独立审查报告。
