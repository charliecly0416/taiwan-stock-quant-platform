# Phase S1B1M 大内存服务器迁移交接文档

生成日期：2026-06-14

## 1. 当前结论

本项目代码、脚本和审查文档已推送到 GitHub：

```text
git@github.com:charliecly0416/taiwan-stock-quant-platform.git
branch: main
latest commit: d1a86ab chore: add tw stock research review artifacts
```

但训练必须用到的数据、qlib provider、frozen recorder 和已完成 partial fold 产物没有上传 GitHub，因为这些目录在 `.gitignore` 中被排除，且属于数据/模型产物。

所以远端服务器不能只 `git clone` 就直接跑。必须同时迁移下列数据目录。

## 2. 已在 GitHub 的内容

远端服务器 `git pull` 后已有：

```text
scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_REVIEW_AND_MEMORY_DIAGNOSIS_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1M_SERVER_HANDOFF_CN.md
```

脚本已支持通过环境变量覆盖远端数据路径：

```text
S1B1_PROVIDER_URI
S1B1_NORMALIZED_DIR
S1B1_FROZEN_RECORDER_DIR
S1B1_REPAIRED_DAILY
S1B1_OUTPUT_DIR
S1B1_WF_VAL_NUM_THREADS
```

## 3. 未上传 GitHub、但必须迁移的内容

必须从当前机器复制到远端服务器：

### 3.1 qlib provider

```text
/home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

本机大小约：`158M`

用途：qlib.init provider，供 Alpha158 / DatasetH 读取 bin 数据。

### 3.2 normalized price 与 universe

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe
```

本机大小约：

```text
normalized_nonempty: 604M
universe: 108K
```

用途：脚本重建 dynamic universe，读取 TW*.csv、TWII.csv、`tw_liquid_dyn.txt`。

### 3.3 frozen qlib recorder

```text
qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a
```

本机大小约：`5.3M`

用途：读取 TEST frozen pred：

```text
artifacts/pred.pkl
```

### 3.4 S1B0R repaired universe audit

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair
```

本机大小约：`200K`

关键文件：

```text
phase_s1b0r_dynamic_universe_feasibility_repaired_daily.csv
```

用途：冻结 scoring calendar 与 selected_count 审计。

### 3.5 S1B1 已完成 partial folds

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores
```

本机大小约：`191M`

用途：复用已完成 folds，远端只补 `WF-VAL`，避免重跑：

```text
folds/WF-2017.csv
folds/WF-2017.manifest.json
folds/WF-2018.csv
folds/WF-2018.manifest.json
folds/WF-2019.csv
folds/WF-2019.manifest.json
folds/WF-2020.csv
folds/WF-2020.manifest.json
folds/TEST.csv
folds/TEST.manifest.json
```

注意：当前 `phase_s1b1_qlib_wf_scores.csv` 是 partial 产物，缺 `WF-VAL`，不能作为完整通过产物。

## 4. 推荐迁移命令

假设远端服务器项目目录为：

```text
/home/<user>/taiwan-stock-quant-platform
```

先在远端拉代码：

```bash
git clone git@github.com:charliecly0416/taiwan-stock-quant-platform.git
cd taiwan-stock-quant-platform
```

再从当前机器同步数据。以下命令在当前机器执行，把 `<remote>` 和 `<user>` 替换成远端信息：

```bash
rsync -avh /home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin \
  <user>@<remote>:/home/<user>/qlib/data_tw/experiments/yahoo_adjusted_primary/

rsync -avh qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty \
  <user>@<remote>:/home/<user>/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/

rsync -avh qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe \
  <user>@<remote>:/home/<user>/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/

rsync -avh qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a \
  <user>@<remote>:/home/<user>/taiwan-stock-quant-platform/qlib_pipeline/mlruns/607910013167647574/

rsync -avh data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair \
  <user>@<remote>:/home/<user>/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/

rsync -avh data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores \
  <user>@<remote>:/home/<user>/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/
```

如果远端没有 `/home/<user>/qlib/...` 这种路径，也可以放在项目目录下，然后用环境变量覆盖 `S1B1_PROVIDER_URI`。

## 5. 远端运行命令

进入远端项目目录：

```bash
cd /home/<user>/taiwan-stock-quant-platform
```

建议先确认依赖：

```bash
python - <<'PY'
import qlib, pandas, numpy, yaml
from qlib.contrib.model.gbdt import LGBModel
print('deps ok')
PY
```

如果按推荐路径同步，运行：

```bash
/usr/bin/time -v env \
  S1B1_PROVIDER_URI=/home/<user>/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin \
  S1B1_WF_VAL_NUM_THREADS=4 \
  python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

如果 `num_threads=4` 仍 OOM，按已授权资源控制顺序尝试：

```bash
/usr/bin/time -v env \
  S1B1_PROVIDER_URI=/home/<user>/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin \
  S1B1_WF_VAL_NUM_THREADS=2 \
  python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py

/usr/bin/time -v env \
  S1B1_PROVIDER_URI=/home/<user>/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin \
  S1B1_WF_VAL_NUM_THREADS=1 \
  python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

一旦某个线程数成功生成完整 `WF-VAL`，必须停止，不得继续比较不同线程数的效果。

## 6. 如果远端路径不同

脚本支持如下路径覆盖。远端 Codex 可以按实际路径设置：

```bash
/usr/bin/time -v env \
  S1B1_PROVIDER_URI=/path/to/qlib_bin \
  S1B1_NORMALIZED_DIR=/path/to/normalized_nonempty \
  S1B1_FROZEN_RECORDER_DIR=/path/to/950741cfd5f14ee5a05464fec3e12e0a \
  S1B1_REPAIRED_DAILY=/path/to/phase_s1b0r_dynamic_universe_feasibility_repaired_daily.csv \
  S1B1_OUTPUT_DIR=/path/to/phase_s1b1_qlib_wf_scores \
  S1B1_WF_VAL_NUM_THREADS=4 \
  python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

## 7. 成功验收标准

成功后必须存在：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
```

完整产物必须更新：

```text
phase_s1b1_qlib_wf_scores.csv
phase_s1b1_fold_training_manifest.csv
phase_s1b1_score_rank_coverage_by_split.csv
phase_s1b1_score_rank_coverage_by_fold.csv
phase_s1b1_score_rank_coverage_by_date.csv
phase_s1b1_leakage_boundary_audit.json
phase_s1b1_gate_summary.json
```

`phase_s1b1_gate_summary.json` 应给出可审查通过的 gate，或至少不再缺 `WF-VAL`。

必须记录 `/usr/bin/time -v` 输出中的：

```text
Maximum resident set size
Elapsed wall clock time
Exit status
```

## 8. 远端执行报告要求

远端 Codex 完成后，必须写：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1M_MEMORY_MIGRATION_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 机器内存、swap、CPU 信息；
- 实际数据路径；
- 使用的 `S1B1_WF_VAL_NUM_THREADS`；
- `/usr/bin/time -v` 关键输出；
- 是否成功生成 `WF-VAL`；
- coverage by split / fold 摘要；
- leakage / boundary audit；
- 是否仍有 OOM；
- 下一步建议：成功则请求审查进入 S1B2；失败则停止等待用户决定是否升到更大内存或改路线。

## 9. 禁止事项

远端执行者不得：

- 训练 LTR；
- 构建 LTR 样本；
- 跑组合回放；
- 做策略比较；
- 减少数据；
- 缩短 train / validation window；
- 减少 universe；
- 改 provider / feature / label / handler / model family；
- 联网拉新数据；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / orders / quick-trade；
- 输出买卖、仓位、收益承诺、胜率或上涨概率语义。
