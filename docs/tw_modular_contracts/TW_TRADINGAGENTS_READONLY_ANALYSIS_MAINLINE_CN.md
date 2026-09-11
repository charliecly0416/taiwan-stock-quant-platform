# TradingAgents 内置迁移与只读研究分析模块接入主线

生成日期：2026-06-30

## 1. 目标

将 `/home/chuliyang/TradingAgents` 迁移到本项目仓库内，形成一个本项目自有、可维护、可审查的内置只读研究分析能力，用于对台股当前候选、单票上下文、风险争议点和外部信息进行旁路解释。

本主线的最终产物不是交易策略、不是新模型、不是下单模块，而是：

```text
repo-local vendored TradingAgents source
repo-local TradingAgents readonly adapter
TradingAgentsReadonlyAnalysisArtifact
```

迁移后的 TradingAgents 代码必须在本仓库内可运行、可测试、可审计；它的业务输出必须落在本项目 `AnalysisArtifact` 边界内，可被人工审查，也可在后续阶段作为 Agent 只读上下文的可选补充。

## 2. 非目标

本主线明确不做：

```text
不替换 Base Qlib / Orthogonal LTR
不新增生产默认模型
不新增生产默认策略
不改变 top50_exit_one_worst_sell
不改变 current-strategy-context 的默认字段语义
不把 TradingAgents 的 Buy/Sell/Hold 直接用于策略
不把 TradingAgents 的输出转成 OrderIntentArtifact
不自动应用到 paper portfolio
不触发 broker、quick-trade、real order
不触发 provider publish / refresh
不切 qlib accepted latest 或 provider accepted latest
不把 LLM 结论作为回放收益证据
不在运行时依赖 /home/chuliyang/TradingAgents
不把 TradingAgents 原始 CLI 作为用户入口
```

## 3. 当前事实与依据

本项目当前主线是：

```text
只读研究 + 产品化候选展示 + 模拟账户
```

当前产品化模型与策略仍以以下文件为准：

```text
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
```

当前标准链路仍是：

```text
DataSource / PriceStore / FeatureArtifact
  -> Model / ModelAdapter
  -> ModelSignalArtifact
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
  -> Readonly Artifact / API / Frontend / PaperPortfolio
```

TradingAgents 的原始形态是 LangGraph 多智能体交易研究框架。它会调用 LLM 与外部数据工具，并可能输出 `Buy`、`Sell`、`Hold`、entry price、stop loss、position sizing、price target 等交易语义。因此必须先进行仓库内迁移与依赖隔离，再降级包装成只读分析模块。

TradingAgents 与本项目均为 Apache-2.0 许可证。迁移时仍必须保留上游 LICENSE、NOTICE/attribution、版本来源和本项目修改说明。

## 4. 必读文件

Executor 和 Reviewer 每个阶段开始前至少读取：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/ANALYSIS_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
```

迁移来源至少读取：

```text
/home/chuliyang/TradingAgents/README.md
/home/chuliyang/TradingAgents/pyproject.toml
/home/chuliyang/TradingAgents/tradingagents/default_config.py
/home/chuliyang/TradingAgents/tradingagents/graph/trading_graph.py
/home/chuliyang/TradingAgents/tradingagents/agents/schemas.py
/home/chuliyang/TradingAgents/tradingagents/reporting.py
```

迁移后仓库内目标位置以第 5 节为准。

## 5. 迁移架构

### 5.1 迁移目标路径

首选迁移形态：

```text
third_party/tradingagents/
  README.md
  LICENSE
  NOTICE.upstream.md 或 ATTRIBUTION.md
  pyproject.toml
  tradingagents/
  cli/
  tests/                         # 只保留与内置验证有关的 upstream tests 子集或另建 THIRD_PARTY_TESTS.md
