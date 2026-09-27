# 清洁版架构

```text
configs/product.yaml
        |
        v
DataCatalog.acquire_all()  完整数据集，统一抓取/标准化/存储
        |
        v
ModelRunner.run()          每个模型都是阶段列表，baseline/shadow 仅是角色
        |
        v
top50_exit_one_worst_sell  唯一策略
        |
        +--> replay()      历史日期循环同一条模型管线
        +--> Flask API     只读查询与动态回放
        +--> Frontend      模型选择、参数选择、结果展示
```

新增数据：在 `configs/product.yaml.datasets` 注册数据集的 source、endpoint、字段、必填字段和数值字段。`DataCatalog` 会统一执行
`fetch -> normalize -> store -> query`，日更主线不需要增加任何数据分支。只有接入一个全新的供应商协议时，才在
`clean_product/data.py` 增加一个 `SourceAdapter` 并注册名称；同一供应商下的后续数据集只改 YAML。

例如新增估值数据只需要：

```yaml
datasets:
  valuation:
    source: finmind
    endpoint: TaiwanStockPER
    date_field: date
    fields: [stock_id, date, PER]
    required: [stock_id, date, PER]
    numeric: [PER]
```

标准化会补齐字段、统一日期和股票代码、转换数值列、去重排序；存储会写入
`data_root/<dataset>.csv` 和同名 manifest，查询仍走同一个 `DataCatalog.query()`。

新增模型：注册新的 stage adapter，并在 `configs/product.yaml.models` 写阶段列表；不改日更主线。
