# Phase S2AR 执行报告：Provider Contract Repair

生成日期：2026-06-14

## 1. 执行范围

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES2A_REVIEW_AND_PHASES2AR_PROVIDER_CONTRACT_REPAIR_WORK_CN.md` 执行，只修复并冻结 S2B fresh qlib training 的 provider/config/thread/leakage 合同。

已执行：

- 核实 canonical qlib provider path；
- 修复 qlib model policy 中的 provider path、runtime thread 合同、handler end；
- 生成 processor / label leakage 审计；
- 更新 gate。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未跑组合回放；
- 未调参；
- 未改 split；
- 未改 universe；
- 未改 LTR feature / label；
- 未新增数据源；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未改前端/API；
- 未触发 monitor / trading chain。

## 2. Provider Contract 修复

S2A 的错误点是把 qlib provider 冻结成了仓库里不存在的：

```text
data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

本轮只读核查后，选择的 canonical provider path 为：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

核查结果：

- `provider_uri_exists = true`
- `provider_uri_has_calendars_features_instruments = true`

目录证据：

- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/features/`
- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt`

修复原则：

- 不通过 refresh / publish 制造新 provider；
- 不切换 accepted latest；
- 只使用当前仓库内已存在的只读 provider。

## 3. 线程合同修复

S2A 的另一处不一致是：

- model policy 仍写 `num_threads = 8`
- resource policy 写低线程阶梯 `4 -> 2 -> 1`

本轮修复后的合同：

- Option C 原始记录值仍保留为 `num_threads_original_record = 8`
- 但 S2B 待生成 yaml 的 runtime 初始线程数必须是 `4`
- 若 OOM 或 exit code `137`，再降为 `2 -> 1`

这样做的效果是：

- 保留与 frozen Option C 的参数血缘关系；
- 同时让 S2B 运行合同与低线程资源策略一致；
- 不需要在训练阶段静默改合同。

## 4. Handler / Processor Leakage 修复

S2A 把 qlib handler `end_time` 冻结到 `2026-06-10`，但 frozen fresh test 只到 `2026-05-07`。这会留下 post-test raw tail 是否影响处理器/标签的解释负担。

本轮修复为：

| 项目 | 修复后 |
| --- | --- |
| handler start_time | `2015-05-04` |
| handler end_time | `2026-05-07` |
| fit_start_time | `2015-05-04` |
| fit_end_time | `2024-12-31` |
| train | `2017-01-10..2024-12-31` |
| valid | `2025-01-01..2025-06-30` |
| test | `2025-07-01..2026-05-07` |

修复后的解释：

- `fit_end_time` 仍然只到训练窗口结束，processor fit 只允许用训练窗；
- handler `end_time` 直接收敛到 frozen test end；
- `2026-05-08..2026-06-10` 不再落入 qlib handler 范围；
- 因此 post-test raw tail 不会进入 test 特征、标签或选择过程。

这轮选择“收敛 handler end”而不是继续证明 `2026-06-10` 也安全，是更保守、更可执行的合同。

## 5. 不变项

本轮明确保持不变：

- split：`train=2017-01-10..2024-12-31`、`valid=2025-01-01..2025-06-30`、`test=2025-07-01..2026-05-07`
- market：`tw_liquid_dyn`
- benchmark：`TWII`
- universe 合同不变
- LTR feature / label 合同不变
- LTR fresh retrain 候选策略不变

## 6. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/phase_s2ar_provider_uri_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/phase_s2ar_model_policy_repaired.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/phase_s2ar_resource_policy_repaired.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/phase_s2ar_processor_leakage_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/phase_s2ar_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/phase_s2ar_gate_summary.json`

## 7. 禁止事项执行结果

- 未训练；
- 未回放；
- 未调参；
- 未改 split / universe / feature / label；
- 未新增数据源；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未改前端/API；
- 未触发 monitor / trading chain；
- 未输出真实交易语义。

## 8. Gate 建议

推荐 gate：

```text
s2ar_provider_contract_repair_pass_request_s2b_fresh_qlib_training
```

理由：

- canonical provider path 已冻结为仓库内真实存在的只读 provider；
- generated config 合同与 provider path 已一致；
- qlib runtime 线程阶梯已与资源合同一致；
- handler end 已收敛到 frozen test end，post-test leakage 歧义已移除。