```

本项目自有适配代码不得写进 `third_party/tradingagents/` 内，除非是明确记录的 vendored patch。适配层放在：

```text
backend/app/services/tradingagents_readonly_adapter.py
scripts/run_tradingagents_readonly_analysis.py
scripts/build_tradingagents_readonly_analysis_artifact.py
scripts/validate_tradingagents_readonly_analysis_artifact.py
```

如果 Executor 判断 `third_party/tradingagents/` 会导致 Python import 或打包冲突，可提出替代路径：

```text
backend/vendor/tradingagents/
```

但必须在 TA0/TA1 审查中明确理由，并更新所有文档和测试。

### 5.2 迁移原则

迁移必须遵守：

```text
保留上游源码边界，先少改或不改 upstream 文件
本项目业务约束写在 adapter/sanitizer/validator
所有 upstream patch 必须有 patch log
不把 upstream CLI 暴露为本项目产品入口
不把 upstream 默认 memory/cache 写到用户 home
不把 upstream dependency 无审查并入 backend runtime
```

### 5.3 许可证和归属

迁移阶段必须产出：

```text
third_party/tradingagents/LICENSE
third_party/tradingagents/ATTRIBUTION.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_LICENSE_AUDIT_CN.md
NOTICE.md 更新建议或实际更新
```

`ATTRIBUTION.md` 至少包含：

```text
上游项目名
上游来源路径或 URL
迁移日期
上游版本 / commit hash / 本地 git hash
许可证
本项目修改策略
```

### 5.4 依赖隔离

迁移源码不等于立刻把依赖加入 backend 生产 requirements。

优先顺序：

```text
1. third_party 源码先进入仓库，但 adapter 默认 mock/dry-run，不 import 真实 LangGraph 运行链路。
2. 新增独立 optional requirements 文件，例如 requirements-tradingagents.txt。
3. 真实运行通过显式环境变量启用，并在隔离环境中验证。
4. 只有依赖冲突审查 PASS 后，才允许讨论是否进入 backend/requirements.txt。
```

建议文件：

```text
requirements-tradingagents.txt
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_DEPENDENCY_AUDIT_CN.md
```

### 5.5 内置运行要求

迁移完成后，任何本项目脚本和服务都不得引用：

```text
/home/chuliyang/TradingAgents
```

必须引用仓库内路径：

```text
third_party/tradingagents
```

或通过本项目 adapter 间接调用。

## 6. 模块边界

### 6.1 允许输入

TradingAgents 只读分析模块只允许读取以下上游标准产物或显式 fixture：

```text
CurrentStrategyContext
ReadonlyStrategySnapshot
ReadonlyReplayWindow
DailyAgentPromptArtifact
AnalysisArtifact review-approved summary
手工指定单票 symbol / asof / target_date
```

优先输入是：

```text
backend/app/services/tw_stock_current_strategy_context.py
GET /api/tw-stock/current-strategy-context
```

不得直接读取模型私有实验 CSV 来绕过 context 或 manifest。

### 6.2 允许输出

唯一允许输出：

```text
data_tw/artifacts/analysis/tradingagents_readonly/{run_id}/
  manifest.json
  input_artifact_index.json
  raw_tradingagents_state.json       # 可选，必须标记 raw_untrusted
  raw_complete_report.md             # 可选，必须标记 raw_untrusted
  sanitized_report.md
  sanitized_report.json
  claim_support_audit.json
  forbidden_semantics_audit.json
