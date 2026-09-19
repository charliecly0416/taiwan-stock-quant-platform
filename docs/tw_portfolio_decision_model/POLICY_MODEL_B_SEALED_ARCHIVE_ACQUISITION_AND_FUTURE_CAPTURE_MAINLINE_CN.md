# Model B 历史 sealed archive 获取与未来日更封存路线

生成日期：2026-08-25
状态：`HSA6_CLOSED_READY_FOR_HSA7_REAL_HANDOFF_PREFLIGHT`

## 目标

把现有本地 raw archive 中能够绑定到原始文件、snapshot id、抓取时间和 checksum 的部分登记为 partial sealed archive；随后检查已知 37 条 2026 margin-short 缺口是否能从本地历史源恢复；最后建立从现在开始的 daily append-only source capture 规范。

## 阶段

1. `HSA0_CONTRACT_AND_LOCAL_SOURCE_INVENTORY`：已完成，确认当前缺口与禁止边界。
2. `HSA1_PARTIAL_ARCHIVE_REGISTER_NO_PROVIDER_WRITE`：登记已有源文件和 checksum，不复制、不修改原文件。
3. `HSA1R_PARTIAL_ARCHIVE_INDEPENDENT_REVIEW`：审查覆盖范围和 sealed 资格。
4. `HSA2_LOCAL_GAP_RECOVERY_FEASIBILITY`：只读检查 37 条缺口；不能用同股票其他日期替代。
5. `HSA3_FUTURE_DAILY_APPEND_ONLY_CAPTURE_DESIGN`：为未来数据建立 raw response、manifest、checksum、available_at 和 completeness 规则；不回填过去。

## 禁止事项

不联网、不调用 provider、不改 accepted latest、qlib、cron、daily auto、frontend/backend；不训练、不评分、不 replay；不使用 later data、zero-fill、neutral-fill 或推断值修复历史缺口。

## 当前结论

现有 `phase0e` 全量 normalized snapshot 可作为候选历史源登记，但不能独自闭合 2026 的 37 条 margin-short 缺口。`phase_o1r` 是按股票拆分的研究阶段 archive，必须保持 partial 标记，不能直接当作全量 sealed archive。

## 当前完成结果

- HSA1：partial archive 已登记并通过附条件审查。
- HSA2：本地 37 条缺口不可恢复，已停止路径二历史重训。
- HSA3：未来 append-only sealed capture 合同已完成；尚未修改 daily auto/cron，待另行授权实现。
- HSA4：isolated daily sealed capture builder 已实现，37 个专项测试和独立审查通过；仅允许显式本地文件输入和 isolated candidate 输出，不授权 runtime wiring、daily auto 或 cron。
- HSA5：daily-auto wiring preflight 已实现并通过独立终审；HSA4/HSA5 共 72 项测试通过。当前 runner 缺少 fail-closed source validator 和 authoritative same-run raw/normalized handoff manifest，因此结论为 `PASS_STOP_HSA5_UPSTREAM_CAPTURE_CONTRACT_GAPS`，不得进入 HSA6。
- HSA5U：synthetic same-run handoff builder 已完成修复并通过独立审查；HSA4/HSA5/HSA5U 共 87 项测试通过，新 evidence 目录包含 24 项递归 checksum，HSA5 synthetic preflight 输出 `READY_FOR_HSA6_NO_CRON_IMPLEMENTATION`。真实 acquisition runner 仍保持 STOP。
- HSA6：HSA5U synthetic handoff 已通过 HSA4 adapter 生成 4 个 isolated sealed candidates；最终独立审查通过，HSA4/HSA5/HSA5U/HSA6 共 102 项测试通过，最终 manifest 覆盖 15 项 artifact，11 类 protected paths before/after 一致。真实 runner 仍未提供 handoff。

因此，原 78 特征 Model B 继续保持 `legacy_exploratory`。路径二只有在取得真实历史快照后才能重启；下一步仅进入 HSA7 real-handoff no-cron preflight，仍不接 runtime/cron。
