# 清洁版接手指南

这是 `product-clean` 分支的最短接手路径。产品是台股只读研究工具，带 simulation-only 的回放展示，不连接实盘、券商或订单系统。

## 先看什么

1. `README.md`：运行方式和产品边界。
2. `docs/ARCHITECTURE_CN.md`：模块关系和扩展方式。
3. `configs/product.yaml`：数据集、模型角色、策略和路径。
4. `clean_product/data.py`：数据源 adapter、标准化、存储和查询。
5. `clean_product/models.py`：统一模型 stage 执行器。
6. `clean_product/orchestrator.py`：日更唯一编排入口。

## 一条数据流

`product.yaml` 注册数据集 -> `DataCatalog.acquire_all()` 获取并标准化 -> `data_root/<dataset>.csv` 和 manifest -> `ModelRunner.run()` 读取价格 -> 策略输出 -> replay/API/frontend 只读展示。

新增同一供应商的数据只改 `datasets` 配置；只有接入新供应商时才在 `clean_product/data.py` 注册一个 source adapter。新增模型只增加 stage adapter 和模型配置，不修改日更编排器。

## 验证

```bash
python -m compileall -q clean_product backend/app scripts/run_product.py
pytest -q tests/test_clean_product.py
python scripts/run_product.py daily --asof 2026-09-25 --dry-run
python scripts/run_product.py replay --model model_a_plus_b --start 2026-09-24 --end 2026-09-25
cd frontend && corepack pnpm build
```

真实采集需要 `FINMIND_TOKEN` 和本机数据目录；不要把本地 token、模型文件或市场数据提交到 Git。
