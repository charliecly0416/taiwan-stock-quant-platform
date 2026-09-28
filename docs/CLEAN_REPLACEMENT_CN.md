# Clean 功能替代与持续维护边界

GitHub 默认分支为 `product-clean`。旧 `main` 保留，切换前的提交由 `legacy-main-20260928` 保存；不会把历史代码删掉来证明精简。clean 运行闭包是 `clean_product/`、薄 API 路由、原生 JavaScript 前端和 systemd。

## 旧入口对应关系

依据旧前端 `frontend/src/api/tw-stock-readonly.js` 与 `tw-stock-action.js`（旧提交 `25839e1`）核对；保留的是当前研究产品功能，不承诺每个历史实验入口行为相同。

| 原有功能 | Clean 对应 | 范围 |
| --- | --- | --- |
| Top30/Top50、排名变化 | rankings、ranking-changes | Model A 实际评分150支，策略Top50 |
| 个股行情和技术背景 | market、cross-analysis | 保留行情、MA20、RSI14；不宣称旧任意技术策略等价 |
| 策略工作台 | strategy/overview | 唯一默认 Model A / top50_exit_one_worst_sell / next_open |
| 固定/动态历史回放 | replay统一引擎 | 成交、费用、现金、净值共用计算与校验 |
| A/B比较 | 只读比较与历史回放 | B仅使用有证据的历史窗口；新日期缺资料不阻塞A |
| Agent研究问答 | 每日固定产物 + simple-chat | 本地解释默认启用；远端适配未启用实调 |
| 账户、持仓、历史 | clean SQLite + owner认证 | 独立模拟账本，预览与确认分离 |
| 手工订单草稿、确认、取消 | 模型预览/确认应用流程 | 未确认不改账本，不恢复自由交易入口 |
| 旧登录 | 短期签名owner token | 不迁移旧密码与会话 |
| 日更、保活、状态 | 单一systemd入口 | 新增独立健康与备份timer |
| 旧monitor写入、复杂tool-agent、券商订单 | 当前产品范围外 | 不恢复为主线入口 |

## 账户和资产迁移

clean 升级时暂停Web写入，以SQLite一致性复制同步最新账本，保留账户、事件、幂等记录。现有 `paper-export/import` 只接受clean格式；导入验证owner、日期、金额与数量，使用独立新数据库，不覆盖在线账本。

旧数据库及owner对应关系未提供，因此没有声称旧账户已迁移。如仍需旧账户，先提供明确的只读导出与owner映射，再转换核对；不自动读取秘密数据库。市场资产和冻结模型通过注册路径备份与恢复，不提交GitHub。

## 持续维护

新增功能按 [开发入口](DEVELOPMENT_ONBOARDING_CN.md) 接入既有模块合同。运行故障、备份、恢复、升级与回退使用 [运维手册](OPERATIONS_CN.md)。实际验证结果见 [主线验收](MAINLINE_ACCEPTANCE_CN.md)。

CI执行Python回归、前端Node测试和生产构建。当前GitHub私有仓库套餐拒绝分支保护（HTTP403，要求升级套餐或公开仓库），因此CI有反馈但尚无服务器强制合并门禁；仓库保持私有。
