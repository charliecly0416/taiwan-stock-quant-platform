> 历史阶段记录：本页保留当时的阻塞与证据。当前运行结论见 [主线验收](MAINLINE_ACCEPTANCE_CN.md)。

# Clean 主线候选验收：2026-09-27（续查更新）

## 结论

**局部修复与当前代码测试通过；正式主线替换和全部旧功能等价仍未通过。**

本报告接续窗口 `01a0e315-7918-7c12-8d21-5d8730e71d46`、`01a0e386-3517-7da2-aff9-7e52dd309d6e`，记录 `product-clean` 当前未提交工作树的实际结果。保留既有改动，没有 reset、删除旧文件、切换正式服务或发布 latest。

本轮证据位于 `tmp/clean_repair_20260927/`；前轮 `tmp/clean_resume_20260927_textonly/`、`tmp/clean_continuation_20260927/` 和本轮初次失败记录均保留。证据目录为本机 ignored 路径，fresh checkout 需要在具备冻结资产的环境重跑。旧报告的 53 项测试和 TW6472 缺价结论仅描述前轮，不能代表修复后的状态。

最终结果：**135 项 Python 测试、8 项前端单元测试、前端构建通过；六页 × 三视口的交互、DOM、请求边界通过。业务 smoke 与浏览器业务验收仍为退出码 1。** 没有调用 `view_image` 或将图片传入对话。

## 最重要的来源问题

`configs/active_baseline_descriptor.yaml` 和冻结训练 manifest 规定唯一 Model A 为 `e4_frozen_qlib_2018_2022`，模型为：

- 文件：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl`。
- SHA256：`b56ab7ca94fc098fd11c0ee3cf1d5b97ae97a3f241fb01c87fb24a62b0bcedf3`。

但 2026-09-24 已发布的旧信号 manifest 自报相同 model_id，其 `source_model_artifact` 实际是：

- 文件：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl`。
- SHA256：`06dc2b59e411044da9747eb58e3a70336b02c0818a9e180a39d8b3302409775e`。

路径和哈希均与合同不符。旧 validator.ok=true 不能消除这个身份冲突。2026-09-24 的每日 Agent 上下文也继承同一来源。证据：`current_lineage_audit.json`、`baseline_identity_audit.json`。本轮仅只读审查，没有重写上述文件或任何生产指针。续查再次计算两个模型文件、已发布 manifest 和 latest 指针的 SHA256，均未变化，见 `protected_lineage_recheck.json`。

clean 配置现已绑定 canonical 模型、训练 manifest、推理配置、post-filter 分数档案与 raw cross-section 档案的哈希。旧 clean 缓存没有符合当前来源身份的 fingerprint，明确 BLOCKED；不会自动用它们冒充有效结果，也没有为使验收变绿而覆盖 ignored 资产。

## 已修复的代码

### 数据、模型与回放

- 数据按 primary key 更新：修订价格不会重复追加，机构分类记录不会互相覆盖。空键和非法日期在转字符串前拒绝。
- 只读目录构造不创建目录；未注册的数据集不能读取同名 CSV。FinMind 数字标的去除 TW 前缀，TWII 保留；请求异常不回显 query token。
- provider status 按实际有效 close 计数，另列 calendar_latest；缺文件、坏偏移或截断二进制明确阻断，不再把日历 × 股票数当作实际行数。
- 共同验证器检查 frozen identity、配置 fingerprint、checksum、日期、重复键、有限分数、排序及完整排名映射。残缺产物不可绕过验证后静默重算。
- 区分 candidate_rank 与 full_qlib_rank；策略退出使用完整基线排名。2025-06-23 的正式 E1 post-filter 档案为 84 行，而原始 cross-section 为 150 行，不能混成一个排名口径。
- B19R2R 固定模型、训练 manifest、78F schema、历史特征的 SHA256，仍只重排同日 Top50，排除 TW7769 不补位。新日期没有经验证的 78F/PIT 来源时返回 `B19R2R_VALIDATED_78F_UNAVAILABLE`，不启用未经等价验证的近似特征兜底。
- 已延续并重测：初始本金参与回撤、最低手续费预留、next_open、缺价明确阻断、Top50 边界变化、RSI 边界、行情预热、缺失值不显示为零及 JSON 非有限值处理。

