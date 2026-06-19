# 可扩展 Contract / Capability / Plugin Registry 设计

生成日期：2026-06-16

## 1. 目的

R0-R2 已冻结并验证最小闭环：

```text
ModelSignalArtifact
  -> YAML config
  -> config-driven replay matrix
  -> baseline 2026_ytd summary / actions / daily_nav parity
```

R3 的目标不是扩大 replay 逻辑，而是定义未来扩展模型、策略、信号字段和 replay 输出的受控机制。核心原则：

- strict core contract 不变；
- optional extension 必须显式声明；
- strategy 必须声明依赖；
- validator 决定某个 strategy 是否可以消费某个 artifact；
- forbidden fields/actions 全局强制；
- 不允许策略直接读取 legacy 私有列。

## 2. Immutable Core Fields

以下字段是 `ModelSignalArtifact` 的不可变核心字段，字段名、语义和策略边界不得被 extension 改写：

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
source_model_artifact
source_feature_artifact
```

核心语义：

- `candidate_rank` 只决定 qlib top50 universe / exit boundary；
- `buy_score` 只决定候选池内买入排序；
- `full_qlib_rank` 只用于 qlib full-rank worst-sell 语义；
- `available_at` 必须支持 PIT 可见性检查；
- `date + instrument` 仍是信号表唯一键。

任何 extension 不得重定义以上字段，也不得用 extension 字段替代核心字段，除非后续有新的 contract version 和单独审查结论。

## 3. Optional Extension Fields

可扩展字段必须满足：

- 字段名不在 core fields 中；
- 字段名不匹配 forbidden field / prefix；
- 在 manifest 的 `extensions.fields` 中声明；
- 声明 dtype、semantic_role、availability_policy、producer、consumer；
- 若可被策略使用，必须被 strategy dependency 显式引用；
- 默认不得进入 ranking、sell boundary、order sizing 或 risk-off 逻辑。

推荐命名：

```text
ext_{domain}_{name}
```

示例：

```text
ext_risk_volatility_score
ext_sector_code
ext_sector_exposure
ext_horizon_5d_score
ext_horizon_20d_score
ext_ensemble_score
ext_liquidity_bucket
```

不推荐：

```text
future_return_10d
label_top_heavy
phasee6_branch_a_fresh_ltr_score
qlib_rank_raw
action
target_position
```

## 4. Capabilities

Artifact manifest 必须用 `capabilities` 描述自己能支持的消费方式。capability 是能力声明，不是策略结论。

示例：

```json
{
  "capabilities": {
    "core_signal_v1": true,
    "candidate_boundary": "qlib_top50",
    "buy_ordering": "buy_score_desc",
    "full_rank_exit": "full_qlib_rank",
    "supports_ltr_rerank": true,
    "supports_sector_exposure": false,
    "supports_risk_score": false,
    "pit_available_at_checked": true
  }
}
```

能力命名规则：

- 用稳定、领域语义明确的 key；
- 不用临时实验名；
- 不把收益、胜率、回撤改善写成 capability；
- 不把 `buggy_e8r` 这类诊断规则写成有效策略能力。

## 5. Plugin Registry

未来新增模型、策略或 validator 时，建议使用只读 registry 文件登记：

```text
configs/tw_modular_registry.yaml
```

建议结构：

```yaml
contracts:
  model_signal:
    core_version: r1.0
    docs: docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md

capabilities:
  core_signal_v1:
    required_fields:
      - date
      - instrument
      - candidate_rank
      - buy_score
      - full_qlib_rank
  sector_exposure_v1:
    extension_fields:
      - ext_sector_code
      - ext_sector_exposure

strategies:
  top50_exit_one_worst_sell:
    dependency_contract: configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
```

Registry 只声明可用能力和依赖，不触发训练、不触发 replay、不修改默认策略。

## 6. Validator 责任

validator 不做策略收益判断，只做 contract compatibility 判断：

1. artifact 文件是否存在；
2. core fields 是否完整；
3. extension schema 是否声明完整；
4. forbidden fields 是否不存在；
5. manifest capabilities 是否满足 strategy dependencies；
6. PIT policy 是否满足；
7. strategy 是否试图读取 legacy 私有列；
8. diagnostic-only rule 是否被误用为 valid strategy。

## 7. 安全边界

R3 设计和后续 validator 必须继续强制禁止：

- 训练；
- 调参；
- 重算模型分数；
- 收益筛选；
- 默认策略切换；
- 前端展示接入；
- 日更 orchestrator 接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 8. 与 R0-R2 的关系

R3 不改变 R0-R2 产物，不要求重跑 replay，不改变 R2 parity 结论。

R3 之后新增能力时必须满足：

```text
core fields pass
extension schema pass
capabilities satisfy strategy dependencies
forbidden field/action audit pass
```

只有通过 validator 的 artifact 才能进入后续研究 replay。
