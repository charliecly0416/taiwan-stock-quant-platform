# Phase S2AR 审查意见与 Phase S2ARR Instrument Contract Repair 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2AR_PROVIDER_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2A_REVIEW_AND_PHASES2AR_PROVIDER_CONTRACT_REPAIR_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2AR 不放行进入 S2B，必须先执行 S2ARR instrument contract repair。`

S2AR 已正确修复上一轮的三个问题：

- provider path 已从不存在的 `data_tw/experiments/yahoo_adjusted_primary/qlib_bin` 改为当前仓库存在的 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`；
- qlib runtime 线程合同已修为 `4 -> 2 -> 1`，并保留 `num_threads_original_record=8` 作为 Option C 血缘记录；
- handler end 已收敛到 frozen test end `2026-05-07`，移除了 `2026-05-08..2026-06-10` post-test tail 泄漏歧义；
- 未训练、未回放、未调参、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

但本轮发现新的可执行性阻塞点：

```text
S2AR repaired policy 仍冻结 market/instruments 为 tw_liquid_dyn，
但 canonical provider 的 instruments 目录内当前只有 all.txt，
没有 tw_liquid_dyn.txt。
```

如果直接进入 S2B，qlib DatasetH / Alpha158 可能无法解析 `tw_liquid_dyn`，导致训练失败，或迫使执行者在 S2B 临场修改 config。该问题仍属于合同修复范围，不应拖到训练轮处理。

允许进入：

```text
Phase S2ARR instrument contract repair
```

不允许进入：

```text
Phase S2B fresh qlib training
fresh LTR training
portfolio replay
parameter tuning
frontend/API
provider refresh/publish
accepted latest switching
monitor
trading chain
```

---

## 2. Findings

### High 1：provider 存在，但 `tw_liquid_dyn` instrument alias 未在 provider 内冻结

S2AR repaired policy 冻结：

```text
market = tw_liquid_dyn
handler instruments = tw_liquid_dyn
provider_uri_contract = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

本地核查：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt 存在
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/tw_liquid_dyn.txt 不存在
```

同时，历史 universe 文件存在于 provider 外：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt
```

影响：

- S2B 生成 yaml 后若写 `instruments: tw_liquid_dyn`，qlib 可能无法从当前 provider 解析该 market；
- S2AR 只检查了 `instruments/` 目录存在，没有检查目标 instrument alias 是否存在；
- 这会让 S2B 在训练阶段才暴露合同错误，或让执行者临场改为 `all`，造成口径漂移。

要求：

- S2ARR 必须冻结 qlib 加载层的真实 `instruments` 合同；
- 必须明确区分：
  - qlib DatasetH / Alpha158 加载用 instruments；
  - fresh score 生成后用于 LTR 样本和回放的 `tw_liquid_dyn` as-of active universe 过滤；
- 不得把二者混写为一个模糊的 `market=tw_liquid_dyn`。

### Medium 1：已有 S1 证据提示 qlib 训练阶段可能应使用 `instruments: all`

此前审查文档已记录：

```text
qlib 训练阶段使用 instruments: all 构造 Alpha158 数据，
dynamic top150 universe 是预测输出后的过滤口径，
不等于训练时只加载 150 只股票。
```

这说明 S2B 的可执行合同很可能应写成：

```text
qlib_train_dataset_instruments = all
score_filter_universe = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt
score_filter_policy = as-of active + daily Top150 / existing S1 policy
```

但执行者不能自行假定，S2ARR 必须用当前脚本和 qlib 可加载证据确认。

### Medium 2：若选择复制 `tw_liquid_dyn.txt` 到 provider/instruments，必须说明这不是 provider refresh/publish

历史 daily prediction 脚本存在将 universe 文件复制到 run-specific provider 的做法：

```text
shutil.copyfile(UNIVERSE_PATH, instruments_dir / "tw_liquid_dyn.txt")
```

但本主线禁止 provider refresh / publish / accepted latest switching。若 S2ARR 选择在 S2B run-specific provider 或临时 provider 中物化 `tw_liquid_dyn.txt`，必须满足：

- 只从现有 `universe/tw_liquid_dyn.txt` 复制；
- 不改 raw data；
- 不 dump 新 provider；
- 不 publish；
- 不切换 accepted latest；
- 不改 canonical provider 的价格/feature 内容；
- 明确该操作只是 instrument alias materialization，用于 qlib 解析。

如果无法清楚证明，应采用 `instruments: all + 后置 as-of universe filter` 的合同。

### Low 1：S2AR 安全边界通过

未发现以下越权：

- frontend/API 修改；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 真实买卖建议、收益承诺、胜率承诺或上涨概率承诺；
- 新数据源或联网。

---

## 3. Gate

S2AR 原建议 gate：

```text
s2ar_provider_contract_repair_pass_request_s2b_fresh_qlib_training
```

审查不接受。

本轮审查 gate：

```text
s2ar_blocked_by_instrument_contract_gap
```

