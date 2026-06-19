# Phase S2ARR 执行报告：Instrument Contract Repair

生成日期：2026-06-14

## 1. 执行范围

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES2AR_REVIEW_AND_PHASES2ARR_INSTRUMENT_CONTRACT_REPAIR_WORK_CN.md` 执行，只修复并冻结 S2B 的 qlib loading instruments 与 score 后置 universe filter 合同。

已执行：

- 盘点 canonical provider 的 `instruments/` 目录；
- 明确 `tw_liquid_dyn` alias 在 canonical provider 内并不存在；
- 冻结 `qlib_dataset_instruments = all`；
- 冻结 `tw_liquid_dyn` 只作为 score 后置 as-of universe filter；
- 更新 S2B 待生成 yaml 的 instruments 合同。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未跑组合回放；
- 未调参；
- 未改 split；
- 未改 feature / label；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未改前端/API；
- 未触发 monitor / trading chain。

## 2. Provider Instruments 盘点

canonical provider：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

`instruments/` 目录当前只读盘点结果：

```text
all.txt
```

不存在：

```text
tw_liquid_dyn.txt
```

同时，provider 外部存在历史 universe 文件：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt
```

## 3. 为什么不继续写 `instruments: tw_liquid_dyn`

当前本地脚本证据显示，`MARKET=tw_liquid_dyn` 能被 qlib 使用，是因为脚本先在 run-specific provider 里复制：

```text
universe/tw_liquid_dyn.txt -> provider/instruments/tw_liquid_dyn.txt
```

对应证据：

- `qlib_pipeline/examples/tw/run_option_c_daily_prediction.py`

这说明对当前 canonical provider 来说：

- `tw_liquid_dyn` 不是已冻结在 provider 内的可直接解析 alias；
- 如果 S2B 继续把 handler instruments 写成 `tw_liquid_dyn`，会把解析风险推迟到训练阶段；
- 也会迫使执行者在 S2B 临场物化 alias 或改 config，破坏审查链路。

## 4. 本轮冻结决策

采用审查文档推荐的方案 A：

### 4.1 qlib 加载层

冻结为：

```text
qlib_dataset_instruments = all
```

解释：

- `all.txt` 已存在于 canonical provider；
- 这保证 S2B 的 DatasetH / Alpha158 加载层可执行；
- 不需要在 S2B 再做 provider 物化动作。

### 4.2 score 后置 universe filter

冻结为：

```text
score_universe_filter_file = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt
```

过滤规则沿用 S1 已冻结口径：

```text
as-of active membership
+ same-day price
+ >=60 historical rows
+ trailing 60-day value top150
```

这轮明确把两层分开：

- qlib 加载层：`all`
- score 后置过滤层：`tw_liquid_dyn`

后续不得再把训练层写成 `tw_liquid_dyn`。

## 5. S2B 待生成 yaml 合同

S2B 生成：

```text
qlib_pipeline/configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml
```

时必须满足：

- `qlib_init.provider_uri = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- `task.dataset.kwargs.handler.kwargs.instruments = all`
- `handler_end_time = 2026-05-07`
- `runtime thread ladder = 4 -> 2 -> 1`

score 生成完成后，再执行：

- `tw_liquid_dyn` as-of active universe filter
- 每日过滤后 selected count 统计

## 6. 不变项

本轮保持不变：

- split：`train=2017-01-10..2024-12-31`、`valid=2025-01-01..2025-06-30`、`test=2025-07-01..2026-05-07`
- provider path：继续使用 S2AR 修复后的 canonical path
- handler end：继续为 `2026-05-07`
- 线程阶梯：继续为 `4 -> 2 -> 1`
- LTR feature / label：不变

## 7. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/phase_s2arr_provider_instrument_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/phase_s2arr_qlib_loading_contract.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/phase_s2arr_score_universe_filter_contract.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/phase_s2arr_model_policy_repaired.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/phase_s2arr_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/phase_s2arr_gate_summary.json`

## 8. 禁止事项执行结果

- 未训练；
- 未回放；
- 未调参；
- 未改 split / feature / label；
- 未新增数据源；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未改前端/API；
- 未触发 monitor / trading chain；
- 未输出真实交易语义。

## 9. Gate 建议

推荐 gate：

```text
s2arr_instrument_contract_repair_pass_request_s2b_fresh_qlib_training
```

理由：

- qlib loading instruments 已冻结为当前 provider 可解析的 `all`；
- `tw_liquid_dyn` 已单独冻结为 score 后置 as-of universe filter；
- S2B 不再依赖 provider 内不存在的 `tw_liquid_dyn` alias；
- 无需 provider mutation，也不需要把 instrument 修复推迟到训练轮。
