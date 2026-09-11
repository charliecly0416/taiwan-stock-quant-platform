你是本项目的后续路线统筹者，请接手台股量化平台的架构收敛与 Model B 纳入 baseline 工作。

  项目目录：
  /home/chuliyang/taiwan-stock-quant-platform

  请先阅读：
  1. docs/tw_modular_contracts/PROJECT_RUNTIME_CONSOLIDATION_AND_MODEL_B_BASELINE_ADMISSION_MAINLINE_CN.md
  2. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
  3. docs/tw_model_b_compatibility/MBCDS3_5_PROSPECTIVE_SHADOW_SCORING_AND_OOS_COMPARISON_AUTOMATION_NO_PUBLISH_CN.md
  4. docs/tw_model_b_compatibility/MBCDS3_5C_R_CONDITION_STATUS_AND_CLOSURE_CN.md

  当前事实和决策：

  - 当前 active baseline 实际是 Model A/Qlib：
    e4_frozen_qlib_2018_2022
  - 当前默认策略：
    top50_exit_one_worst_sell
  - 当前执行价口径：
    next_open
  - 当前产品 latest 最近证据为 2026-09-04。
  - Model B 是：
    e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
  - Model B 的历史训练和历史回放，接受项目负责人声明：当时的数据隔离、数据可用性和测试过程是正确的。不要再把主要精力用于追溯或否定历史过程，也不要因为旧证据记录不完整就直接废弃历史成果。
  - 历史 Model B 结果保留为 declared_legacy_prior。
  - 后续重点是使用当前标准、当前可复现数据，验证 Model A+B 是否仍然优于 Model A-only。
  - Model B 目标是正式加入 baseline，但必须保持可回滚、可审查、可比较。
  - 当前不能把 Model B 直接写入 active baseline，也不能直接修改 latest。

  工作总目标：

  1. 收敛项目架构，减少 route、阶段脚本、重复合同和多套 Model B 身份。
  2. 让 Model A-only 和 Model A+B 共用统一的数据、PIT、same-run、ModelSignalArtifact、策略、费用和回放口径。
  3. 用新数据重新比较 A-only 与 A+B 的排序和策略效果。
  4. 如果新数据上 Model A+B 稳定优于 Model A-only，并且没有不可接受的换手、费用、回撤或数据依赖风险，再通过受控、可回滚流程把 Model B 纳入 baseline。
  5. 收敛完成后进入稳定日常运维，不再继续无止境增加同类 route。

  执行规则：

  - 每个阶段都启动执行者和独立审查者。
  - 执行者只执行当前工作单；审查者独立检查代码、artifact、checksum、测试、边界和实际 diff。
  - 不需要每一步都等待我批准；没有意外问题时按主线连续推进。
  - 遇到未预料的问题、范围冲突、需要修改默认模型、需要写 protected latest、需要改 cron/provider 或需要人工决策时才暂停并说明。
  - 不删除或回滚未知用户改动。
  - 不覆盖历史 artifact。
  - 不连接 broker，不下单，不生成真实目标仓位。
  - 不修改生产默认值，不切换 Model B latest，不跳过 validator。
  - 不把 synthetic、旧回放、in-sample 或缺失 paired 日期当成新 OOS 证据。

  Model B 纳入 baseline 的最低要求：

  - canonical model identity 统一；
  - Model B 只能重排 Model A 的 top50，不能改变 candidate universe；
  - 具备 signal_asof、available_at、source manifest、feature manifest 和 checksum；
  - 当前标准数据下 A-only 与 A+B 使用完全相同日期、股票范围、策略、费用、税、lot size、next_open 和 mark-to-market；
  - 至少完成真实有效 paired prospective evidence；
  - 完成净收益、超额收益、最大回撤、换手、费用、Rank IC、月度和 regime 稳定性比较；
  - 完成 exact replay；
  - 保留 Model A-only rollback artifact；
  - 通过独立审查后，才允许一次 controlled A+B baseline switch；
  - 切换后还要通过 API、前端、readonly artifact 和自然 cron 验收。

  第一步只做 ARCH-0_RUNTIME_TRUTH_INVENTORY_NO_WRITE：

  只读盘点并输出执行报告和审查报告，内容包括：

  - active signal latest 的 model_id、asof、run_id、checksum；
  - Model A/B registry、artifact 目录、模型 hash 和 fallback；
  - 最近日更 job、raw/provider/calendar 状态和 blocker；
  - installed cron 与 actual crontab 的差异；
  - 前端/API 实际默认模型和策略；
  - Model B 当前 shadow 状态和新数据可用数量；
  - protected latest fingerprints；
  - 代码、generated artifact、evidence、archive 的数量和边界。

  ARCH-0 阶段禁止修改代码、cron、provider、latest、前端默认值和 baseline。

  完成 ARCH-0 后，按照主线依次推进 ARCH-1 至 ARCH-5，再推进 MB-0 至 MB-4。每一步都写执行报告、独立审查报告和下一步工作单。最终请明确报告：

  - 是否完成架构收敛；
  - 当前 active baseline 是什么；
  - Model B 是否已经通过新数据验证；
  - Model B 是否可以纳入 baseline；
  - 日更是否已经进入稳定运维；
  - 尚未解决的问题和下一次需要人工授权的精确范围。