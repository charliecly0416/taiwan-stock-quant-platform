# Model A + Model B Compatibility Baseline 恢复与重评测主线

## 1. 目标

恢复既有 Phase1C `old qlib + new LTR` 的研究成果，使用当前 `ModelSignalArtifact` 接口生成隔离的兼容 artifact，并复核其与 Model A-only 的同窗口收益、回撤和动作差异。

## 2. 重要区分

- 本路线恢复的是已有 Phase1C anchor，不重新训练另一个 fresh LTR。
- 兼容 artifact 可以用于只读研究比较，但不自动成为 production default。
- `source_feature_artifact=legacy_unknown` 明确表示历史特征可追溯性不足；不得宣称严格 PIT OOS 已完成。

## 3. 固定口径

- Model A：既有 qlib/top50 baseline。
- Model B：Phase1C `head10_all_l31`，`blend_alpha=0.7`，只在 qlib top50 内重排买入顺序。
- 比较窗口：`2025-07-01..2026-05-07`。
- 策略：既有 next-day execution、10 holdings、fee `0.001425`、tax `0.003`。
- 对照：Model A-only 与 Model A + Model B，full universe 和 common universe 都要报告。

## 4. 阶段

1. `AB0`：冻结 identity、输入、窗口、边界，审查已有 Phase1C evidence。
2. `AB1`：将冻结 score 映射为隔离标准 ModelSignalArtifact，跑 validator/golden checks。
3. `AB2`：复用既有 replay engine 做同窗重评测和差异分析。
4. `AB3`：独立审查；只允许输出“研究 baseline 恢复/继续 blocked/可进入候选讨论”结论。

## 5. 禁止

不得训练、调参、改 feature/label/window、访问网络或 DB、修改 provider/qlib/latest/cron、改 frontend/API default、触发 broker/order/target 或把未来收益写入 signal artifact。

## 6. 放行标准

必须同时具备：标准字段完整、无 forbidden fields、日期/键无重复、top50 boundary 保持、历史 replay 指标可复现、Model B 的 legacy/PIT 限制清晰标注。通过后仍是 research candidate，是否进入正式 baseline 需要后续 default-candidate gate。

## 7. 路线状态（2026-09-05）

- `AB0`：完成。
- `AB1`：完成，标准 artifact validator 通过。
- `AB2`：完成；补充 `AB2R direct replay re-execution`，标准 artifact 已由冻结 replay engine 直接消费。
- `AB3`：完成，独立审查为 `PASS`。

路线结论：`Model A + Model B` 已恢复为 `legacy-compatible research baseline`。full/common universe 的指标、逐日 NAV、动作、费用税费和 next-day execution 均复现；strict PIT/OOS 仍未通过，production default、daily auto 和前端默认均未获得授权。
