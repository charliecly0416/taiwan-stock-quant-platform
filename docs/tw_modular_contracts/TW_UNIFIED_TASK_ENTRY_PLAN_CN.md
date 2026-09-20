# 统一任务入口实施方案

状态：已实现，已通过独立复审。

## 1. 目标

为已经解耦的数据、模型、策略、回放和只读展示模块增加一个薄的统一入口。调用方只提交任务类型和参数；任务注册表决定使用哪个受控 executor、workflow spec 和依赖配置。

统一入口不复制数据抓取、模型评分、策略或回放逻辑，也不允许请求直接指定 Python 文件、模块路径或 shell 命令。

## 2. 三层结构

```text
TaskRequest
  -> TaskRegistry / parameter schema
  -> TaskDispatcher
       -> daily_update_v1 -> 现有日更入口
       -> readonly_backtest_v1 -> 现有只读回放 artifact builder
       -> workflow_spec_v1 -> 现有 WorkflowEngine
```

职责如下：

- `TaskRequest`：只包含 `task_type` 与该任务允许的业务参数。
- `TaskRegistry`：登记 executor、默认值、参数 schema、固定代码和配置绑定。
- `TaskDispatcher`：校验、规范化、生成稳定 run identity、调用 executor、记录统一结果。
- executor：只翻译参数并调用已有模块或 workflow，不重新实现业务。

## 3. 首批任务

### 3.1 daily_update

参数包括目标日期、模型轨道、FinMind scope、超时和 worker 数。模型轨道只能来自 `configs/daily_model_tracks.yaml`，且必须包含 required 的 `model_a_only`。

它调用现有 `scripts/run_daily_tw_stock_auto_update.py`。provider/latest 等权限仍由原日更 gate 和环境授权控制，统一入口不扩大权限。

### 3.2 readonly_backtest

参数包括模型轨道、策略和日期范围。模型轨道先通过 `configs/readonly_model_tracks.yaml` 映射为模型 ID，再由 `configs/tw_replay_window_policy.yaml`、模块 registry、训练窗口和 PriceStore 合同校验。

当前只有已经进入 replay policy 且具备标准历史信号的组合可以执行。不支持的模型或窗口必须明确失败，不能用临时数据补齐。

### 3.3 readonly_model_comparison

使用 `workflow_spec_v1` executor 调用现有 `tw_stock_workflow` DAG，证明新增 YAML workflow 可以只通过 registry 接入统一入口。

## 4. 运行记录

每次任务以规范化请求和 registry entry 计算稳定 identity，并写入：

```text
data_tw/ops/unified_tasks/{task_type}/{run_id}/
  normalized_request.json
  plan.json
  stdout.txt
  stderr.txt
  result.json
```

相同回测或 workflow 请求与相同 registry 配置若已经成功，直接返回既有成功记录，避免重复执行。日更必须保留同日多班次重试，因此每次都委托原日更入口，由原有 readiness、pending 和幂等逻辑决定是否实际更新。日更中的动态 `asof: auto` 会先解析为 Asia/Taipei 日期，再参与 identity 计算。

同一 identity 的检查、执行和结果写入由任务目录文件锁串行化，JSON 通过临时文件原子替换。日更的 `stage_timeout_seconds` 只传给原 orchestrator 的单个子阶段，`overall_timeout_seconds` 单独约束完整任务；外层超时时终止整个进程组，避免子进程继续写 artifact。

## 5. 安全边界

- 不接受任意命令、脚本路径或 import path。
- 所有绑定路径必须位于仓库内并由 registry 固定。
- 回测输出只能进入任务隔离目录，不能写产品 latest。
- B19R2R 保持 `production_allowed=false`、`no_apply=true`。
- 统一入口不修改 baseline、虚拟账户 allowlist 或前端默认项。
- `--validate-only` 只返回执行计划，不调用任何任务。

## 6. 验收

- 请求 schema、registry 与 executor 映射均 fail closed。
- 日更模型选择不能绕过 required Model A。
- 回测模型、策略和窗口必须通过现有 policy。
- workflow executor 复用现有 engine、权限、DAG 和 run registry。
- 相同成功任务支持幂等复用。
- focused tests、M3、模块合同回归、`make verify` 和独立审查通过。
