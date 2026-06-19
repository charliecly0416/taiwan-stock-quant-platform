# Phase E7 决策报告：默认候选收口

生成时间：`2026-06-16T05:12:00+00:00`

## 1. Gate

- gate：`phase_e7_default_candidate_decision_recorded`。
- 本阶段只做 E4 / E5B / E6 证据汇总与默认候选决策审查。
- 未训练 qlib，未训练 LTR，未回放，未调参，未改默认策略，未改前端/API/provider/accepted latest/monitor/交易链路，未触发 broker / quick-trade / orders。

## 2. 引用证据

- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5_E4_FAIRNESS_AUDIT_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5B_E4_VS_FRESH_EXACT_2026_BRIDGE_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE6_BRIDGE_LTR_2025_TWO_QLIB_BASES_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_bridge_manifest.json`

## 3. 核心指标表

| evidence | method | window | net_return | max_drawdown | actions | fee_tax | turnover_proxy | note |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| E4 | frozen qlib top50 baseline | 2026-01-01..2026-05-07 | 0.146704 | -0.051150 | 154 | 46595.67 | 15.111736 | E4 control |
| E4 | frozen qlib + orthogonal LTR 2023-2025 | 2026-01-01..2026-05-07 | 0.602499 | -0.071473 | 151 | 53524.77 | 14.904165 | E4 treatment |
| E5B | repaired fresh qlib top50 adaptive | 2026-01-01..2026-05-07 | 0.289419 | -0.037564 | 154 | 50394.08 | 15.248647 | exact bridge fresh baseline |
| E6 Branch A | repaired fresh qlib top50 adaptive | 2026-01-01..2026-05-07 | 0.289419 | -0.037564 | 154 | 50394.08 | 15.248647 | fresh control |
| E6 Branch A | fresh qlib + orthogonal LTR 2025-only | 2026-01-01..2026-05-07 | 0.464734 | -0.058226 | 151 | 53987.82 | 15.295390 | fresh treatment |
| E6 Branch B | frozen qlib top50 baseline | 2026-01-01..2026-05-07 | 0.146704 | -0.051150 | 154 | 46595.67 | 15.111736 | frozen control |
| E6 Branch B | frozen qlib + orthogonal LTR 2025-only | 2026-01-01..2026-05-07 | 0.318632 | -0.083641 | 153 | 51280.57 | 15.223378 | frozen treatment |

## 4. 必答问题

### 4.1 E4 是否合规且公平

是。E5 审计结论为 `phase_e5_e4_fairness_audit_passed`，E4 内部 control/treatment 通过以下审计：

- future function / future label：通过；E4 replay-ready 表不含 future return、label 或 realized PnL 决策字段。
- coverage：通过；control/treatment 均为 79 个交易日、3950 行、daily top50 为 50/50/50、duplicate keys 为 0。
- next-day accounting：通过；两侧 missing_price_days、skipped_trade_count、last_day_new_trade_without_next_price_count 均为 0。
- rule boundary：通过；同一 replay engine、fee/tax、candidate_k=50、target_position_count=10，treatment 只在 qlib top50 内 rerank。

限制：E4 内部 control 是 2018-2022 frozen qlib raw-score top50 baseline，不是 repaired fresh qlib adaptive baseline。因此 E4 本身不能单独证明对 repaired fresh qlib 的默认替换。

### 4.2 E4 是否在 2026 exact bridge 中高于 repaired fresh qlib

是。E5B exact 2026 bridge 显示：

- E4 frozen qlib + orthogonal LTR 2023-2025：`0.602499`。
- repaired fresh qlib top50 adaptive：`0.289419`。
- E4 treatment 相对 repaired fresh：`+0.313080`。

同时 E4 treatment 的 drawdown 更深：`-0.071473` vs repaired fresh `-0.037564`，因此收益优势伴随更高回撤。

### 4.3 E6 是否证明 2025-only orthogonal LTR 在两个底座上都有增益

是。

- Branch A fresh qlib：`0.464734 - 0.289419 = +0.175315`。
- Branch B frozen qlib：`0.318632 - 0.146704 = +0.171928`。

两条分支使用同一 2025 LTR 训练窗、同一 78 特征 whitelist、同一 label、同一 LGBMRanker 参数、同一 replay contract。训练样本不是 top50-only：Branch A train daily rows `148/149/150`，Branch B train daily rows `148/149/149`。

### 4.4 E6 是否支持更长 LTR 训练窗口带来额外提升

支持，但仍是单窗口证据。

- E6 Branch B frozen qlib + 2025-only LTR：`0.318632`。
- E4 frozen qlib + 2023-2025 LTR：`0.602499`。
- 差异：`+0.283867`。

在 frozen qlib 底座、相同 2026 test window 与同类 replay 口径下，2023-2025 LTR 明显高于 2025-only LTR，支持“LTR 训练数据长度不足会压低增益”的解释。

### 4.5 E4 的高收益是否仍有未解释风险

有。E4 仍只有一个 2026-01-01..2026-05-07 exact window，且该窗口较短。高收益虽通过 E5 合规、公平、集中度审计，但仍可能受窗口行情、行业轮动、少数强势交易日或 2026 early-period regime 影响。

E5 集中度审计降低了异常单点解释风险：E4 treatment 最大单股 turnover share 为 `0.073495`，single symbol >50% 为 `False`；top1 positive PnL share 为 `0.071638`，top5 positive PnL share 为 `0.261263`。这说明结果不是单一股票完全驱动，但还不能替代更长 OOS 或 rolling robustness。

### 4.6 回撤、换手、费用、PnL 集中是否可接受

可进入默认候选讨论，但不足以直接默认。

- 回撤：E4 treatment `-0.071473`，深于 frozen baseline `-0.051150` 与 repaired fresh `-0.037564`。
- 换手：E4 treatment turnover proxy `14.904165`，略低于 frozen baseline `15.111736` 与 repaired fresh `15.248647`。
- 费用：E4 treatment fee/tax `53524.77`，高于 frozen baseline `46595.67` 与 repaired fresh `50394.08`，但动作数更少。
- 集中度：E5 未发现单一股票或单日完全解释收益的集中风险。

综合看，E4 的收益优势足够进入默认候选讨论；回撤更深和短窗口风险要求继续只读验证。

### 4.7 是否建议把 E4 作为默认候选，而不是直接默认

建议：`recommend_default_candidate_discussion`。

E4 不应直接切换为默认策略。当前证据支持将 `2018-2022 frozen qlib + orthogonal LTR trained on 2023-2025` 放入新的默认候选讨论池，并作为高优先级只读候选继续审查。

### 4.8 是否需要开启日更/产品化支线

建议：

- `recommend_readonly_productization_design`
- `recommend_daily_readonly_candidate_refresh`

范围必须限定为只读候选生产链路：每日生成 candidate score / rank / audit artifact，展示为研究候选，不发布 accepted latest，不触发 provider refresh，不触发 monitor / broker / orders，不替换现有默认策略。

### 4.9 是否需要更长 OOS 或 rolling robustness 进一步验证

需要：`recommend_additional_robustness_validation`。

建议至少补充：

- 更长 2026 OOS 或后续追加窗口复核；
- rolling / subwindow robustness；
- regime / market drawdown 分段；
- common universe 与 repaired fresh baseline 的分段公平比较；
- PnL concentration、行业/个股暴露与换手费用敏感性复核。

## 5. 正交 LTR 增益判断

正交 LTR 增益成立，但应以“候选证据”表述，不应表述为未来收益承诺。

E6 证明 2025-only LTR 在 fresh qlib 与 frozen qlib 两个底座上均有正增益；E4 证明扩展训练窗口后 frozen qlib + orthogonal LTR 在同一 2026 exact bridge 中显著高于 repaired fresh qlib。该证据链说明 orthogonal LTR 的增益不是单纯依赖某一个 qlib 底座，也不是 E4 内部 control 选择造成的孤立现象。

## 6. 与 Fresh Qlib 的公平比较结论

E5B 已补齐 E5 指出的 exact-window caveat。对 `2026-01-01..2026-05-07`：

- 同一 replay engine；
- next-day execution；
- fee_rate `0.001425`；
- tax_rate `0.003`；
- target_position_count `10`；
- candidate_k `50`；
- repaired fresh 使用 C4 replay-ready artifact。

在此口径下，E4 treatment 高于 repaired fresh qlib top50 adaptive，但回撤更深。结论是“可进入默认候选讨论”，不是“直接替换 fresh qlib 默认”。

## 7. 风险与 Caveat

- 2026 exact bridge window 仍短，不能排除窗口偶然性。
- E4 treatment 的 max drawdown 深于 repaired fresh qlib。
- E6 Branch A 使用 fresh qlib frozen raw score；若 2025H1 曾作为 fresh qlib validation，则 Branch A 不是严格 qlib-never-seen 2025 LTR train。
- E6 支持训练长度影响，但不是完整 rolling OOS 证明。
- 当前报告不承诺未来收益、胜率或上涨概率。
- 当前报告不构成默认策略切换授权。

## 8. 决策

允许结论：

- `recommend_default_candidate_discussion`
- `recommend_readonly_productization_design`
- `recommend_daily_readonly_candidate_refresh`
- `recommend_additional_robustness_validation`

禁止并未执行：

- 不直接切换默认策略；
- 不直接替换前端展示；
- 不触发 provider / accepted latest；
- 不触发 monitor / broker / orders；
- 不承诺未来收益、胜率或上涨概率。

## 9. 下一步建议

1. 开启只读产品化设计支线：定义 E4 candidate 的 daily artifact、审计字段、展示边界与禁用动作。
2. 开启 daily readonly candidate refresh 支线：只生成候选分数与审计报告，不发布、不交易。
3. 开启 robustness 支线：扩展 OOS、rolling subwindow、regime 分段、费用敏感性和集中度复核。
4. 默认策略讨论中将 E4 标记为“候选”，保留 repaired fresh qlib 作为现有研究基线，直到更长 OOS / rolling evidence 通过。
