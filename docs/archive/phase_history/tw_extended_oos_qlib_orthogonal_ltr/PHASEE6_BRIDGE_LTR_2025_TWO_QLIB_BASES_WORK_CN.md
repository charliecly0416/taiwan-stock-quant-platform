# Phase E6 工作文档：2025 LTR 桥接双底座实验

生成日期：2026-06-16

## 1. 本阶段目标

本阶段只做一件事：

```text
在相同的 2025 LTR 训练窗口下，
分别接 fresh qlib 与 2018-2022 frozen qlib 两个底座，
重新训练 orthogonal LTR，
判断 LTR 效果是否与 qlib 底座 / 训练长度相关。
```

本阶段不是默认策略切换，不改前端，不改交易链路，不改规则。

本阶段不得重训任何 qlib。两条分支都只能使用既有 frozen qlib score artifact：

- Branch A 使用既有 fresh qlib score；
- Branch B 使用既有 E1 2018-2022 frozen qlib OOS score。

## 2. 实验分支

必须建立两条完全对称的实验分支：

### 2.1 Branch A：fresh qlib 底座

```text
qlib base: fresh qlib（2017-2024）
LTR train: 2025-01-01..2025-12-31
LTR test: 2026-01-01..2026-05-07
```

### 2.2 Branch B：frozen qlib 底座

```text
qlib base: 2018-2022 frozen qlib
LTR train: 2025-01-01..2025-12-31
LTR test: 2026-01-01..2026-05-07
```

两条分支必须共享：

- 同一 LTR 模型家族；
- 同一 LTR 参数；
- 同一 label；
- 同一 78 特征 whitelist；
- 同一宽候选训练口径；
- 同一 replay 规则；
- 同一 next-day accounting；
- 同一 candidate_k=50；
- 同一 target_position_count=10。

## 3. 控制变量要求

本阶段只允许一个变量族变化：

```text
qlib 底座 / qlib score 来源
```

必须保持不变：

- LTR 模型结构；
- LTR 超参数；
- LTR label；
- LTR feature whitelist；
- LTR 训练窗口（固定 2025）；
- LTR 测试窗口；
- candidate_k；
- 持仓数；
- 费用税费；
- 回放引擎；
- 回放边界 top50 rerank；
- next-day accounting。

## 4. 输入合同

### 4.1 fresh qlib 分支

必须区分 training sample 输入与 replay/default baseline 输入：

```text
training/sample score source: S2B fresh qlib raw/post-filter score covering 2025 and 2026
replay/default baseline source: C4 repaired fresh qlib replay-ready artifact
```

不得只用 C4 replay-ready artifact 构建 2025 LTR 训练样本，因为 C4 主要是 replay-ready 修复产物，不能替代 2025 全年宽候选训练样本合同。

必要输入应来自：

- S2B fresh qlib raw/post-filter score/rank；
- C4 repaired fresh qlib replay-ready artifact；
- 2025 LTR 样本构建结果；
- 2026 untouched test row-aligned sample。

必须审计并报告：

- 2025 train daily rows min/median/max；
- 2026 test daily rows min/median/max；
- 是否 filtered_to_top50_for_training；
- 是否 filtered_to_full_market_top150_intersection；
- 2025H1 是否作为 qlib validation 被 fresh qlib 使用过；
- 若 2025H1 是 qlib validation，必须明确说明 Branch A 不是“严格 qlib-never-seen 2025 LTR train”，而是“fresh qlib frozen score + 2025 LTR train”桥接实验。

### 4.2 frozen qlib 分支

必须使用 2018-2022 frozen qlib OOS score 作为底座输入。

必要输入应来自：

- `phase_e1_raw_oos_score_rank_2023_2026.csv`
- 从 E1 raw OOS score 重新切出的 2025 宽候选 LTR train sample，或同等可审计 2025 LTR 样本
- `phasee2_feature_schema.csv`
- 2026 test row-aligned sample

不得复用 E3 的 2023-2025 已训练模型；本阶段必须训练一个只使用 2025 的 Branch B LTR。

## 5. 训练要求