### 日更、API 与前端

- 数据与模型故障按依赖隔离，影子失败不污染基线；CLI 的 BLOCKED 返回非零退出码。
- 日更每个 run_id 单独存档；手工重试不会覆盖同日 scheduled 证据。operations 分别返回 latest_manual 和 latest_scheduled。
- 失败信号写到 failed_runs，不覆盖已有成功信号。测试验证成功 manifest 的字节保持不变。
- readiness 不再恒定成功：检查冻结身份、模型哈希、provider 日期与当前物化信号；不评分，失败为 503。这个 scope 仍小于完整发布验收。
- 行情或交叉背景缺失时明确 BLOCKED，不展示空表为 READY。
- 前端统一表单请求处理；旧响应不能覆盖最新请求或已切换页面。补齐浏览器前进/后退，转义错误文本和标签，修复平板比较页长错误文本溢出。

### 本次继续审查的边界修复

在先前 118 项通过后，新增反例仍复现了 14 个失败用例，说明既有绿灯不代表所有功能准确。修复后加上正向与缺失日历检查，共 135 项 Python 测试通过。

- 个股解释改为完整代码精确匹配；查询 2330 不会再命中 TW12330。行情与解释共用输入校验，不把 abc2330、23-30、2330.5 等错误输入拼成另一只股票。
- 榜单变化在历史不足时返回 RANKING_HISTORY_INSUFFICIENT；不再把首日与自己比较，或悄悄缩短用户要求的 lookback。
- 行情最新收盘为缺失、无穷、零或负值时返回 MARKET_LATEST_CLOSE_INVALID，不展示 READY 和空指标。
- 回放共用入口对齐 provider 交易日历；缺失交易日或出现非交易日价格明确 BLOCKED，不静默跳日改变 next_open。日历中合法的非交易日间隔仍可通过。API 与 CLI 共用这一检查，fixture 明确保持隔离。
- 只修改既有 config/service/replay 和测试；未新增运行时模块、框架或生产入口。前端说明同步纠正为允许精确限定的本地 simple-chat POST。

反例证据：`boundary_before.log`；修复后命令退出码：`boundary_command_results.json`。旧证据保留，最新浏览器记录为 `frontend_boundary_verified/summary.json`，源码/构建哈希核对记录在 `final_verification.json`。

### Agent 与打包

- 新增小型 `clean_product/agent.py` 与 `POST /api/tw-stock/agent/simple-chat`。只接收研究问题、日期、股票代码和数量限制，不接收 endpoint、key、tools 或 action。
- 自由提问只读取 DailyAgentPromptArtifact，验证 checksum、日期、安全标记、源文件哈希、源模型身份及排名一致性；不以动态服务数据替代每日 artifact，不伪造引用。
- 当前模式为 `artifact_local`：可解释排名、指定股票、日期、策略口径，证据不足时明确提示；危险问题在读取上下文前拒绝。不调用远端语言模型，不能称为完整远端 Agent 等价。
- 后端 Dockerfile 修正为仓库根 context，显式 COPY clean 模块和配置；前后端均避免把环境文件/凭据带进镜像。补充模型依赖版本并固定 pnpm。
- 统一 catalog、runner、strategy、replay、validator 的小模块结构保持不变；表单逻辑复用，没有恢复整套旧后端、引入新前端框架或复杂工具 Agent。

## 真实历史数据复核

原先失败的窗口 **2025-06-23 至 2025-06-30**，现使用正确冻结模型的原始 E1 post-filter 档案跑通，未改窗口、补造价格或按当前缺价删股。原始完整排名同时保留供退出选择使用。

