# LTR 正交数据纳入受控实验主线

生成日期：2026-06-15

## 1. 主线目标

本主线只做一件事：

```text
在严格复刻第一版 simple LTR / Phase1C anchor 的前提下，
只把法人筹码、融资融券等正交数据作为新增特征加入 LTR，
比较“加入正交数据的 LTR”是否稳定优于“第一版 simple LTR”。
```

本主线不是：

- 不重训 qlib；
- 不切换前端默认策略；
- 不新增交易过滤器；
- 不新增风险闸门；
- 不修改回放买卖规则；
- 不做 fresh qlib / fresh LTR 的新主线比较；
- 不把未验证结果产品化。

如果正交数据不能产生清晰、稳定、可解释的增益，则本主线收尾，保留数据审计结论，不进入前端主推荐。

## 2. 背景结论

前序问题基本已经进入可收尾状态：

- Phase1C anchor 已复刻并冻结为研究基准；
- Fresh Top50 replay-ready 覆盖修复已完成；
- 前端默认策略已切回 `rank_rotate_top50_adaptive_score`；
- LTR 在没有正交信息增量时，增益不稳定；
- 后续最值得验证的是：正交数据是否能给 LTR 带来真实增量。

因此本主线的实验设计必须严格控制变量，避免再次出现“模型、样本、过滤、窗口、特征口径一起变化，导致无法判断收益来源”的问题。

## 3. 第一版 simple LTR Anchor 合同

本主线的 control 必须是第一版 simple LTR / Phase1C anchor，不得替换。

