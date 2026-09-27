# 数据模块地图与统一接口说明

## 1. 这份文档解决什么问题

项目里的“数据处理”不是一个把抓取、加工、查询和 API 返回全部包起来的巨大类，而是三个职责边界：

```text
Data Acquisition       抓取或读取来源
        |
        v
Data Artifacts         标准化、PIT 特征、PriceStore 和审计证据
        |
        v
Data Access / Serving  查询已验证 artifact，并转换成 API DTO
```

这样拆分是为了保证：

- 查询不会因为用户打开页面而触发抓取。
- 抓取失败不会直接覆盖当前可用的 latest。
- 模型只消费特征或标准输入，不读取 provider 私有目录。
- API 只返回已经通过身份、日期、checksum 和 readonly 边界校验的数据。

当前没有一个把所有实现揉成大类的 `DataService`。仓库新增了一个很薄的 `tw_stock_workflow.data_pipeline.DataPipeline` facade：它只负责按顺序调用抓取、标准化、存储三个注入阶段，并传播 `READY/BLOCKED/FAILED/PENDING` 状态；真实 provider、脚本和 latest gate 仍由现有实现负责。这样既有一个统一入口，又不会把数据源、校验规则和存储实现耦合在一起。

## 2. 三个边界和当前代码

| 边界 | 当前真实入口 | 标准输入 | 标准输出 | 允许的副作用 |
| --- | --- | --- | --- | --- |
| Acquisition | `scripts/run_daily_tw_stock_auto_update.py`；provider/data-source 实现如 `backend/app/data_sources/tw_stock.py` | `asof`、scope、symbol universe、provider 配置 | 原始来源记录、抓取状态、`source_name/asof/available_at/run_id` | 可以请求 provider、写隔离运行证据；不能直接切 accepted latest |
| Artifact production | 日更标准化阶段、qlib/feature 生成脚本；合同见 `DATA_INGESTION_ARTIFACT_CONTRACT_CN.md`、`FEATURE_ARTIFACT_CONTRACT_CN.md`、`PRICE_STORE_CONTRACT_CN.md` | 原始来源、映射、价格、可得时间 | normalized data、FeatureArtifact、PriceStore、manifest、audit、checksum | 可以写新的隔离 artifact；不能把失败结果发布成产品 latest |
| Access / Serving | `tw_stock_workflow/artifacts.py` 的 `ArtifactResolver` 和 adapters；`tw_stock_workflow/readonly_snapshot.py`、`replay.py`；backend readonly services/routes | artifact identity、`asof`、查询过滤条件 | `ArtifactRef`、snapshot/replay DTO、API JSON | 只读；不能抓 provider、训练、重算并覆盖产品结果 |

数据层的轻量组合入口是 `tw_stock_workflow/data_pipeline.py`。它接收 `DataPipelineRequest`，依次调用已有的 acquisition、normalization、storage 实现；目前日更仍由现有 orchestrator 负责调用，未改变 cron、provider/latest 或 Model A 行为。

`configs/tw_modular_registry.yaml` 中的 `data_source` 和 `data_ingestion` 条目是合同与能力登记；部分 M2 条目仍是 `CONTRACT`，不能仅凭 registry entry 说它们已经替代日更 runtime。当前真实产品链的状态仍以日更证据、latest manifest、validator 和 `/api/ready` 为准。

## 3. 统一接口（合同级）

### 3.1 Acquisition 接口

调用方提供一个业务请求，不能传任意 shell 命令或脚本路径：

```yaml
asof: "2026-09-18"
scope: daily
symbols: ["2330", "2317"]
source_profile: tw-stock-default
decision_cutoff: "2026-09-18T08:30:00+08:00"
```

概念输出如下：

```yaml
schema_version: tw.data.source.run.v1
run_id: source_20260918_...
status: READY            # 或 PENDING / BLOCKED / FAILED
source_name: tw-stock
provider: finmind
asof: "2026-09-18"
available_at: "2026-09-18T18:10:00+08:00"
raw_artifacts: [...]     # 只引用隔离运行目录
coverage_audit: {...}
schema_audit: {...}
no_provider_publish: true
no_accepted_latest_switch: true
```

当前日更由现有 orchestrator 负责重试、pending 和 publish gate。这个接口说明的是数据边界，不要求现在把整个日更脚本重写成一个新 adapter。

调用方如果需要组合三个阶段，可以使用下面这个薄 facade；阶段实现仍然来自现有脚本或 provider adapter：

```python
from tw_stock_workflow.data_pipeline import DataPipeline, DataPipelineRequest

pipeline = DataPipeline(
    acquire=existing_acquisition_adapter,
    normalize=existing_normalization_adapter,
    store=existing_qlib_provider_writer,
)
result = pipeline.run(DataPipelineRequest(asof="2026-09-18", scope="daily"))
```

`result.stages` 保存三个阶段的 manifest/status，遇到 `BLOCKED`、`FAILED` 或 `PENDING` 会停止下游调用并保留已完成阶段；它本身不发请求、不写 latest，也不替代当前日更 executor。

### 3.2 Artifact production 接口

标准化阶段把来源记录变成可被下游引用的 artifact：

```text
DataSource run
  -> DataIngestionArtifact
  -> FeatureArtifact / PriceStore
```

