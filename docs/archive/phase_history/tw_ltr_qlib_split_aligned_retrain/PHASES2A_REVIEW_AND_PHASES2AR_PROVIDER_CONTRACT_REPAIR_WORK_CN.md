# Phase S2A 审查意见与 Phase S2AR Provider Contract Repair 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2A_FRESH_RETRAIN_CONTRACT_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6R_REVIEW_AND_PHASES2A_FRESH_RETRAIN_CONTRACT_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2A 不放行进入 S2B，必须先执行 S2AR provider/config contract repair。`

S2A 的主方向基本正确：

- fresh split 已按主线冻结为 `train=2017-01-10..2024-12-31`、`validation=2025-01-01..2025-06-30`、`test=2025-07-01..2026-05-07`；
- qlib 与 LTR 都纳入 fresh retrain 验证，没有只重训 LTR；
- `fresh_ltr_simple` 与 `fresh_ltr_turnover_controlled` 保持同级候选，没有提前分高低；
- 删除退化的 `rank_rotate_top30` primary candidate 合理；
- 沿用 S1B6R 的 next-day execution accounting 合同；
- 未训练、未回放、未调参、未联网、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

但 S2A 冻结的 qlib provider/config 合同存在硬问题。如果直接进入 S2B，执行者只能失败或静默修改合同，这会破坏审查链路。因此本轮不能通过到 S2B。

允许进入：

```text
Phase S2AR provider/config contract repair
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

### High 1：qlib provider_uri_contract 指向当前仓库不存在的路径

S2A 报告和 `phase_s2a_model_policy.json` 冻结：

```text
provider_uri_contract = data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

本地核查结果：

```text
data_tw/experiments/yahoo_adjusted_primary/qlib_bin 不存在
```

当前可见的 qlib provider-like 目录是：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

该目录包含：

```text
calendars/
features/
instruments/
```

影响：

- S2B fresh qlib training 会在 qlib init / DatasetH 加载阶段失败；
- 或者执行者在 S2B 静默改 provider path，导致合同先后不一致；
- 这属于进入训练前必须修复的合同问题，不是训练阶段可临场处理的问题。

要求：

