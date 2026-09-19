# MBCDS3-5C_R Execution Report

日期：2026-09-06

## 1. Scope

- 阶段：`MBCDS3-5C_R_REVIEW_CONDITION_REPAIR`
- 目标：关闭 MBCDS3-5A_R 当前可实施条件，重点建立 signal-time PIT-safe regime。
- 非目标：不修改 cron/latest/provider/default/publish，不训练，不声明 A+B 优于 A，不切换 baseline。

## 2. Contracts Read

- `MBCDS3_5A_R_INDEPENDENT_REVIEW_CN.md`
- `MBCDS3_5_PROSPECTIVE_SHADOW_SCORING_AND_OOS_COMPARISON_AUTOMATION_NO_PUBLISH_CN.md`
- `POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md`
- `POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md`
- RSR2 generated market-regime rule drafts and field boundaries

## 3. Changes

1. 新增冻结 JSON regime contract 及 checksum-locked loader/classifier。该合同是 outcome 未见前冻结的 RSR2-derived existing-feature-frame adaptation，不是逐字复用 RSR2 的 MA20/MA5 判定；risk-on 改用 frozen Model B 已有 MA60/ret20 字段，避免为本路线引入未冻结的新输入。
2. feature builder 使用 target-asof TWII fields 分类，生成独立 `signal_time_regime.json`，并绑定 source run、cutoff、feature frame 和 contract checksum。
3. scorer 校验 feature manifest、regime artifact、合同 checksum 及 150 行 TWII cross-section 一致性，独立重算 regime 后写入 scorer manifest。
4. ledger 独立校验 scorer 的 regime lineage，并在 `SIGNAL_REGISTERED` 封存 regime、artifact checksum 和 contract checksum。
5. outcome candidate 不再输出 regime；settlement 拒绝 outcome manifest 中任何 regime 字段，并只继承 signal event 的 regime。
6. comparison 与 regime stability 改为使用 signal-time regime。
7. 新增阈值边界、missing/non-finite、contract checksum drift、artifact drift、outcome injection、非 `UNCLASSIFIED` 和 Model A non-blocking 覆盖。

## 4. Validation

```text
python -m pytest tests/isolated/test_tw_mbcds35_*.py -q
43 passed

python -m py_compile <6 MBCDS3-5/daily scripts>
PASS

python scripts/build_tw_mbcds3_shadow_accumulator.py --self-test
PASS

python scripts/validate_tw_daily_orchestrator_m3.py \
  --audit-script scripts/run_daily_tw_stock_auto_update.py --json
PASS, two pre-existing explicitly gated legacy-path warnings

git diff --check
PASS
```

## 5. Forbidden Scope Audit

- cron modified: no
- latest/provider/Qlib pointer modified: no
- frontend/backend default modified: no
- production publish: no
- training/retraining: no
- DB/OpenAI/network: no
- broker/order/target: no

## 6. Remaining Conditions

实现条件已关闭。20/60/120 natural evidence、首个真实 E2E、exact strategy replay 与独立 baseline switch review 均为 `WAITING_EXTERNAL_EVIDENCE`，详见 `MBCDS3_5C_R_CONDITION_STATUS_AND_CLOSURE_CN.md`。在这些条件完成前，Model B 继续 shadow-only，Model A 继续作为不受阻塞的当前 baseline。

## 7. Recommendation

`PASS_READY_FOR_INDEPENDENT_REVIEW_AND_NATURAL_ACCUMULATION`
