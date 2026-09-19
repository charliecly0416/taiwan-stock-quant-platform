# DNG5 RouteDataDependencyContract 审查报告

生成日期：2026-06-29

## 1. 结论

审查结论：`PASS_WITH_CONDITIONS_GO_DNG6`

DNG5 已建立可执行的路线数据依赖合同模板、validator、三份示例合同和 validation catalog。审查复跑确认：

- 模板字段覆盖数据层、日期范围、字段、latest 概念、fallback、forbidden paths/actions、expected outputs 与 readiness gate。
- validator 能阻断 required dependency missing，并且不会把 required stale / missing / gate mismatch 误判为 `gate_pass=true`。
- `qlib_ltr_model_b_20260625` 被正确判定为 `BLOCK`，未误通过为 full LTR ready。
- `strategy_input_bundle_20260625` 被正确判定为 `PARTIAL` 且 `gate_pass=false`，只能作为 input-bundle contract evidence，不能进入 replay/performance。
- 本轮审查未触发真实抓数、provider publish/refresh、latest switch、训练、推理、score、回放、下单或 target weight/position 写入。

进入 DNG6 的条件：DNG6 只能做 daily auto catalog / readiness / dashboard integration，不得把 DNG5 的 partial 或 block 结果解释为 qlib accepted latest、Model B LTR、ReplayResult、readonly publish、Agent prompt publish 或生产就绪。

## 2. 审查输入