| 指标 | 实测 |
| --- | ---: |
| 交易日 | 6 |
| 模拟成交 | 58 |
| 初始资金 | 1,000,000 |
| 期末 NAV | 1,008,037.0437944806 |
| 累计收益 | 0.8037043794% |
| 最大回撤 | -1.0410105958% |
| 费用 | 1,898.7121287903785 |

证据：`canonical_rechecked.json`。它只证明该历史窗口和当前代码，不是现时可交易性或完整历史覆盖证明。

隔离目录还实际验证了：2026-04-30 的 Model A/B 分别为 133/50 行；2026-05-07 为 150/49 行，TW7769 排除后不补位，Top50 交集 49。历史 B19 比较不是前瞻/OOS 绩效认证。2025-06-23 的 B19 78F 不完整仍然 BLOCKED，没有缩减候选来制造成功。

## 命令与证据

| 检查 | 本工作树结果 | 证据（相对本轮目录） |
| --- | --- | --- |
| `pytest -q` | 135 passed | `pytest_boundary_final.log` |
| `python -m compileall -q clean_product backend/app scripts tests` | 退出码 0 | `final_verification.json` |
| `node --test frontend/tests/*.test.js` | 8 passed | `frontend_unit_boundary_final.log` |
| `corepack pnpm --dir frontend build` | 退出码 0 | `frontend_build_boundary_final.log` |
| 隔离源文件导入/启动 | health=200，缺资产 ready=503，config=200 | `packaging_boundary_check.json` |
| `python scripts/verify_clean_product.py` | 17 个请求，退出码 1 / BLOCKED | `integration_boundary_final.json` |
| `python scripts/accept_clean_frontend.py --serve-build` | 退出码 1；ui_passed=true，passed=false | `frontend_boundary_verified/summary.json` |
| 正式 5000/8000 GET 探测 | ready=503，clean overview/operations=404 | `live_boundary_readonly_probes.json` |
| 文档路径与 diff 检查 | 见最终验证记录 | `documentation_checks.json`、`final_verification.json` |

浏览器覆盖桌面 1440×1000、平板 820×1100、手机 390×844，共 18 个页面/视口组合；另有三视口费用 fixture、真实历史模型比较响应的页面检查，以及延迟请求后的导航竞争检查。费用 fixture 是 98 单位、费用 20、NAV 882、回撤 -11.80%。历史比较的后台来源为真实冻结资产和临时物化目录，但浏览器响应由测试注入，记录明确注明，不当作默认资料链路通过。

最终无页面异常、控制台错误、失败网络请求或越界请求；表单与声明的 DOM 几何断言通过。24 张 PNG 仅保存到本地，未打开、未嵌入请求。`visual_review=NOT_PERFORMED`，没有像素级人工视觉验收。无法据此确认图片是 Codex 422 的唯一原因。

请求边界为同源 localhost GET，加精确限定的本地 simple-chat 只读 POST；其余 POST 和外部请求在发送前拦截。18 个 API 路由中 17 个为 GET，1 个为只读问答 POST；没有 paper 写入、券商、订单、monitor 或 provider 操作入口。

## 尚未完成与不能越过的边界