每个 artifact 至少要能回答：

```yaml
artifact_type: feature_artifact
schema_version: ...
run_id: ...
asof: "2026-09-18"
available_at: "2026-09-18T18:10:00+08:00"
source_artifacts: [...]
output_path: ...
manifest_sha256: ...
pit_policy: ...
validation_status: PASS
```

下游只拿 manifest 和公开字段，不读取上游私有 CSV 的未声明列。FeatureArtifact 不能含未来收益或标签；PriceStore 必须声明 `next_day_execution_availability`，否则不能用于 `next_open` 回放。

### 3.3 Access / Serving 接口

工作流内部通过 `ArtifactResolver.query(...)` 查询标准引用，查询条件只能是已声明的身份过滤：

```python
refs = resolver.query(
    artifact_type="model_signal",
    model_id="e4_frozen_qlib_2018_2022",
    asof="2026-09-18",
    status="accepted",
)
```

返回的是经过校验的 `ArtifactRef`，不是任意文件路径：

```text
adapter_id
artifact_type
model_id
asof
status
run_id
path
manifest_path
manifest_sha256
metadata
```

backend service 再把这些 artifact 转成 API DTO。例如：

```text
GET /api/tw-stock/current-strategy-context
  -> backend/app/services/tw_stock_current_strategy_context.py
  -> 已验证 Model A signal / snapshot
  -> JSON DTO
```

前端只消费 DTO，不读取 `data_tw/`、qlib 目录或 provider 原始文件。

## 4. 一天数据的完整流转示例

以 2026-09-18 为例：

```text
1. run_tw_task.py
   -> daily_update request
2. run_daily_tw_stock_auto_update.py
   -> 读取目标日期、scope、model tracks 和 runtime gate
3. provider/data source
   -> 获取 FinMind 或已授权的隔离来源
   -> 记录 source run、available_at、覆盖率和失败 symbol
4. normalized / feature / price stages
   -> 生成标准化输入、PIT 特征、PriceStore 和 manifest
5. Model A track
   -> 读取已验证输入，输出 ModelSignalArtifact
6. strategy / snapshot
   -> 生成策略摘要和 readonly snapshot
7. backend readonly service
   -> 校验日期、身份、checksum，转换为 API DTO
8. frontend workbench
   -> 展示候选、回放和模型比较
```

任何一步失败时，当前产品遵守以下规则：

- Acquisition 失败：目标日期进入 pending，previous latest 保持不变。
- Artifact validator 失败：隔离产物可以保留作证据，但不能进入产品 latest。
- Model B 失败：记录为 nonblocking shadow 失败，不污染 Model A。
- Access 校验失败：API 返回明确错误或 stale 状态，不绕过校验直接读文件。

## 5. 新增数据源或查询功能时怎么做

### 新增数据源

1. 先写 `DataSource` 合同和来源字段映射。
2. 声明 `asof`、`available_at`、symbol mapping、coverage 和 license/access note。
3. 只写隔离的 source/normalized artifact。
4. 为成功和失败各提供 validator/golden sample。
5. 确认它的 consumer 是 Feature 或 PriceStore，而不是策略或前端。
6. 只有通过日更 gate 和明确授权，才考虑接入产品链；不能自行切 latest。

### 新增查询或 API

1. 先确定要查询的 artifact 类型和身份字段。
2. 在 resolver/adaptor 或已有 readonly service 中实现查询。
3. 查询只返回通过 checksum、日期和 readonly 校验的 DTO。
4. backend route 只负责参数校验和响应，不自己抓数据或读取实验目录。
5. 增加 GET-only 测试，并确认失败不会清空 Model A 主内容。

不要为每个新 provider 或每个页面再写一套“抓取后直接返回 JSON”的脚本；先接入上述边界和合同。

## 6. 代码导航

| 想看什么 | 文件 |
| --- | --- |
| 日更编排、抓取时机和 gate | `scripts/run_daily_tw_stock_auto_update.py`、`scripts/tw_daily_runtime_stages.py` |
| FinMind/TW 股票 data source | `backend/app/data_sources/tw_stock.py` |
| DataSource/DataIngestion 合同 | `docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md`、`DATA_INGESTION_ARTIFACT_CONTRACT_CN.md` |
| Feature/PriceStore 合同 | `FEATURE_ARTIFACT_CONTRACT_CN.md`、`PRICE_STORE_CONTRACT_CN.md` |
| artifact 查询和身份校验 | `tw_stock_workflow/artifacts.py` |
| snapshot/replay 查询 | `tw_stock_workflow/readonly_snapshot.py`、`tw_stock_workflow/replay.py` |
| 当前策略 API | `backend/app/services/tw_stock_current_strategy_context.py` |
| readonly snapshot/replay API | `backend/app/services/readonly_strategy_snapshot.py`、`readonly_replay_window.py` |
| API 路由 | `backend/app/routes/tw_stock_context_routes.py`、`readonly_strategy_snapshot.py`、`readonly_replay_window.py` |
| 模块能力和 consumer | `configs/tw_modular_registry.yaml` |

这份地图的目的，是让新开发者先知道“数据属于哪个边界”，再去读具体实现；它不改变当前 baseline、日更 Cron、provider/latest 或 Model B 的治理状态。
