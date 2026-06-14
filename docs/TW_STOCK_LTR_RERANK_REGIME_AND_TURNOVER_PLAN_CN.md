# 台股 LTR 重排序 + 市场状态自适应 + 换手控制 主线方案文档

## 1. 文档定位

本文档是下一条主线的**总设计与执行边界文档**。

用途只有三个：

1. 冻结这条主线的目标、边界、输入、输出和验收口径；
2. 作为执行者与审查者后续多轮协作的唯一主线依据；
3. 让审查者基于本文件，在每一轮审查后单独撰写“下一步步骤文档”。

因此：

- **执行者不能自行扩写主线**；
- **审查者不能擅自偏离本主文档新增副主线**；
- 若出现文档外重大问题、证据冲突、或需要用户做 tradeoff 判断，必须停下并回到用户确认。

---

## 2. 为什么现在做这条主线

前面多轮工作已经得到明确结论：

1. 当前 `qlib baseline` 是稳定且有价值的研究主线；
2. 纯规则轮动（Top30/Top50/confirmed_exit）已经形成可用 baseline，但存在：
   - 排名变化快，容易高换手；
   - 牛市有效规则在差市况会失真；
   - 排名高不等于马上适合买；
   - 前端解释仍然缺“为什么今天不动作”的稳定机制；
3. 更复杂的黑盒 Decision Model 路线，当前没有证据证明比 baseline 更稳更强；
4. 文献深读补强后，最有证据支撑的路线是：
   - **LTR 横截面重排序**
   - **市场状态轻量自适应**
   - **组合层换手控制**

所以新的主线不是替换 qlib，而是：

```text
qlib baseline
-> LTR reranker
-> regime-aware gating
-> turnover-controlled portfolio layer
-> readonly replay + frontend explanation
```

---

## 3. 产品第一原则

整个实现过程必须持续满足这三个优先级，且顺序不能颠倒：

1. **简单**：用户不需要理解复杂模型结构也能看懂结果；
2. **准确**：输出语义必须和真实系统能力一致，不能把排序分数包装成收益率或买卖概率；
3. **清晰**：用户一眼能知道“今天谁值得看”“为什么”“为什么不动”。

补充约束：

- 不得因为追求研究先进性而破坏当前页面的可读性；
- 不得把系统重新做成运维面板；
- 不得把模型输出包装成自动交易建议；
- 不得新增一批用户看不懂的新分数，而没有可解释语义。

---

## 4. 这条主线要解决的问题

### 4.1 当前要解决的核心问题

1. `qlib_score` 是横截面排序分数，但现在缺少第二阶段重排序；
2. 同一套规则在 `normal / risk_off` 环境下表现差异明显；
3. 纯跟排名容易带来过度换手和成本侵蚀；
4. 当前前端还缺“为什么今天不建议替换”的结构化解释；
5. 策略回放需要从“毛收益导向”升级到“净收益 + 回撤 + 动作次数 + 成本”的现实口径。

### 4.2 当前不试图解决的问题

1. 不做真实自动交易；
2. 不做分钟级主线策略；
3. 不把还未 PIT-safe 的 FinMind 基本面/筹码数据强行纳入；
4. 不做端到端大黑盒模型；
5. 不承诺收益率、胜率、上涨概率。

---

## 5. 系统目标

这条主线的目标不是“发明一个新策略名字”，而是把当前系统从：

```text
qlib rank -> 人工看表 -> 简单规则回放
```

升级成：

```text
qlib rank
-> 更合理的横截面重排序
-> 根据市场状态调节动作门槛
-> 用换手控制把信号变成更可执行的组合动作
-> 前端给出简单、清楚、只读的解释
```

最终用户应能得到四类明确信息：

1. 今天哪些台股更值得先看；
2. baseline 和 rerank 是否一致；
3. 当前市场环境下是否适合动作；
4. 不动作时，究竟是因为环境、价格位置风险、还是换手预算。

---

## 6. 主线结构

## 6.1 Stage 1：qlib baseline（保留）

### 作用

作为第一阶段稳定研究排序，不推翻、不替换。

### 输入

- qlib historical prediction / accepted latest
- 当前已有 Top30 / Top50 / historical signal backfill

### 输出语义

- `qlib_score`：横截面排序分数
- `qlib_rank`：每日横截面相对位置
- `top30/top50`：研究观察候选

### 严格边界

- 不得将 `qlib_score` 解释成收益率、上涨概率、买入概率、胜率、仓位比例。

---

## 6.2 Stage 2：LTR reranker

### 目标

在不推翻 qlib 的前提下，给出第二阶段研究重排序。

### 第一版模型要求

- 第一版仅允许使用：**LambdaMART 或同等级树模型 LTR**
- 不允许第一版直接做：
  - Transformer reranker
  - 复杂 end-to-end deep ranking
  - 黑盒 decision-focused 主模型

### 候选输入特征白名单

