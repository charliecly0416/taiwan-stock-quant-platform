# Readonly Replay Window 产品化开发规范

生成日期：2026-06-17

## 1. 新增窗口流程

新增可展示 replay window 必须按以下顺序执行：

```text
1. 通过 ReplayWindowPolicy 校验模型、规则、start/end。
2. 只消费 OrderIntentArtifact、PriceStore 和 ExecutionConfig，离线生成 readonly ReplayResultArtifact。
3. 运行 validate_tw_readonly_replay_window_artifact.py。
4. 登记到 readonly replay window D7 index。
5. 运行 validate_tw_readonly_replay_window_index.py。
6. API 只读读取 index 和 artifact。
7. 前端只读取 GET index/detail，不本地 replay。
```

Phase M 后新增窗口还必须能追踪：

```text
PriceStore manifest
RunRegistry record, if produced by DailyOrchestrator
FrontendReadonlyDisplay allowed fields
```

## 2. 禁止事项

```text
禁止 API handler 内即时 replay
禁止 provider publish / refresh
禁止 accepted latest switch
禁止 monitor config save / scan / alerts write
禁止 broker / quick-trade / orders
禁止 target_position / target_weight
禁止把 diagnostic rule 当作有效策略证据
禁止前端本地 replay
禁止 readonly latest pointer 与 provider / qlib accepted latest 混用
禁止前端 embedded Agent 因 replay window 展示而新增 tool/action/prompt 能力
```

## 3. 必跑验证

```bash
python scripts/build_tw_readonly_replay_window_index.py --json
python scripts/validate_tw_readonly_replay_window_index.py --json
python scripts/validate_tw_readonly_replay_window_query.py --json
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact <manifest> --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
```

若涉及前端展示变更，还必须运行：

```bash
corepack pnpm build
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
```

## 4. 审查口径

审查时应按功能块检查新增范围。`tw-stock-monitor/index.vue` 是历史大文件，不能仅凭全文件出现 monitor、broker、order 等旧模块词汇判定 D7 越界；应重点审查 readonly replay window panel、loader 和 API wrapper。

