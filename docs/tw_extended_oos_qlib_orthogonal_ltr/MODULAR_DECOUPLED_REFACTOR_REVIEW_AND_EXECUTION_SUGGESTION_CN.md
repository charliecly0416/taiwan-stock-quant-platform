# 模块化解耦重构审查建议与执行方案

生成日期：2026-06-16

## 1. 审查结论

`MODULAR_DECOUPLED_RESEARCH_AND_PRODUCTION_PIPELINE_DESIGN_CN.md` 的方向是合理的，也符合当前项目进入下一阶段的需要。

当前项目已经在 formal replay matrix 中完成了第一层解耦：

- `candidate_rank` 决定 qlib top50 universe / exit boundary；
- `buy_score` 决定 top50 内买入顺序；
- `full_qlib_rank` 用于持仓跌出 top50 后的最差持仓判断；
- qlib 与 LTR 可以复用同一个 replay engine，只改变输入列映射。

但这仍然只是回放内部的局部解耦。后续如果继续新增模型、正交数据、策略规则、前端展示或日更链路，若没有统一 artifact contract，项目仍会继续产生大量临时脚本。

因此，模块化重构有必要推进。我的建议是：

```text
认可总体架构，但必须渐进实施。
先稳定研究/回放链路，再处理数据抓取、前端展示和日更生产链路。
```

## 2. 核心原则

本轮重构的目标不是立刻重写整个项目，而是先建立可持续扩展的接口边界。

必须坚持以下原则：

1. 先 contract，后重构。
2. 先 adapter，后替换旧脚本。
3. 先只读研究链路，后日更生产链路。
4. 新旧结果必须可复现对齐。
5. 默认策略切换必须单独决策，不由重构自动发生。
6. 不因为模块化而新增策略结论。
7. 不触发 provider publish / accepted latest / monitor / broker / order。

## 3. 对原设计的保留意见

原设计中以下模块边界应保留：

| 模块 | 是否保留 | 原因 |
| --- | --- | --- |
| ModelSignalArtifact | 保留，优先级最高 | 这是模型与策略解耦的核心。 |
| StrategyRuleContract | 保留，优先级最高 | 新策略必须只消费标准信号和持仓状态。 |
| OrderIntentArtifact | 保留，优先级高 | 能把策略决策和成交记账拆开。 |
| ReplayResultArtifact | 保留，优先级高 | 让分析和前端不再读临时回放文件。 |
| Validator | 保留，优先级高 | 防止 future label、口径漂移、错误字段进入链路。 |
| Provider / Normalizer | 保留，但后置 | 改动风险高，容易影响现有日更。 |
| Daily Orchestrator | 保留，但最后做 | 必须先 shadow run，不能直接替换现有自动化脚本。 |
| Presentation Contract | 保留，但后置 | 前端应只读发布产物，但要等 artifact 稳定后再接。 |

## 4. 需要收敛的地方

### 4.1 M0 不要一次性冻结所有大合同

原文 M0 要产出很多 contract 文档，方向正确，但第一轮过大。

建议 M0 只冻结最小可执行合同：

```text
MODEL_SIGNAL_CONTRACT_CN.md
STRATEGY_RULE_CONTRACT_CN.md
ORDER_INTENT_CONTRACT_CN.md
REPLAY_RESULT_CONTRACT_CN.md
```

Provider、Normalizer、Feature、Daily Orchestrator 可以先写草案，不作为第一轮实现阻塞项。

### 4.2 M1 与 M2 应调整顺序

原设计是先把 `StrategySpec` 从 Python 移到 YAML，再做 ModelSignalArtifact 标准化。

更稳的顺序是：

```text
旧 qlib/LTR replay-ready CSV
  -> legacy adapter
  -> 标准 ModelSignalArtifact
  -> YAML config 指向标准 signal artifact
  -> replay matrix 从标准 signal artifact 读取
```

原因：

- 如果先 YAML 化但仍读取旧私有列名，解耦不彻底；
- 新模型接入的真正接口应该是 `ModelSignalArtifact`，不是某个历史 CSV 的列名；
- adapter 可以保护现有研究结果，不需要重跑模型。

### 4.3 必须保留旧产物兼容层

现有核心产物不能废弃，例如：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv
```

第一轮应写 adapter，把它们转换成标准信号产物，而不是要求重训或重算。

### 4.4 Daily Orchestrator 必须后置

`scripts/run_daily_tw_stock_auto_update.py` 涉及真实日更、provider publish、accepted latest、前端展示等敏感链路。

第一阶段不能直接替换它。

后续如果要接入，必须满足：

- shadow artifact only；
- 不修改 `latest_signal.json`；
- 不切换 accepted latest；
- 不阻塞 fresh qlib 当前主链路；
- 连续多日只读验证通过后再讨论正式接入。

## 5. 推荐实施路线

### Phase R0：最小合同冻结

目标：

- 冻结研究/回放链路最小 contract；
- 不改业务逻辑；
- 不重跑模型；
- 不产生新策略结论。

产物：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

验收：

- 每个 contract 有 required fields；
- 每个 contract 有 forbidden fields/actions；
- 明确 `candidate_rank / buy_score / full_qlib_rank` 语义；
- 明确 qlib 与 LTR 如何映射到统一 signal；
- 明确 `buggy_e8r` 只能作为 diagnostic。

禁止：

- 训练模型；
- 修改前端；
- 修改日更；
- 改默认策略；
- 重跑收益筛选。

### Phase R1：Legacy Signal Adapter

目标：

把现有 qlib / LTR 产物转换为标准 `ModelSignalArtifact`。

输入：

```text
phasec4_repaired_replay_ready_scores.csv
phasee4_replay_ready_scores_2026.csv
phasee6_replay_ready_scores_2026.csv
phasee1_raw_oos_score_rank_2023_2026.csv
```

输出示例：

```text
data_tw/artifacts/signals/fresh_qlib_adaptive/{run_id}/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/{run_id}/manifest.json
data_tw/artifacts/signals/frozen_qlib_2018_2022/{run_id}/manifest.json
```

标准字段至少包含：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
```

