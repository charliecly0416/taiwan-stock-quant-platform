# Phase D8 最终收口审查补充意见

生成日期：2026-06-17

## 1. 审查结论

D4-D7R 当前主链路基本完善，可以进入 D8 最终收口。

已闭合链路：

```text
D4 readonly standard artifact index
  -> D5 ReplayWindowPolicy 后端窗口校验
  -> D6 audited readonly replay artifact 离线生成
  -> D7 readonly replay window index
  -> D7R fixed/generated 窗口统一经 D7 index gate
  -> D8 final release bundle / acceptance closure
```

未发现需要暂停 D8 的阻塞问题。

## 2. D8 需要补强的非阻塞项

### 2.1 把 D7R index gate 作为最终反回归硬门

D7R 修复了固定窗口绕过 D7 index 的问题。D8 最终验收不能只记录“当前通过”，还应把以下负例列为 release bundle 的必须证据：

```text
fixed window requires D7 latest/index
generated window requires D7 latest/index
missing D7 latest fails closed
missing fixed index entry fails closed
query response window_index_manifest matches loaded D7 index entry
```

D8 不得接受以下回退：

```text
fixed window direct D4 fallback
hard-coded window_index_manifest without actual index load
API handler on-demand replay generation
frontend local replay
```

### 2.2 明确 D8 只做收口，不扩功能

D8 不应新增：

```text
new model
new strategy
new replay rule
new user window generation path
new provider/accepted latest/monitor/trading integration
```

如果需要新增窗口，只能走后续独立阶段，且必须重新经过：

```text
ReplayWindowPolicy validation
offline artifact generation
artifact validator
window index registration
query validator
readonly API/frontend audit
```

### 2.3 Release bundle 需要包含非法窗口拒绝证据

D8 除了列出合法窗口结果，还应显式保存非法窗口拒绝结果，至少包括：

```text
training window rejected
future beyond latest signal rejected
diagnostic rule rejected as valid strategy evidence
missing indexed artifact rejected
```

原因：用户选择回放窗口是产品化核心能力，不能只依赖前端 date picker，也不能只展示成功路径。

### 2.4 前端/API 只读边界继续按功能块审查

前端大文件中存在历史 monitor、交易、收益等词汇，不能用全文件关键词直接判定越界。D8 审查应限定新增 replay window 面板和对应 API 调用：

```text
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
```

必须确认没有：

```text
POST/PUT/PATCH/DELETE
provider publish / refresh
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
```

## 3. 给执行者的 D8 补充要求

执行者在 D8 报告中必须新增一节：

```text
Final anti-regression evidence
```

该节至少列出：

```text
D7R fixed window index-gate negative tests
ReplayWindowPolicy illegal-window rejection results
D6 artifact validator result
D7 window index validator result
D7R query validator result
backend/frontend test results
readonly snapshot validator result
network/E2E GET-only audit result
```

并明确声明：

```text
D8 did not generate new replay results in API handler
D8 did not modify provider/accepted latest/monitor/broker/order paths
D8 did not change default strategy
D8 did not add new model/strategy/replay rule
```

## 4. 给审查者的 D8 审查重点

审查者需要重点确认：

```text
D8 是否只是 release bundle / acceptance closure
fixed 和 generated 查询是否都依赖 D7 latest/index
API 是否只读取 indexed audited artifact
非法训练窗口和未来窗口是否由后端拒绝
前端是否只展示 API 输出，不本地回放
是否没有把 diagnostic rule 放入有效策略对比
是否没有 provider/accepted latest/monitor/broker/order 写入口
```

如果上述任一项失败，应停止收口，要求进入修复轮。
