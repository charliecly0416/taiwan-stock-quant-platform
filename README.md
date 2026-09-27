# Taiwan Stock Clean Research Product

这是原项目的无历史包袱分支。产品边界只有：完整数据采集、两个平等模型轨道、一个策略、动态回放、只读 API 和一个前端研究台。

## 核心设计

- `configs/product.yaml`：唯一产品配置。模型差异由阶段列表表达，不写进日更编排器。
- `clean_product/data.py`：统一数据目录。每个 dataset 通过配置选择 source、endpoint 和字段，抓取、标准化、存储、查询沿用同一流程；只有新供应商协议才需要新增并注册 adapter。
- `clean_product/models.py`：统一模型阶段执行器。Model A 为 `[model_a_score]`，Model A+B 为 `[model_a_score, model_b_rerank]`。
- `clean_product/orchestrator.py`：唯一日更主线，永远抓配置中的完整数据并遍历所有模型。
- `clean_product/replay.py`：相同模型管线在历史日期循环运行。
- `backend/app/`：只读 API。
- `frontend/src/`：模型比较与动态回放界面。

## 运行

```bash
python -m pip install -r backend/requirements.txt
python scripts/run_product.py daily --asof 2026-09-25 --dry-run
cd backend && python run.py
cd frontend && corepack pnpm install && corepack pnpm build
```

实时数据采集需要环境变量 `FINMIND_TOKEN`。产品不包含实盘、券商、订单、支付、加密货币或历史实验路线。

## 新增数据

同一数据源的新数据只需在 `configs/product.yaml` 的 `datasets` 中增加配置：定义接口、字段、必填字段和数值字段。`DataCatalog` 会统一产生 CSV 和 manifest，模型通过 `query()` 读取标准化结果。不要在 `orchestrator.py` 为某个数据集增加条件分支；只有接入新供应商时才新增一个 source adapter。
