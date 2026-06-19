# Phase5 真实只读接入实现执行报告

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

执行依据：`docs/tw_ltr_rerank_regime_turnover/PHASE4B_REVIEW_AND_PHASE5_READONLY_INTEGRATION_IMPLEMENTATION_WORK_CN.md`

---

## 1. 本轮目标

按 Phase4B 冻结后的展示契约，完成最小真实只读接入：

- 后端新增一个只读 GET，包装固定 Phase3C payload；
- 前端在现有台股研究页面做最小展示；
- 首屏只展示 4 个信息单元；
- 详情层只展示受约束历史回放指标，并保持费用后净值变化、最大回撤、动作次数、notional turnover proxy 同屏；
- 补充后端契约测试、前端静态检查和只读 E2E；
- 不扩展到模型训练、新数据源、provider、accepted latest、monitor 写入、交易或推荐语义。

---

## 2. 实际改动文件

### 2.1 后端

- 新增：`backend/app/services/tw_ltr_readonly_explanation.py`
  - 读取固定 artifact：
    `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_readonly_explanation_payload.json`
  - 输出 Phase5 产品只读视图：
    `schema_version = phase5_product_readonly_view_v1`
  - 过滤原始研究字段，不透出 `source_trace`、原始 `summary_notes[]`、原始 `safety_boundary`。

- 修改：`backend/app/routes/tw_stock.py`
  - 新增：
    `GET /api/tw-stock/ltr-readonly-explanation`
  - 仅调用 `TWLTRReadonlyExplanationService.product_view()`。
  - 未新增 POST / PUT / PATCH / DELETE。

### 2.2 前端

- 修改：`frontend/src/api/tw-stock.js`
  - 新增 `getTwStockLTRReadonlyExplanation()`，只使用 GET。

- 修改：`frontend/src/views/tw-stock-monitor/index.vue`
  - 在“今日复盘与历史模拟”区域加入最小只读展示面板：
    `data-testid="ltr-readonly-explanation-panel"`
  - 首屏展示顺序：
    1. `item.why_no_action`
    2. `item.tradeoff_summary`
    3. `item.research_role_label`
    4. `item.readonly_disclaimer`
  - 详情层展示：
    - `net_return_summary`
    - `drawdown_summary`
    - `action_count_summary`
    - `turnover_summary`
    - `relative_to_top50_adaptive`
    - `detail_disclaimer`

### 2.3 测试

- 新增：`backend/tests/test_tw_ltr_readonly_explanation_api.py`
- 修改：`frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- 修改：`frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`

---

## 3. 新增接口与字段白名单

### 3.1 接口

```text
GET /api/tw-stock/ltr-readonly-explanation
```

### 3.2 顶层返回字段

- `ok`
- `schema_version`
- `payload_source`
- `as_of_scope`
- `data_quality`
- `methods`
- `readonly_disclaimer`
- `no_write_guarantees`
- `research_only`

### 3.3 methods[] 字段

- `method_key`
- `method_label`
- `research_role_label`
- `research_role_note`
- `why_no_action`
- `tradeoff_summary`
- `readonly_disclaimer`
- `detail`
- `data_quality_note`

### 3.4 detail 字段

- `net_return_summary`
- `drawdown_summary`
- `action_count_summary`
- `turnover_summary`
- `relative_to_top50_adaptive`
- `detail_disclaimer`

未暴露字段：

- `source_trace`
- 原始 `summary_notes[]`
- 原始 `safety_boundary`

---

## 4. 前端展示结构说明

本轮未新增独立页面，只在现有 `/tw-stock-monitor` 的“今日复盘与历史模拟”卡片内加入只读说明面板。

首屏每个方法卡片只显示 4 个信息单元：

```text
今天不动作的主要原因：{原因短语}。
历史回放取舍：{动作频率}，{换手压力}，{回撤水平}。
{用户短标签}
仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。
```

精确数值仅放在折叠详情层，且费用后净值变化、最大回撤、动作次数、notional turnover proxy 同屏出现。首屏不显示高风险精确数值。

用户短标签使用 Phase4B 冻结映射：

- `baseline` -> `对照参考`
- `aggressive_rerank_research` -> `高换手观察`
- `turnover_control_research` -> `少动作观察`
- `risk_review_reference` -> `风险复盘`

---

## 5. 验证结果

### 5.1 后端契约测试

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
```

结果：

```text
4 passed in 1.13s
```

覆盖点：