执行者必须：

1. 先确认 2025 LTR 样本是宽候选，不得 top50-only。
2. 对 fresh qlib 与 frozen qlib 两条分支分别训练一个 LTR。
3. 两条分支都必须使用同一模型配置：
   - `LightGBM.LGBMRanker`
   - `lambdarank`
   - `ndcg`
   - `num_leaves=31`
   - `learning_rate=0.03`
   - `n_estimators=120`
   - `min_child_samples=40`
   - `random_state=42`
   - `n_jobs=2`
4. 不得调参，不得训练多个版本挑最好。
5. 不得使用 2026 进行训练、early stopping、模型选择或阈值选择。
6. 必须输出两条分支的 group audit：
   - train rows；
   - train dates；
   - train daily rows min/median/max；
   - train non-top50 rows；
   - test rows；
   - test dates；
   - test daily rows min/median/max；
   - test non-top50 rows；
   - top50-only 是否为 false。

## 6. 回放要求

两条分支训练完成后，必须在同一 2026 窗口做只读回放：

```text
window = 2026-01-01..2026-05-07
execution = next-day execution
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
candidate_k = 50
replay boundary = qlib top50 rerank only
```

每条分支必须至少包含一个 qlib baseline 和一个 LTR treatment：

```text
Branch A control: repaired fresh qlib Top50 adaptive
Branch A treatment: fresh qlib + orthogonal LTR trained on 2025

Branch B control: 2018-2022 frozen qlib top50 baseline
Branch B treatment: 2018-2022 frozen qlib + orthogonal LTR trained on 2025
```

报告中还必须列出参考项：

```text
E4 treatment: 2018-2022 frozen qlib + orthogonal LTR trained on 2023-2025
E5B repaired fresh qlib exact 2026 bridge result
```

参考项只用于解释训练长度，不得参与模型选择或调参。

必须输出：

- control vs treatment summary；
- daily NAV；
- actions；
- coverage audit；
- next-day accounting audit；
- PnL concentration；
- rank metrics；
- feature importance；
- forbidden action audit。

## 7. 重点审查

本阶段必须明确回答：

1. fresh qlib 底座和 frozen qlib 底座在同一 2025 LTR 训练窗下，谁更强；
2. LTR 增益是否依赖 qlib 底座；
3. LTR 增益是否依赖训练样本长度；
4. 是否还存在 top50-only 训练偏差；
5. 是否仍然只有 qlib 底座不同，其余控制变量都对齐；
6. 是否可以用该实验建立“比较链路”闭环。
7. 2025-only LTR 与 E4 的 2023-2025 LTR 差异是否支持“训练长度影响增益”的解释。

## 8. 停止条件

发现以下任一情况，必须停止并报告：

- 2025 LTR 样本仍是 top50-only；
- 2025 LTR train daily rows 明显不是接近 150，且无法解释；
- fresh qlib 与 frozen qlib 的 LTR 训练窗不一致；
- 2026 被用于训练或选择；
- 回放边界不是 qlib top50 rerank；
- 两条分支的 replay accounting 不一致；
- Branch A / Branch B 缺少各自 qlib baseline；
- 需要引入新特征、新规则、新 filter；
- 需要修改 qlib / LTR 参数；
- 需要重训 qlib；
- 需要触发 provider / accepted latest / frontend / monitor / trading 链路。

## 9. 输出报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE6_BRIDGE_LTR_2025_TWO_QLIB_BASES_EXECUTION_REPORT_CN.md
```

报告必须至少包含：

- 两条分支各自的训练合同；
- 2025 样本覆盖；
- 2025H1 fresh qlib validation caveat；
- 2026 replay 结果；
- Branch A control vs treatment；
- Branch B control vs treatment；
- Branch A treatment vs Branch B treatment；
- E4 2023-2025 LTR treatment 参考对比；
- LTR 训练长度与增益关系；
- 是否可以进入下一轮默认策略讨论。

## 10. Gate

若完成且未触发停止条件，gate 为：

```text
phase_e6_bridge_ltr_2025_two_qlib_bases_completed
```

