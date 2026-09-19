# MBCDS3-5C_R 独立审查

日期：2026-09-06

## 1. Verdict

`PASS_WITH_CONDITIONS / READY_FOR_NATURAL_PROSPECTIVE_ACCUMULATION`

未发现仍需阻止 isolated、no-publish 自然积累的实现缺陷。可实施审查条件已关闭；剩余条件仅为真实 20/60/120 日证据、首个 live E2E、exact strategy replay 和后续人工 baseline switch review。当前不得声称 Model A+Model B 优于 Model A，也不得切换 baseline。

## 2. Findings

### P0/P1

无未关闭 P0/P1 finding。

### 已澄清的合同差异

本合同不是逐字复用 RSR2 的 MA20/MA5 regime，而是 outcome 未见前冻结的 `RSR2-derived existing-feature-frame adaptation`：

- 保留 `crash <= -0.15`、`risk_off <= -0.08` 的 drawdown 阈值及 crash 优先级；
- 以 frozen Model B 既有的 `TWII_close_vs_MA60`、`TWII_ret20` 代替 RSR2 的 MA20/MA5 trend 判定；
- `risk_neutral` 在本合同中命名为 `neutral`；
- JSON 的 `source_policy`、字段语义、优先级、边界、missing/non-finite 和 forbidden inputs 均明确冻结。

该 adaptation 合理：它避免为 frozen compatibility scorer 临时引入未冻结的新特征来源，并且 regime 只用于 prospective comparison 的预声明分层，不改变 Model B 输入、评分或生产决策。限制是：后续报告只能称其为 MBCDS3-5 adapted regime，不能将分 regime 结果表述为 RSR2 exact-regime 结果。

## 3. Contract And PIT Review

1. classifier 只接受三个冻结字段，缺失或非有限值 fail closed；`-0.15`、`-0.08`、零值和优先级均有边界测试。
2. feature builder 只读取 `date <= target_asof` 的 checksum-bound source records，并要求 `combined_available_at <= decision_cutoff`；regime artifact 绑定 asof、cutoff、source run、feature-frame checksum 和 contract checksum。
3. scorer 校验冻结合同原始字节 SHA256，复核 150 行 TWII 字段一致性并独立重算 regime；合同、artifact、frame 或 source checksum drift 均阻断。
4. `SIGNAL_REGISTERED` 将 regime、regime artifact checksum 和 contract checksum 写入 append-only hash-chain event；comparison 从 signal event 读取 regime。
5. outcome builder 不生成 regime。settlement 不接受 outcome regime，并继承 signal event 的 regime，不能覆盖 signal-time 分类。
6. `UNCLASSIFIED` 不在 allowed regimes，分类失败不能注册 signal；120 日 gate 仍保留 regime coverage 防护。

## 4. Reviewer Repairs

本次独立审查完成两项窄修复：

1. 收紧状态与执行报告措辞，明确合同是 existing-feature-frame adaptation，不是 RSR2 MA20/MA5 原样机器化。
2. 将 outcome regime 注入审计从 manifest 顶层扩展为递归 manifest key，并拒绝 outcome CSV 中任何 regime 列；新增 nested manifest 和 CSV injection 测试。

未修改分类阈值、scorer、daily wiring、cron、latest、provider、default 或 publish。

## 5. External Conditions Audit

以下状态记录准确，未被 synthetic tests 或文档虚假关闭：

| Gate | Review status |
|---|---|
| 20 real accepted prospective input days | `WAITING_EXTERNAL_EVIDENCE` |
| first live feature -> score -> signal -> settlement E2E | `WAITING_EXTERNAL_EVIDENCE` |
| 60 settled paired OOS days | `WAITING_EXTERNAL_EVIDENCE` |
| 120 settled paired OOS days | `WAITING_EXTERNAL_EVIDENCE` |
| exact same-contract strategy replay | `WAITING_EXTERNAL_EVIDENCE` |
| baseline switch | `NOT_AUTHORIZED / HUMAN_REVIEW_REQUIRED` |

默认 natural accumulator 和 prospective ledger 尚未产生 live evidence，这与当前等待状态一致。

## 6. Forbidden Scope Audit

- installed/actual cron：本轮未修改；
- protected latest、formal provider、Qlib accepted latest：本轮未修改；
- frontend/backend default、publish：本轮未修改；
- training、DB、OpenAI、broker/order/target：未执行；
- Model A：保持 non-blocking current baseline；
- Model B：保持 isolated shadow-only。

## 7. Validation

```text
python -m pytest tests/isolated/test_tw_mbcds35_*.py -q
45 passed

python -m py_compile <6 relevant MBCDS3-5/daily scripts>
PASS

python scripts/build_tw_mbcds3_shadow_accumulator.py --self-test
PASS

python scripts/validate_tw_daily_orchestrator_m3.py \
  --audit-script scripts/run_daily_tw_stock_auto_update.py --json
PASS (仅有两项既有、显式 gate 的 legacy-path warning)

git diff --check
PASS
```

冻结 regime contract 实际 SHA256：

```text
74e50aecda4353e74e9f34e8bbcd934a356738e1e8d8ced2c74751ef905d3ffe
```

## 8. Closure

`MBCDS3-5C_R` 实现修复可关闭，并进入自然 prospective accumulation。下一次审查触发点不是继续修改合同，而是首个真实 live E2E 或达到 20/60/120 门槛后的只读证据验收。
