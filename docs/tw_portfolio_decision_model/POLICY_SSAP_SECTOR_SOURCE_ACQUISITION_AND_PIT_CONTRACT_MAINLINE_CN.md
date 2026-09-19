---
created_at: 2026-08-21
status: coordinator_mainline
route: SECTOR_SOURCE_ACQUISITION_AND_PIT_CONTRACT
route_id: SSAP
current_phase: SSAP0_CONTRACT_AND_SOURCE_CANDIDATE_PREFLIGHT
readonly_research_only: true
isolated_candidate_write_allowed: true
production_allowed: false
provider_publish_allowed: false
latest_switch_allowed: false
strategy_or_replay_allowed: false
broker_authorized: false
---

# SSAP 产业分类来源获取与 PIT 合同主线

## 1. 目标

为台股标准信号建立一个可审计、可版本化、可校验 checksum、具明确 taxonomy 与时间可用性的产业分类 `DataSource` 候选，并判断它能否支持未来 `ModelSignalArtifact` 的 `ext_sector_code` extension。

本路线解决 MSTR1 的输入 blocker，不续写 MSTR2，也不验证策略收益。最终允许的最好结果是：形成通过独立审查的隔离 DataSource/extension candidate 和 MSTR re-entry 建议；任何生产、日更或策略接入仍需另行授权。

## 2. 非目标

- 不实现 sector-aware StrategyRule；
- 不生成 OrderIntentArtifact、ReplayResultArtifact 或收益结论；
- 不训练、重训、调参或重算模型分数；
- 不修改 formal provider、qlib provider、accepted/legacy/latest 指针；
- 不修改 daily auto、cron、前后端、Agent 或默认策略；
- 不连接 broker、quick-trade、monitor/order/target；
- 不使用股票代码 bucket、模型推断行业或非权威网页文本代替 taxonomy；
- 不把当前分类静态回填到历史并声称 PIT-safe。

## 3. 当前事实

1. MSTR1 已正式停止：本地不存在合格的历史产业分类 lineage。
2. 现有 `sector_smoke_*` 由股票代码前两位生成，只能验证 schema，不是真实分类。
3. primary qlib 信号覆盖 `2023-01-03..2026-05-07`、802 日、150 symbols，但没有 sector extension。
4. 现有 LTR artifact 只有 Top50 行，不可独立承担 rank-buffer-100 的 full-rank holding lookup。
5. `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` 当前允许的 semantic role 是 `sector` 或 `industry`；未来字段名可为 `ext_sector_code`，但 `semantic_role` 必须使用 `sector`，除非先修订合同。
6. 现有 TWSE 月营收访问诊断不能提供产业 taxonomy，也不能证明历史分类可得性。

## 4. 必读合同与前序结论

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/templates/NEW_DATA_SOURCE_WORK_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MSTR1_SECTOR_DIVERSIFIED_BUY_ADMISSION_INPUT_READINESS_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MSTR_ROUTE_CLOSURE_AFTER_MSTR1_SECTOR_LINEAGE_STOP_CN.md`

## 5. 来源优先级

必须按以下顺序评估，不得因访问方便跳级：

1. TWSE/TPEx/MOPS 官方 OpenAPI、官方下载或官方历史档案；
2. 可验证由官方资料派生、具版本/许可/有效期说明的公开静态档案；
3. 只有用户另行批准时，才评估付费、需凭证或第三方来源。

SSAP 默认不授权第 3 类来源。若第 1/2 类无法满足历史 PIT，路线必须说明“仅可从当前日期向前积累”或停止，不得静默降级。

## 6. 时间语义

产业分类候选至少包含：

```text
instrument
sector_code
sector_name
taxonomy_name
taxonomy_version
effective_from
effective_to
source_asof
available_at
source_artifact
source_sha256
```

硬规则：

- `available_at <= signal_asof` 才能用于对应决策日；
- effective period 与 available period 必须分开；
- 若来源没有历史 effective dating，只能使用实际首次采集日作为 `available_at/effective_from` 的保守下界；
- 当前快照不得回填到快照日前的信号；
- 分类修订、转板、合并、更名和 symbol 变化必须版本化；
- missing/unknown/conflict/duplicate 在策略消费前必须 hard fail；
- 决策相关 signal 与 holding coverage 必须为 100%。

## 7. 隔离架构

允许的候选数据流：

```text
official source probe
  -> isolated raw response + request/response metadata
  -> normalized sector source candidate
  -> PIT/symbol/taxonomy/coverage audits
  -> DataSource candidate manifest
  -> isolated ModelSignal extension dry-run candidate