冻结身份如下：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
random_state: 42
```

冻结回放口径：

```text
next-day execution
fee_rate: 0.001425
tax_rate: 0.003
target position count: 10
preserve_scope: top50_only
```

冻结评测窗口至少包含：

```text
Phase1C anchor final test: 2025-07-01..2026-05-07
```

如执行者需要扩展训练或评测窗口，必须先证明不会改变 control 合同，并在审查者确认后才可执行。

## 4. 控制变量原则

本主线只允许一个变量变化：

```text
Treatment LTR = 第一版 simple LTR + 新增正交特征
Control LTR   = 第一版 simple LTR
```

必须保持不变：

- 旧 qlib 冻结模型；
- qlib score 生成口径；
- LTR 样本行；
- LTR 训练时间段；
- LTR 验证/测试时间段；
- LTR 标签；
- LTR 原有特征；
- LTR 模型类型；
- LTR 超参数；
- top50 rerank / preserve_scope 规则；
- 回放规则；
- 费用税费；
- 持仓数；
- full/common universe 报告方式。

禁止静默加入：

- 新过滤器；
- 新买入阈值；
- 新卖出阈值；
- 大盘闸门；
- score 自适应规则；
- turnover-control；
- 不同股票池 top-up；
- 缺失值导致的样本删除；
- 任何未在本文件列出的主线变量。

如果发现必须改变上述任一项，执行者必须停止并提交问题说明，不得自行继续。

## 5. 正交数据范围

第一批只验证 FinMind 已确认可取且相对有信息增量的数据：

### 5.1 法人筹码

FinMind dataset：

```text
TaiwanStockInstitutionalInvestorsBuySell
```

候选特征：

- 外资买卖超；
- 投信买卖超；
- 自营商买卖超；
- 三大法人合计买卖超；
- 1/3/5/10 日 rolling 买卖超；
- 连续买超/卖超天数；
- 买卖超占成交量比例。

### 5.2 融资融券

FinMind dataset：

```text
TaiwanStockMarginPurchaseShortSale
```

候选特征：

- 融资余额变化；
- 融券余额变化；
- 融资使用率 proxy；
- 融券回补 proxy；
- 融资快速增加风险 proxy；
- 融资/融券方向与价格趋势背离 proxy。

### 5.3 暂不纳入

月营收 YoY 暂不纳入本轮 treatment。

原因：

```text
当前 FinMind 月营收响应缺少可靠历史公告日字段；
无法保证 point-in-time safe；
不能为了模型效果牺牲 PIT 合同。
```

如后续找到 MOPS/TWSE/TPEx 的可靠公告日来源，应另开小支线。

## 6. PIT 与数据口径规则

法人筹码和融资融券均按盘后数据处理。

第一版保守 PIT 规则：

```text
available_at = next_trading_day(trade_date)
```

含义：

- `trade_date` 是数据对应交易日；
- 数据只允许在 `available_at` 及之后使用；
- 不允许同日使用；
- 不允许用未来补齐历史缺口；
- 不允许用回测窗口后的数据修正窗口内特征。

每条 raw archive 至少保留：

```text
symbol
stock_id
trade_date
available_at
source_dataset
fetched_at
raw_payload_hash
raw_snapshot_path
```

所有 normalized feature 必须能追溯到 raw archive。

## 7. 缺失值处理规则

缺失值不得导致样本行被静默删除。

默认处理：

```text
数值特征：neutral fill，例如 0 或同日横截面中位数；
缺失标记：每类正交特征都增加 is_missing flag；
覆盖报告：按日期、股票、特征族报告 missing ratio；
样本行数：treatment 必须与 control 完全一致。
```

如执行者认为必须删除样本行，必须停止并提交用户确认。

## 8. 阶段设计

### Phase O0：冻结 Anchor 与实验合同

目标：

```text
确认本轮 control 精确等于第一版 simple LTR / Phase1C anchor。
```

执行内容：

- 读取 Phase1C anchor card；
- 固定 control candidate_id / score_column / label / model 参数；
- 找到第一版 simple LTR 样本构造脚本、训练脚本、回放脚本；
- 输出 control artifact 清单；
- 输出本轮禁止变化清单。

验收 gate：

```text
phase_o0_anchor_and_control_contract_frozen
```

停止条件：

- 找不到第一版 simple LTR 的可复刻脚本或 artifact；
- control 复刻指标无法对齐；
- 执行者无法确认训练窗口或样本构造细节。

### Phase O1：正交数据可得性与 PIT 审计

目标：

```text
确认法人筹码、融资融券可按目标股票池和目标时间段稳定获取，并可形成 PIT raw archive。
```

执行内容：

- 使用现有 FinMind token；
- 必要时使用 scrapling + token；
- 小范围先测 10-20 支股票；
- 再扩展到 Phase1C control 样本涉及股票；
- 统计 API 成功率、字段稳定性、日期覆盖、缺失分布；
- 验证是否能构造 `available_at = next_trading_day(trade_date)`。

验收 gate：

```text
phase_o1_orthogonal_data_pit_availability_passed
```

停止条件：

- 数据拉取大面积 402/403/429；
- 字段不稳定；
- 历史日期覆盖不足；
- 无法建立 PIT available_at；
- 需要引入新的数据源或账号权限。

### Phase O2：Raw Archive 与 Feature Builder

目标：

```text
把可得数据构造成可复现、可追溯、PIT safe 的正交特征。
```

执行内容：

- 建立 raw archive；
- 建立 normalized daily table；
- 建立 feature builder；
- 所有特征按 sample_date as-of join；
- 输出 feature dictionary；
- 输出 missing report；
- 输出 PIT leakage audit。

验收 gate：

```text
phase_o2_pit_safe_feature_builder_passed
```

停止条件：

- 需要用未来数据补特征；
- 特征无法追溯 raw archive；
- join 后 treatment 样本行数少于 control；
- 需要改变 control 的 sample_date 或 symbol 集合。

### Phase O3：受控样本拼接

目标：

```text
在不改变第一版 simple LTR 样本行的前提下，把正交特征拼到 treatment 样本。
```

执行内容：

- 读取 control LTR sample；
- 按 `symbol + sample_date` 做 as-of join；
- 输出 control/treatment row-level 对齐报告；
- 确认 label 完全一致；
- 确认原有特征完全一致；
- 确认新增列只来自正交特征族；
- 输出 row hash / feature schema diff。

验收 gate：

```text
phase_o3_treatment_sample_row_aligned_passed
```

硬性要求：

```text
control_rows == treatment_rows
control_label_hash == treatment_label_hash
control_original_feature_hash == treatment_original_feature_hash
```

停止条件：

- 行数不一致；
- 标签不一致；
- 原有特征被改动；
- 出现未授权新增字段；
- 因缺失值删除样本。

### Phase O4：Treatment LTR 训练

目标：

```text
用相同 LTR 训练配置训练“加入正交特征”的 treatment 模型。
```

执行内容：

- 使用 Phase1C 同模型类型；
- 使用 Phase1C 同超参数；
- 使用 Phase1C 同训练窗口；
- 使用 Phase1C 同 label；
- 只增加 O2/O3 确认过的正交特征列；
- 记录特征重要性；
- 输出训练日志与模型 artifact。

验收 gate：

```text
phase_o4_controlled_treatment_ltr_trained
```

停止条件：

- 训练配置变化；
- 超参数变化；
- 自动调参；
- label 重构；
- 训练窗口变化；
- 加入未审查特征。

### Phase O5：同口径评测与回放

目标：

```text
在完全相同回放口径下比较 treatment LTR 与第一版 simple LTR。
```

必须报告：

- rank metric；
- TopK hit / NDCG 或项目已有排名指标；
- full universe fee/tax adjusted return；
- common universe fee/tax adjusted return；
- max drawdown；
- action_count；
- turnover；
- next-day accounting；
- 真实 PnL contribution；
- 按市场环境分段；
- 按年份或月份分段；
- 与 Phase1C anchor 的差值；
- 新增正交特征重要性和稳定性。

主对照：

```text
Treatment orthogonal LTR vs 第一版 simple LTR / Phase1C anchor
```

次要参考可以包含：

```text
Fresh qlib Top50 adaptive default baseline
```

但次要参考不得替代主对照结论。

验收 gate：

```text
phase_o5_controlled_replay_evaluation_completed
```

停止条件：

- 评测窗口不一致；
- 回放规则不一致；
- 只报告收益不报告回撤/动作/费用；
- 只用 full universe 不报告 common universe；
- 发现未来函数或 PIT 违规。

### Phase O6：审查与决策

目标：

```text
判断正交数据是否真的给 LTR 带来可用增益。
```

通过标准建议：

必须同时满足：

- full universe 收益不低于 control；
- common universe 收益不低于 control；
- max drawdown 不明显恶化；
- action_count / turnover 不明显恶化；
- 分段表现不能只靠单一月份或单一股票贡献；
- 正交特征重要性不是随机噪音；
- 没有 PIT / 样本 / universe 合同问题。

若通过：

```text
只允许进入下一条“只读产品化设计”主线；
不得本轮直接改前端默认。
```

若不通过：

```text
收尾为数据与实验结论；
保留 raw archive / feature builder；
不进入前端策略。
```

验收 gate：

```text
phase_o6_orthogonal_ltr_decision_recorded
```

## 9. 执行者报告要求

每个 Phase 完成后，执行者必须写报告到：

```text
docs/tw_ltr_orthogonal_features_controlled/
```

报告必须包含：

- 做了什么；
- 使用了哪些脚本；
- 输入 artifact；
- 输出 artifact；
- row count；
- 日期范围；
- symbol 覆盖；
- hash 或 schema diff；
- 是否改变 control 合同；
- 是否触发停止条件；
- 下一步建议。

不得只给口头结论。

## 10. 审查者报告要求

审查者必须检查：

- 是否符合本主线目标；
- 是否只改变正交特征；
- 是否保持 Phase1C anchor 合同；
- 是否有未来函数；
- 是否有静默过滤；
- 是否有用户未授权的新规则；
- 是否符合用户第一性原则；
- 是否允许进入下一 Phase。

审查者每轮必须输出：

```text
通过 / 不通过 / 需要用户确认
```

若不通过或需要用户确认，必须明确指出阻塞原因。

## 11. 用户第一性原则

本主线服务的最终用户是投资小白，因此实验结果最终必须能转化为简单、清晰、准确、有价值的信息。

但在本主线阶段，优先级是：

```text
先证明正交数据是否真的有增量，再考虑展示。
```

禁止为了看起来有新功能而提前产品化。

最终若进入产品化，前端只能回答：

```text
这个策略相对原 simple LTR 是否更稳？
为什么更稳？
哪些新增信息起作用？
今天的模拟研究动作是否因此变化？
风险是否变大？
```

不能把复杂指标堆给用户。

## 12. 总结

本主线的核心纪律：

```text
第一版 simple LTR 是 control；
冻结旧 qlib 是输入；
同训练窗口、同样本、同标签、同模型、同回放；
只新增正交特征；
有问题就停下来讨论。
```

如果执行中发现任何“必须额外过滤、改标签、改窗口、改策略规则才有效”的情况，说明这已经不是本主线，应停止并交给用户决策。
