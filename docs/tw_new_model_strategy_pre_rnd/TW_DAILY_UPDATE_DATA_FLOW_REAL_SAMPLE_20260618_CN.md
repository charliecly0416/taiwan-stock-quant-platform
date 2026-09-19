# 台股日更全链路真实数据样本说明：2026-06-17 信号到 2026-06-18 前端

生成日期：2026-06-20

本文是 `TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md` 的真实样本补充版。它不再只讲流程，而是按模块写清楚：模块吃什么输入数据、字段是什么意思、本地真实样本值是多少、这些值如何变成下一环输入、`TW2330` 在哪一步停止，以及用 `TW3481` 展示一只实际进入前端候选的完整样本。

只读边界：本文只读本地 artifact，不触发抓数、provider publish、accepted latest switch、monitor write、broker、quick-trade、order、target position、target weight，也不调用 OpenAI。

## 1. 先说结论

本次本地可验证链路是：

```text
标准化价格 / qlib provider
-> qlib 基础模型 Model A
-> qlib top50 候选门
-> YZ2 LTR 特征包
-> LTR Model B 重新排序
-> 次日执行价格可用性检查
-> 2026-06-18 readonly strategy snapshot
-> 前端策略工作台可展示数据
```

关键日期：

| 名称 | 值 | 小白解释 |
|---|---:|---|
| `signal_asof` | `2026-06-17` | 模型用来打分的信号日期，可以理解为“昨天收盘后形成的研究判断”。 |
| `target_date` | `2026-06-18` | 前端策略快照面向的复盘日期，可以理解为“今天要看的策略候选”。 |
| `data_asof` | `2026-06-17` | 策略快照声明它依据的数据日期。 |

`TW2330` 的真实情况：

| 模块 | 是否有数据 | 具体结果 |
|---|---|---|
| 标准化价格 CSV | 有历史价格，但本地最后一行只到 `2026-06-01` | 没有 `2026-06-17` / `2026-06-18` 的 OHLCV。 |
| qlib Model A | 有 | `buy_score=-0.024562304811117618`，`score_rank=103`。 |
| qlib top50 门 | 没通过 | `candidate_rank` 为空，因为 rank 103 不在前 50。 |
| LTR 特征包 | 没有 | top50 外的股票不进入 LTR。 |
| LTR Model B | 没有 | 因为没有进入 LTR 特征包。 |
| readonly strategy snapshot | 没有进入 top candidates | 前端候选列表不会展示为前排候选。 |

所以，`2330` 不是“数据完全没有”，而是“基础模型给了分，但排名不够靠前，没过 qlib top50 候选门”。后续完整链路本文用 `TW3481` 展示，因为它在 `2026-06-17` 进入了 qlib top50，并被 LTR 排到候选第 1。

## 2. 模块 A：标准化价格数据

输入文件：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW2330.csv
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW3481.csv
```

价格 CSV 字段：

| 字段 | 含义 |
|---|---|
| `instrument` | 股票代码。 |
| `date` | 交易日。 |
| `open` | 当天开盘价。 |
| `high` | 当天最高价。 |
| `low` | 当天最低价。 |
| `close` | 当天收盘价。 |
| `volume` | 成交量，表示当天成交了多少股或单位。 |
| `vwap` | 成交量加权平均价，粗略理解为“当天平均成交价格”。 |
| `factor` | 复权因子，用来处理拆股、配股、除权息等价格可比性问题；这里是 `1.0`。 |

`TW2330` 本地最后一行真实价格：

```text
TW2330,2026-06-01,2355.0,2415.0,2350.0,2355.0,37791319,2368.75,1.0
```

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `date` | `2026-06-01` | 本地价格源里 `TW2330` 最新可读交易日。 |
| `open` | `2355.0` | 当天一开盘是 2355。 |
| `high` | `2415.0` | 当天最高到 2415。 |
| `low` | `2350.0` | 当天最低到 2350。 |
| `close` | `2355.0` | 当天收盘回到 2355。 |
| `volume` | `37791319` | 当天成交量约 3779 万。 |
| `vwap` | `2368.75` | 当天平均成交价约 2368.75。 |
| `factor` | `1.0` | 当前没有额外复权调整。 |

`TW3481` 本地最后一行真实价格：

```text
TW3481,2026-06-01,54.5,56.09999847412109,53.70000076293945,56.09999847412109,477616189,55.09999942779541,1.0
```

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `date` | `2026-06-01` | 本地价格源里 `TW3481` 最新可读交易日。 |
| `open` | `54.5` | 当天开盘 54.5。 |
| `high` | `56.09999847412109` | 当天最高约 56.10。 |
| `low` | `53.70000076293945` | 当天最低约 53.70。 |
| `close` | `56.09999847412109` | 当天收盘约 56.10。 |
| `volume` | `477616189` | 当天成交量约 4.776 亿。 |
| `vwap` | `55.09999942779541` | 当天平均成交价约 55.10。 |
| `factor` | `1.0` | 当前没有额外复权调整。 |

重要限制：本地没有 `2026-06-17,TW2330`、`2026-06-18,TW2330`、`2026-06-17,TW3481`、`2026-06-18,TW3481` 的价格行。因此本文不能给出“2026-06-18 的 2330 开高低收”，因为本地没有这条真实数据。

## 3. 模块 B：qlib provider 和基础 qlib 特征

qlib provider 路径：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

相关配置：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_generated_qlib_config.yaml
```