#### A. qlib 层

- `qlib_score_raw`
- `qlib_rank`
- `qlib_score_percentile_by_date`
- `qlib_score_zscore_by_date`
- `rank_change_1d`
- `rank_change_3d`
- `rank_change_5d`
- `top10_flag`
- `top30_flag`
- `top50_flag`
- `top30_streak`
- `top50_streak`

#### B. 技术趋势层

- `MA5`
- `MA10`
- `MA20`
- `MA60`
- `RSI14`
- `MACD`
- `Bollinger_position`
- `ret20`
- `volatility20`
- `volume_ratio20`
- `trend_score`（若现有口径稳定）

#### C. 流动性层

- `avg_trading_value_20d`
- `volume_stability20`
- `missing_rate20`
- `suspension_proxy`
- `slippage_proxy`

#### D. 市场状态层

- `TWII_ret20`
- `TWII_ret60`
- `TWII_close_vs_MA60`
- `TWII_close_vs_MA120`
- `market_volatility20`
- `market_drawdown60`
- `market_breadth20`

### 禁止输入特征

在当前主线中，以下特征一律禁止加入训练与回放主线：

- institutional_net_buy
- margin_balance
- short_balance
- monthly_revenue_yoy_mom
- valuation_PER_PBR
- 任意没有 `available_at` / `announcement_date` 的 PIT 不安全字段

### 训练目标原则

- 核心任务是**横截面排序优化**，不是点预测回归；
- 不得把标签定义成“未来收益率点预测越准越好”这一种单一目标；
- 优先采用和 TopK / rank quality 更一致的训练与评估口径。

### 评估要求

至少要同时报告：

- rank quality 指标
- TopK 表现指标
- baseline vs rerank 的对照
- 分年度 / 分阶段结果

不得只给单一整体收益率。

---

## 6.3 Stage 3：Regime-aware gating

### 目标

让系统知道：

- 正常环境可以更积极参考 rerank；
- 差市况时应提高动作门槛，降低错误补仓和追高概率。

### 第一版实现要求

只允许做**轻量 regime gating**，不允许一开始做复杂深度 context reranker。

### 第一版 regime 状态

必须先收敛为 3 态：

- `normal`
- `caution`
- `risk_off`

### Regime 输入白名单

- `TWII_ret20`
- `TWII_ret60`
- `market_drawdown60`
- `market_volatility20`
- `market_breadth20`

### Regime 的作用边界

Regime 第一版只能影响这些环节：

1. 新进候选的动作阈值
2. 每日允许替换数量
3. 风险 / 流动性过滤强度
4. 是否允许补仓 / 替换的保守程度

### Regime 不允许影响的环节

- 不得直接生成买卖指令
- 不得输出用户不可解释的隐藏状态分数
- 不得绕开现有 readonly 边界

---

## 6.4 Stage 4：Turnover-controlled portfolio layer

### 目标

解决“高点买入、低点卖出、手续费太高、动作太多”问题。

### 第一版必须支持的机制

1. `no_trade_buffer`
   - 候选优势不明显时不替换
2. `confidence_gap`
   - 新候选必须足够优于当前最差持仓才触发
3. `partial_rebalance`
   - 只允许部分调整，不做激进全换仓
4. `max_actions_per_day`
   - 每天动作上限
5. `min_holding_days`（若样本与现有规则兼容）
   - 至少持有若干天，除非风险信号明显
6. `score_or_confidence_clipping`
   - 抑制过强输出直接驱动剧烈动作
7. `turnover_budget`
   - 周 / 月级动作或换手预算

### 第一版禁止事项

- 不得把 portfolio layer 设计成真实订单系统
- 不得写入真实 broker / order / position
- 不得新增脱离前端解释能力的复杂优化器

### 评估指标要求

组合层回放必须至少报告：

- gross return
- fee/tax-adjusted net return
- action count
- turnover proxy
- max drawdown
- final equity
- 与 baseline 规则对照

不得只看毛收益。

---

## 6.5 Stage 5：前端解释层

### 目标

让新主线的结果**用户看得懂**。

### 前端必须能解释的内容

1. baseline 排名高不高
2. rerank 是上调还是下调
3. 当前处于什么市场状态
4. 今天为什么建议观察 / 为什么建议不替换
5. 是环境约束、价格位置风险、流动性风险，还是换手预算在阻止动作

### 前端禁止输出

- 自动交易措辞
- target position / target weight
- expected return / upside probability / win rate
- 把 research-only 输出包装成 action order

### 前端优先级

优先展示：

1. 值得先看的候选
2. 原因
3. 不动作的原因
4. 历史回放中的现实指标

不优先展示：

- 模型训练细节
- 运维状态
- 大量内部诊断分数

---

## 7. 标签、训练、评估原则

## 7.1 标签原则

必须遵守：