```

其中 `sanitized_report.*` 才允许给后续 Agent 或前端候选接入；`raw_*` 只能用于审查，不得直接展示给普通用户。

### 6.3 禁止输出

输出中不得出现可被产品链路消费的以下产物：

```text
ModelSignalArtifact
StrategyRule
OrderIntentArtifact
ReplayResultArtifact
ReadonlyStrategySnapshot
PaperPortfolio decision/apply payload
provider latest pointer
qlib accepted latest pointer
```

## 7. Artifact 合同草案

### 7.1 manifest.json required fields

```json
{
  "artifact_type": "tradingagents_readonly_analysis",
  "schema_version": "tradingagents_readonly_analysis_v1",
  "analysis_name": "tradingagents_readonly",
  "run_id": "string",
  "created_at": "ISO-8601 string",
  "source": {
    "project": "TradingAgents",
    "project_path": "third_party/tradingagents",
    "version": "0.3.0 or detected",
    "vendored": true,
    "upstream_reference": "commit hash or local source hash",
    "selected_analysts": ["market", "news"]
  },
  "input_artifacts": [],
  "input_symbols": [],
  "signal_asof": "YYYY-MM-DD",
  "target_date": "YYYY-MM-DD",
  "readonly_only": true,
  "not_order": true,
  "not_target_position": true,
  "not_investment_advice": true,
  "production_trade_enabled": false,
  "no_replay": true,
  "no_strategy_return_conclusion": true,
  "not_valid_strategy_evidence": true,
  "not_valid_default_switch_evidence": true,
  "output_report": "sanitized_report.md",
  "quality_status": "pass|warning|failed",
  "claim_support_audit": "claim_support_audit.json",
  "forbidden_semantics_audit": "forbidden_semantics_audit.json"
}
```

### 7.2 sanitized_report.json required fields

```json
{
  "schema_version": "tradingagents_sanitized_report_v1",
  "run_id": "string",
  "signal_asof": "YYYY-MM-DD",
  "target_date": "YYYY-MM-DD",
  "symbols": [
    {
      "symbol": "2330",
      "instrument": "TW2330 or 2330.TW",
      "source_context": {},
      "research_summary": "string",
      "bull_points": [],
      "bear_points": [],
      "risk_review_points": [],
      "data_limitations": [],
      "human_review_questions": [],
      "forbidden_decision_removed": true,
      "raw_decision_label_removed": true
    }
  ],
  "research_only_disclaimer": "仅供研究观察，不构成交易建议；不代表买卖、仓位、胜率或收益承诺。"
}
```

### 7.3 forbidden_semantics_audit.json required fields

```json
{
  "ok": true,
  "checked_files": [],
  "blocked_terms_found": [],
  "raw_untrusted_files_excluded_from_display": [],
  "forbidden_patterns": [
    "target_position",
    "target_weight",
    "buy_now",
    "sell_now",
    "建议买入",
    "建议卖出",
    "应该买入",
    "应该卖出",
    "position sizing",
    "stop loss",
    "price target",
    "guaranteed return",
    "win rate promise",
    "broker_order_id"
  ]
}
```

## 8. Sanitizer 规则

Executor 必须实现确定性 sanitizer，不得只靠 prompt 约束。

原始 TradingAgents 输出中的以下内容必须删除、替换或降级：

| 原始语义 | 允许降级为 |
| --- | --- |
| Buy / Sell / Hold / Overweight / Underweight | 外部框架方向性标签已移除，仅保留论点 |
| Entry Price | 删除 |
| Stop Loss | 删除 |
| Position Sizing | 删除 |
| Price Target | 删除 |
| Final Transaction Proposal | 删除 |
| 应买入/应卖出 | 改为“需人工复盘的利多/利空论点” |
| 目标仓位/权重 | 删除 |
| 胜率/收益承诺 | 删除并标记 audit failed |

如果 sanitizer 无法确认输出安全，必须：

```text
quality_status=failed
不生成可展示 sanitized_report
不更新任何 latest pointer
```

## 9. 阶段计划

### Phase TV0：Vendor 迁移可行性、许可证与依赖审计

目标：

```text
确认 TradingAgents 可以合法、可维护地迁入本仓库，并冻结迁移路径、许可证归属、依赖隔离策略。
```

允许修改：

```text
docs/tw_modular_contracts/TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_LICENSE_AUDIT_CN.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_DEPENDENCY_AUDIT_CN.md
```

禁止修改：

```text
third_party/
backend/
frontend/
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
backend/requirements.txt
任何 data_tw latest pointer
```

Executor 产物：

```text
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_TV0_FEASIBILITY_EXECUTION_REPORT_CN.md
```

Reviewer 产物：

```text
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_TV0_FEASIBILITY_REVIEW_CN.md
```

验收：

```text
确认上游 Apache-2.0 许可证兼容。
确认目标 vendor 路径。
确认是否需要 NOTICE.md 更新。
确认依赖不得直接进入 backend/requirements.txt。
确认后续迁移不再运行时依赖 /home/chuliyang/TradingAgents。
```

### Phase TV1：源码 vendor 迁入仓库

目标：

```text
将 TradingAgents 源码迁入本仓库 third_party/tradingagents，保留许可证和归属文件，不接入业务运行。
```

允许新增：

```text
third_party/tradingagents/
third_party/tradingagents/ATTRIBUTION.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_TV1_IMPORT_EXECUTION_REPORT_CN.md
```

禁止：

```text
不得修改 backend 业务代码
不得修改 frontend
不得修改默认 registry
不得运行 TradingAgents 真实 LLM 调用
不得安装依赖
不得更新 backend/requirements.txt
```

迁移方式：

```text
优先使用 cp -a /home/chuliyang/TradingAgents third_party/tradingagents
然后删除或隔离不应纳入本仓库的本地生成目录，例如 build、*.egg-info、__pycache__、本地 cache、results、.env
保留 README、LICENSE、pyproject.toml、tradingagents 包、必要 tests 和 assets
```

必须检查：

```text
third_party/tradingagents/.env 不得存在
third_party/tradingagents/.git 不得存在
third_party/tradingagents/build 不得存在，除非 Reviewer 明确接受
third_party/tradingagents/tradingagents.egg-info 不得存在
```

验收命令：

```bash
find third_party/tradingagents -maxdepth 2 -type f | sort | head -80
find third_party/tradingagents -name '.env' -o -name '__pycache__' -o -name '*.pyc'
python -m py_compile third_party/tradingagents/tradingagents/default_config.py third_party/tradingagents/tradingagents/graph/trading_graph.py
```

Reviewer 必须确认 vendor import 是源码迁入，不是运行时依赖外部目录。

### Phase TV2：内置源码最小静态验证

目标：

```text
验证 third_party/tradingagents 的关键源码可读、可静态检查，并建立本项目对内置源码的最小 smoke test。
```

建议新增：

```text
backend/tests/test_tradingagents_vendor_static.py
requirements-tradingagents.txt
```

测试必须覆盖：

```text
third_party/tradingagents/LICENSE 存在
third_party/tradingagents/ATTRIBUTION.md 存在
不引用 /home/chuliyang/TradingAgents
关键文件存在：default_config.py、trading_graph.py、schemas.py、reporting.py
blocked trading semantics 已被 adapter/sanitizer 规划，不允许直接暴露 raw decision
```

禁止：

```text
不得 import 需要未安装 LangGraph/LangChain 的真实运行模块，除非依赖已隔离安装并经过审查
不得调用 LLM
不得联网
```

验收命令：

```bash
python -m pytest backend/tests/test_tradingagents_vendor_static.py -q
```

### Phase TA0：合同冻结与现状审计

目标：

```text
在 vendor 源码已迁入或 TV0 已 PASS 的前提下，冻结 TradingAgents 只读接入边界，确认内置源码入口、输出风险和最小 artifact 合同。
```

允许修改：

```text
docs/tw_modular_contracts/TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md
docs/tw_portfolio_decision_model/ 或 docs/tw_modular_contracts/ 下的审计报告
```

禁止修改：

```text
backend/app/routes
backend/app/services
frontend
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
任何 data_tw latest pointer
```

Executor 产物：

```text
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA0_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