验收：

- row count 与旧 replay-ready 输入一致；
- 2026_ytd 每日 top50 覆盖一致；
- duplicate key 为 0；
- forbidden field 不存在；
- 不改变任何 score 数值；
- 不改变任何排序结果。

### Phase R2：Config-driven Formal Replay Matrix

目标：

让 formal replay matrix 不再硬编码 `StrategySpec`，而是读取 YAML config。

配置示例：

```yaml
signals:
  - method: fresh_qlib_adaptive
    artifact: data_tw/artifacts/signals/fresh_qlib_adaptive/latest/manifest.json
  - method: e4_frozen_qlib_2023_2025_ltr
    artifact: data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/latest/manifest.json

rules:
  - original
  - top50_exit_all
  - top50_exit_one_worst_sell
  - one_sell_one_buy_correct
  - one_sell_one_buy_buggy_e8r

windows:
  - name: 2026_ytd
    start: 2026-01-01
    end: 2026-05-07
```

验收：

- 新 config 版 summary 与当前 formal replay summary 在 `2026_ytd` 下完全一致；
- daily_nav / actions / snapshots 可追溯；
- no training / no tuning；
- no provider / accepted latest / frontend / monitor / trading。

### Phase R3：StrategyDecision / OrderIntent 拆分

目标：

把当前 replay 内部的策略决策拆出来。

拆分后：

```text
ModelSignalArtifact + PortfolioState + StrategyRule
  -> OrderIntentArtifact
OrderIntentArtifact + PriceStore + ExecutionConfig
  -> ReplayResultArtifact
```

验收：

- order intent 可单独审计；
- replay execution 不读取 `buy_score` 以外的模型私有文件；
- 同一规则下 replay result 与 R2 完全一致；
- 能证明策略模块没有读取未来价格或 future return。

### Phase R4：Analysis Artifact

目标：

把收益、回撤、换手、PnL 集中度、规则归因从 replay 中拆出来。

验收：

- analysis 只读 ReplayResultArtifact；
- analysis 不重新回放；
- analysis 不改默认策略；
- 可以输出前端可读 summary。

### Phase R5：Daily Shadow Integration

目标：

只读接入日更链路，但不替换现有主流程。

要求：

- 只在 fresh qlib accepted latest 成功后运行；
- 只写 shadow readonly artifact；
- 不修改 latest_signal；
- 不切 accepted latest；
- 不触发 monitor / broker / order。

验收：

- 连续多个 asof 可生成 signal / decision / replay / analysis artifact；
- 失败不会影响现有页面和日更；
- E2E readonly 安全通过。

## 6. 第一轮建议执行范围

第一轮不要做 M4-M6。建议执行者只做：

```text
R0 + R1 + R2
```

也就是：

1. 冻结最小 contract；
2. 写 legacy signal adapter；
3. formal replay matrix 改成读取标准 signal artifact + YAML config；
4. 验证结果与当前 formal replay matrix 完全一致。

这样能最快解决当前痛点：

- 新模型不用再改 replay engine；
- 新策略不用再解析模型私有文件；
- 旧研究结果不丢；
- 未来接正交数据、新 LTR、新 qlib、新策略都有入口。

## 7. 风险与防护

| 风险 | 防护 |
| --- | --- |
| 重构范围过大 | 第一轮只做 R0-R2。 |
| 新旧结果不一致 | 要求 summary/action/nav 关键字段 diff 为 0。 |
| 旧产物被废弃 | 先做 adapter，不重训不重算。 |
| 日更链路被破坏 | Daily Orchestrator 后置，只 shadow run。 |
| 前端误展示临时实验 | Presentation 接入必须等 publish artifact 稳定。 |
| 策略收益被重构过程影响 | 重构阶段不得新增策略结论。 |
| future label 泄漏 | validator 必查 forbidden fields。 |

## 8. 给执行者的一句话

请按本建议文档先执行 R0-R2：冻结最小 ModelSignal/StrategyRule/OrderIntent/ReplayResult contract，新增 legacy signal adapter，并把 formal replay matrix 改成读取标准 ModelSignalArtifact + YAML config；必须证明新旧 `2026_ytd` replay summary/actions/nav 关键结果完全一致，不得训练、调参、改默认策略、触发 provider/accepted latest/frontend/monitor/交易链路。

## 9. 给审查者的一句话

请审查执行者 R0-R2 结果是否真正实现了模型信号与策略/回放解耦，重点核对 contract 字段、legacy adapter 是否零改动复刻旧排序、config replay 与旧 formal replay 的结果是否完全一致，以及是否有训练、调参、future label、provider/accepted latest/frontend/monitor/交易链路越界；若结果不一致或 contract 需要变更，必须停下来让用户确认。
