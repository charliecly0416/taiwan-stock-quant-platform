# MBCDS3-5A_R 独立实际复审

生成日期：2026-09-06

## 1. Verdict

`PASS_WITH_CONDITIONS`

MBCDS3-5A_R 已具备进入 prospective shadow 自然积累的实现条件，但不代表 Model A+Model B 已优于 Model A，也不授权 baseline switch、publish、cron/default 修改。历史 `strict_pit_oos=false` compatibility 结果仍只可作为 prior。

## 2. 实际复审范围

- `scripts/run_tw_mbcds35_compatibility_frozen_scorer.py`
- `scripts/build_tw_mbcds2_isolated_feature_input.py`
- `scripts/build_tw_mbcds35_outcome_candidate.py`
- `scripts/build_tw_mbcds35_prospective_oos_ledger.py`
- `scripts/run_daily_tw_stock_auto_update.py`
- `tests/isolated/test_tw_mbcds35_*.py`
- `docs/tw_model_b_compatibility/MBCDS3_5A_R_EXECUTION_REPORT_CN.md`

## 3. 通过项

1. Frozen Model B 实际加载成功：类型为 `lightgbm.sklearn.LGBMRanker`，`predict` 可调用，`n_features_in_=34`；模型 SHA256 为 `f833146520c942a9c2953ae382235ab0d1536ccc9d153c8db1ad500ca3117cd9`。
2. scorer 固定并验证 model、contract、training medians checksum 与 34-feature 顺序；只消费 Model A top50，要求精确 `50x34` finite，不训练、不填补、不 publish。
3. feature builder 只接受显式 Model A、source ledger、accepted accumulator 和 isolated output；不扫描 arbitrary latest。source `combined_available_at <= decision_cutoff`、timezone、same-run、asof 和 artifact checksum 均 fail closed。
4. 复审中已将 prospective feature transform 对齐冻结训练 builder：percentile tie、RSI、Bollinger clipping、missing rate、suspension、VWAP 与 TWII drawdown 语义一致。
5. scorer 会复核 feature frame、Model A 和 source ledger checksum，并验证 source availability/cutoff binding，防止 feature build 后替换输入。
6. ledger 独立重算 Qlib/Model B percentile、`0.7/0.3` blend 与最终 rank；伪造 blend、rank、canonical candidate、alias policy 或 frozen artifact lineage 均被拒绝。
7. canonical candidate 为 `head10_all_l31_alpha0.7_top50_only`；`score_head10_all_l31_alpha0.7_top50_only` 仅是 non-binding alias，不能替代 canonical identity。
8. settlement 验证交易所 calendar checksum及 signal 后第一、第二交易日；缺失、NaN、零或负 open 保持 pending，不向后寻找其他日期。
9. identical settlement retry 幂等返回已有 event；不同 payload/hash 的冲突 retry fail closed；event hash chain 继续有效。
10. daily-auto 每轮先尝试结算旧 pending signal，再处理当日 feature/scoring。即使当日 feature 或 scorer 失败，旧 settlement 仍运行且返回 `model_a_non_blocking=true`。
11. 四类计数已分离：`valid_input_days`、`model_b_scored_days`、`settled_signal_days`、`paired_oos_days`；20/60/120 gate 不自动切换 baseline。
12. daily orchestrator 安全审计通过；本路线未修改 installed cron、protected latest、provider、frontend/backend default、DB、OpenAI 或 broker/order/target。

## 4. 复审中直接修复

- 增加 source availability/cutoff 和 timezone 验证。
- 增加 feature manifest 对 Model A/source ledger 的 checksum binding。
- 增加 ledger 对 frozen contract/medians、candidate alias、percentile metadata 和 blend 的独立重算。
- 修正 prospective `valid_input_days` 不应等于 registered signal 数的问题。
- 增加 outcome source run/asof lineage gate。
- 对未分类 regime 显式阻止 120 日后误报 baseline review eligible。
- 移除测试中“合法 A+B 必然优于 A”的预设，改为只验证 paired evidence 与安全门槛。

## 5. 验证结果

```text
python -m pytest tests/isolated/test_tw_mbcds35_*.py -q
30 passed

python -m py_compile <5 relevant scripts>
PASS

python scripts/build_tw_mbcds3_shadow_accumulator.py --self-test
PASS

python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
PASS (warnings only for pre-existing explicitly gated legacy provider paths)

git diff --check
PASS
```

相关 wider regression 为 `41 passed, 1 failed`。唯一失败是既有 FPALA cron 测试仍断言 legacy provider publish flag 不得启用，而当前已安装运维合同明确启用了该独立路径；本路线没有修改 cron，也不得通过关闭现行 provider 日更来迁就旧断言。

## 6. Remaining Conditions

1. 当前尚无足够真实 accepted prospective input day；达到 20 日前不得调用真实 Model B shadow scoring，达到 60/120 paired days 前不得形成初步/正式比较结论。
2. 当前 outcome regime 为 `UNCLASSIFIED`。实现已保证这种状态不能通过 120 日 baseline gate；在形成 baseline review 前，必须另行冻结 signal-time、PIT-safe regime 分类合同并积累分类覆盖。
3. 自然 cron 尚未提供首个真实 20-day scorer/record/settlement end-to-end evidence。首轮达到门槛后应做 readonly observation，验证真实 source payload 足以生成 50x34 feature frame。
4. 即使达到 120 paired days 且统计结果通过，仍必须运行 exact strategy replay 和独立 baseline switch review；不得自动切换。

## 7. 最终边界结论

允许：保持现有 flag，进入 no-publish prospective shadow 自然积累和只读观察。

禁止：把历史 compatibility evidence 计入 strict OOS、宣称 A+B 已提升收益、修改 baseline/default、写任何 latest/provider/cron，或触发交易路径。
