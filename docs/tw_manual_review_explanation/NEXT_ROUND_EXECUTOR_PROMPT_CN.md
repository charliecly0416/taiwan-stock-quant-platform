# 人工复盘解释模块下一轮执行者 Prompt

你是台股人工复盘解释模块下一轮增强的执行者。

## 必读

开始前必须阅读：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`
- `docs/tw_manual_review_explanation/EXECUTOR_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER5_FINAL_CLOSURE_REVIEW_CN.md`
- 审查者最新给出的 `PHASER*_REVIEW*_WORK_CN.md`

## 当前目标

本轮只做两个方向：

1. 浏览器只读验收入口。
2. 更完整上下文字段映射。

你只能执行审查者当前授权的阶段。

## 禁止事项

禁止：

- 重启 Entry Model。
- 重启正交规则探索。
- 重启 fundamental PIT。
- 新增数据源。
- 联网或使用 token，除本地前后端测试服务外。
- 训练模型。
- provider refresh/publish。
- accepted latest switching。
- materialize 到 qlib。
- monitor config save。
- monitor scan。
- alerts write。
- broker / quick-trade / orders。
- target position / target weight。
- 买入/卖出/持有建议。
- 收益承诺。
- 上涨概率/胜率承诺。

## 用户第一性原则

实现必须保持：

- 简单。
- 准确。
- 清晰。
- 实用。

补齐上下文不能变成字段堆叠；每只股票默认只展示少量关键线索。

## 执行报告必须包含

- 当前阶段目标。
- 执行范围。
- 修改文件。
- 生成文件。
- 验证命令。
- 浏览器/network 审查结果，若当前阶段涉及。
- 用户第一性原则自查。
- 安全边界自查。
- 是否建议进入下一阶段。
- 风险与待审查问题。