Reviewer 产物：

```text
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA0_CONTRACT_AUDIT_REVIEW_CN.md
```

验收：

```text
TA0 不需要跑 TradingAgents，不需要网络，不需要 OpenAI。
TA0 必须确认后续实现不依赖 /home/chuliyang/TradingAgents。
必须列出所有接入风险和 stop condition。
```

### Phase TA1：fixture 驱动 artifact builder

目标：

```text
新增一个离线 builder，使用 fixture 或 mock TradingAgents state 生成 tradingagents_readonly_analysis artifact。
```

建议文件：

```text
scripts/build_tradingagents_readonly_analysis_artifact.py
scripts/validate_tradingagents_readonly_analysis_artifact.py
data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal/
data_tw/golden_samples/tradingagents_readonly_analysis/fail_forbidden_semantics/
backend/tests/test_tradingagents_readonly_analysis_artifact.py
```

禁止：

```text
不得调用 OpenAI
不得调用网络
不得导入并执行真实 TradingAgentsGraph.propagate
不得更新 latest pointer
```

验收命令：

```bash
python scripts/validate_tradingagents_readonly_analysis_artifact.py data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal --json
python scripts/validate_tradingagents_readonly_analysis_artifact.py data_tw/golden_samples/tradingagents_readonly_analysis/fail_forbidden_semantics --json
python -m pytest backend/tests/test_tradingagents_readonly_analysis_artifact.py -q
```