```

允许写入仅限：

```text
data_tw/experiments/sector_source_acquisition_and_pit_contract/
docs/tw_portfolio_decision_model/POLICY_SSAP*.md
后续工作单明确列出的独立 builder/validator（不得在 SSAP0 创建）
```

禁止写入 canonical `data_tw/artifacts/signals/`、formal provider、latest、registry、策略 dependency、产品配置和日更路径。

## 8. 阶段计划

| phase | 目标 | 允许输出 | 放行条件 |
| --- | --- | --- | --- |
| SSAP0 | 冻结来源、schema、PIT、许可、范围和停止条件 | 文档盘点与唯一 SSAP1 方案 | 官方候选明确；无静态历史回填 |
| SSAP1 | 官方端点/下载访问与字段预检 | 隔离 probe metadata/raw excerpt、字段矩阵 | 可访问；字段含 symbol+sector；来源/许可可说明 |
| SSAP2 | 受控当前快照候选采集 | 原始响应、checksum、request manifest | TWSE/TPEx universe 可追溯；不写生产 |
| SSAP3 | 历史 PIT/effective-dating 路径 | 历史可得性审计、crosswalk 设计或 stop | 有合法历史路径，或明确 forward-only |
| SSAP4 | 标准 DataSource 候选 | normalized mapping、manifest、schema/PIT/coverage audits | taxonomy/version/PIT/coverage hard gates 通过 |
| SSAP5 | extension adapter dry-run no signal write | isolated extension candidate、validator/golden sample | core signal 不变；semantic role=`sector`; 100% coverage |
| SSAP6 | 收口与 MSTR re-entry 判断 | closure review | 不自动创建 MSTR2；不生产化 |

每阶段由执行者写执行报告，独立审查者写 review 和下一工作单。预期 blocker 应走 STOP/forward-only classification，不得用数据修饰绕过。

## 9. SSAP0 必须回答

1. 哪些官方 endpoint/download 可能包含上市、上柜公司的产业代码和名称？
2. 是否存在官方历史快照、有效期或可复建的发布日期？
3. 分类体系是 TWSE/TPEx 各自 taxonomy，还是可映射到统一 taxonomy？
4. ETF、DR、金融、KY、转板和下市 symbol 如何处理？
5. 当前 150-symbol universe 中上市/上柜覆盖预期如何；是否需要双源？
6. 数据使用说明、访问条款和缓存/归档边界是什么？
7. 若只能获得 current snapshot，路线是 forward-only accumulation 还是 STOP historical research？

## 10. 审计与验证要求

候选必须提供：

- request URL/parameters/status/content type/fetched_at/checksum；
- source authority/provenance/access note；
- raw 与 normalized schema；
- taxonomy/version/code-name consistency；
- TWxxxx symbol crosswalk；
- effective/available/PIT audit；
- duplicate/conflict/missing/unknown audit；
- primary qlib 150-symbol 决策覆盖；
- forbidden fields/actions audit；
- no-provider/no-latest/no-strategy/no-replay 声明。

## 11. 停止条件

- 官方来源不含稳定 sector code/name；
- 只能通过浏览器人工交互、验证码、绕过访问控制或违反条款获得；
- 需要付费、凭证或第三方来源但用户未批准；
- 无法区分 current snapshot 与历史有效期；
- 覆盖无法达到未来决策相关 100%，且没有明确 hard-fail policy；
- taxonomy 冲突无法版本化解决；
- 任何实现要求修改 provider/latest/daily/default/strategy/replay。

## 12. 关闭标准

SSAP 只有在 SSAP0-SSAP6 的实际执行阶段均有独立审查、DataSource candidate 可复现、PIT 语义无歧义、forbidden audit clean 后才能以 READY_FOR_MSTR_REENTRY 关闭。若只能 forward-only，则必须以 `FORWARD_ONLY_ACCUMULATION_NOT_HISTORICAL_REPLAY_READY` 收口。

## 13. SSAP0 执行命令

只读盘点仓库和既有资料，冻结官方来源候选、schema/PIT/access 合同与 SSAP1 probe 计划；只写 SSAP0 执行报告，不访问网络、不采集数据、不写 builder/artifact。

## 14. SSAP0 审查任务

独立检查来源优先级、endpoint 候选依据、历史 PIT 分类、许可边界、双市场覆盖和下一阶段 probe 是否足够窄。通过后写 SSAP1 工作单；不得提前授权第三方、付费、绕过访问控制或生产写入。