配置里可验证到：

| 配置项 | 值 | 含义 |
|---|---|---|
| `provider_uri` | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin` | qlib 模型读取的二进制行情库。 |
| `model.class` | `LGBModel` | 基础模型是 LightGBM 回归模型。 |
| `handler.class` | `Alpha158` | qlib 内置的 Alpha158 特征处理器。 |
| `market` | `tw_liquid_dyn` | 使用台湾股票动态流动性股票池。 |
| `benchmark` | `TWII` | 参考市场指数是台湾加权指数。 |
| `train` | `2018-01-01` 到 `2022-12-31` | 模型训练区间。 |
| `oos` | `2023-01-01` 到 `2026-05-07` | 样本外评分区间。 |

qlib provider 的底层日线字段可以从文件结构验证：

```text
features/tw3481/open.day.bin
features/tw3481/high.day.bin
features/tw3481/low.day.bin
features/tw3481/close.day.bin
features/tw3481/vwap.day.bin
features/tw3481/volume.day.bin
features/tw3481/factor.day.bin
```

这些字段和 CSV 里的 `open/high/low/close/vwap/volume/factor` 对应。qlib 的 `Alpha158` 会基于价格、成交量和滚动窗口构造大量技术特征，例如价格相对位置、成交量变化、5/10/20/60 日窗口、收益和波动。

当前限制：qlib Alpha158 的逐股票逐日特征值保存在 qlib 运行时数据结构和二进制 provider 中，当前本地链路没有明文导出 `2026-06-17 TW2330` 的 Alpha158 全量特征 CSV。所以本文对 qlib 部分只给出可验证的输入 provider、配置和模型输出，不伪造 qlib 内部逐特征值。

## 4. 模块 C：qlib 基础模型 Model A 输出

输入：

```text
source_artifact: qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
source_model_artifact: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl
```

输出文件：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/signals.csv
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
```

Model A manifest 关键值：

| 字段 | 值 | 含义 |
|---|---|---|
| `artifact_type` | `daily_model_signal` | 每日模型信号产物。 |
| `phase` | `YZ1` | 第一阶段模型信号。 |
| `model_family` | `qlib` | 来自 qlib 基础模型。 |
| `signal_asof` | `2026-06-17` | 信号日期。 |
| `score_source` | `frozen_e1_qlib_model.predict` | 用冻结模型预测，不重新训练。 |
| `candidate_k` | `50` | 只取 qlib 排名前 50 进入下一环。 |
| `row_count` | `150` | 这一天基础模型给 150 只股票打了分。 |
| `rank_source` | `daily qlib raw_score descending, instrument ascending tie-break` | 按 qlib 原始分从高到低排名，同分用代码排序。 |

`signals.csv` 字段：

| 字段 | 含义 |
|---|---|
| `date` | 模型信号日期。 |
| `instrument` | 股票代码。 |
| `model_id` / `model_name` | 模型标识。 |
| `model_family` | 模型族，这里是 `qlib`。 |
| `candidate_rank` | 如果进入 top50，这里等于 qlib 候选排名；没进 top50 就为空。 |
| `buy_score` | 模型分数。名字叫 buy_score，但这里只是研究排序分，不是买入指令。 |
| `raw_score` | 原始模型分数。Model A 中等于 `buy_score`。 |
| `score_rank` | 按 `buy_score` 从高到低的全体排名。 |
| `full_qlib_rank` | qlib 全体 150 只里的排名。 |
| `signal_asof` / `available_at` | 信号日期和下游可用日期。 |