### Phase TA2：TradingAgents runner adapter dry-run

目标：

```text
新增 adapter，能在明确开关下调用本仓库内置 third_party/tradingagents，但默认 dry-run/mock。
```

建议文件：

```text
backend/app/services/tradingagents_readonly_adapter.py
scripts/run_tradingagents_readonly_analysis.py
backend/tests/test_tradingagents_readonly_adapter.py
```

默认行为：

```text
TRADINGAGENTS_READONLY_ENABLE_REAL_RUN=false
```

真实运行必须显式设置：

```text
TRADINGAGENTS_READONLY_ENABLE_REAL_RUN=true
```

并且只能输出到：

```text
data_tw/artifacts/analysis/tradingagents_readonly/{run_id}/
```

Runner 必须设置：

```text
readonly_only=true
selected_analysts 最小化
output_language=Chinese 或 English 后再 sanitizer
checkpoint_enabled=false
results_dir=data_tw/artifacts/analysis/tradingagents_readonly/_raw_runs/{run_id}
data_cache_dir=data_tw/artifacts/analysis/tradingagents_readonly/_cache
memory_log_path=data_tw/artifacts/analysis/tradingagents_readonly/_memory/trading_memory.md
```

Runner 禁止：

```text
sys.path 指向 /home/chuliyang/TradingAgents
读取 /home/chuliyang/TradingAgents
把 ~/.tradingagents 作为默认 cache/memory
```

验收命令：

```bash
python scripts/run_tradingagents_readonly_analysis.py --fixture data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal --dry-run --output-dir /tmp/tradingagents_readonly_smoke
python scripts/validate_tradingagents_readonly_analysis_artifact.py /tmp/tradingagents_readonly_smoke --json
python -m pytest backend/tests/test_tradingagents_readonly_adapter.py -q
```

### Phase TA3：只读 API 接入

目标：

```text
新增 GET-only API 读取已验证 artifact。API 不触发 TradingAgents run。
```

建议路径：

```text
GET /api/tw-stock/tradingagents-readonly-analysis/latest
GET /api/tw-stock/tradingagents-readonly-analysis/<run_id>
```

允许读取：

```text
manifest.json
sanitized_report.json
sanitized_report.md
forbidden_semantics_audit.json
```

禁止：

```text
POST/PUT/PATCH/DELETE
API 内调用 TradingAgents
API 内调用 OpenAI
API 内跑 provider refresh
API 内生成或修改 artifact
```

验收命令：

```bash
python -m pytest backend/tests/test_tradingagents_readonly_analysis_api.py -q
```

### Phase TA4：Agent 上下文可选接入

目标：

```text
将 review-approved sanitized summary 作为 DailyAgentPromptArtifact 的可选来源之一。
```

约束：

```text
只有 validated artifact 且 forbidden_semantics_audit.ok=true 时可进入 Agent prompt context。
Agent 回答仍必须使用现有 guardrails。
不得把 raw TradingAgents report 放入 prompt。
```

建议修改：

```text
scripts/build_tw_agent_daily_prompt_artifact.py
backend/app/services/tw_stock_agent_simple_chat.py
backend/tests/test_tw_stock_agent_daily_prompt_builder.py
backend/tests/test_tw_stock_agent_simple_chat.py
```

验收命令：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_builder.py backend/tests/test_tw_stock_agent_simple_chat.py -q
```

### Phase TA5：前端只读展示

目标：

```text
在 /tw-stock-monitor 增加一个低优先级只读研究摘要区域，展示 sanitized summary。
```

约束：

```text
不得展示 Buy/Sell/Hold
不得展示目标价、仓位、止损
不得新增交易按钮
不得改变现有策略主视觉层级
无 artifact 时静默降级或显示“外部研究摘要暂不可用”
```

验收命令：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
corepack pnpm build
```

如涉及截图验收，再追加 readonly Playwright。

### Phase TA6：受控真实运行实验入口

目标：

```text
在默认关闭和手动确认的前提下，允许 CLI 触发 repo-local TradingAgentsGraph 真实运行实验。
```

必须满足：

