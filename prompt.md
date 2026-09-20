# G0 provenance 只读盘点报告（2026-09-15）

盘点UTC：2026-09-14T17:51:57.837965+00:00

## 范围

仅读取项目内 docs/artifacts/GPU bundle/supplement/stage1 及可见 Codex 历史中的文本格式；未解压归档、未扫整个home、未运行GPU/模型/API/生成器或trace。

## 3076535 与 3076533 冲突

两值原样并列；当前没有权威R10 manifest/evaluation原文件可供裁决，均不能修正、合并或选择。
- `/lustre/home/2401213359/llm-scheduling/docs/gpu_stage1_20260914/reviews/input_fixture_review_zh.md` L10：2. registry的1,404,294行与60/40 row split属于其登记的另一个全源；不能套到本文件22,882行。全部timestamp早于registry声明evaluation_first_timestamp_s=3076535，可以声明“依据registry声明的时间边界分离”；由于没有全源occurrence映射，不能宣称验证了原始calibration partition membership或完整source lineage。
- `/lustre/home/2401213359/llm-scheduling/gpu_calibration_supplement_20260914_v2/inputs/trace_registry.json` L100："evaluation_first_timestamp_s": 3076535.0,

## 字段状态与未知原因

- trace、content sidecar、稳定request/job ID：**UNKNOWN**，未发现可核验原件；文本候选不能升格。
- 行数、首末时间、时区、tick、缺失/截断、provenance：**UNKNOWN**，缺少 exact 输入。
- split/seed/window/evaluation：**UNKNOWN**，未定位冻结 manifest。
- local/API/offline/transition cost、价格/币种/舍入、terminal cutoff：**UNKNOWN**，只有构造或历史声称。
- GPU/model/backend：已有旧报告候选，但本盘点不重新核验，不能代替 exact trace 合同。
- timestamp→tick、no-lookahead、completion/censoring：**UNKNOWN**。

文本命中文件 2767；不可访问 0。

## 边界

本报告不是G0 PASS，不授权Stage1/Stage2；不得把derived、partial或diagnostic产物包装为exact ED/guard。