`TW2330` 的 Model A 真实行：

```text
2026-06-17,TW2330,e4_frozen_qlib_2018_2022,e4_frozen_qlib_2018_2022,qlib,,-0.024562304811117618,-0.024562304811117618,103,103,2026-06-17,2026-06-17,qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin,data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl,qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `instrument` | `TW2330` | 这条是 2330。 |
| `buy_score` | `-0.024562304811117618` | qlib 模型给出的研究分数，负数表示在当天 150 只里不靠前。 |
| `raw_score` | `-0.024562304811117618` | 原始分数，和 buy_score 相同。 |
| `score_rank` | `103` | 150 只股票里排第 103。 |
| `full_qlib_rank` | `103` | qlib 全排名也是第 103。 |
| `candidate_rank` | 空 | 没进入 top50，所以没有候选排名。 |

`TW3481` 的 Model A 真实行：

```text
2026-06-17,TW3481,e4_frozen_qlib_2018_2022,e4_frozen_qlib_2018_2022,qlib,31,0.0748663325254153,0.0748663325254153,31,31,2026-06-17,2026-06-17,qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin,data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl,qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `instrument` | `TW3481` | 完整链路样本股票。 |
| `buy_score` | `0.0748663325254153` | qlib 模型分数为正，比 2330 靠前。 |
| `score_rank` | `31` | 150 只里排第 31。 |
| `full_qlib_rank` | `31` | qlib 全排名第 31。 |
| `candidate_rank` | `31` | 进入 qlib top50，可以送到 LTR。 |

## 5. 模块 D：qlib top50 候选门

输入是 Model A `signals.csv` 的 150 行 qlib 分数和排名。规则很简单：只让 `full_qlib_rank <= 50` 的股票进入 LTR 特征包。

| 股票 | `full_qlib_rank` | 是否进入 top50 | 下一步 |
|---|---:|---|---|
| `TW2330` | `103` | 否 | 链路停止在 Model A，不进入 LTR。 |
| `TW3481` | `31` | 是 | 进入 YZ2 LTR 特征包。 |

这不是 bug，而是候选门的设计：LTR 只在 qlib top50 内重排，不会从 top50 外把股票捞回来。

## 6. 模块 E：YZ2 LTR 特征包

输入：

```text
universe_source: data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
feature_schema_path: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv
```