已按要求阅读：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_WORK_CN.md`
- `docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md`
- `scripts/validate_tw_route_data_dependency.py`
- `data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml`
- `data_tw/catalog/route_dependency_contract_examples/qlib_ltr_model_b_20260625.yaml`
- `data_tw/catalog/route_dependency_contract_examples/strategy_input_bundle_20260625.yaml`
- `data_tw/catalog/dng5_route_dependency_validation.json`

## 3. 模板审查

模板合格。`ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md` 明确要求：

- 顶层字段：`contract_version`、`route_id`、`route_type`、`asof`、`owner`、`required_data_layers`、`required_date_range`、`required_universe`、`required_fields`、`required_latest_concepts`、`dependencies`、`optional_dependencies`、`allowed_fallbacks`、`forbidden_private_paths`、`forbidden_actions`、`expected_outputs`、`readiness_gate`。
- dependency 字段：`dependency_name`、`required`、`layer`、`dataset_id`、`artifact_path`、`latest_concept`、`required_fields`、`date_min`、`date_max`、`coverage_requirement`、`pit_required`、`available_at_required`、`fallback_allowed`、`fallback_policy`、`blocker_if_missing`。
- `required=true` 且 artifact missing 时不得输出 `gate_pass=true`。
- fallback 必须声明 `allowed_when`、`impact_on_claim`、`reviewer_approval_required`，并限制可声称内容。
- forbidden actions 覆盖抓数、publish/latest switch、训练、推理、score、回放、ReplayResult/NAV、交易与 target position/weight。

模板足够支持 DNG6 前置 route dependency gate，但仍应保持为 gate 合同，不应扩展解释为生产发布授权。

## 4. Validator 审查

validator 合格。代码检查到以下关键行为：

- 必填顶层字段和 dependency 字段缺失会进入 `schema_errors`。
- `required_latest_concepts` 和 dependency `latest_concept` 必须存在于 `latest_status.latest_by_concept`。
- dependency artifact path 会解析到本地文件；required 且缺失时进入 `gate_blockers` 或 partial，但无论哪种都不会 `gate_pass=true`。
- required dependency 的 latest asof 早于 contract asof，且无 fallback 时进入 blocker。
- `forbidden_private_paths` 命中会 blocker。
- `forbidden_actions` 缺少 DNG5 必禁动作会 schema fail；`expected_outputs` 包含禁行动作会 blocker。
- `readiness_gate.required_gate_checks` 支持 JSON pointer 检查，mismatch 可 blocker 或 partial。
- 输出区分 `validation_ok`、`gate_result`、`gate_pass`，避免把 schema ok 或 partial 当作 gate pass。

审查还做了一个 `/tmp` 临时负例：把 required dependency 的 `artifact_path` 指向不存在路径，并使用 `--no-write-catalog` 运行 validator。结果包含 `artifact_path missing` blocker，`gate_result=BLOCK`，`gate_pass=false`。这验证 required missing 可被阻断。

## 5. 复跑结果

执行的只读/静态命令：

```bash
python -m py_compile scripts/validate_tw_route_data_dependency.py
python scripts/validate_tw_route_data_dependency.py --contract data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
python scripts/validate_tw_route_data_dependency.py --contract data_tw/catalog/route_dependency_contract_examples/qlib_ltr_model_b_20260625.yaml --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
python scripts/validate_tw_route_data_dependency.py --contract data_tw/catalog/route_dependency_contract_examples/strategy_input_bundle_20260625.yaml --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
```

结果：

| route_id | gate_result | gate_pass | 审查判断 |
| --- | --- | --- | --- |
| `qlib_only_model_score_20260625` | `PARTIAL` | `false` | 合理。qlib-only 路线可报告 partial readiness，但 qlib accepted/model signal latest 仍 stale，不得声称 2026-06-25 ModelSignalArtifact 已生成。 |
| `qlib_ltr_model_b_20260625` | `BLOCK` | `false` | 合理。`model_signal_latest` 为 2026-06-17，且 DNG3 `/can_continue_to_model_b_ltr=false`，full LTR 未误通过。 |
| `strategy_input_bundle_20260625` | `PARTIAL` | `false` | 合理。DNG4 bundle status 为 `PARTIAL_READY`，只允许作为 input-bundle contract evidence，不允许 replay/performance。 |

`data_tw/catalog/dng5_route_dependency_validation.json` 汇总为 3 条 route、0 pass、2 partial、1 block，`all_gate_pass=false`，符合预期。

## 6. 重点问题核查

模板是否足够：通过。字段覆盖 DNG5 工作文档要求，并明确 latest 不可跨层推断、fallback 后 claim 受限。

required missing 是否阻断：通过。代码路径和临时负例均确认 required missing 不会 `gate_pass=true`。

`qlib_ltr_model_b` 是否被 BLOCK：通过。validator 复跑结果为 `BLOCK`，blocker 包括 `model_signal_latest` stale 以及 DNG3 `can_continue_to_model_b_ltr=false`。

strategy bundle 是否 partial 且不能 replay：通过。validator 复跑结果为 `PARTIAL/gate_pass=false`；DNG4 validation 明确 `status=PARTIAL_READY`，replay input bundle 的 `empty_order_intents.csv` 为 placeholder，`not_replay_result=true`，replay execution remains blocked。

forbidden action 是否触发：未触发。DNG5 validation catalog、DNG3 readiness、DNG4 input bundle validation 中 forbidden action flags 均为 false；本轮审查只运行 py_compile、validator 和 `/tmp` 临时负例。

## 7. 条件与边界

DNG6 可以开始，但必须满足以下边界：

- 只做 daily auto catalog integration、readiness matrix integration、latest status dashboard / report integration。
- 不得执行真实抓数、provider refresh/publish、qlib accepted latest switch、readonly latest publish、Agent prompt latest publish。
- 不得执行模型训练、模型推理、模型 score 生成、策略收益回放、ReplayResult/NAV 生成。
- 不得把 `validation_ok=true`、`ok=true`、`PARTIAL_READY` 或 `gate_result=PARTIAL` 解读为 `gate_pass=true`。
- Model B LTR 仍以 DNG3 `can_continue_to_model_b_ltr=false` 为 blocker，直到后续授权 repair 和重新审查。
- StrategyInputBundle partial 只能用于合同/依赖证据，不能进入 replay、performance、order intent 或 target weights。

## 8. 下一步

建议进入 DNG6 daily auto catalog integration。DNG6 的验收重点应是：日更脚本能自动产出/更新 DataCatalog、latest_status、readiness matrix、RouteDataDependencyContract validation catalog，并在任何 required dependency missing、latest stale、forbidden action 或 gate mismatch 时停止下游路线。