- 标签设计要与“排序/替换质量”一致；
- 不得把未来信息泄露进输入特征；
- 不得把 `future_return_label_base` 等审计列错误放回输入；
- 若采用多周期标签，必须明确其和 TopK / 回放口径之间的关系。

## 7.2 数据切分原则

必须至少包含：

- 训练期
- 验证期
- 独立测试期
- 差市况/非差市况分段

不得只报告一个整体回放区间。

## 7.3 基线对照原则

新的主线必须至少对照以下已有策略：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

若新方案不能在至少一个清晰维度上优于这些 baseline，则不得强推进前端主展示。

---

## 8. 执行边界

## 8.1 执行者允许做的事

- 在当前主文档边界内实现代码、脚本、测试、回放、报告；
- 补充必要的只读 API / 解释字段；
- 修改前端只读展示；
- 编写执行报告；
- 明确指出问题、证据不足和风险。

## 8.2 执行者禁止做的事

- 擅自改变主线目标
- 擅自引入新的主模型路线
- 擅自纳入文档白名单外数据
- 擅自扩写真实交易功能
- 擅自把输出写成买卖建议

## 8.3 审查者允许做的事

- 审查执行者产物与证据
- 基于本主文档撰写下一轮“步骤文档”
- 收紧范围、修正偏差、要求补证据
- 在必要时要求停止并回到用户确认

## 8.4 审查者禁止做的事

- 擅自新增主线外大模块
- 擅自把探索项抬升为主线
- 在证据不足时强行放行
- 为了追求更高收益率破坏用户第一原则

---

## 9. 审查者输出的步骤文档要求

后续每一轮的步骤文档由**审查者**撰写，而不是由主文档预先拆死。

### 步骤文档必须包含

1. 本轮目标
2. 本轮允许改动的范围
3. 本轮禁止事项
4. 必做验证
5. 必交付产物
6. 验收门槛
7. 若失败如何收尾或回滚到上一步结论

### 步骤文档必须遵守

- 一轮只推进一个明确子目标；
- 不得混入主线外探索；
- 不得要求执行者同时做训练、前端、回放、重构四件大事；
- 必须显式指出本轮是否允许改接口 / 改前端 / 改训练口径。

---

## 10. 执行报告要求

执行者每轮提交给审查者的报告必须固定包含：

1. 本轮目标
2. 实际完成内容
3. 改动文件清单
4. 新增产物清单
5. 验证内容与结果
6. 是否达到本轮门槛
7. 风险 / 异常 / 未解决问题
8. 需要审查者重点检查的点

如果本轮没有达成目标，也必须明确失败原因，不能含糊表述。

---

## 11. 最终验收标准

这条主线最终是否成立，不看“是否实现了很多东西”，而看是否满足以下条件：

### 11.1 模型/回放层

1. `LTR rerank` 相比纯 qlib baseline 或现有纯规则，在至少一个清晰维度上有稳定增益；
2. `regime-aware gating` 在差市况下至少能证明减少明显失真或不必要动作；
3. `turnover-controlled portfolio layer` 能实质降低不必要动作，并改善净收益 / 回撤 / 换手平衡；
4. 结果对 baseline 的改进不是只出现在单一偶然窗口。

### 11.2 前端层

1. 用户能看懂 baseline、rerank、regime、动作约束之间的关系；
2. 页面没有因为引入模型层而变复杂混乱；
3. 不会误导用户把研究输出看成自动交易指令。

### 11.3 边界层

1. 仍然保持 readonly / research-only
2. 不引入真实交易动作
3. 不引入 PIT 不安全特征
4. 不引入文档外隐藏主线

---

## 12. 失败收尾标准

如果后续多轮执行与审查证明：

- `LTR + regime + turnover` 在现有数据条件下并未优于 baseline；
- 或改进只存在于不可复现的小窗口；
- 或前端解释代价过高，反而破坏用户第一原则；

那么必须允许收尾为：

- 保留研究产物与失败结论；
- 不强推前端主线；
- 把有效部分下沉为解释模块或内部研究工具。

也就是说，这条主线必须接受“可失败但要有价值收尾”的约束。

---

## 13. 当前推荐推进顺序

虽然步骤文档由审查者写，但主线建议顺序应固定为：

1. 冻结样本 / 特征 / 标签 / baseline 对照口径
2. 做最小可用 `LTR baseline`
3. 做 `regime gating`
4. 做 `turnover-controlled portfolio layer`
5. 做前端解释接入
6. 做最终只读验收

不得跳过前面对照和回放，直接先做前端包装。

---

## 14. 结论

这条主线的核心不是“做一个更厉害的模型”，而是：

- 用 LTR 把排序做对一些；
- 用 regime 让差市况少犯错；
- 用 turnover control 把信号变成更可执行的组合动作；
- 用前端解释把结果讲清楚。

这也是当前最符合：

- 文献深读结论
- 项目现有数据能力
- 已有 baseline 现实表现
- 用户第一性原则

的一条实现路线。