输出：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/features.csv
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json
```

manifest 关键值：

| 字段 | 值 | 含义 |
|---|---:|---|
| `artifact_type` | `YZ2StrictE4OrthogonalFeaturePackage` | LTR 使用的严格特征包。 |
| `signal_asof` | `2026-06-17` | 特征对应信号日期。 |
| `row_count` | `50` | 只包含 qlib top50。 |
| `feature_schema_column_count` | `78` | LTR 训练特征有 78 个。 |
| `coverage_ratio` | `1.0` | 50 只候选都有特征。 |
| `pit_violation_count` | `0` | 没发现未来数据穿越。 |
| `no_fallback` | `true` | 没用临时兜底特征伪造缺失值。 |
| `missing_symbols` | `[]` | top50 没有缺失股票。 |

`TW2330` 在这个文件里不存在，因为它没有过 top50 门。`TW3481` 的 LTR 特征真实行按类别如下。

### 6.1 qlib 排名和候选状态

| 字段 | 值 | 怎么来的 | 小白解释 |
|---|---:|---|---|
| `qlib_score_raw` | `0.0748663325254153` | Model A 输出 | qlib 原始分。 |
| `qlib_rank` | `31` | Model A 输出 | qlib 排第 31。 |
| `qlib_score_percentile_by_date` | `0.8` | 当日分位数 | 大约处于前 20% 区间。 |
| `qlib_score_zscore_by_date` | `0.709438000669807` | 当日标准化 | 比当天平均分高约 0.71 个标准差。 |
| `rank_change_1d` / `3d` / `5d` | `0.0 / 0.0 / 0.0` | 排名变化 | 近 1/3/5 日排名变化为 0。 |
| `top10_flag` / `top30_flag` / `top50_flag` | `0 / 0 / 1` | 排名判断 | 不在 top10/top30，但在 top50。 |
| `top30_streak` / `top50_streak` | `0 / 1` | 连续状态 | 当前 top50 连续状态为 1。 |

### 6.2 价格趋势和技术指标

| 字段 | 值 | 怎么构建 | 小白解释 |
|---|---:|---|---|
| `MA5` | `49.880000305175784` | 最近 5 个交易日平均收盘价 | 短期平均价格约 49.88。 |
| `MA10` | `45.81500015258789` | 最近 10 个交易日平均收盘价 | 两周平均价格约 45.82。 |
| `MA20` | `39.40750007629394` | 最近 20 个交易日平均收盘价 | 一个月平均价格约 39.41。 |
| `MA60` | `30.560833326975505` | 最近 60 个交易日平均收盘价 | 一个季度平均价格约 30.56。 |
| `RSI14` | `74.1217841066629` | 14 日 RSI | 动能偏强；数值高表示近期涨势强。 |
| `MACD` | `6.313494812713138` | 趋势动量指标 | 正值较大，说明趋势动量偏强。 |
| `Bollinger_position` | `1.0025850136118906` | 价格在布林带的位置 | 接近或略高于上轨，说明价格位置偏高。 |
| `ret20` | `1.2620967822566116` | 近 20 日收益率 | 约 +126.2%，最近 20 日涨幅很大。 |
| `volatility20` | `0.06433702840311349` | 近 20 日波动率 | 最近波动水平较高。 |
| `volume_ratio20` | `0.5910153184869338` | 当前成交量相对 20 日均量 | 小于 1，当前量能低于近 20 日平均代理值。 |
| `avg_trading_value_20d` | `31956668684.184307` | 近 20 日平均成交金额 | 平均每天成交金额约 319.57 亿。 |
| `volume_stability20` | `0.6884878475830002` | 成交量稳定性 | 量能稳定度的模型特征。 |
| `missing_rate20` | `0.0` | 近 20 日缺失率 | 没有缺失交易数据。 |
| `suspension_proxy` | `0.0` | 停牌代理变量 | 没有明显停牌代理信号。 |
| `slippage_proxy` | `0.0427807090278042` | 滑点代理变量 | 交易摩擦代理值。 |

`TW3481` 呈现出 `MA5 > MA10 > MA20 > MA60`，`ret20` 很高，RSI 也高。这类特征帮助 LTR 判断“这个 top50 候选是否仍然值得排在前面”。

### 6.3 大盘环境

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `TWII_ret20` | `0.09212990915419761` | 台湾加权指数近 20 日约 +9.21%。 |
| `TWII_ret60` | `0.23098753158317442` | 台湾加权指数近 60 日约 +23.10%。 |
| `TWII_close_vs_MA60` | `0.13726620933348244` | 大盘收盘价高于 60 日均线约 13.73%。 |
| `TWII_close_vs_MA120` | `0.25430109229959585` | 大盘收盘价高于 120 日均线约 25.43%。 |
| `market_volatility20` | `0.017247299627174886` | 大盘近 20 日波动水平。 |
| `market_drawdown60` | `-0.013487217226779924` | 大盘近 60 日回撤约 -1.35%。 |
| `market_breadth20` | `0.0` | 市场广度代理值。 |

### 6.4 三大法人资金流

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `foreign_net_buy` | `163249451.0` | 外资当期净买入约 1.632 亿。 |
| `investment_trust_net_buy` | `7444.0` | 投信当期小幅净买入。 |
| `dealer_net_buy` | `1784101.0` | 自营商当期净买入约 178 万。 |
| `institutional_total_net_buy` | `165040996.0` | 三大法人合计净买入约 1.650 亿。 |
| `foreign_net_buy_roll3` | `-94432896.0` | 外资 3 日合计净卖出约 9443 万。 |
| `foreign_net_buy_roll5` | `-301356148.0` | 外资 5 日合计净卖出约 3.014 亿。 |
| `foreign_net_buy_roll10` | `-249862200.0` | 外资 10 日合计净卖出约 2.499 亿。 |
| `institutional_total_net_buy_roll1` | `165040996.0` | 三大法人 1 日合计净买入。 |
| `institutional_total_net_buy_roll3` | `-112547359.0` | 三大法人 3 日合计净卖出约 1.125 亿。 |
| `institutional_total_net_buy_roll5` | `-335137590.0` | 三大法人 5 日合计净卖出约 3.351 亿。 |
| `institutional_total_net_buy_roll10` | `-278268834.0` | 三大法人 10 日合计净卖出约 2.783 亿。 |
| `institutional_total_net_buy_streak` | `1.0` | 当前连续方向代理值为 1。 |
| `institutional_missing_flag` / `delay_flag` | `0.0 / 0.0` | 法人数据未缺失、未标记延迟。 |

这里能看出：`roll1` 为正但 `roll3/5/10` 为负，说明“当天买入”与“过去几天累计”并不一致。LTR 会把这种结构也当成特征学习。

### 6.5 融资融券

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `margin_balance` | `440670.0` | 融资余额，粗略理解为借钱买股票的余额。 |
| `margin_balance_change` | `9483.0` | 融资余额增加 9483。 |
| `short_balance` | `15446.0` | 融券余额，粗略理解为借股票卖出的余额。 |
| `short_balance_change` | `-537.0` | 融券余额减少 537。 |
| `margin_balance_change_roll3` | `29250.0` | 融资 3 日累计增加 29250。 |
| `margin_balance_change_roll5` | `11299.0` | 融资 5 日累计增加 11299。 |
| `margin_balance_change_roll10` | `35793.0` | 融资 10 日累计增加 35793。 |
| `short_balance_change_roll3` | `-727.0` | 融券 3 日累计减少 727。 |
| `short_balance_change_roll5` | `-6381.0` | 融券 5 日累计减少 6381。 |
| `short_balance_change_roll10` | `1678.0` | 融券 10 日累计增加 1678。 |
| `margin_direction_proxy` | `1.0` | 融资方向偏增加。 |
| `short_direction_proxy` | `-1.0` | 融券方向偏减少。 |
| `margin_short_divergence_proxy` | `2.0` | 融资和融券方向分化较明显。 |
| `margin_short_missing_flag` / `delay_flag` | `0.0 / 0.0` | 融资融券数据未缺失、未标记延迟。 |

## 7. 模块 F：LTR Model B 输出

输入：

```text
source_artifact: data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json
source_model_artifact: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
```

输出：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/signals.csv
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
```