```text
TRADINGAGENTS_READONLY_ENABLE_REAL_RUN=true
TRADINGAGENTS_READONLY_REAL_RUN_CONFIRM=manual_real_run_ack
--real-run
```

约束：

```text
只允许 CLI 手动触发
不接日更
不接前端按钮
不更新 latest.json
不切 provider accepted latest 或 qlib accepted latest
runtime results/cache/memory 必须全部在 data_tw/artifacts/analysis/tradingagents_readonly/
真实运行异常必须返回结构化 failed JSON，不得 traceback 作为用户接口
成功输出仍必须经过 sanitizer + validator
只有 validated sanitized artifact 才能进入 GET API / Agent / 前端
```

建议命令：

```bash
TRADINGAGENTS_READONLY_ENABLE_REAL_RUN=true \
TRADINGAGENTS_READONLY_REAL_RUN_CONFIRM=manual_real_run_ack \
PYTHONDONTWRITEBYTECODE=1 \
/home/chuliyang/software/miniconda3/envs/tradingagents/bin/python \
scripts/run_tradingagents_readonly_analysis.py \
  --real-run \
  --symbol 2330.TW \
  --trade-date 2026-06-30 \
  --run-id ta6_2330_20260630_market_smoke \
  --output-dir data_tw/artifacts/analysis/tradingagents_readonly/ta6_2330_20260630_market_smoke \
  --selected-analysts market \
  --llm-base-url https://chat.pku.edu.cn/v1 \
  --deep-model gpt-5.5 \
  --quick-model gpt-5.4-mini \
  --json
```

验收命令：

```bash
python -m pytest backend/tests/test_tradingagents_readonly_adapter.py backend/tests/test_tradingagents_readonly_analysis_artifact.py backend/tests/test_tradingagents_readonly_analysis_api.py backend/tests/test_tradingagents_vendor_static.py -q
find third_party/tradingagents -name '.git' -o -name '.env' -o -name '__pycache__' -o -name '*.pyc' -o -name 'build' -o -name 'tradingagents.egg-info'
```

### Phase TA7：端到端只读回归与关闭

目标：

```text
验证 artifact builder -> validator -> GET-only API -> Agent optional context -> frontend readonly display 全链路。
```

必须审计：

```text
没有默认模型/策略变化
没有 latest accepted switch
没有 provider publish
没有 broker/order/quick-trade
没有 POST/PUT/PATCH/DELETE trading endpoint
没有 forbidden semantics 泄露
```

产物：

```text
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA7_FINAL_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA7_FINAL_ACCEPTANCE_REVIEW_CN.md
```

## 10. Executor 通用要求

每个阶段 Executor 必须：

```text
只执行当前阶段
先读本主线文档
先读阶段要求中的合同和测试
不做未授权架构变更
不修改产品默认 registry
不触发真实数据刷新
不触发真实 TradingAgents run，除非阶段明确允许且开关显式启用
不引用 /home/chuliyang/TradingAgents，除非 TV1 源码迁移阶段用于一次性复制来源
写 Execution Report
```

Execution Report 模板：

```markdown
# Execution Report

## 1. Scope
- Assigned phase:
- Mainline document:
- Non-goals confirmed:

## 2. Documents / Contracts / Skills Read

## 3. Changes Made

## 4. Evidence Produced
- Artifacts:
- Logs:
- Validator/test output:

## 5. Compliance With Mainline

## 6. Forbidden Actions Audit

## 7. Issues / Blockers / Deviations

## 8. Files Changed

## 9. Recommendation For Reviewer
```

## 11. Reviewer 通用要求

每个阶段 Reviewer 必须：

```text
读本主线文档
读 Executor report
检查 diff、artifact、validator/test output
检查是否越权修改默认模型/策略/API/前端
检查是否仍存在运行时外部目录依赖
检查 forbidden semantics audit
给出 PASS / PASS_WITH_CONDITIONS / FAIL_NEEDS_REPAIR / STOP
写下一阶段或修复阶段 work document
```

Reviewer Output 模板：