- S2AR 必须冻结真实存在、只读可用的 canonical qlib provider path；
- 不得通过 provider refresh / publish / accepted latest switching 来制造新 provider；
- 如果最终选择的 canonical path 不是 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`，必须说明证据。

### Medium 1：qlib model num_threads=8 与资源阶梯 4 -> 2 -> 1 冲突

`phase_s2a_model_policy.json` 中 qlib model params 沿用：

```text
num_threads = 8
```

但 `phase_s2a_resource_policy.json` 冻结：

```text
qlib_training_thread_ladder = [4, 2, 1]
```

影响：

- 如果 S2B 配置直接写 `num_threads=8`，会违反本轮为避免 OOM 冻结的低线程策略；
- 如果执行者运行时再改成 4，又会形成“模型参数合同”和“资源合同”不一致。

要求：

- S2AR 必须明确 qlib fresh training 的初始线程数为 `4`，OOM 后依次 `2 -> 1`；
- 或者明确区分“Option C 原始参数记录值”和“S2 runtime resource override”，并在待生成 yaml 中以 S2 override 为准；
- 不得为了省内存缩小 universe、缩短 split、删 feature 或改 model family。

### Medium 2：handler end_time 超过 frozen test end，需要确认不会产生处理器或标签泄漏

`phase_s2a_model_policy.json` 中 qlib handler dates：

```text
end_time = 2026-06-10
test = 2025-07-01..2026-05-07
fit_end_time = 2024-12-31
```

这不必然错误，但在进入训练前必须解释清楚：

- Alpha158 / DatasetH 处理器是否只在 `fit_start_time..fit_end_time` 拟合；
- `2026-05-08..2026-06-10` 是否会影响 test 特征、标准化、缺失处理、标签或过滤；
- qlib label 是否会用到 test end 之后的数据；
- 如果后续 raw tail 只是为了 signal/coverage 证据，为什么不把 handler end 收敛到 `2026-05-07`。

要求：

- S2AR 必须给出 processor leakage audit；
- 若不能证明 `2026-05-08..2026-06-10` 不影响 test，必须把 S2 fresh qlib handler end 收敛到 `2026-05-07`；
- 不得利用 test 后数据做参数选择、阈值选择或候选策略筛选。

### Low 1：S2A 安全边界通过

本轮未发现以下越权：

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

S2A 原建议 gate：

```text
s2a_fresh_retrain_contract_pass_request_s2b_fresh_qlib_training
```

审查不接受。

本轮审查 gate：

```text
s2a_blocked_by_provider_contract_gap
```

下一轮只允许执行：

```text
s2ar_provider_config_contract_repair
```

---

## 4. Phase S2AR 工作目标

S2AR 只回答一个问题：

```text
S2B fresh qlib training 的 provider path、qlib config、线程策略、handler/processor 窗口是否已经冻结到可执行且不泄漏的合同？
```

S2AR 是窄修复轮，不是新实验轮。

---

## 5. Phase S2AR 执行范围

执行者必须完成：

1. 核实 canonical qlib provider path：
   - 路径必须真实存在；
   - 必须包含 `calendars/`、`features/`、`instruments/`；
   - 必须是当前本地已有只读数据；
   - 不得触发 provider refresh / publish；
   - 不得切换 accepted latest。

2. 修复 qlib model policy：
   - 更新 `provider_uri_contract`；
   - 冻结 S2B 待生成 yaml 的 qlib init provider path；
   - 明确 market / universe / benchmark 不变；
   - 明确 split 不变。

3. 修复线程合同：
   - qlib fresh training 默认从 `num_threads=4` 开始；
   - 若 OOM 或 exit code 137，再降为 `2`；
   - 若仍失败，再降为 `1`；
   - 不得直接改 universe、split、feature、label、model family 或参数搜索。

4. 审计 handler / processor / label leakage：
   - 列出 handler start/end、fit start/end、train/valid/test；
   - 列出 qlib processor 是否有 learnable fit；
   - 证明 fit 只用 train window；
   - 证明 test end 之后数据不会影响 test feature/label/selection；
   - 若证据不足，把 handler end 修复为 `2026-05-07`。

5. 更新 gate summary：
   - 只有 provider path 存在、线程合同一致、leakage audit 通过，才允许请求进入 S2B。

---

## 6. Phase S2AR 禁止事项

本轮禁止：

- 训练 qlib；
- 训练 LTR；
- 跑 portfolio replay；
- 调参或参数搜索；
- 改 split；
- 改 universe；
- 新增、删除或重定义 feature / label；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改前端/API；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、收益承诺、胜率承诺、上涨概率承诺。

---

## 7. Phase S2AR 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2ar_provider_contract_repair/
```

必须产物：

```text
phase_s2ar_provider_uri_audit.json
phase_s2ar_model_policy_repaired.json
phase_s2ar_resource_policy_repaired.json
phase_s2ar_processor_leakage_audit.json
phase_s2ar_forbidden_action_audit.json
phase_s2ar_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2AR_PROVIDER_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md
```

---

## 8. Phase S2AR 通过条件

只有全部满足时，才允许下一轮进入 S2B：

```text
provider_uri_exists = true
provider_uri_has_calendars_features_instruments = true
provider_uri_contract_matches_generated_config = true
no_provider_refresh_publish = true
no_accepted_latest_switching = true
qlib_training_thread_ladder_effective = [4, 2, 1]
split_contract_unchanged = true
universe_contract_unchanged = true
feature_label_contract_unchanged = true
processor_fit_window_train_only = true
test_tail_leakage_absent_or_handler_end_repaired = true
no_training_in_s2ar = true
no_replay_in_s2ar = true
```

通过 gate：

```text
s2ar_provider_contract_repair_pass_request_s2b_fresh_qlib_training
```

失败 gate：

```text
s2a_blocked_by_provider_contract_gap
s2a_blocked_by_split_purity_risk
s2a_blocked_by_scope_violation
s2a_blocked_by_user_tradeoff_required
```

---

## 9. 给执行者的一句话

请执行 Phase S2AR：只修复并冻结 S2B fresh qlib training 的真实 provider path、待生成 qlib config、线程阶梯和 handler/processor 泄漏审计，不得训练、不得回放、不得调参、不得改 split/universe/feature/label、不得触发 provider/accepted latest/monitor/前端/API/交易链路；完成后提交 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES2AR_PROVIDER_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md`。