manifest 关键值：

| 字段 | 值 | 含义 |
|---|---|---|
| `phase` | `YZ2` | 第二阶段模型信号。 |
| `model_family` | `ltr` | Learning-to-Rank 排序模型。 |
| `score_source` | `E3_LGBMRanker.predict_on_YZ2_strict_E4_orthogonal_package` | 用冻结 LTR 模型对特征包打分。 |
| `rank_source` | `LTR score_rank within YZ1 Model A qlib top50; candidate/full_qlib_rank preserved from Model A` | LTR 只在 qlib top50 内重新排序。 |
| `row_count` | `50` | 只输出 top50 候选。 |
| `no_training` / `no_tuning` | `true / true` | 日更时没有重新训练或调参。 |

`TW2330` 在 Model B 文件中不存在，因为它没进入 top50。

`TW3481` 的 Model B 真实行：

```text
2026-06-17,TW3481,e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025,e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025,ltr,31,1.4873123416297531,1.4873123416297531,1,31,2026-06-17,2026-06-17,data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json,data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl,data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json
```

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `candidate_rank` | `31` | 保留 qlib 的原始候选排名。 |
| `buy_score` | `1.4873123416297531` | LTR 给出的新排序分。 |
| `raw_score` | `1.4873123416297531` | LTR 原始分。 |
| `score_rank` | `1` | 在 qlib top50 内被 LTR 排到第 1。 |
| `full_qlib_rank` | `31` | qlib 全排名仍然是第 31，没有被改写。 |

核心解释：qlib 说 `TW3481` 在 150 只里排第 31，可以进候选；LTR 说在这 50 个候选里面，结合趋势、资金流、融资融券、大盘等 78 个特征后，`TW3481` 排第 1。LTR 没有说“明天一定涨”，也不是交易指令。

## 8. 模块 G：次日执行价格可用性检查

输入：

```text
model_b_source: data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
price_source: qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

输出：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/manifest.json
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/price_availability_audit.csv
```

