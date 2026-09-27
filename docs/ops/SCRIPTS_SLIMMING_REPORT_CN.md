# 脚本目录瘦身报告

日期：2026-09-27

这次整理的目标是让新开发者能先看到完整、可运行的产品主线，同时保留历史研究证据。
没有删除源文件，也没有修改数据、模型、provider latest、cron 或 paper account。

## 做了什么

- 从 `scripts/` 根目录移出 172 个阶段号、日期号、旧模型路线和一次性研究脚本。
- 归档位置：`scripts/archive/historical_research/root_recovered_20260927/`。
- 移动前逐文件搜索了 `configs/`、`backend/`、`frontend/src/`、`tests/`、`.github/`、
  `tw_stock_workflow/` 和项目级构建文件；被当前运行链或测试直接引用的文件没有移动。
- `scripts/check_tw_project.py --json` 在移动后仍通过，且没有出现未分类脚本。

根目录 Python 文件由 304 个降为 132 个。剩余根目录文件主要是稳定入口、当前日更支持、
产品 artifact builder、合同 validator 和部署检查；这几类文件仍被配置、CI 或测试直接使用。

## 当前主线

```text
run_tw_task.py
  -> TaskDispatcher
  -> tw_task_registry.yaml
  -> daily_update / readonly_backtest / readonly_model_comparison
```

日更的实际执行器仍是 `scripts/run_daily_tw_stock_auto_update.py`。历史回放、模型轨道、策略、
只读 API 和前端的入口没有改路径，旧 baseline 和 B19R2R 的治理边界没有改变。

## 备份与恢复证据

备份目录（仓库外）：

`/home/chuliyang/taiwan-stock-quant-platform-backups/slimming-20260927-r1/`

- `MANIFEST.sha256`：174 个候选原始文件的精确 SHA256；其中 2 个现行运维脚本已恢复到根目录。
- `SECRET_SCAN_RESULT.txt`：扫描结论；两处命中只是环境变量读取代码，没有凭据值。
- `RESTORE_VERIFY.txt`：隔离目录恢复校验，174/174 个候选文件通过。
- `files/scripts/`：按原始相对路径保存的备份内容。

回收是可逆的。若以后确实需要某个历史脚本，先从备份或 Git 恢复到隔离目录，再重新检查
当前合同和依赖，不要直接把它加入日更或统一任务注册表。

## 验证

本次未运行真实抓取、provider publish、模型训练、latest 切换或交易操作。已运行：

```bash
python scripts/check_tw_project.py --json
```

下一步如果继续拆分 8,600 行的日更入口，应采用小步提取、保留兼容入口、每步运行日更 focused
tests 和 M3 validator，避免把本次低风险目录整理扩大成运行逻辑重写。
