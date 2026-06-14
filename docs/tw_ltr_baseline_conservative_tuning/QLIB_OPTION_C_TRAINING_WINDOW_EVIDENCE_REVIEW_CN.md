# Qlib Option C 训练窗口证据审查

## 结论

用户质疑成立：审查者不能先假设 qlib 是“2020 年前训练”。本轮已重新查证本地仓库证据。

基于当前仓库可验证证据，`Option C / qlib baseline` 使用的 frozen recorder 为：

- `950741cfd5f14ee5a05464fec3e12e0a`
- recorder 路径：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a`
- model 路径：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl`
- 配置路径：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`

该 frozen qlib baseline 的 split 为：

| split | 日期区间 | 可否作为样本外解释 |
| --- | --- | --- |
| train | 2015-05-04 至 2020-12-31 | 不可 |
| valid | 2021-01-01 至 2022-12-31 | 不可当最终样本外，只能作验证期 |
| test / research backtest | 2023-01-01 至 2025-06-30 | 可作为相对样本外测试/研究回放依据 |

因此，更准确的说法不是“qlib 用 2020 年前数据训练”，而是：当前 Option C frozen qlib baseline 的训练集截止到 `2020-12-31`，验证集为 `2021-01-01..2022-12-31`，测试/研究回放从 `2023-01-01` 开始。

## 证据

### 1. daily signal 指向 frozen recorder

文件：`qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260610_20260610T183814Z/run_metadata.json`

关键字段：

- `frozen_recorder`: `950741cfd5f14ee5a05464fec3e12e0a`
- `recorder_path`: `mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a`
- `model_path`: `mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl`
- `config`: `configs/tw_yahoo_primary_alpha158.yaml`
- `model_retraining_performed`: false
- `model_tuning_performed`: false

这说明当前日频 Option C 信号使用的是 frozen model，不是在 daily signal 阶段重训或调参。

### 2. qlib baseline 配置明确 split

文件：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`

关键配置：

- `fit_start_time`: `2015-05-04`
- `fit_end_time`: `2020-12-31`
- `segments.train`: `[2015-05-04, 2020-12-31]`
- `segments.valid`: `[2021-01-01, 2022-12-31]`
- `segments.test`: `[2023-01-01, 2025-06-30]`
- backtest: `2023-01-01` 至 `2025-06-30`

### 3. recorder artifact 保存了同一 split

文件：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/task`

该 artifact 为 pickle 内容，直接读取得到的文本片段显示同一结构：

- handler `start_time`: `2015-05-04`
- handler `end_time`: `2025-06-30`
- handler `fit_start_time`: `2015-05-04`
- handler `fit_end_time`: `2020-12-31`
- `segments.train`: `2015-05-04..2020-12-31`
- `segments.valid`: `2021-01-01..2022-12-31`
- `segments.test`: `2023-01-01..2025-06-30`

### 4. 当前预测脚本沿用 frozen recorder 和同一 fit 边界

文件：`qlib_pipeline/examples/tw/run_option_c_daily_prediction.py`

关键常量：

- `RECORDER_DIR = ROOT / "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a"`
- `MODEL_PATH = RECORDER_DIR / "artifacts/params.pkl"`
- `CONFIG_PATH = ROOT / "configs/tw_yahoo_primary_alpha158.yaml"`
- `RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"`

预测 handler 使用：

- `fit_start_time`: `2015-05-04`
- `fit_end_time`: `2020-12-31`

文件：`qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py` 也在 provider 版本预测中使用同一 `MODEL_PATH` 与同一 `fit_end_time = 2020-12-31`。

## 对 LTR 的影响

当前 LTR split 是：

- train: `2022-01-10..2024-08-09`
- validation: `2024-08-12..2025-06-24`
- independent_test: `2025-06-25..2026-05-07`

这与 Option C frozen qlib baseline 的 split 不同。直接把 LTR 在 `2025-06-25..2026-05-07` 的 independent_test 收益，与 qlib/Top50 在更长或不同 split 的历史表现混在一起解释，会产生不公平比较风险。

更严谨的处理方式：

1. 当前已收尾的 B2A 结论仍可保留，但必须标注 LTR 的独立测试仅覆盖 `2025-06-25..2026-05-07`，不是完整 2023 后 out-of-sample。
2. 如果下一轮要做“和 qlib 同等级、同口径”的策略判断，应新开一个 split 对齐实验：使用 `2015-05-04..2020-12-31` 训练 LTR，`2021-01-01..2022-12-31` 验证，`2023-01-01..2025-06-30` 测试；但这属于重新训练/新实验，不能塞回已收尾的 readonly 产品化结论。
3. 在没有执行 split 对齐重训前，不能宣称 LTR 相对 qlib baseline 在同一训练假设下更优；只能说当前 LTR 在自己的 frozen split independent_test 上表现较好。

## 审查结论

- 已查明当前 Option C frozen qlib baseline 的训练窗口：`2015-05-04..2020-12-31`。
- 已查明验证窗口：`2021-01-01..2022-12-31`。
- 已查明测试/研究回放窗口：`2023-01-01..2025-06-30`。
- 前序“qlib 是不是用 2020 年前数据训练”的回答需要修正为：训练集截止 `2020-12-31`，不是未经证据支持的泛称。
- 若用户希望公平评估 2020/2023 之后表现，应开启独立的 LTR split-aligned retraining/evaluation 主线，而不是继续沿用现有 2022 后训练的 LTR 结果做最终优劣判断。