manifest 关键值：

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `signal_asof` | `2026-06-17` | 检查的是 6/17 信号。 |
| `target_next_trading_day` | `2026-06-18` | 想检查 6/18 的次日开盘/收盘价格是否已经有了。 |
| `row_count` | `50` | 检查 LTR top50 的 50 只。 |
| `next_open_available_count` | `0` | 50 只里没有任何一只能拿到 6/18 开盘价。 |
| `next_close_available_count` | `0` | 50 只里没有任何一只能拿到 6/18 收盘价。 |
| `close_on_or_before_signal_asof_available_count` | `50` | 50 只都有“信号日或之前”的最后可用收盘价。 |
| `missing_next_open_count` | `50` | 50 只都缺 6/18 开盘价。 |
| `status` | `execution_price_unavailable` | 次日执行价格不可用。 |
| `recommended_gate` | `blocked_before_yz3` | 应阻塞进入需要真实执行价的下一阶段。 |
| `no_fallback_to_next_close` / `no_fallback_to_signal_close` | `true / true` | 不用其他价格冒充次日开盘价。 |

`TW3481` 的价格可用性真实行：

```text
2026-06-17,TW3481,2026-06-18,,False,qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW3481.csv,False,,,56.09999847412109,2026-06-01,False,False,True,False,False,False,execution_price_unavailable
```

| 字段 | 值 | 小白解释 |
|---|---:|---|
| `target_next_trading_day` | `2026-06-18` | 目标次日是 6/18。 |
| `price_source_has_target_next_day_row` | `False` | 价格 CSV 没有 6/18 这一行。 |
| `next_trading_day_open` / `close` | 空 / 空 | 没有 6/18 开盘价和收盘价。 |
| `close_on_or_before_signal_asof` | `56.09999847412109` | 能拿到的最后一个不晚于信号日的收盘价。 |
| `close_on_or_before_signal_asof_date` | `2026-06-01` | 这个最后可用收盘价来自 6/1，不是 6/17。 |
| `next_open_available` / `next_close_available` | `False / False` | 次日价格不可用。 |
| `signal_close_available` | `True` | 至少有信号日前的最后可用收盘价。 |
| `status` | `execution_price_unavailable` | 不能进入依赖真实次日价格的执行/回测阶段。 |

这一步非常重要：即使模型和候选排名已经有了，也不能把 6/1 的价格冒充 6/18 的执行价格。

## 9. 模块 H：readonly strategy snapshot 和前端候选

输入：

```text
source_model_signal_manifest: data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
source_feature_manifest: data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json
source_model_a_manifest: data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
```

输出：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-18/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

snapshot 关键值：

| 字段 | 值 | 小白解释 |
|---|---|---|
| `asof` | `2026-06-18` | 快照日期。 |
| `data_asof` | `2026-06-17` | 使用 6/17 的数据。 |
| `signal_asof` | `2026-06-17` | 使用 6/17 的模型信号。 |
| `target_date` | `2026-06-18` | 面向 6/18 的策略工作台展示。 |
| `model_id` | `e4_frozen_qlib_2023_2025_ltr` | 产品显示模型 ID。 |
| `canonical_model_id` | `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025` | 规范模型 ID。 |
| `base_model_id` | `e4_frozen_qlib_2018_2022` | 基础 qlib 模型。 |
| `strategy_rule` | `top50_exit_one_worst_sell` | 策略规则名称。 |
| `candidate_boundary` | `qlib_top50` | 候选边界是 qlib top50。 |
| `ranking_source` | `ltr_rerank_within_qlib_top50` | 排名来自 LTR 在 top50 内重排。 |
| `readonly_only` / `not_order` / `not_target_position` | `true / true / true` | 只读研究快照，不是订单或仓位。 |

前端可展示的 top candidates 前 10：

| 前端排名 | 股票 | qlib 候选排名 | LTR 排名 | qlib 全排名 | LTR 分数 |
|---:|---|---:|---:|---:|---:|
| 1 | `TW3481` | `31` | `1` | `31` | `1.4873123416297531` |
| 2 | `TW2303` | `4` | `2` | `4` | `0.6735604888652592` |
| 3 | `TW2327` | `3` | `3` | `3` | `0.5680202383483134` |
| 4 | `TW4971` | `12` | `4` | `12` | `0.438856040558897` |
| 5 | `TW3189` | `33` | `5` | `33` | `0.3861511639212199` |
| 6 | `TW6446` | `7` | `6` | `7` | `0.358085568621519` |
| 7 | `TW6147` | `25` | `7` | `25` | `0.3025788685533739` |
| 8 | `TW8358` | `17` | `8` | `17` | `0.269782813037722` |
| 9 | `TW3131` | `44` | `9` | `44` | `0.2477566635627043` |
| 10 | `TW4991` | `36` | `10` | `36` | `0.2404722325502988` |

