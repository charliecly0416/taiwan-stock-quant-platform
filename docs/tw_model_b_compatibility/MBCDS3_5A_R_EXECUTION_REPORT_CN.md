# MBCDS3-5A_R Execution Report

生成日期：2026-09-06

## 1. 结论

`IMPLEMENTATION_PASS_WITH_NATURAL_ACCUMULATION_CONDITIONS`

MBCDS3-5 prospective shadow scoring、outcome settlement 与 OOS comparison 已接入现有 MBCDS3 daily gate。该路径保持 no-publish、shadow-only，并且任何 Model B 失败都不会改变或阻塞 Model A baseline。

本报告不代表 Model A+Model B 已证明优于 Model A，也不授权 baseline switch。当前有效 prospective input day 仍不足 20，真实 daily scoring 必须等待后续合格 same-run evidence 自然累计。

## 2. 实施内容

### Frozen scorer

- 新增 `scripts/run_tw_mbcds35_compatibility_frozen_scorer.py`。
- 固定 `head10_all_l31`、34 特征顺序及 model/contract/training medians SHA256。
- 实际加载 frozen `LGBMRanker` pickle，不训练。
- 仅评分同日 Model A top50。
- percentile 方向固定为 higher-is-better，tie 规则固定且可复现。
- feature missing/NaN/Inf、顺序、checksum、same-run 或 universe 不一致均 fail closed。

### Prospective feature builder

- 参数改为显式 `asof`、same-run Model A、source ledger、accepted accumulator 和 output。
- 不读取 arbitrary latest，不扫描历史 prediction 目录。
- rank change/streak 仅来自 accumulator 中 `VALID_DAY_ACCEPTED` 的 prospective ranking。
- price/TWII 仅来自 source ledger checksum 绑定的 artifact。
- 按 TWII 交易日补出缺行表示；缺值不会用 median、forward-fill 或 zero-fill 修复。
- 仍输出 150 行供诊断，但 readiness 严格按 scorer 实际消费的 Model A top50 做 `50x34` finite gate；top50 外缺值不会永久阻塞 scorer。

### Ledger / comparison

- identical outcome retry 返回既有 event，不追加、不重写 materialized ledger。
- conflicting retry fail closed。
- entry/exit 必须是显式交易所 calendar 中 signal 后第一、第二个交易日。
- 停牌、缺失或非正 open 保持 pending，不向后跳到下一可用价格。
- 新增 daily Rank IC、mean Rank IC、monthly stability 与 regime stability。
- 计数明确为 valid input、Model B scored、settled signal、paired OOS。
- `exact_strategy_replay_still_required_before_switch=true`。

### Daily-auto wiring

- 复用既有 `ENABLE_TW_MBCDS3_DAILY_SHADOW`，未修改 cron。
- `<20 valid_input_days` 不调用 builder/scorer。
- `>=20` 后依次执行 feature builder、frozen scorer、record-signal。
- 每轮先独立尝试从当前 same-run source ledger 结算旧 pending signals；该阶段不依赖当日 feature/scorer/record 成功。
- 任一步失败只形成 isolated/job status，`model_a_non_blocking=true`。

### Candidate identity

- immutable contract 的 canonical candidate ID 保持 `head10_all_l31_alpha0.7_top50_only`。
- 主线曾使用的 `score_head10_all_l31_alpha0.7_top50_only` 仅作为 manifest `candidate_aliases` 中的 non-binding alias。
- 未修改 frozen model、contract 或 training medians 文件，因此三者 checksum 保持不变。

## 3. 文件

- `scripts/build_tw_mbcds2_isolated_feature_input.py`
- `scripts/run_tw_mbcds35_compatibility_frozen_scorer.py`
- `scripts/build_tw_mbcds35_outcome_candidate.py`
- `scripts/build_tw_mbcds35_prospective_oos_ledger.py`
- `scripts/run_daily_tw_stock_auto_update.py`
- `tests/isolated/test_tw_mbcds35_prospective_feature_builder.py`
- `tests/isolated/test_tw_mbcds35_compatibility_frozen_scorer.py`
- `tests/isolated/test_tw_mbcds35_prospective_oos_ledger.py`
- `tests/isolated/test_tw_mbcds35_daily_wiring.py`

## 4. 验证证据

- focused MBCDS3-5 tests：`23 passed`。
- frozen production artifact load：`lightgbm.sklearn.LGBMRanker`, `predict=True`。
- MBCDS3 accumulator self-test：PASS。
- py_compile：PASS。
- git diff --check：PASS。
- wider related regression：`78 passed, 1 failed`。唯一失败为既有 FPALA 测试仍要求 installed cron 不得启用 legacy provider publish，但当前运维 cron 已明确启用该路径；本路线未修改 cron，也未通过关闭正式 provider 日更来迁就旧断言。

## 5. 未关闭条件

- 当前 accumulator 的真实 valid prospective input 尚未达到 20，不能声称 Model B daily shadow 已开始产生真实分数。
- 60 paired OOS days 前仅可积累，不可形成比较结论。
- 120 paired OOS days、稳定性审查和 exact strategy replay 全部完成后，才可另开 baseline switch review；永不自动切换。
- 历史 `strict_pit_oos=false` 结果继续仅作 prior，不计入 prospective 门槛。

## 6. 边界审计

本轮未修改 provider、accepted/legacy/product latest、cron、frontend/backend、DB、OpenAI、broker/order/target，未训练模型，未执行 baseline switch。