- GET 正常返回产品只读视图；
- 返回 6 个方法；
- 不透出 `source_trace`、`summary_notes`；
- 首屏字段前缀符合 Phase4B；
- 详情层 4 类精确指标齐备；
- POST / PUT / PATCH / DELETE 返回 405；
- monkeypatch 变更服务后 GET 不触发这些服务；
- route 源码切片中未出现 provider、accepted latest、monitor 写入或 portfolio replay 服务调用。

### 5.2 Python 编译检查

```text
python -m py_compile backend/app/services/tw_ltr_readonly_explanation.py backend/app/routes/tw_stock.py backend/tests/test_tw_ltr_readonly_explanation_api.py
```

结果：通过。

### 5.3 前端静态检查

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
tw-stock-monitor static checks passed
```

覆盖点：

- API 函数与 `/ltr-readonly-explanation` 路径存在；
- 面板 `data-testid` 存在；
- 首屏字段绑定存在；
- 详情层字段绑定存在；
- 页面源码不含 `source_trace`、`summary_notes`。

### 5.4 前端构建

```text
corepack pnpm build
```

结果：通过。

说明：

- 尝试使用 Vite dev server 验证时，系统 watcher 达到上限：
  `ENOSPC: System limit for number of file watchers reached`
- 因此改用生产构建 + 已有静态服务脚本验证，未修改系统配置。

### 5.5 只读 E2E

先用既有 `http://127.0.0.1:8000` 服务执行 E2E，失败原因是该服务未加载本轮最新前端构建，页面未请求 `/api/tw-stock/ltr-readonly-explanation`。该失败不作为产品验收结果，只作为环境诊断记录。

随后执行：

```text
python scripts/serve_frontend_static_proxy.py --host 127.0.0.1 --port 8011 --dist frontend/dist --backend http://127.0.0.1:5000
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

结果：

```text
tw-stock rank-tech portfolio replay readonly e2e passed
```

关键计数：

```json
{
  "ltr_readonly_explanation_request_count": 2,
  "sim_write_request_count": 0,
  "quick_trade_request_count": 0,
  "broker_request_count": 0,
  "real_order_request_count": 0,
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "qlib_ops_post_count": 0,
  "accepted_latest_switch_count": 0,
  "provider_publish_refresh_count": 0,
  "target_position_request_count": 0,
  "target_weight_request_count": 0,
  "forbidden_request_count": 0,
  "page_error_count": 0
}
```

---

## 6. 安全边界声明

本轮没有做以下事项：

- 没有新增模型训练；
- 没有新增数据源；
- 没有联网抓取；
- 没有 provider refresh / publish；
- 没有 accepted latest switching；
- 没有 monitor config save / scan / alerts write；
- 没有 broker / quick-trade / order；
- 没有 target position / target weight；
- 没有把 Phase3C explanation payload 抬升成推荐层；
- 没有新增真实交易、仓位、收益承诺、胜率或上涨概率语义。

安全扫描结果：

- `backend/app/services/tw_ltr_readonly_explanation.py` 未命中危险交易语义；
- E2E 与静态测试中出现的 `broker`、`quick-trade`、`orders` 等词均为防御性计数、禁止断言或既有只读边界文案；
- `frontend/src/api/tw-stock.js` 和 `backend/app/routes/tw_stock.py` 中命中的 sim/order 路由为既有模块，不属于本轮新增 LTR 接口。

---

## 7. 是否达到只读接入验收门槛

结论：达到 Phase5 最低验收门槛，等待审查者审查。

对应关系：

- 后端只读 GET 正常返回：已通过后端测试；
- 前端最小只读展示符合 Phase4B 契约：已通过静态检查和 E2E；
- 只读 E2E 通过：已在当前构建产物上通过；
- 无写请求、无状态变更、无危险文案：E2E 计数为 0，安全扫描未发现本轮 LTR 新增危险语义；
- 未扩线到推荐层或交易层：本轮只做 Phase3C payload 的只读产品视图包装和展示。

---

## 8. 待审查事项

1. 本轮真实页面接入位置为现有 `/tw-stock-monitor` 的“今日复盘与历史模拟”区域，未新增独立页面。
2. 详情层保留了 Phase4B 允许的精确历史回放指标，首屏不展示这些精确数值。
3. 既有 8000 服务不是当前构建产物，E2E 必须使用当前源码构建后的 8011 静态服务验证；本报告已记录该环境差异。
