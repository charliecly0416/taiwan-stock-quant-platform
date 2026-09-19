---
created_at: 2026-08-24
status: coordinator_mainline
route: MODEL_B_LTR_LONG_WINDOW_LINEAGE_REPAIR_AND_STANDARD_SIGNAL_INPUT_BUILD
current_phase: MBLR0_RESEARCH_ONLY_LINEAGE_REPAIR_AND_CANDIDATE_BUILD
readonly_product: true
research_write_allowed: true
replay_allowed: false
production_allowed: false
default_switch_allowed: false
---

# Model B/LTR Long-Window Lineage Repair And Standard Signal Input Build 主线

## 1. 目标

将已有 E1/E2/E3 Model B/LTR 研究结果，在不训练、不访问外部数据的前提下，整理为可审计的 research-only 标准 `ModelSignalArtifact` candidate，目标窗口为 `2023-01-03..2026-05-07`、universe 为 `option_c_150`。

## 2. 与当前日更的边界

当前日更链路已推进到 `2026-08-21`，它服务于当日 freshness/product artifacts；本路线处理的是历史 OOS research lineage，不能用日更单日数据补历史，也不修改日更或 latest。

## 3. 允许范围

- 读取已有本地 E1/E2/E3 score、feature、model、manifest 和既有标准 adapter；
- 只在独立 research 目录生成 candidate、lineage、PIT、coverage 和 validator evidence；
- 如原始证据无法满足合同，必须输出 blocker，不得推断或填补；
- 只允许标准 core fields：`date/instrument/model_name/model_family/candidate_rank/buy_score/raw_score/score_rank/full_qlib_rank/signal_asof/available_at/source_artifact`。

## 4. 禁止范围

- 不训练、重训、调参或改变模型；
- 不访问 network/DB/OpenAI，不读取 future return/label/realized PnL 作为输入；
- 不运行 OrderIntent、ReplayResult 或收益回放；
- 不修改 scripts/config/registry/provider/qlib/latest/cron/frontend/backend/Agent；
- 不拼接不同 lineage、短窗口和长窗口；
- 不进入 optional binding/core registry actual route。

## 5. 阶段计划

| phase | 目标 | 输出 | 放行 |
| --- | --- | --- | --- |
| MBLR0 | 清理/映射已有 lineage，生成标准 candidate 或 blocker | candidate、PIT/coverage/validator、执行报告 | 独立审查 |
| MBLR1 | 标准 artifact 与 golden/negative validation | validator evidence | 独立审查 |
| MBLR2 | 只读输入链路验收 | integration report | 另开 replay route |

## 6. 停止条件

任何关键字段、日期覆盖、PIT/available_at 或 LTR top50 映射无法由已有本地证据证明时，停止为 `BLOCKED_MISSING_STANDARD_MODEL_B_INPUT`，不得把 candidate 包装成可比较输入。