```markdown
# Review Opinion And Next Work Document

## 1. Verdict
PASS / PASS_WITH_CONDITIONS / FAIL_NEEDS_REPAIR / STOP

## 2. Findings
### Critical
### High
### Medium
### Low

## 3. Mainline Compliance

## 4. Evidence Checked

## 5. Missing Evidence Or Open Questions

## 6. Forbidden Actions Audit

## 7. Next Work Document

## 8. Command For Executor Or Coordinator
```

## 12. Stop Conditions

任何角色遇到以下情况必须停止：

```text
需要新增生产默认模型或策略
需要改变 current-strategy-context 核心字段语义
需要把 TradingAgents 输出转成 OrderIntentArtifact
需要真实下单、broker、quick-trade
需要 provider publish / refresh
需要 accepted latest switch
需要读取或提交真实密钥
validator 缺失且无法在当前阶段补齐
sanitizer 无法确定安全
LLM 输出含 forbidden semantics 且无法确定性删除
依赖安装会破坏现有 backend 环境
迁移后仍需运行时依赖 /home/chuliyang/TradingAgents
缺少上游 LICENSE 或 attribution
```

## 13. 依赖隔离要求

TradingAgents 依赖较重。源码可以 vendor 进仓库，但依赖不得直接无审查合并进 `backend/requirements.txt`。

优先顺序：

```text
1. third_party/tradingagents 源码进入仓库。
2. adapter 默认 mock/dry-run，不要求安装 LangGraph/LangChain。
3. 若必须 import repo-local tradingagents，先使用 requirements-tradingagents.txt 在隔离环境验证。
4. 若必须加入 backend requirements，必须单独开依赖升级阶段并跑 backend 全量相关测试。
```

TV1、TV2、TA1 和 TA2 dry-run 阶段不得要求安装新依赖。

## 14. 安全与文案规则

所有用户可见文案必须使用以下语义：

允许：

```text
外部多智能体研究摘要
利多论点
利空论点
风险复盘点
数据限制
人工复盘问题
仅供研究观察
```

禁止：

```text
买入
卖出
应买
应卖
目标价
止损价
仓位
配置比例
胜率
保证收益
交易建议
订单
```

如果必须引用 TradingAgents 原始 rating，只允许在审查报告中出现，并标注：

```text
raw_untrusted_not_user_visible
```

## 15. 首个 Executor 指令

请执行 Phase TV0。

要求：

```text
1. 阅读本主线文档和第 4 节必读文件。
2. 只做 vendor 迁移可行性、许可证和依赖审计，不复制源码，不写业务代码。
3. 不运行 TradingAgents，不调用 OpenAI，不联网。
4. 输出 docs/tw_portfolio_decision_model/TRADINGAGENTS_VENDOR_TV0_FEASIBILITY_EXECUTION_REPORT_CN.md。
5. 报告必须包含：许可证兼容性、上游归属保留方案、目标 vendor 路径、依赖隔离方案、TV1 准入条件、stop conditions。
```

## 16. 首个 Reviewer 审查 brief

请审查 TV0 Executor report。

审查重点：

```text
1. 是否遵守本主线的非目标和禁止项。
2. 是否确认 Apache-2.0 迁移兼容并保留上游归属。
3. 是否明确 vendor 目标路径和不再运行时依赖 /home/chuliyang/TradingAgents。
4. 是否没有要求直接改默认模型/策略/前端/API。
5. 是否明确依赖隔离，不直接修改 backend/requirements.txt。
6. 是否给出 TV1 可执行 work document。
7. 如果缺少许可证、归属或依赖隔离方案，判定 FAIL_NEEDS_REPAIR。
```

## 17. 关闭标准

本主线只有在以下条件全部满足时才能关闭：

```text
TV0-TV2 和 TA0-TA6 均 PASS 或被 Coordinator 明确接受 PASS_WITH_CONDITIONS
third_party/tradingagents 源码已在本仓库内，且有 LICENSE / ATTRIBUTION
运行时不依赖 /home/chuliyang/TradingAgents
所有可展示输出均来自 sanitized_report
forbidden_semantics_audit.ok=true
validator 支持 pass/fail golden samples
GET-only API 不触发生成或外部调用
Agent 和前端均不展示 raw TradingAgents 决策语义
未修改产品默认模型、默认策略和 accepted latest
最终审查报告确认没有 broker/order/quick-trade/provider publish 行为
```