下一轮只允许执行：

```text
s2arr_instrument_contract_repair
```

---

## 4. Phase S2ARR 工作目标

S2ARR 只回答一个问题：

```text
S2B fresh qlib training 的 qlib DatasetH/Alpha158 instruments 合同，与 S2 后续 score universe filter 合同，是否已经分层冻结并可执行？
```

S2ARR 是窄修复轮，不是新实验轮。

---

## 5. Phase S2ARR 执行范围

执行者必须完成：

1. 核实 qlib provider instrument 文件：
   - 列出 `option_c_150_qlib_bin/instruments/` 下所有文件；
   - 明确是否存在 `tw_liquid_dyn.txt`；
   - 明确 qlib 如果配置 `instruments: tw_liquid_dyn` 是否可加载；
   - 若做最小 smoke，只能做 qlib init / instruments resolution / DatasetH config load，不得训练。

2. 冻结 qlib 加载层 instruments 合同，二选一：
   - 推荐 A：`qlib_dataset_instruments = all`，并把 `tw_liquid_dyn` 作为 score 后置 as-of universe filter；
   - 备选 B：在不 refresh/publish provider 的前提下，物化 `tw_liquid_dyn.txt` instrument alias，并证明 qlib 可解析。

3. 冻结 score 后置 universe filter 合同：
   - universe 文件：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt`；
   - 过滤规则：按 as-of active date 过滤；
   - 保持 S1 已用的 daily selected universe / Top150 policy；
   - 输出 score/rank 覆盖时必须统计过滤后每日股票数。

4. 更新 repaired model/resource/gate policy：
   - provider path 继续使用 S2AR 修复后的 canonical path；
   - handler end 继续为 `2026-05-07`；
   - 线程阶梯继续为 `4 -> 2 -> 1`；
   - split 不变；
   - LTR feature / label 不变；
   - 不引入参数搜索。

5. 明确 S2B 的生成配置要求：
   - `qlib_pipeline/configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml` 中的 `qlib_init.provider_uri` 必须与 repaired provider contract 一致；
   - `task.dataset.kwargs.handler.kwargs.instruments` 必须与 S2ARR 冻结的 qlib loading instruments 一致；
   - 若使用 `all + 后置 filter`，不得在报告中把训练层写成 `tw_liquid_dyn`。

---

## 6. Phase S2ARR 禁止事项

本轮禁止：

- 训练 qlib；
- 训练 LTR；
- 跑 portfolio replay；
- 调参或参数搜索；
- 改 split；
- 改 feature / label；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改前端/API；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、收益承诺、胜率承诺、上涨概率承诺。

允许的最小技术动作：

- 只读检查 provider instruments；
- 只读检查 qlib config 可加载性；
- 若选择备选 B，可在 S2ARR 专用 artifact 或 run-specific 临时目录内从现有 `universe/tw_liquid_dyn.txt` 物化 instrument alias，但不得 publish 或切换 accepted latest。

---

## 7. Phase S2ARR 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2arr_instrument_contract_repair/
```

必须产物：

```text
phase_s2arr_provider_instrument_audit.json
phase_s2arr_qlib_loading_contract.json
phase_s2arr_score_universe_filter_contract.json
phase_s2arr_model_policy_repaired.json
phase_s2arr_forbidden_action_audit.json
phase_s2arr_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2ARR_INSTRUMENT_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md
```

---

## 8. Phase S2ARR 通过条件

只有全部满足时，才允许下一轮进入 S2B：

```text
provider_uri_exists = true
provider_uri_has_calendars_features_instruments = true
qlib_loading_instruments_resolvable = true
qlib_loading_instruments_contract_frozen = true
score_universe_filter_contract_frozen = true
score_universe_filter_uses_existing_tw_liquid_dyn = true
provider_refresh_publish = false
accepted_latest_switching = false
split_contract_unchanged = true
handler_end = 2026-05-07
thread_ladder = [4, 2, 1]
no_training_in_s2arr = true
no_replay_in_s2arr = true
no_parameter_tuning = true
```

通过 gate：

```text
s2arr_instrument_contract_repair_pass_request_s2b_fresh_qlib_training
```

失败 gate：

```text
s2ar_blocked_by_instrument_contract_gap
s2ar_blocked_by_provider_mutation_risk
s2ar_blocked_by_scope_violation
s2ar_blocked_by_user_tradeoff_required
```

---

## 9. 给执行者的一句话

请执行 Phase S2ARR：只修复并冻结 S2B 的 qlib loading instruments 与 score 后置 universe filter 合同，确认 `tw_liquid_dyn` 是否能被当前 provider 解析；优先采用 `instruments: all + 现有 tw_liquid_dyn as-of 后置过滤` 或证明 instrument alias 物化不属于 provider refresh/publish；不得训练、回放、调参、改 split/feature/label，完成后提交 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES2ARR_INSTRUMENT_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md`。