`TW2330` 不在这张表里，因为它的 qlib 全排名是 103，早在 top50 候选门就停止了。

前端应该展示的语义：这是 readonly candidate，不是买入指令；排名第一表示 LTR 在 qlib top50 内排第一；不表示明天一定上涨；不表示系统已经有真实 2026-06-18 执行价；不表示可以下单。

## 10. 模块 I：策略规则和 OrderIntent 的边界

当前 snapshot 的策略规则名是 `top50_exit_one_worst_sell`，但本次 `2026-06-18` readonly snapshot 里：

```text
exit_candidates: []
```

snapshot 自带解释：

```text
exit candidates are not fabricated because no trusted live holding state was supplied to this snapshot publisher
```

小白解释：卖出候选需要可信的当前持仓状态。如果没有可信持仓，系统不会编造“要卖哪只”。

当前仓库里另有 OrderIntent 样例：

```text
data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T041436Z/order_intents.csv
```

但它是 `signal_date=2026-05-07` 的 D1 样例，不是本文 `2026-06-17 -> 2026-06-18` 的今日链路产物。因此只能作为字段格式示例，不能说成今天的策略意图。

## 11. 模块 J：Agent prompt context 的当前证据状态

预期产品链路里，Agent 应该吃 DailyAgentPromptArtifact。它通常会把当前策略快照、候选排名和分数、策略解释、模型日期和只读边界装入 prompt。

本次只读检查发现：

```text
data_tw/artifacts/agent_daily_prompt/latest.json 不存在
data_tw/artifacts/agent_daily_prompt/ 目录不存在
```

仓库里存在的是 golden samples：

```text
data_tw/golden_samples/agent_daily_prompt/...
data_tw/golden_samples/agent_daily_prompt_builder/...
```

因此本文不能给出真实 `2026-06-18` Agent prompt artifact 的输入 JSON。能确定的是：如果 Agent 要回答 `TW3481` 为什么排名第一，它应该引用 `readonly_strategy_snapshot/2026-06-18` 和 `YZ2 LTR` 证据；如果问 `2330`，它应该回答“2330 在 qlib Model A 排第 103，未进入 top50，因此不在当前 LTR 候选和前端 top candidates 中”。

## 12. 2330 单股链路复盘

| 环节 | 输入 | 输出 | 是否继续 |
|---|---|---|---|
| 标准化价格 | `TW2330.csv` | 最新本地价格是 `2026-06-01 close=2355.0` | 可作为历史价格源，但缺 6/17 和 6/18。 |
| qlib provider | `option_c_150_qlib_bin` | qlib 可生成模型输入并产出 Model A 分数 | 继续到 Model A。 |
| Model A | 冻结 qlib 模型 | `buy_score=-0.024562304811117618`，`rank=103` | 不继续。 |
| top50 门 | Model A 排名 | `candidate_rank` 为空 | 停止。 |
| LTR 特征 | 只接收 top50 | 无 `TW2330` 行 | 停止。 |
| LTR Model B | 只接收 LTR 特征 | 无 `TW2330` 行 | 停止。 |
| 前端 snapshot | 只接收 LTR 候选 | `TW2330` 不在 top candidates | 不展示为当前前排候选。 |

一句话解释：2330 这一天不是没有被基础模型看见，而是基础模型看完后只排第 103；系统规定只有前 50 才进入更细的 LTR 排序，所以 2330 没有后续 LTR 分数，也不会出现在 6/18 前端候选榜。

## 13. TW3481 完整链路复盘

| 环节 | 输入 | 输出 | 是否继续 |
|---|---|---|---|
| 标准化价格 | `TW3481.csv` | 最新本地价格是 `2026-06-01 close=56.09999847412109` | 可作为历史价格源，但缺 6/17 和 6/18。 |
| qlib provider | `option_c_150_qlib_bin` | qlib 读取 open/high/low/close/vwap/volume/factor bin | 继续到 Model A。 |
| Model A | 冻结 qlib 模型 | `buy_score=0.0748663325254153`，`full_qlib_rank=31` | 进入 top50。 |
| top50 门 | Model A 排名 | `candidate_rank=31` | 继续到 LTR 特征。 |
| LTR 特征 | qlib 分数、价格趋势、资金流、融资融券、大盘环境 | 78 个特征，`coverage_ratio=1.0` | 继续到 LTR Model B。 |
| LTR Model B | 78 个特征 + 冻结 LTR 模型 | `buy_score=1.4873123416297531`，`score_rank=1` | 进入前端候选。 |
| 执行价格检查 | 目标 `2026-06-18` 价格 | `execution_price_unavailable` | 阻塞真实执行价阶段。 |
| readonly snapshot | LTR top candidates | `TW3481` 排前端候选第 1 | 前端可展示为只读研究候选。 |

