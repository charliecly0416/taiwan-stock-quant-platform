# Phase M0 审查补充意见

生成日期：2026-06-17

## 1. 结论

M0 没有明显走偏，可以进入 M1。

M0 的范围保持正确：

```text
只补合同和文档索引
不训练新模型
不跑新 replay / 新收益结论
不切默认策略
不触发 provider publish / refresh
不切 accepted latest
不改 monitor / broker / quick-trade / order
不改前端 Agent 行为
不新增 Agent tool / action / prompt
```

但 M0 合同仍是文档层，不能被视为工程闭环。M1 必须把这些合同变成可执行 validator、golden samples 和结构化审计证据。

## 2. 非阻塞问题

### Low: M0 执行报告较简略

执行报告列出了新增合同和未执行事项，但文件存在性、关键字段覆盖、文档索引更新的检查证据较少。当前审查文档已经补了这部分判断，因此不阻塞 M1。

M1 开始后，执行报告不能继续只写“已覆盖”，必须列出：

```text
validator 命令
golden sample 路径
pass/fail 结果
错误码
检查文件数量
未覆盖项
```

### Low: M1 不能只做关键词扫描

M1 validator 必须避免只用字符串 grep 证明合规。最低要求：

```text
manifest required fields 结构化检查
数据列 required fields 检查
forbidden fields 精确字段 + 前缀/正则检查
forbidden actions 读取结构化 audit 文件
network/request audit fixture 检查
latest pointer state transition 检查
```

没有结构化审计文件时，应返回：

```text
audit_missing
not_verifiable
```

不得静默通过。

### Low: 既有两小时自动脚本必须在 M1/M3 被映射到合同

M0 已新增 `AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md`，但 M1/M3 必须明确审计既有自动脚本，而不是只造一个抽象样例。

后续至少要确认：

```text
既有脚本路径
触发周期
no_new_data 行为
fresh_data_success 行为
validator_failed 行为
previous latest 是否保留
是否触发 provider accepted latest
是否触发 monitor / broker / order
```

如果 M1 暂不检查真实脚本，也必须在 M1 报告中列为 M3 必查项。

### Low: Agent 只允许 placeholder，不允许实现

M0 已把 Agent 纳入合同占位，这是正确的。M1 只能做：

```text
Agent readonly context fixture
forbidden tool/action/prompt expansion fixture
Agent response forbidden semantics fixture
```

M1 不得修改前端 Agent 面板、prompt、tool 权限或动作入口。

## 3. 对 M1 工作文档的补充要求

M1 除 `PHASEM0_REVIEW_AND_PHASEM1_WORK_CN.md` 已列事项外，还应补充以下硬门：

```text
每个合同必须绑定明确 schema_version
每个 fail sample 必须失败在预期 error code
validator 输出必须稳定：ok / contract / status / errors / warnings / checked_files
frontend/Agent 安全检查必须区分允许的只读回放术语和真实交易语义
auto-update 样例必须覆盖 no_new_data、success、validator_failed、forbidden accepted_latest/order
contract regression 必须纳入所有 M1 validator
```

## 4. 审查者 M1 重点

M1 审查时应重点看：

```text
是否把合同变成可执行检查
是否有每个合同的 pass/fail golden sample
是否有 forbidden actions 的结构化证据
是否没有训练、回放收益、默认策略切换
是否没有 provider/accepted latest/monitor/broker/order 越界
是否没有修改 Agent 行为
是否没有把 smoke/diagnostic 当成有效策略证据
```

如果 M1 只是新增文档或只做弱关键词检查，应要求修复后再进入 M2。