| 项目 | 当前缺口 |
| --- | --- |
| 最新有效产物 | 已发布源模型身份冲突，clean 旧缓存也未通过新验证。需要正确来源和完整血缘的候选产物以及单独准入；不能原地改名、改哈希或重写 latest 来消除报错。 |
| 新日期 Model A / B | 历史 post-filter 来源不覆盖当前窗口，B 新日期 78F/PIT 等价生产链未完成。没有触发采集、训练、provider publish 或资产替换。 |
| 持久化模拟账户 | `/paper` 仍是明确标记 persisted=false 的初始模拟参数；回放账户为临时状态。旧账户身份、持仓、apply/reset 的迁移未完成，不能称为全部功能已恢复。 |
| Agent 全功能 | artifact 验证和本地自由提问已补回；当前旧 prompt 的源模型身份不符被拒绝。远端适配、完整回答质量和每日 prompt 生成的调度链未完成，未进行真实 OpenAI 调用。 |
| 正式部署 | 两个正式端口仍不是 clean 完整服务。本轮只启动并关闭随机本地验收端口，没有重启或切换生产。 |
| 可复现模型环境 | Docker daemon socket 拒绝访问，未实际构建镜像；源文件打包检查复用当前解释器。台湾定制 Qlib 0.9.8.dev31 的 wheel 与全新环境验证待补。 |
| 调度与发布准入 | 隔离 fixture 证明代码隔离，不证明真实 scheduled lane 成功。原 research-stack、ARCH-1、M3、模块回归入口/registry 未全部迁回，未冒称这些旧准入检查通过。 |
| 仓库清理 | 7 个旧遗留候选继续保留；删除闭包、仓库外备份、凭据扫描及恢复验证尚未完成，不能声称物理清理已结束。未使用的旧特征 helper 没有挂入运行链。 |

## 复核命令

```bash
python -m compileall -q clean_product backend/app scripts tests
pytest -q
node --test frontend/tests/*.test.js
corepack pnpm --dir frontend build
python scripts/verify_clean_product.py
python scripts/accept_clean_frontend.py --serve-build
git diff --check
```

后两项业务验收出现非零退出码时，先读 JSON 中的具体来源/资料阻断，不改写为整体通过。真实操作约束来自根 AGENTS.md：provider、accepted latest、production default、实际账户写入等不在本次只读验证范围内。

## 2026-09-28 授权续查附录

- 当前工作树重新实测：`pytest -q` 为 176 passed，前端 Node 为 11 passed，production build、ARCH-1、M3、clean modules（57 focused tests）和 `git diff --check` 均通过。
- `accept_clean_frontend.py --serve-build` 最新结果为 `ui_passed=true`、`passed=false`：七页三视口的 DOM、网络、console、纸面账户确认门均通过；业务请求继续如实显示 `SIGNAL_ARTIFACT_IDENTITY_MISMATCH` / `AGENT_SOURCE_MODEL_IDENTITY_MISMATCH`，没有被 fixture 掩盖。`visual_review=NOT_PERFORMED`，未使用 `view_image`。
- 经明确授权执行的 Yahoo-only staged refresh 位于 `data_tw/experiments/provider_bridge_productionization/authorized_yahoo_staged_20260928/`：option_c_150 为 150/150，normalized/provider/artifact validators 通过，日期为 2026-09-24；模式为 `provider_only`，没有写正式 provider、accepted latest、signal、Agent 或 paper。
- 150 支 staged 候选不能替代完整动态 universe 的 canonical selection source（现有 1,987 支资料仍有 1,822 支停在 2026-05-21），所以 `verify_clean_product.py` 与 `verify_tw_stock_research_stack.py` 继续 BLOCKED 是预期的安全结果。
- Docker 两个镜像构建已实际尝试，但 Docker Hub 基础镜像 metadata 请求超时；没有声称镜像或正式部署成功。日志保存在 `tmp/clean_authorized_20260928/backend_image_build.log` 与 `frontend_image_build.log`。

## 2026-09-28 续查补充：全量数据与 150 候选口径

Yahoo-only refresh 已接入 daily orchestrator。1,964 个截至 `2026-09-24` 有效的标的是全量行情与流动性筛选覆盖；Model A 依照旧 E1 流程只对筛选出的 150 支候选推理，实际结果为 150 signal rows、150 full ranks、50 intents。provider 构建已改为逐文件流式写入。B19R2R 仍为 non-blocking shadow lane，缺 78 PIT 特征时保持 BLOCKED。