一句话解释：TW3481 先被 qlib 选进前 50，再因为趋势、资金流、融资融券和大盘等 LTR 特征组合，被 LTR 排到候选第 1；但本地没有 2026-06-18 的真实执行价格，所以它仍然只是只读研究候选，不是可执行交易指令。

## 14. 哪些数据进入 qlib，哪些数据进入 LTR

qlib Model A 输入：

| 数据 | 路径 | 是否有明文样本 |
|---|---|---|
| qlib provider | `option_c_150_qlib_bin` | 二进制 bin，可验证字段文件。 |
| 原始日线字段 | open/high/low/close/vwap/volume/factor | CSV 和 bin 均可验证。 |
| qlib 特征处理器 | `Alpha158` | 配置可验证。 |
| qlib 模型 | `phasee1_frozen_qlib_model.pkl` | 模型文件可验证。 |

进入 qlib 的是日线价格、成交量、复权因子等基础市场数据，再由 `Alpha158` 在 qlib 内部生成技术特征。当前没有明文导出某日某股票全部 Alpha158 值。

LTR Model B 输入：

| 数据 | 样本值 |
|---|---|
| qlib 分数 | `TW3481 qlib_score_raw=0.0748663325254153` |
| qlib 排名 | `TW3481 qlib_rank=31` |
| 技术指标 | `MA5=49.880000305175784`，`RSI14=74.1217841066629`，`ret20=1.2620967822566116` |
| 大盘环境 | `TWII_ret20=0.09212990915419761`，`market_volatility20=0.017247299627174886` |
| 法人资金 | `institutional_total_net_buy=165040996.0` |
| 融资融券 | `margin_balance=440670.0`，`short_balance=15446.0` |

LTR 的输入是明文 CSV，一共 50 行、78 个训练特征。它的职责不是重新从全市场选股，而是在 qlib top50 内重排。

## 15. 后续为了讲得更细还缺什么

如果要把这份文档升级到“qlib 内部也逐列逐值可解释”，建议新增一个只读开发任务：

```text
导出 qlib Alpha158 单日单股明细：
- 输入：provider_uri、instrument、date
- 输出：alpha158_feature_values.csv
- 样本：2026-06-17 TW2330、2026-06-17 TW3481
- 禁止：重新训练、重新打分、provider publish、accepted latest switch
```

导出后可以补齐 qlib 内部 Alpha158 每一列的真实值、每个 qlib 特征对分数的解释、以及 2330 被排 103 的逐特征原因。当前文档已经覆盖可验证的标准化价格、qlib 输出、LTR 明文特征、LTR 输出、执行价格可用性、readonly snapshot 和前端候选。

## 16. 给执行者和审查者的使用方式

执行者后续实现或调试时，不能只说“模型产生分数”。必须至少写清楚：输入 artifact 路径、输入字段、样本股票真实行、输出字段、样本输出值、是否进入下一模块、如果没进入停止原因是什么。

审查者审查时，重点看：有没有把缺失的 2026-06-18 价格伪造成真实价格；有没有把 readonly candidate 说成买卖建议；有没有把 2330 说成进入 LTR；有没有把 LTR `score_rank=1` 误解成 qlib `full_qlib_rank=1`；有没有绕过 qlib top50 候选门；有没有用 OrderIntent 样例冒充 2026-06-18 今日意图；有没有伪造 Agent DailyAgentPromptArtifact latest。

本文的核心事实可以浓缩为：

```text
2330: qlib rank 103 -> 不进 top50 -> 不进 LTR -> 不进前端 top candidates。
TW3481: qlib rank 31 -> 进 top50 -> LTR rank 1 -> 进入 2026-06-18 readonly 前端候选第 1。
但 2026-06-18 真实执行价格缺失，所以只能做只读研究展示，不能做执行或交易结论。
```
