# Phase 3 审查意见：Simple Chat 后端服务

生成日期：2026-06-19

## 1. 审查结论

审查结论：不通过。

暂不允许进入 Phase 4。本次不写 `PHASE4_WORK_CN.md`。

主要阻塞原因：Simple Chat 的模型输出安全校验漏放英文危险语义，模型回答中出现 `place orders`、`target_weight`、`target_position` 时会原样返回用户，没有被 deterministic refusal 覆盖。这违反 Phase 3 工作文档中 output validation 必须阻断 `broker/order/quick-trade`、target position/weight 等行动性危险语义的要求。

## 2. 主线一致性判断

Phase 3 执行方向基本正确：

- 新增了 artifact loader：`backend/app/services/tw_stock_agent_daily_prompt.py`。
- 新增了 simple chat service：`backend/app/services/tw_stock_agent_simple_chat.py`。
- 新增了后端测试：`backend/tests/test_tw_stock_agent_simple_chat.py`。
- 未新增 API 路由。
- 未改前端。
- 未改现有 `/api/tw-stock/agent/chat`。
- 未做真实 OpenAI smoke。

loader 复用 Phase 1 `validate_artifact(...)`，blocked intent 在加载 artifact 和调用 OpenAI 前返回，这些方向符合 Phase 3 工作单。

但 output validator 覆盖不足，不能放行进入 Phase 4。

## 3. 安全边界审查

本次审查未发现新增真实 provider publish、accepted latest、monitor 写入、broker/order/quick-trade 路径，也未发现真实 OpenAI 调用。

已复现：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
11 passed in 1.12s
9 passed in 0.14s
```

前端 OpenAI 静态检索有命中，但命中均为既有 locale 文案或前端测试 denylist/assertion；本阶段未改前端。

tool/function calling 静态检索：

```bash
rg -n "tool_choice|tools|function_call|functions" backend/app/services/tw_stock_agent_simple_chat.py backend/app/services/tw_stock_agent_openai.py
```

结果：无命中。

## 4. Artifact Loader 审查

`TWStockAgentDailyPromptLoader` 符合 Phase 3 要求：

- 支持显式 `artifact_dir`。
- 支持 latest pointer。
- 校验 `latest.artifact_type == "tw_agent_daily_prompt_latest"`。
- 校验 latest pointer 的 manifest、checksum、signal_asof。
- 调用 `validate_artifact(...)`。
- 校验 readonly flags。
- 返回 context digest。
- 生成 citation allowlist。

未发现 loader 读取实验 CSV、调用动态 preview service、provider/monitor/broker/order 或自动构建/更新 latest pointer。

## 5. Simple Chat 审查

通过项：

- blocked intent 在 artifact load 和 OpenAI 调用前返回。
- OpenAI disabled 会 deterministic fallback。
- invalid JSON fallback。
- forged citation fallback。
- monitor write 用户问题会 blocked 且不调用 OpenAI。
- paper apply status 只读查询未被误判为交易。
- valid mock JSON 可以通过。

阻塞项：

`_unsafe_answer_terms` 覆盖不完整。当前包含中文下单、自动交易、目标仓位、broker、quick-trade、monitor、provider、qlib refresh、retrain、调参、收益承诺等，但缺少至少以下英文/字段级危险语义：

- `orders`
- `place orders`
- `target_position`
- `target-position`
- `target_weight`
- `target weight`
- `order`
- `submit order`
- `place order`

这导致模型输出可以绕过安全校验。

## 6. 可复现问题

审查者用 mock adapter 构造模型输出，并通过真实 service 路径验证。临时 probe 只读工作区 fixture、写 `/tmp`，不访问网络。

输入模型回答：

```text
Please place orders for 2330.
Set target_weight to 50% for 2330.
Use target_position for 2330.
```

实际结果：

```text
Please place orders for 2330. => blocked= False mode= mock answer= Please place orders for 2330.
Set target_weight to 50% for 2330. => blocked= False mode= mock answer= Set target_weight to 50% for 2330.
Use target_position for 2330. => blocked= False mode= mock answer= Use target_position for 2330.
```

预期结果：以上三类输出都必须被 deterministic refusal 覆盖，不能原样返回。

## 7. 测试与证据审查

现有测试覆盖了中文 unsafe answer：

```text
请下单并设置目标仓位。
```

但缺少英文/字段级危险语义测试，因此未捕获上述缺口。

需要新增测试覆盖：

- `Please place orders for 2330.`
- `Set target_weight to 50% for 2330.`
- `Use target_position for 2330.`
- `Submit order for 2330.`
- `Set target-position to 50%.`

这些输出均应被覆盖为 blocked/refusal，且不应原样展示。

## 8. 发现的问题

### High

1. output validator 漏放英文 order/target position/target weight 危险语义。
   影响：OpenAI mock/真实模型一旦输出英文执行类语义，后端会将其作为有效答案返回，违反 research-only 安全边界。
   处理：必须修复 `_unsafe_answer_terms` 或改为复用 Phase 1 forbidden patterns，并补充测试。

### Medium

1. output validator 与 Phase 1 validator 词表重复且不一致。
   影响：输入 artifact 能挡住的危险语义，模型输出未必能挡住。
   处理：建议抽出共享 forbidden action checker，或至少让 simple chat 的 unsafe answer checker 覆盖 Phase 1 全部 forbidden patterns。

### Low

1. 本阶段未新增 API 路由。
   这是低风险选择，不阻塞；Phase 4 前需要明确前端调用哪个后端 endpoint。

## 9. 必须修复项

进入 Phase 4 前必须完成：

1. 扩充 output unsafe checker，至少覆盖：

```text
orders
order
place order
place orders
submit order
target_position
target-position
target weight
target_weight
quick-trade
broker
monitor config
monitor scan
monitor alerts
provider publish
accepted latest
qlib refresh
retrain
调参
保证收益
保证上涨
胜率承诺
上涨概率
```

2. 新增测试，证明上述英文/字段级危险输出都会被 deterministic refusal 覆盖。
3. 重新运行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
rg -n "tool_choice|tools|function_call|functions" backend/app/services/tw_stock_agent_simple_chat.py backend/app/services/tw_stock_agent_openai.py
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_simple_chat.py
```

4. 提交 `PHASE3_FIX_EXECUTION_REPORT_CN.md` 或更新 Phase 3 执行报告，说明修复和测试结果。

## 10. 可后续优化项

- 将 Phase 1 artifact validator 和 Phase 3 output validator 的 forbidden pattern 统一成共享模块。
- 为 allowed research-only answer 增加结构化 answer type，减少纯文本关键词绕过。
- Phase 4 前明确是否新增 `/api/tw-stock/agent/simple-chat`，或保持服务层等待后续路由接入。

## 11. 是否允许进入 Phase 4

不允许进入 Phase 4。

当前未满足 Phase 3 放行标准：

```text
unsafe model answer 不会展示给用户
```

英文 order/target position/target weight 输出仍可原样展示。
