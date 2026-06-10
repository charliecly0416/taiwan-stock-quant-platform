<template>
  <div class="tw-stock-sim-account">
    <div class="topbar">
      <div>
        <h2>台股模拟账户</h2>
        <div class="subline">手动记录模拟成交，用真实日线收盘价复盘研究判断。</div>
      </div>
      <div class="top-actions">
        <a-button @click="refreshAll" :loading="loading">
          <a-icon type="reload" /> 刷新模拟账户
        </a-button>
      </div>
    </div>

    <a-alert
      class="boundary-alert"
      type="info"
      show-icon
      message="本页面仅用于台股研究信号的历史与模拟验证，不连接券商，不提交真实订单，不构成投资建议。"
    />
    <a-alert
      v-if="pendingSignalDraft"
      class="state-alert"
      type="success"
      show-icon
      :message="pendingSignalDraftMessage"
    />
    <a-alert
      v-if="safetyError"
      class="state-alert"
      type="error"
      show-icon
      :message="safetyError"
    />
    <a-alert
      v-if="error"
      class="state-alert"
      type="warning"
      show-icon
      :message="error"
    />

    <a-spin :spinning="loading && !accountsLoaded">
      <a-card v-if="!hasAccount" class="sim-card" :bordered="false">
        <template slot="title">创建模拟账户</template>
        <div class="create-form">
          <a-input v-model="accountForm.name" placeholder="台股研究模拟账户" />
          <a-input-number v-model="accountForm.initial_cash" :min="10000" :step="100000" style="width: 180px" />
          <a-button type="primary" @click="createAccount" :loading="creatingAccount">
            <a-icon type="plus" /> 创建模拟账户
          </a-button>
        </div>
      </a-card>

      <template v-else>
        <a-card class="sim-card" :bordered="false">
          <template slot="title">账户概览</template>
          <div class="account-toolbar">
            <a-select v-model="activeAccountUid" style="min-width: 260px" @change="handleAccountChange">
              <a-select-option v-for="item in accounts" :key="item.account_uid" :value="item.account_uid">
                {{ item.name || item.account_uid }}
              </a-select-option>
            </a-select>
            <a-tag color="green">simulation_only=true</a-tag>
            <a-tag color="blue">source_type=manual</a-tag>
          </div>
          <div class="metric-grid">
            <div class="metric-card">
              <span>账户名称</span>
              <strong>{{ account.name || '-' }}</strong>
              <small>{{ account.currency || 'TWD' }}</small>
            </div>
            <div class="metric-card">
              <span>初始资金</span>
              <strong>{{ money(account.initial_cash) }}</strong>
              <small>TWD</small>
            </div>
            <div class="metric-card">
              <span>现金</span>
              <strong>{{ money(account.cash) }}</strong>
              <small>TWD</small>
            </div>
            <div class="metric-card">
              <span>持仓市值</span>
              <strong>{{ money(account.market_value) }}</strong>
              <small>按最新可用收盘价</small>
            </div>
            <div class="metric-card">
              <span>总权益</span>
              <strong>{{ money(account.total_equity) }}</strong>
              <small>TWD</small>
            </div>
            <div class="metric-card">
              <span>累计收益</span>
              <strong>{{ signedMoney(account.total_pnl) }}</strong>
              <small>{{ percent(account.total_return) }}</small>
            </div>
          </div>
        </a-card>

        <a-card class="sim-card" :bordered="false">
          <template slot="title">绩效复盘</template>
          <a-alert
            class="state-alert"
            type="info"
            show-icon
            message="历史/模拟结果，不代表未来收益。价格按最新可用收盘价估算；价格缺失或日期滞后时请先复核数据。"
          />
          <div class="metric-grid">
            <div class="metric-card">
              <span>持仓浮动盈亏</span>
              <strong>{{ signedMoney(performanceSummary.unrealized_pnl) }}</strong>
              <small>最新可用收盘价</small>
            </div>
            <div class="metric-card">
              <span>已实现盈亏 MVP</span>
              <strong>{{ signedMoney(performanceSummary.realized_pnl) }}</strong>
              <small>卖出成交按移动平均成本估算</small>
            </div>
            <div class="metric-card">
              <span>胜负笔数 MVP</span>
              <strong>{{ performanceSummary.win_count }} / {{ performanceSummary.loss_count }}</strong>
              <small>基于已实现盈亏正负</small>
            </div>
            <div class="metric-card">
              <span>累计费用</span>
              <strong>{{ money(performanceSummary.total_fee) }}</strong>
              <small>手续费</small>
            </div>
            <div class="metric-card">
              <span>累计交易税</span>
              <strong>{{ money(performanceSummary.total_tax) }}</strong>
              <small>卖出模拟成交</small>
            </div>
            <div class="metric-card">
              <span>成交来源</span>
              <strong>{{ performanceSummary.trade_count }}</strong>
              <small>manual {{ sourceTypeCounts.manual }} / qlib {{ sourceTypeCounts.qlib_rank }} / cross {{ sourceTypeCounts.cross_analysis }} / agent_research {{ sourceTypeCounts.agent_research }}</small>
            </div>
          </div>
        </a-card>

        <a-card class="sim-card" :bordered="false">
          <template slot="title">策略候选（模拟验证）</template>
          <a-alert
            class="state-alert"
            type="info"
            show-icon
            message="低换手规则：qlib 先给出研究候选池，QuantDinger 趋势和交叉分析再做技术确认或风险复盘；这里只生成模拟草稿，不是交易指令。"
          />
          <div class="combo-overview">
            <div class="combo-card combo-card--primary">
              <span>组合策略结论</span>
              <strong>{{ comboSummary.primaryLabel }}</strong>
              <small>{{ comboSummary.primaryHint }}</small>
            </div>
            <div class="combo-card">
              <span>模拟新增观察</span>
              <strong>{{ comboSummary.buyCount }}</strong>
              <small>未持有且多信号一致</small>
            </div>
            <div class="combo-card">
              <span>持仓风险复盘</span>
              <strong>{{ comboSummary.riskCount }}</strong>
              <small>排名掉队、趋势转弱或历史验证不佳</small>
            </div>
            <div class="combo-card">
              <span>人工复核</span>
              <strong>{{ comboSummary.reviewCount }}</strong>
              <small>模型、趋势或资料质量存在分歧</small>
            </div>
          </div>
          <div class="combo-rules">
            <a-tag color="blue">qlib 决定候选池</a-tag>
            <a-tag color="green">QuantDinger 做技术确认</a-tag>
            <a-tag color="orange">分歧进入人工复核</a-tag>
            <a-tag color="purple">MA/RSI/MACD/Bollinger 按需验证</a-tag>
          </div>
          <div class="today-advice-panel">
            <div class="today-advice-head">
              <div>
                <strong>今日模拟操作建议</strong>
                <span>{{ selectedPolicyProfile.description }}</span>
              </div>
              <a-select v-model="strategyPolicyProfile" size="small" style="width: 180px">
                <a-select-option v-for="item in strategyPolicyOptions" :key="item.key" :value="item.key">{{ item.label }}</a-select-option>
              </a-select>
            </div>
            <a-alert
              class="state-alert compact-alert"
              type="info"
              show-icon
              :message="todayStrategyAdvice.summary"
            />
            <div v-if="todayStrategyAdvice.items.length" class="today-advice-list">
              <div v-for="item in todayStrategyAdvice.items" :key="`advice-${item.side}-${item.symbol}`" class="today-advice-item">
                <div class="today-advice-main">
                  <a-tag :color="item.color">{{ item.sideLabel }}</a-tag>
                  <strong>{{ item.symbol }}</strong>
                  <span>{{ adviceQuantityText(item) }}</span>
                  <span>{{ adviceAmountText(item) }}</span>
                </div>
                <div class="today-advice-reason">{{ item.reason }}</div>
                <div class="strategy-actions">
                  <a-button v-if="item.side !== 'hold' && item.quantity > 0" size="small" @click="prefillPolicyAdviceDraft(item)">填入模拟草稿</a-button>
                  <a-button v-if="item.sourceItem && item.sourceItem.canValidate" size="small" :loading="validatingBacktestSymbol === item.symbol" @click="validateStrategyBacktest(item.sourceItem)">只读历史验证</a-button>
                </div>
              </div>
            </div>
            <div v-else class="empty-note">当前策略没有明确模拟动作，先观察。</div>
          </div>
          <div class="module-grid">
            <div class="module-box">
              <div class="module-title">
                <strong>策略规则中心</strong>
                <a-select v-model="strategyRuleProfile" size="small" style="width: 120px">
                  <a-select-option value="conservative">稳健</a-select-option>
                  <a-select-option value="balanced">平衡</a-select-option>
                  <a-select-option value="active">积极</a-select-option>
                </a-select>
              </div>
              <div class="rule-list">
                <div v-for="rule in activeRuleSummary" :key="rule.label" class="rule-item">
                  <span>{{ rule.label }}</span>
                  <strong>{{ rule.value }}</strong>
                </div>
              </div>
            </div>
            <div class="module-box">
              <div class="module-title"><strong>今日复盘队列</strong><span>{{ actionQueue.length }} 项</span></div>
              <div v-if="actionQueue.length" class="module-list">
                <div v-for="item in actionQueue" :key="`queue-${item.queueType}-${item.symbol}`" class="queue-item">
                  <div class="queue-head">
                    <strong>{{ item.symbol }}</strong>
                    <a-tag :color="item.queueColor">{{ item.queueLabel }}</a-tag>
                  </div>
                  <span>{{ item.queueReason }}</span>
                  <div class="strategy-actions" v-if="item.queueSide || item.canValidate">
                    <a-button v-if="item.queueSide" size="small" @click="prefillStrategyDraft(item, item.queueSide)">填入模拟草稿</a-button>
                    <a-button v-if="item.canValidate" size="small" :loading="validatingBacktestSymbol === item.symbol" @click="validateStrategyBacktest(item)">只读历史验证</a-button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-note">暂无优先复盘项</div>
            </div>
            <div class="module-box">
              <div class="module-title"><strong>历史验证证据</strong><span>{{ validatedBacktestItems.length }} 项</span></div>
              <div v-if="validatedBacktestItems.length" class="module-list">
                <div v-for="item in validatedBacktestItems" :key="`evidence-${item.symbol}`" class="queue-item">
                  <div class="queue-head">
                    <strong>{{ item.symbol }}</strong>
                    <a-tag :color="item.backtestColor">{{ item.backtestText }}</a-tag>
                  </div>
                  <span>{{ item.evidenceText }}</span>
                </div>
              </div>
              <div v-else class="empty-note">尚未对候选执行只读历史验证</div>
            </div>
          </div>
          <div class="strategy-grid">
            <div class="strategy-box">
              <div class="strategy-title"><strong>模拟买入候选</strong><span>Top30 未持有，且技术确认较好的标的优先</span></div>
              <div v-if="strategyBuyCandidates.length" class="strategy-list">
                <div v-for="item in strategyBuyCandidates" :key="`buy-${item.symbol}`" class="strategy-item">
                  <div class="strategy-item-head">
                    <strong>{{ item.symbol }}</strong>
                    <a-tag :color="item.matchColor">模拟匹配度 {{ item.confidence }}%</a-tag>
                  </div>
                  <div class="signal-tags">
                    <a-tag :color="item.actionPlanColor">{{ item.actionPlanLabel }}</a-tag>
                    <a-tag :color="item.positionRiskColor">位置 {{ item.positionRiskLabel }}</a-tag>
                    <a-tag :color="item.backtestColor">{{ item.backtestText }}</a-tag>
                  </div>
                  <div class="strategy-evidence-line">{{ item.strategyEvidence }}</div>
                  <span>{{ item.strategySummary }}</span>
                  <div class="strategy-actions">
                    <a-button size="small" @click="prefillStrategyDraft(item, 'buy')">填入模拟草稿</a-button>
                    <a-button size="small" :loading="validatingBacktestSymbol === item.symbol" @click="validateStrategyBacktest(item)">只读历史验证</a-button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-note">Top30 暂无未持有标的</div>
            </div>
            <div class="strategy-box">
              <div class="strategy-title"><strong>模拟卖出候选</strong><span>当前持仓，按排名掉队和技术转弱程度排序</span></div>
              <div v-if="strategySellCandidates.length" class="strategy-list">
                <div v-for="item in strategySellCandidates" :key="`sell-${item.symbol}`" class="strategy-item">
                  <div class="strategy-item-head">
                    <strong>{{ item.symbol }}</strong>
                    <a-tag :color="item.riskColor">风险复盘 {{ item.confidence }}%</a-tag>
                  </div>
                  <div class="signal-tags">
                    <a-tag :color="item.actionPlanColor">{{ item.actionPlanLabel }}</a-tag>
                    <a-tag :color="item.positionRiskColor">位置 {{ item.positionRiskLabel }}</a-tag>
                    <a-tag :color="item.backtestColor">{{ item.backtestText }}</a-tag>
                  </div>
                  <div class="strategy-evidence-line">{{ item.strategyEvidence }}</div>
                  <span>{{ item.strategySummary }}</span>
                  <div class="strategy-actions">
                    <a-button size="small" @click="prefillStrategyDraft(item, 'sell')">填入风险复盘草稿</a-button>
                    <a-button size="small" :loading="validatingBacktestSymbol === item.symbol" @click="validateStrategyBacktest(item)">只读历史验证</a-button>
                  </div>
                </div>
              </div>
              <div v-else class="empty-note">当前账户暂无持仓</div>
            </div>
            <div class="strategy-box">
              <div class="strategy-title"><strong>继续保留观察</strong><span>排名或技术确认仍可接受的持仓</span></div>
              <div v-if="strategyHoldCandidates.length" class="strategy-list">
                <div v-for="item in strategyHoldCandidates" :key="`hold-${item.symbol}`" class="strategy-item">
                  <div class="strategy-item-head">
                    <strong>{{ item.symbol }}</strong>
                    <a-tag color="green">风险复盘 {{ item.confidence }}%</a-tag>
                  </div>
                  <div class="signal-tags">
                    <a-tag :color="item.actionPlanColor">{{ item.actionPlanLabel }}</a-tag>
                    <a-tag :color="item.positionRiskColor">位置 {{ item.positionRiskLabel }}</a-tag>
                    <a-tag :color="item.backtestColor">{{ item.backtestText }}</a-tag>
                  </div>
                  <div class="strategy-evidence-line">{{ item.strategyEvidence }}</div>
                  <span>{{ item.strategySummary }}</span>
                </div>
              </div>
              <div v-else class="empty-note">暂无保留观察项</div>
            </div>
            <div class="strategy-box">
              <div class="strategy-title"><strong>人工复核</strong><span>模型和趋势矛盾或数据需复核</span></div>
              <div v-if="strategyReviewCandidates.length" class="strategy-list">
                <div v-for="item in strategyReviewCandidates" :key="`review-${item.symbol}`" class="strategy-item">
                  <div class="strategy-item-head">
                    <strong>{{ item.symbol }}</strong>
                    <a-tag color="orange">人工复核</a-tag>
                  </div>
                  <div class="signal-tags">
                    <a-tag :color="item.actionPlanColor">{{ item.actionPlanLabel }}</a-tag>
                    <a-tag :color="item.positionRiskColor">位置 {{ item.positionRiskLabel }}</a-tag>
                    <a-tag :color="item.backtestColor">{{ item.backtestText }}</a-tag>
                  </div>
                  <div class="strategy-evidence-line">{{ item.strategyEvidence }}</div>
                  <span>{{ item.strategySummary }}</span>
                </div>
              </div>
              <div v-else class="empty-note">暂无冲突项</div>
            </div>
          </div>
        </a-card>

        <a-card class="sim-card" :bordered="false">
          <template slot="title">模拟成交标记</template>
          <div class="marker-toolbar">
            <span class="muted">简化列表替代 K 线标记；仅展示当前账户模拟成交，不含真实订单 ID 或券商账号。</span>
            <a-select v-model="selectedMarkerSymbol" style="min-width: 180px" placeholder="选择标的">
              <a-select-option value="all">全部标的</a-select-option>
              <a-select-option v-for="symbol in markerSymbols" :key="symbol" :value="symbol">{{ symbol }}</a-select-option>
            </a-select>
          </div>
          <div v-if="filteredTradeMarkers.length" class="marker-list">
            <div v-for="marker in filteredTradeMarkers" :key="marker.key" class="marker-item">
              <a-tag :color="marker.side === 'sell' ? 'orange' : 'blue'">{{ sideText(marker.side) }}</a-tag>
              <strong>{{ marker.symbol }}</strong>
              <span>{{ marker.price_date || '数据日期需复核' }}</span>
              <span>价格 {{ number(marker.price, 4) }}</span>
              <span>数量 {{ number(marker.quantity) }}</span>
              <span>来源 {{ marker.source_type || 'manual' }}</span>
            </div>
          </div>
          <div v-else class="empty-note">暂无可展示的模拟成交标记</div>
        </a-card>

        <a-card class="sim-card" :bordered="false">
          <template slot="title">手动模拟交易</template>
          <div class="manual-form">
            <a-select v-model="tradeForm.account_uid" style="min-width: 240px" @change="clearDraft">
              <a-select-option v-for="item in accounts" :key="item.account_uid" :value="item.account_uid">
                {{ item.name || item.account_uid }}
              </a-select-option>
            </a-select>
            <a-input v-model="tradeForm.symbol" placeholder="股票代码，例如 2330 或 TW6290" style="width: 220px" @change="markSignalDraftEdited" />
            <a-radio-group v-model="tradeForm.side" button-style="solid">
              <a-radio-button value="buy">模拟买入</a-radio-button>
              <a-radio-button value="sell">模拟卖出</a-radio-button>
            </a-radio-group>
            <a-input-number v-model="tradeForm.quantity" :min="10" :step="10" style="width: 150px" @change="markSignalDraftEdited" />
            <span class="muted">需为 10 股倍数 · source_type {{ tradeForm.source_type || 'manual' }} · 价格为最新可用收盘价</span>
          </div>
          <div class="draft-actions">
            <a-button @click="createDraft('buy')" :loading="drafting && tradeForm.side === 'buy'">
              生成模拟买入草稿
            </a-button>
            <a-button @click="createDraft('sell')" :loading="drafting && tradeForm.side === 'sell'">
              生成模拟卖出草稿
            </a-button>
          </div>

          <div v-if="draftOrder" class="draft-box">
            <div class="draft-header">
              <strong>草稿状态：{{ draftOrder.status }}</strong>
              <a-tag :color="draftOrder.status === 'draft' ? 'blue' : draftOrder.status === 'rejected' ? 'red' : 'default'">
                {{ draftOrder.simulation_only ? 'simulation_only=true' : 'simulation_only=false' }}
              </a-tag>
            </div>
            <div class="draft-grid">
              <span>标的 <strong>{{ draftOrder.symbol }}</strong></span>
              <span>方向 <strong>{{ sideText(draftOrder.side) }}</strong></span>
              <span>数量 <strong>{{ number(draftOrder.quantity) }}</strong></span>
              <span>参考价 <strong>{{ number(draftOrder.reference_price, 4) }}</strong></span>
              <span>价格日期 <strong>{{ draftOrder.price_date || '数据日期需复核' }}</strong></span>
              <span>成交金额 <strong>{{ money(draftOrder.gross_amount) }}</strong></span>
              <span>手续费 <strong>{{ money(draftOrder.fee) }}</strong></span>
              <span>交易税 <strong>{{ money(draftOrder.tax) }}</strong></span>
              <span>现金影响 <strong>{{ signedMoney(draftOrder.net_cash_effect) }}</strong></span>
              <span>来源 <strong>{{ draftOrder.source_type || 'manual' }}</strong></span>
              <span>研究上下文 <strong>{{ draftSourceContextText }}</strong></span>
            </div>
            <div v-if="draftWarnings.length" class="warning-list">
              <a-tag v-for="warning in draftWarnings" :key="warning" color="orange">{{ warningText(warning) }}</a-tag>
            </div>
            <a-alert
              v-if="draftOrder.status === 'rejected'"
              class="state-alert"
              type="warning"
              show-icon
              :message="draftRejectMessage"
            />
            <div class="confirm-row">
              <a-button v-if="canConfirmDraft" type="primary" @click="confirmDraft" :loading="confirmingDraft">
                确认模拟成交
              </a-button>
              <a-button v-if="draftOrder.status === 'draft'" @click="cancelDraft" :loading="cancellingDraft">
                取消草稿
              </a-button>
            </div>
          </div>
        </a-card>

        <a-card class="sim-card" :bordered="false">
          <template slot="title">持仓列表</template>
          <a-table
            row-key="symbol"
            size="small"
            class="responsive-table"
            :columns="positionColumns"
            :data-source="positions"
            :pagination="false"
          >
            <template slot="money" slot-scope="value">{{ money(value) }}</template>
            <template slot="price" slot-scope="value">{{ number(value, 4) }}</template>
            <template slot="latest_date" slot-scope="value">
              <a-tag :color="value ? 'blue' : 'orange'">{{ value || '数据日期需复核' }}</a-tag>
            </template>
            <template slot="pnl" slot-scope="value">{{ signedMoney(value) }}</template>
          </a-table>
        </a-card>

        <a-card class="sim-card" :bordered="false">
          <template slot="title">成交记录</template>
          <a-table
            row-key="sim_trade_uid"
            size="small"
            class="responsive-table"
            :columns="tradeColumns"
            :data-source="trades"
            :pagination="{ pageSize: 8 }"
          >
            <template slot="side" slot-scope="value">{{ sideText(value) }}</template>
            <template slot="money" slot-scope="value">{{ money(value) }}</template>
            <template slot="signed" slot-scope="value">{{ signedMoney(value) }}</template>
            <template slot="price" slot-scope="value">{{ number(value, 4) }}</template>
          </a-table>
        </a-card>
      </template>
    </a-spin>
  </div>
</template>

<script>
import {
  getTwStockSimAccounts,
  createTwStockSimAccount,
  getTwStockSimAccount,
  getTwStockSimPositions,
  getTwStockSimTrades,
  getLatestQlibOptionCSignals,
  getTwStockCrossAnalysisLatest,
  runTwStockReadonlyBacktest,
  draftTwStockSimOrder,
  confirmTwStockSimOrder,
  cancelTwStockSimOrder
} from '@/api/tw-stock'

const SIM_DRAFT_CONTEXT_KEY = 'tw-stock-sim-draft-context'

export default {
  name: 'TWStockSimAccount',
  data () {
    return {
      loading: false,
      accountsLoaded: false,
      creatingAccount: false,
      drafting: false,
      confirmingDraft: false,
      cancellingDraft: false,
      validatingBacktestSymbol: '',
      error: '',
      safetyError: '',
      accounts: [],
      activeAccountUid: '',
      account: {},
      positions: [],
      trades: [],
      strategySignals: { qlib: null, cross: null },
      strategyBacktestResults: {},
      strategyBacktestErrors: {},
      readonlyBacktestStrategies: [
        { id: 'ma_cross_builtin', label: 'MA Cross', template: { fastWindow: 5, slowWindow: 20 } },
        { id: 'rsi_builtin', label: 'RSI', template: { period: 14, oversold: 30, overbought: 70 } },
        { id: 'macd_builtin', label: 'MACD', template: { fast: 12, slow: 26, signal: 9 } },
        { id: 'bollinger_builtin', label: 'Bollinger', template: { period: 20, stdDev: 2 } }
      ],
      loadingStrategySignals: false,
      draftResponse: null,
      pendingSignalDraft: null,
      selectedMarkerSymbol: 'all',
      strategyRuleProfile: 'balanced',
      strategyPolicyProfile: 'confirmed_exit',
      strategyPolicyOptions: [
        { key: 'confirmed_exit', label: '连续转弱才复盘', description: '默认低频策略；10 支上限，连续转弱后才复盘，避免过度交易。' },
        { key: 'rank_rotate_top50', label: '跌出 Top50 轮动', description: '进阶高收益策略；10 支上限，跌出 Top50 后用 Top10 候选补位。' },
        { key: 'rank_rotate_top30', label: '跌出 Top30 轮动', description: '中间参考策略；10 支上限，反应更快但交易更频繁。' }
      ],
      accountForm: {
        name: '台股研究模拟账户',
        initial_cash: 1000000
      },
      tradeForm: {
        account_uid: '',
        symbol: '2330',
        side: 'buy',
        quantity: 10,
        source_type: 'manual',
        source_context: {}
      },
      positionColumns: [
        { title: 'symbol', dataIndex: 'symbol', width: 100 },
        { title: 'quantity', dataIndex: 'quantity', width: 110 },
        { title: 'avg_cost', dataIndex: 'avg_cost', scopedSlots: { customRender: 'price' }, width: 120 },
        { title: 'latest_close', dataIndex: 'latest_close', scopedSlots: { customRender: 'price' }, width: 130 },
        { title: 'latest_date', dataIndex: 'latest_date', scopedSlots: { customRender: 'latest_date' }, width: 140 },
        { title: 'market_value', dataIndex: 'market_value', scopedSlots: { customRender: 'money' }, width: 150 },
        { title: 'unrealized_pnl', dataIndex: 'unrealized_pnl', scopedSlots: { customRender: 'pnl' }, width: 150 }
      ],
      tradeColumns: [
        { title: 'symbol', dataIndex: 'symbol', width: 90 },
        { title: 'side', dataIndex: 'side', scopedSlots: { customRender: 'side' }, width: 110 },
        { title: 'quantity', dataIndex: 'quantity', width: 110 },
        { title: 'price', dataIndex: 'price', scopedSlots: { customRender: 'price' }, width: 110 },
        { title: 'price_date', dataIndex: 'price_date', width: 120 },
        { title: 'fee', dataIndex: 'fee', scopedSlots: { customRender: 'money' }, width: 110 },
        { title: 'tax', dataIndex: 'tax', scopedSlots: { customRender: 'money' }, width: 110 },
        { title: 'net_cash_effect', dataIndex: 'net_cash_effect', scopedSlots: { customRender: 'signed' }, width: 150 },
        { title: 'source_type', dataIndex: 'source_type', width: 120 },
        { title: 'created_at', dataIndex: 'created_at', width: 180 }
      ]
    }
  },
  computed: {
    hasAccount () {
      return this.accounts.length > 0
    },
    draftOrder () {
      return this.draftResponse && this.draftResponse.sim_order ? this.draftResponse.sim_order : null
    },
    draftWarnings () {
      const warnings = this.draftOrder && this.draftOrder.warnings
      return Array.isArray(warnings) ? warnings : []
    },
    draftRejectMessage () {
      if (!this.draftResponse) return ''
      return this.draftResponse.message || (this.draftOrder && this.draftOrder.message) || '模拟草稿被拒绝，请检查现金、数量、价格或持仓。'
    },
    canConfirmDraft () {
      return Boolean(this.draftOrder && this.draftOrder.status === 'draft' && !this.safetyError)
    },
    pendingSignalDraftMessage () {
      const draft = this.pendingSignalDraft || {}
      const source = draft.source_type === 'cross_analysis' ? '交叉分析' : draft.source_type === 'qlib_rank' ? '研究排名' : '手动输入'
      const edited = draft.user_edited ? '，已人工修改' : ''
      return `已从${source}预填模拟草稿：${draft.symbol || '-'}，请复核数量、价格日期和费用后再手动生成草稿${edited}。`
    },
    draftSourceContextText () {
      const context = this.draftOrder && this.draftOrder.source_context
      if (!context || !Object.keys(context).length) return '-'
      const parts = []
      if (context.asof) parts.push(`日期 ${context.asof}`)
      if (context.qlib_rank != null) parts.push(`排名 #${context.qlib_rank}`)
      if (context.trend_label) parts.push(`QuantDinger ${this.trendText(context.trend_label)}`)
      if (context.cross_category || context.cross_alignment) parts.push(`交叉 ${this.crossText(context.cross_category, context.cross_alignment)}`)
      if (context.technical_status) parts.push(`状态 ${context.technical_status}`)
      if (context.combo_label) parts.push(`组合 ${context.combo_label}`)
      if (context.backtest_return != null) parts.push(`历史验证 ${Number(context.backtest_return).toFixed(1)}%`)
      if (context.user_edited) parts.push('已人工修改')
      return parts.join(' · ') || '-'
    },
    sourceTypeCounts () {
      const counts = { manual: 0, qlib_rank: 0, cross_analysis: 0, agent_research: 0 }
      this.trades.forEach(item => {
        const key = counts[item.source_type] == null ? 'manual' : item.source_type
        counts[key] += 1
      })
      return counts
    },
    strategyRuleConfig () {
      const configs = {
        conservative: {
          topCore: 10,
          buyPool: 30,
          riskPool: 50,
          buyMin: 78,
          riskMin: 55,
          requireBacktest: true,
          label: '稳健',
          hint: '只优先处理多信号一致且历史验证不差的候选。'
        },
        balanced: {
          topCore: 10,
          buyPool: 30,
          riskPool: 50,
          buyMin: 70,
          riskMin: 45,
          requireBacktest: false,
          label: '平衡',
          hint: '先看多信号一致候选，历史验证作为加分和风控。'
        },
        active: {
          topCore: 10,
          buyPool: 50,
          riskPool: 50,
          buyMin: 62,
          riskMin: 40,
          requireBacktest: false,
          label: '积极',
          hint: '允许更多候选进入观察，但仍需要人工确认模拟草稿。'
        }
      }
      return configs[this.strategyRuleProfile] || configs.balanced
    },
    selectedPolicyProfile () {
      return this.strategyPolicyOptions.find(item => item.key === this.strategyPolicyProfile) || this.strategyPolicyOptions[1]
    },
    todayStrategyAdvice () {
      const profile = this.selectedPolicyProfile
      const items = this.buildTodayPolicyAdvice(profile.key)
      const primary = items[0]
      const summary = primary
        ? `${profile.label}：优先${primary.sideLabel} ${primary.symbol}，${primary.quantity > 0 ? `${this.number(primary.quantity)} 股` : '先复核'}。${primary.reason}`
        : `${profile.label}：今天没有足够一致的模拟买卖动作，先保留观察。`
      return { profile, summary, items }
    },
    activeRuleSummary () {
      const cfg = this.strategyRuleConfig
      return [
        { label: '规则模式', value: cfg.label },
        { label: '模式说明', value: cfg.hint },
        { label: '核心优先', value: `Top${cfg.topCore}：优先看` },
        { label: '新增观察池', value: `Top${cfg.buyPool} 未持有` },
        { label: '持仓风险池', value: `跌出 Top${cfg.buyPool} 或未进 Top${cfg.riskPool}` },
        { label: '新增观察门槛', value: `模拟匹配度 >= ${cfg.buyMin}%` },
        { label: '风险复盘门槛', value: `风险复盘 >= ${cfg.riskMin}%` },
        { label: '历史验证', value: cfg.requireBacktest ? '需先通过' : '按需加权' },
        { label: '执行边界', value: '只生成模拟草稿' }
      ]
    },
    actionQueue () {
      const cfg = this.strategyRuleConfig
      const buyItems = this.strategyBuyCandidates
        .filter(item => item.confidence >= cfg.buyMin)
        .filter(item => !cfg.requireBacktest || this.backtestPasses(item.backtest))
        .slice(0, 5)
        .map(item => ({
          ...item,
          queueType: 'buy_watch',
          queueSide: 'buy',
          canValidate: !item.backtest && !item.backtestError,
          queueLabel: '新增观察',
          queueColor: 'green',
          queueReason: `${item.comboReason} ${item.backtest ? '已有历史验证证据。' : '可先做只读历史验证再生成草稿。'}`
        }))
      const riskItems = this.strategySellCandidates
        .filter(item => item.confidence >= cfg.riskMin || item.comboType === 'risk_review' || item.comboType === 'manual_review')
        .slice(0, 5)
        .map(item => ({
          ...item,
          queueType: 'risk_review',
          queueSide: item.comboType === 'risk_review' ? 'sell' : '',
          canValidate: !item.backtest && !item.backtestError,
          queueLabel: item.comboType === 'manual_review' ? '人工复核' : '风险复盘',
          queueColor: item.comboType === 'manual_review' ? 'orange' : 'red',
          queueReason: `${item.comboReason} 先复核持仓原因、价格日期和历史验证。`
        }))
      const reviewItems = this.strategyReviewCandidates
        .slice(0, 4)
        .map(item => ({
          ...item,
          queueType: 'manual_review',
          queueSide: '',
          canValidate: !item.backtest && !item.backtestError,
          queueLabel: '人工复核',
          queueColor: 'orange',
          queueReason: item.comboReason || item.reason
        }))
      const merged = [...riskItems, ...buyItems, ...reviewItems]
      const seen = new Set()
      return merged.filter(item => {
        const key = `${item.queueType}-${item.symbol}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      }).slice(0, 10)
    },
    validatedBacktestItems () {
      return this.strategyItems
        .filter(item => item.backtest || item.backtestError)
        .map(item => ({
          ...item,
          evidenceText: item.backtestError
            ? `验证失败：${item.backtestError}`
            : `${item.comboLabel}；最佳 ${this.backtestText(item.backtest, '')}；明细 ${this.backtestDetailText(item.backtest)}；${item.comboReason}`
        }))
        .slice(0, 8)
    },
    comboSummary () {
      const cfg = this.strategyRuleConfig
      const buyCount = this.strategyBuyCandidates.filter(item => item.comboType === 'simulate_watch' || item.confidence >= cfg.buyMin).length
      const riskCount = this.strategySellCandidates.filter(item => item.comboType === 'risk_review' || item.confidence >= cfg.riskMin).length
      const reviewSymbols = new Set(this.strategyReviewCandidates.map(item => item.symbol))
      this.strategySellCandidates.forEach(item => {
        if (item.comboType === 'manual_review') reviewSymbols.add(item.symbol)
      })
      const reviewCount = reviewSymbols.size
      let primaryLabel = '先看少量高一致候选'
      let primaryHint = '优先复核多信号一致的标的，避免每天跟随 Top30 大幅换手。'
      if (riskCount > buyCount && riskCount > 0) {
        primaryLabel = '先复盘现有持仓风险'
        primaryHint = '持仓里有排名掉队或技术转弱标的，先做风险复盘再看新增。'
      } else if (buyCount === 0 && reviewCount > 0) {
        primaryLabel = '以人工复核为主'
        primaryHint = '模型和技术面分歧较多，暂时不扩大模拟仓位。'
      } else if (buyCount === 0 && riskCount === 0) {
        primaryLabel = '继续观察'
        primaryHint = '当前没有明显新增或风险复盘候选。'
      }
      return { buyCount, riskCount, reviewCount, primaryLabel, primaryHint }
    },
    performanceSummary () {
      const sorted = [...this.trades].sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || '')))
      const lots = {}
      let realized = 0
      let wins = 0
      let losses = 0
      let totalFee = 0
      let totalTax = 0
      sorted.forEach(trade => {
        const symbol = String(trade.symbol || '')
        const qty = Number(trade.quantity || 0)
        const price = Number(trade.price || 0)
        const fee = Number(trade.fee || 0)
        const tax = Number(trade.tax || 0)
        totalFee += Number.isFinite(fee) ? fee : 0
        totalTax += Number.isFinite(tax) ? tax : 0
        if (!symbol || !Number.isFinite(qty) || qty <= 0 || !Number.isFinite(price)) return
        if (!lots[symbol]) lots[symbol] = { qty: 0, cost: 0 }
        const lot = lots[symbol]
        if (trade.side === 'sell') {
          const avg = lot.qty > 0 ? lot.cost / lot.qty : 0
          const pnl = (price - avg) * qty - fee - tax
          realized += pnl
          if (pnl > 0) wins += 1
          if (pnl < 0) losses += 1
          lot.qty = Math.max(0, lot.qty - qty)
          lot.cost = Math.max(0, lot.cost - avg * qty)
        } else {
          lot.qty += qty
          lot.cost += price * qty + fee
        }
      })
      const unrealized = this.positions.reduce((sum, item) => sum + Number(item.unrealized_pnl || 0), 0)
      return {
        trade_count: this.trades.length,
        unrealized_pnl: unrealized,
        realized_pnl: realized,
        win_count: wins,
        loss_count: losses,
        total_fee: totalFee,
        total_tax: totalTax
      }
    },
    strategyItems () {
      const qlibSignals = (this.strategySignals.qlib && this.strategySignals.qlib.signals) || []
      const crossItems = (this.strategySignals.cross && this.strategySignals.cross.items) || []
      const crossBySymbol = new Map(crossItems.map(item => [String(item.symbol || '').toUpperCase(), item]))
      return qlibSignals.map(row => {
        const symbol = String(row.symbol || '').toUpperCase()
        const cross = crossBySymbol.get(symbol) || {}
        const trend = (cross.quantdinger && cross.quantdinger.trend_label) || (row.trend && row.trend.trend_label) || ''
        const trendScore = Number((cross.quantdinger && cross.quantdinger.trend_score) || (row.trend && row.trend.trend_score) || 0)
        const category = cross.cross && cross.cross.category
        const alignment = cross.cross && cross.cross.alignment
        const actionPlan = cross.actionPlan || row.actionPlan || {}
        const positionRisk = cross.positionRisk || (cross.technical && cross.technical.positionRisk) || (row.technical && row.technical.positionRisk) || {}
        const enriched = {
          symbol,
          rank: Number(row.rank || 999),
          score: row.qlib_score,
          trend,
          trendScore: Number.isFinite(trendScore) ? trendScore : 0,
          category,
          alignment,
          actionPlan,
          positionRisk,
          crossAsOf: cross.asof || cross.date || '',
          qlibAsOf: row.asof || '',
          latestClose: this.firstPositiveNumber(
            row.latest_close,
            row.close,
            row.trend && row.trend.latest_close,
            cross.latest_close,
            cross.latestClose,
            cross.quantdinger && cross.quantdinger.latest_close,
            cross.quantdinger && cross.quantdinger.latestClose
          )
        }
        return this.decorateStrategyItem(enriched)
      }).filter(item => item.symbol)
    },
    heldSymbolSet () {
      return new Set(this.positions.map(item => String(item.symbol || '').toUpperCase()).filter(Boolean))
    },
    strategyBuyCandidates () {
      return this.strategyItems
        .filter(item => !this.heldSymbolSet.has(item.symbol))
        .filter(item => item.rank <= this.strategyRuleConfig.buyPool)
        .map(item => {
          const confidence = this.buyConfidence(item)
          return this.decorateStrategyItem({
            ...item,
            confidence,
            matchColor: this.confidenceColor(confidence),
            reason: this.buyReason(item, confidence)
          })
        })
        .sort((a, b) => (b.confidence - a.confidence) || (a.rank - b.rank))
    },
    strategySellCandidates () {
      return this.positions
        .map(pos => {
          const symbol = String(pos.symbol || '').toUpperCase()
          const item = this.strategyItems.find(row => row.symbol === symbol) || { symbol, rank: 999 }
          const confidence = this.sellConfidence(item)
          return this.decorateStrategyItem({
            ...item,
            symbol,
            quantity: pos.quantity,
            confidence,
            riskColor: this.riskColor(confidence),
            reason: this.sellReason(item, confidence)
          })
        })
        .filter(item => item.symbol)
        .sort((a, b) => (b.confidence - a.confidence) || ((b.rank || 999) - (a.rank || 999)))
    },
    strategyHoldCandidates () {
      return this.strategySellCandidates
        .filter(item => item.confidence < 45)
        .map(item => this.decorateStrategyItem({
          ...item,
          reason: item.rank && item.rank < 999
            ? `仍在研究池 ${item.rankText}，QuantDinger ${item.trendText}，风险复盘强度较低`
            : '持仓暂未进入 Top50，先观察价格和资料日期后再人工判断'
        }))
        .slice(0, 10)
    },
    strategyReviewCandidates () {
      return this.strategyItems
        .filter(item => ['model_trend_divergence', 'data_review_required'].includes(item.category) || this.positionRiskStatus(item) === 'overheated')
        .slice(0, 5)
        .map(item => this.decorateStrategyItem({
          ...item,
          reason: this.positionRiskStatus(item) === 'overheated'
            ? `${item.crossText}，QuantDinger ${item.trendText}；${item.positionRiskLabel}，先复核追高风险`
            : `${item.crossText}，QuantDinger ${item.trendText}；模型排名和技术状态不完全一致，建议只做人工复核`
        }))
    },
    markerSymbols () {
      return Array.from(new Set(this.trades.map(item => item && item.symbol).filter(Boolean))).sort()
    },
    filteredTradeMarkers () {
      const selected = this.selectedMarkerSymbol
      return this.trades
        .filter(item => selected === 'all' || item.symbol === selected)
        .map(item => ({ ...item, key: item.sim_trade_uid || `${item.symbol}-${item.created_at}-${item.side}` }))
    }
  },
  created () {
    this.loadPendingSignalDraft()
    this.refreshAll()
  },
  methods: {
    firstPositiveNumber (...values) {
      for (const value of values) {
        const num = Number(value)
        if (Number.isFinite(num) && num > 0) return num
      }
      return 0
    },
    buildTodayPolicyAdvice (policyKey) {
      const policy = policyKey || 'confirmed_exit'
      const heldMap = new Map(this.positions.map(item => [String(item.symbol || '').toUpperCase(), item]))
      const buyPool = this.policyBuyCandidates(policy)
      const sellPool = this.policySellCandidates(policy)
      const holdPool = this.policyHoldCandidates(policy)
      const sellItems = sellPool.slice(0, 1).map(item => this.policyAdviceItem(item, 'sell', heldMap.get(item.symbol), policy))
      const buyItems = buyPool.slice(0, 1).map(item => this.policyAdviceItem(item, 'buy', null, policy))
      const holdItems = holdPool.slice(0, 2).map(item => this.policyAdviceItem(item, 'hold', heldMap.get(item.symbol), policy))
      return [...sellItems, ...buyItems, ...holdItems].filter(item => item.symbol).slice(0, 5)
    },
    policyBuyCandidates (policy) {
      const base = this.strategyBuyCandidates.filter(item => item.rank <= 30)
      return base.filter(item => Number(item.rank || 999) <= 10 && this.actionPlanCode(item) !== 'chasing_review').sort((a, b) => (a.rank - b.rank) || (b.confidence - a.confidence))
    },
    policySellCandidates (policy) {
      const base = this.strategySellCandidates
      if (policy === 'rank_rotate_top30') return base.filter(item => Number(item.rank || 999) > 30).sort((a, b) => (b.rank || 999) - (a.rank || 999))
      if (policy === 'rank_rotate_top50') return base.filter(item => Number(item.rank || 999) > 50).sort((a, b) => (b.rank || 999) - (a.rank || 999))
      return base.filter(item => item.comboType === 'risk_review' && item.confidence >= 70).sort((a, b) => b.confidence - a.confidence)
    },
    policyHoldCandidates (policy) {
      if (policy === 'rank_rotate_top30') return this.strategySellCandidates.filter(item => Number(item.rank || 999) <= 30).slice(0, 6)
      if (policy === 'rank_rotate_top50') return this.strategySellCandidates.filter(item => Number(item.rank || 999) <= 50).slice(0, 6)
      return this.strategySellCandidates.filter(item => item.confidence < 70).slice(0, 6)
    },
    policyAdviceItem (item, side, position, policy) {
      const price = this.adviceReferencePrice(item, position)
      const quantity = side === 'buy'
        ? this.suggestBuyQuantity(item, price, policy)
        : side === 'sell'
          ? this.suggestSellQuantity(item, position, policy)
          : 0
      const estimatedAmount = price > 0 && quantity > 0 ? price * quantity : 0
      return {
        symbol: item.symbol,
        side,
        sideLabel: side === 'buy' ? '模拟买入' : side === 'sell' ? '模拟卖出' : '建议保留',
        color: side === 'buy' ? 'green' : side === 'sell' ? 'red' : 'blue',
        quantity,
        estimatedAmount,
        referencePrice: price,
        reason: this.policyAdviceReason(item, side, quantity, policy, price),
        sourceItem: { ...item, canValidate: !item.backtest && !item.backtestError }
      }
    },
    adviceReferencePrice (item, position) {
      return this.firstPositiveNumber(
        item && item.latestClose,
        position && position.latest_close,
        position && position.latestClose,
        position && position.avg_cost
      )
    },
    suggestBuyQuantity (item, price, policy) {
      if (!price || price <= 0) return 0
      const cash = Number(this.account.cash || 0)
      const maxHoldings = 10
      const remainingSlots = Math.max(1, maxHoldings - this.positions.length)
      const policyRatio = policy === 'confirmed_exit' ? 0.14 : 0.1
      const budgetBySlot = cash / remainingSlots
      const budget = Math.max(0, Math.min(cash * policyRatio, budgetBySlot))
      return this.roundLotDown(budget / price)
    },
    suggestSellQuantity (item, position, policy) {
      const heldQty = Number(position && position.quantity || item.quantity || 0)
      if (!Number.isFinite(heldQty) || heldQty <= 0) return 0
      if (policy === 'rank_rotate_top30' || policy === 'rank_rotate_top50') return this.roundLotDown(heldQty)
      return this.roundLotDown(Math.max(this.lotSize(), heldQty * 0.3))
    },
    roundLotDown (quantity) {
      const lot = this.lotSize()
      const qty = Math.floor(Number(quantity || 0) / lot) * lot
      return Math.max(0, qty)
    },
    lotSize () {
      return 10
    },
    policyAdviceReason (item, side, quantity, policy, price) {
      const policyLabel = (this.strategyPolicyOptions.find(option => option.key === policy) || {}).label || '组合策略'
      const basis = `${policyLabel}；${item.rankText}；${item.actionPlanLabel}；位置 ${item.positionRiskLabel}`
      if (side === 'hold') return `${basis}，当前没有达到模拟卖出门槛，先保留观察。`
      if (!price || price <= 0) return `${basis}，缺少可用参考价，先补齐价格再生成模拟草稿。`
      if (!quantity || quantity <= 0) return `${basis}，现金或持仓不足以形成 10 股倍数，先观察。`
      if (side === 'buy') return `${basis}，按现金和持仓上限估算 ${this.number(quantity)} 股。`
      return `${basis}，按持仓风险强度估算 ${this.number(quantity)} 股。`
    },
    adviceQuantityText (item) {
      return item && Number(item.quantity) > 0 ? `${this.number(item.quantity)} 股` : '先复核'
    },
    adviceAmountText (item) {
      return item && Number(item.estimatedAmount) > 0 ? `约 ${this.money(item.estimatedAmount)}` : '金额待价格确认'
    },
    prefillPolicyAdviceDraft (advice) {
      if (!advice || !advice.symbol || !advice.side || advice.side === 'hold') return
      const source = advice.sourceItem || {}
      this.prefillStrategyDraft({
        ...source,
        symbol: advice.symbol,
        quantity: advice.quantity,
        comboLabel: this.selectedPolicyProfile.label,
        comboType: advice.side === 'sell' ? 'policy_risk_review' : 'policy_simulate_watch',
        comboReason: advice.reason
      }, advice.side)
      this.tradeForm.quantity = advice.quantity || this.tradeForm.quantity
      this.tradeForm.source_context = {
        ...(this.tradeForm.source_context || {}),
        combo_label: this.selectedPolicyProfile.label,
        combo_type: advice.side === 'sell' ? 'policy_risk_review' : 'policy_simulate_watch',
        combo_reason: advice.reason,
        source_label: `今日${this.selectedPolicyProfile.label}模拟建议`
      }
    },
    decorateStrategyItem (item) {
      const rank = Number(item.rank || 999)
      const trend = item.trend || ''
      const category = item.category || ''
      const alignment = item.alignment || ''
      const symbol = String(item.symbol || '').toUpperCase()
      const backtest = symbol ? this.strategyBacktestResults[symbol] : null
      const backtestError = symbol ? this.strategyBacktestErrors[symbol] : ''
      const combo = this.comboDecision({ ...item, symbol, rank, trend, category, alignment }, backtest, backtestError)
      return {
        ...item,
        symbol,
        rank,
        rankText: rank < 999 ? `qlib #${rank}` : '未进入 Top50',
        trendText: this.trendText(trend),
        trendColor: this.trendColor(trend),
        crossText: this.crossText(category, alignment),
        crossColor: this.crossColor(category, alignment),
        technicalStatus: this.technicalStatus(item),
        riskHint: this.riskHint(item),
        positionRiskLabel: this.positionRiskLabel(item),
        positionRiskColor: this.positionRiskColor(item),
        positionRiskReason: this.positionRiskReason(item),
        actionPlanLabel: this.actionPlanLabel(item),
        actionPlanColor: this.actionPlanColor(item),
        actionPlanReason: this.actionPlanReason(item),
        backtest,
        backtestError,
        backtestText: this.backtestText(backtest, backtestError),
        backtestColor: this.backtestColor(backtest, backtestError),
        comboType: combo.type,
        comboLabel: combo.label,
        comboColor: combo.color,
        comboReason: combo.reason,
        strategySummary: this.strategySummary({ ...item, rank, trend, category, alignment }, combo),
        strategyEvidence: this.strategyEvidence({ ...item, rank, trend, category, alignment }, combo, backtest, backtestError)
      }
    },
    buyConfidence (item) {
      const rank = Number(item.rank || 999)
      const rankScore = rank <= 30 ? Math.round(((31 - rank) / 30) * 40) : 0
      let score = 35 + rankScore
      if (item.category === 'focus_watch') score += 14
      if (item.alignment === 'aligned') score += 10
      if (['uptrend', 'breakout', 'strong_uptrend'].includes(item.trend)) score += 12
      if (['sideways', 'neutral', 'range_bound'].includes(item.trend)) score -= 4
      if (['downtrend', 'pullback', 'weak_downtrend'].includes(item.trend)) score -= 24
      if (['model_trend_divergence', 'data_review_required'].includes(item.category)) score -= 18
      if (this.positionRiskStatus(item) === 'overheated') score -= 28
      else if (this.positionRiskStatus(item) === 'elevated') score -= 14
      else if (this.positionRiskStatus(item) === 'reasonable') score += 4
      return Math.max(0, Math.min(95, score))
    },
    sellConfidence (item) {
      const rank = Number(item.rank || 999)
      let score = 20
      if (rank > 50) score += 22
      else if (rank > 30) score += 12
      else score += Math.max(0, Math.round((rank / 30) * 8))
      if (['model_trend_divergence', 'data_review_required'].includes(item.category)) score += 24
      if (['downtrend', 'pullback', 'weak_downtrend'].includes(item.trend)) score += 28
      if (['sideways', 'neutral', 'range_bound'].includes(item.trend)) score += 4
      if (item.category === 'focus_watch' || item.alignment === 'aligned') score -= 18
      if (['uptrend', 'breakout', 'strong_uptrend'].includes(item.trend)) score -= 18
      if (this.positionRiskStatus(item) === 'overheated') score += 8
      if (this.actionPlanCode(item) === 'risk_review') score += 14
      if (this.actionPlanCode(item) === 'simulate_watch' || this.actionPlanCode(item) === 'continue_observe') score -= 10
      return Math.max(5, Math.min(95, score))
    },
    buyReason (item, confidence) {
      const tier = item.rank <= this.strategyRuleConfig.topCore ? `Top${this.strategyRuleConfig.topCore} 核心优先` : `Top${this.strategyRuleConfig.buyPool} 观察池`
      const parts = [`${item.rankText} / ${tier}`]
      parts.push(`QuantDinger ${item.trendText}`)
      parts.push(`交叉分析：${item.crossText}`)
      parts.push(`位置：${item.positionRiskLabel}`)
      if (this.positionRiskStatus(item) === 'overheated') parts.push('位置偏热，先人工复核追高风险')
      else if (this.positionRiskStatus(item) === 'elevated') parts.push('趋势强但位置偏高，等待回调更稳妥')
      if (confidence >= 75) parts.push('模型和技术面较一致，可优先做模拟验证')
      else if (confidence >= 55) parts.push('具备候选价值，但仍需复核资料日期和价格')
      else parts.push('匹配度偏低，适合观察而非直接生成大量模拟成交')
      return parts.join('；')
    },
    sellReason (item, confidence) {
      const parts = [item.rankText, item.rank > this.strategyRuleConfig.buyPool ? `跌出 Top${this.strategyRuleConfig.buyPool}` : '仍在观察池']
      parts.push(`QuantDinger ${item.trendText}`)
      parts.push(`交叉分析：${item.crossText}`)
      parts.push(`位置：${item.positionRiskLabel}`)
      if (this.positionRiskStatus(item) === 'overheated') parts.push('位置偏热，只作为风险复盘提示')
      if (confidence >= 70) parts.push('风险复盘强度高，适合先生成小额模拟草稿验证')
      else if (confidence >= 45) parts.push('有转弱或分歧迹象，建议人工复核')
      else parts.push('风险复盘强度较低，偏继续观察')
      return parts.join('；')
    },
    strategySummary (item, combo) {
      const risk = this.positionRiskLabel(item)
      if (combo && combo.type === 'manual_review') return `先复核：${combo.reason || '信号存在分歧。'} 位置：${risk}`
      if (combo && combo.type === 'risk_review') return `先复盘风险：${combo.reason || '持仓信号转弱。'} 位置：${risk}`
      if (combo && combo.type === 'simulate_watch') return `可放入模拟观察：信号较一致，位置：${risk}`
      if (combo && combo.type === 'keep_watch') return `继续观察：持仓仍在研究池，位置：${risk}`
      return `先观察：信号还不够一致，位置：${risk}`
    },
    strategyEvidence (item, combo, backtest, backtestError) {
      const rank = item && item.rank < 999 ? `排名 #${item.rank}` : '未进入 Top50'
      const trend = this.trendText(item && item.trend)
      const cross = this.crossText(item && item.category, item && item.alignment)
      const history = this.backtestText(backtest, backtestError)
      const action = this.actionPlanLabel(item)
      return `依据：${rank}，趋势${trend}，交叉${cross}，研究动作${action}，${history}`
    },
    trendText (trend) {
      const labels = {
        strong_uptrend: '强上升',
        breakout: '突破',
        uptrend: '上升',
        sideways: '震荡',
        range_bound: '区间震荡',
        neutral: '中性',
        pullback: '回调',
        weak_downtrend: '弱下降',
        downtrend: '下降'
      }
      return labels[trend] || '未知'
    },
    trendColor (trend) {
      if (['strong_uptrend', 'breakout', 'uptrend'].includes(trend)) return 'green'
      if (['downtrend', 'pullback', 'weak_downtrend'].includes(trend)) return 'red'
      if (['sideways', 'range_bound', 'neutral'].includes(trend)) return 'gold'
      return 'default'
    },
    crossText (category, alignment) {
      const categoryLabels = {
        focus_watch: '重点观察',
        model_trend_divergence: '模型/趋势分歧',
        data_review_required: '资料需复核',
        neutral_watch: '中性观察',
        rank_only: '仅排名信号'
      }
      const alignmentLabels = {
        aligned: '一致',
        divergent: '分歧',
        unknown: '未知'
      }
      return categoryLabels[category] || alignmentLabels[alignment] || '待确认'
    },
    crossColor (category, alignment) {
      if (category === 'focus_watch' || alignment === 'aligned') return 'green'
      if (category === 'model_trend_divergence' || alignment === 'divergent') return 'orange'
      if (category === 'data_review_required') return 'red'
      return 'default'
    },
    confidenceColor (value) {
      return value >= 75 ? 'green' : value >= 55 ? 'blue' : 'orange'
    },
    riskColor (value) {
      return value >= 70 ? 'red' : value >= 45 ? 'orange' : 'green'
    },
    actionPlanCode (item) {
      return String((item && item.actionPlan && item.actionPlan.code) || '')
    },
    actionPlanLabel (item) {
      const action = (item && item.actionPlan) || {}
      const labels = {
        simulate_watch: '可模拟观察',
        wait_pullback: '等回调',
        chasing_review: '追高复核',
        continue_observe: '继续观察',
        risk_review: '风险复盘',
        data_review: '资料复核'
      }
      return action.label || labels[action.code] || '继续观察'
    },
    actionPlanColor (item) {
      const code = this.actionPlanCode(item)
      if (code === 'simulate_watch') return 'green'
      if (code === 'risk_review') return 'red'
      if (code === 'chasing_review' || code === 'wait_pullback') return 'orange'
      if (code === 'data_review') return 'default'
      return 'blue'
    },
    actionPlanReason (item) {
      return (item && item.actionPlan && item.actionPlan.reason) || ''
    },
    positionRiskStatus (item) {
      return String((item && item.positionRisk && item.positionRisk.status) || '')
    },
    positionRiskLabel (item) {
      const risk = (item && item.positionRisk) || {}
      const labels = {
        reasonable: '位置合理',
        elevated: '强势但偏高',
        overheated: '过热谨慎',
        pullback_watch: '回调观察',
        data_insufficient: '数据不足'
      }
      return risk.label || labels[risk.status] || '位置待确认'
    },
    positionRiskColor (item) {
      const status = this.positionRiskStatus(item)
      if (status === 'reasonable') return 'green'
      if (status === 'elevated' || status === 'pullback_watch') return 'gold'
      if (status === 'overheated') return 'orange'
      return 'default'
    },
    positionRiskReason (item) {
      return (item && item.positionRisk && item.positionRisk.reason) || '暂未计算价格位置'
    },
    technicalStatus (item) {
      if (['model_trend_divergence', 'data_review_required'].includes(item.category)) return 'review'
      if (item.category === 'focus_watch' || item.alignment === 'aligned') return 'confirmed'
      if (['downtrend', 'pullback', 'weak_downtrend'].includes(item.trend)) return 'weak'
      return 'watch'
    },
    riskHint (item) {
      const status = this.technicalStatus(item)
      if (this.positionRiskStatus(item) === 'overheated') return '位置偏热需复核'
      if (status === 'confirmed') return '技术确认较好'
      if (status === 'weak') return '技术面转弱'
      if (status === 'review') return '需人工复核'
      return '观察信号'
    },
    bestBacktestResult (pack) {
      if (!pack || !Array.isArray(pack.items)) return pack || null
      return pack.items.filter(item => !item.error && this.backtestMetricsOf(item.result)).sort((a, b) => this.backtestScore(b.result) - this.backtestScore(a.result))[0] || null
    },
    backtestScore (result) {
      const metrics = this.backtestMetricsOf(result)
      if (!metrics) return -999
      const totalReturn = Number(metrics.totalReturn)
      const maxDrawdown = Math.abs(Number(metrics.maxDrawdown || 0))
      const trades = Number(metrics.totalTrades)
      if (!Number.isFinite(totalReturn)) return -999
      return totalReturn - maxDrawdown * 0.6 - (Number.isFinite(trades) && trades < 2 ? 20 : 0)
    },
    backtestPasses (result) {
      const best = this.bestBacktestResult(result)
      const metrics = this.backtestMetricsOf(best && best.result ? best.result : best)
      if (!metrics) return false
      const totalReturn = Number(metrics.totalReturn)
      const totalTrades = Number(metrics.totalTrades)
      return Number.isFinite(totalReturn) && totalReturn > 0 && (!Number.isFinite(totalTrades) || totalTrades >= 2)
    },
    backtestMetricsOf (result) {
      if (!result) return null
      return result.metrics || result
    },
    backtestText (result, error) {
      if (error) return '历史验证失败'
      const best = this.bestBacktestResult(result)
      const bestResult = best && best.result ? best.result : best
      const metrics = this.backtestMetricsOf(bestResult)
      if (!metrics) return '待历史验证'
      const totalReturn = Number(metrics.totalReturn)
      const totalTrades = Number(metrics.totalTrades)
      if (!Number.isFinite(totalReturn)) return '历史验证需复核'
      const label = best && best.label ? best.label : '历史验证'
      const tradeText = Number.isFinite(totalTrades) ? ` / ${totalTrades} 笔` : ''
      return `${label} ${totalReturn > 0 ? '+' : ''}${totalReturn.toFixed(1)}%${tradeText}`
    },
    backtestDetailText (pack) {
      if (!pack || !Array.isArray(pack.items)) return '未执行多策略验证'
      return pack.items.map(item => {
        if (item.error) return `${item.label} 失败`
        const metrics = this.backtestMetricsOf(item.result)
        const totalReturn = metrics ? Number(metrics.totalReturn) : NaN
        const trades = metrics ? Number(metrics.totalTrades) : NaN
        if (!Number.isFinite(totalReturn)) return `${item.label} 需复核`
        return `${item.label} ${totalReturn > 0 ? '+' : ''}${totalReturn.toFixed(1)}%${Number.isFinite(trades) ? `/${trades}笔` : ''}`
      }).join('，')
    },
    backtestColor (result, error) {
      if (error) return 'red'
      const best = this.bestBacktestResult(result)
      const metrics = this.backtestMetricsOf(best && best.result ? best.result : best)
      if (!metrics) return 'default'
      const totalReturn = Number(metrics.totalReturn)
      const trades = Number(metrics.totalTrades)
      if (!Number.isFinite(totalReturn) || (Number.isFinite(trades) && trades < 2)) return 'orange'
      return totalReturn > 0 ? 'green' : 'red'
    },
    comboDecision (item, backtest, backtestError) {
      const held = this.heldSymbolSet.has(String(item.symbol || '').toUpperCase())
      const rank = Number(item.rank || 999)
      const trend = item.trend || ''
      const weakTrend = ['downtrend', 'pullback', 'weak_downtrend'].includes(trend)
      const strongTrend = ['strong_uptrend', 'breakout', 'uptrend'].includes(trend)
      const divergent = ['model_trend_divergence', 'data_review_required'].includes(item.category) || item.alignment === 'divergent'
      const aligned = item.category === 'focus_watch' || item.alignment === 'aligned'
      const bestBacktest = this.bestBacktestResult(backtest)
      const metrics = this.backtestMetricsOf(bestBacktest && bestBacktest.result ? bestBacktest.result : bestBacktest)
      const totalReturn = metrics ? Number(metrics.totalReturn) : null
      const maxDrawdown = metrics ? Math.abs(Number(metrics.maxDrawdown || 0)) : null
      const trades = metrics ? Number(metrics.totalTrades) : null
      if (divergent || backtestError) return { type: 'manual_review', label: '人工复核', color: 'orange', reason: '模型、趋势、资料或历史验证存在分歧。' }
      if (metrics && Number.isFinite(trades) && trades < 2) return { type: 'manual_review', label: '样本太少', color: 'orange', reason: '只读历史验证交易次数太少。' }
      if (metrics && Number.isFinite(totalReturn) && totalReturn <= 0) {
        return held
          ? { type: 'risk_review', label: '风险复盘', color: 'red', reason: '历史验证不支持继续扩大模拟暴露。' }
          : { type: 'watch_only', label: '仅观察', color: 'orange', reason: '历史验证暂不支持新增模拟观察。' }
      }
      if (metrics && Number.isFinite(totalReturn) && Number.isFinite(maxDrawdown) && maxDrawdown >= Math.max(20, Math.abs(totalReturn) * 1.2)) {
        return { type: 'manual_review', label: '回撤偏大', color: 'orange', reason: '历史验证回撤相对收益偏大。' }
      }
      if (held && (weakTrend || divergent || (rank > 50 && !strongTrend))) return { type: 'risk_review', label: '风险复盘', color: weakTrend ? 'red' : 'orange', reason: '持仓排名掉队且趋势、资料或技术面出现确认信号。' }
      if (held && rank <= 50 && !weakTrend) return { type: 'keep_watch', label: '继续观察', color: 'green', reason: '持仓仍在研究池，未出现明确转弱确认。' }
      if (!held && rank <= 30 && strongTrend && this.positionRiskStatus(item) === 'overheated') return { type: 'manual_review', label: '追高复核', color: 'orange', reason: '趋势偏强但位置偏热，先复核追高风险。' }
      if (!held && rank <= 30 && aligned && strongTrend) return { type: 'simulate_watch', label: '新增观察', color: 'green', reason: 'qlib、QuantDinger 和交叉分析相对一致。' }
      if (!held && rank <= 30 && (aligned || strongTrend)) return { type: 'watch_only', label: '观察', color: 'blue', reason: '进入研究池，但仍缺少完整一致信号。' }
      return { type: 'watch_only', label: '观察', color: 'default', reason: '信号强度不足，先观察。' }
    },
    unwrap (response) {
      if (response && response.data && Object.prototype.hasOwnProperty.call(response.data, 'data')) return response.data.data
      return response && response.data ? response.data : response
    },
    assertSimulationSafe (payload) {
      const trading = payload && payload.trading
      const simulationOnly = payload && payload.simulation_only === true
      const safeTrading = trading && trading.simulation_only === true && trading.real_orders_enabled === false && trading.connects_to_broker === false
      if (!simulationOnly || !safeTrading) {
        this.safetyError = '模拟账户安全边界异常：后端未返回 simulation_only=true / real_orders_enabled=false / connects_to_broker=false，已禁止确认。'
        return false
      }
      this.safetyError = ''
      return true
    },
    async refreshAll () {
      this.loading = true
      this.error = ''
      try {
        const data = this.unwrap(await getTwStockSimAccounts())
        this.assertSimulationSafe(data)
        this.accounts = Array.isArray(data.items) ? data.items : []
        this.accountsLoaded = true
        if (this.accounts.length) {
          if (!this.activeAccountUid || !this.accounts.some(item => item.account_uid === this.activeAccountUid)) {
            this.activeAccountUid = this.accounts[0].account_uid
          }
          this.tradeForm.account_uid = this.activeAccountUid
          await this.loadAccountDetail()
          await this.loadStrategySignals()
        } else {
          this.account = {}
          this.positions = []
          this.trades = []
        }
      } catch (error) {
        this.error = this.errorText(error, '模拟账户加载失败')
      } finally {
        this.loading = false
      }
    },
    async createAccount () {
      this.creatingAccount = true
      this.error = ''
      try {
        const data = this.unwrap(await createTwStockSimAccount(this.accountForm))
        if (this.assertSimulationSafe(data)) {
          this.activeAccountUid = data.account && data.account.account_uid
          await this.refreshAll()
        }
      } catch (error) {
        this.error = this.errorText(error, '创建模拟账户失败')
      } finally {
        this.creatingAccount = false
      }
    },
    async handleAccountChange () {
      this.tradeForm.account_uid = this.activeAccountUid
      this.clearDraft()
      await this.loadAccountDetail()
    },
    async loadAccountDetail () {
      if (!this.activeAccountUid) return
      const [accountData, positionData, tradeData] = await Promise.all([
        getTwStockSimAccount(this.activeAccountUid),
        getTwStockSimPositions(this.activeAccountUid),
        getTwStockSimTrades(this.activeAccountUid, { limit: 100 })
      ])
      const accountPayload = this.unwrap(accountData)
      const positionPayload = this.unwrap(positionData)
      const tradePayload = this.unwrap(tradeData)
      this.assertSimulationSafe(accountPayload)
      this.assertSimulationSafe(positionPayload)
      this.assertSimulationSafe(tradePayload)
      this.account = accountPayload.account || {}
      this.positions = Array.isArray(positionPayload.items) ? positionPayload.items : []
      this.trades = Array.isArray(tradePayload.items) ? tradePayload.items : []
      if (this.selectedMarkerSymbol !== 'all' && !this.markerSymbols.includes(this.selectedMarkerSymbol)) {
        this.selectedMarkerSymbol = 'all'
      }
    },
    async createDraft (side) {
      this.drafting = true
      this.error = ''
      this.tradeForm.side = side
      try {
        const data = this.unwrap(await draftTwStockSimOrder({
          ...this.tradeForm,
          account_uid: this.tradeForm.account_uid || this.activeAccountUid,
          source_type: this.tradeForm.source_type || 'manual',
          source_context: this.tradeForm.source_context || {}
        }))
        this.assertSimulationSafe(data)
        this.draftResponse = data
      } catch (error) {
        const payload = error && error.response && error.response.data && error.response.data.data
        if (payload) {
          this.assertSimulationSafe(payload)
          this.draftResponse = payload
        }
        this.error = this.errorText(error, '生成模拟草稿失败')
      } finally {
        this.drafting = false
      }
    },
    async confirmDraft () {
      if (!this.canConfirmDraft) return
      this.confirmingDraft = true
      this.error = ''
      try {
        const data = this.unwrap(await confirmTwStockSimOrder(this.draftOrder.sim_order_uid))
        if (this.assertSimulationSafe(data)) {
          this.draftResponse = data
          await this.loadAccountDetail()
        }
      } catch (error) {
        this.error = this.errorText(error, '确认模拟成交失败')
      } finally {
        this.confirmingDraft = false
      }
    },
    async cancelDraft () {
      if (!this.draftOrder) return
      this.cancellingDraft = true
      this.error = ''
      try {
        const data = this.unwrap(await cancelTwStockSimOrder(this.draftOrder.sim_order_uid))
        this.assertSimulationSafe(data)
        this.draftResponse = data
      } catch (error) {
        this.error = this.errorText(error, '取消草稿失败')
      } finally {
        this.cancellingDraft = false
      }
    },
    loadPendingSignalDraft () {
      try {
        const raw = window.localStorage.getItem(SIM_DRAFT_CONTEXT_KEY)
        if (!raw) return
        const draft = JSON.parse(raw)
        if (!draft || !['qlib_rank', 'cross_analysis'].includes(draft.source_type)) return
        this.pendingSignalDraft = { ...draft, user_edited: false }
        this.tradeForm.symbol = draft.symbol || this.tradeForm.symbol
        this.tradeForm.side = draft.side === 'sell' ? 'sell' : 'buy'
        this.tradeForm.quantity = Number(draft.quantity || 10)
        this.tradeForm.source_type = draft.source_type
        this.tradeForm.source_context = { ...(draft.source_context || {}), user_edited: false }
        window.localStorage.removeItem(SIM_DRAFT_CONTEXT_KEY)
      } catch (error) {
        this.error = '研究页预填模拟草稿读取失败，可继续手动填写。'
      }
    },
    markSignalDraftEdited () {
      if (!this.pendingSignalDraft) return
      this.pendingSignalDraft = { ...this.pendingSignalDraft, user_edited: true }
      this.tradeForm.source_context = { ...(this.tradeForm.source_context || {}), user_edited: true }
    },
    async loadStrategySignals () {
      this.loadingStrategySignals = true
      try {
        const [qlib, cross] = await Promise.allSettled([
          getLatestQlibOptionCSignals({ bucket: 'top50', enrichTrend: true, trendLimit: 120 }),
          getTwStockCrossAnalysisLatest({ bucket: 'top50', maxItems: 50, includeRawTrend: true })
        ])
        this.strategySignals = {
          qlib: qlib.status === 'fulfilled' ? (this.unwrap(qlib.value) || null) : null,
          cross: cross.status === 'fulfilled' ? (this.unwrap(cross.value) || null) : null
        }
      } catch (error) {
        this.strategySignals = { qlib: null, cross: null }
      } finally {
        this.loadingStrategySignals = false
      }
    },
    async validateStrategyBacktest (item) {
      const symbol = String(item && item.symbol || '').toUpperCase()
      if (!symbol || this.validatingBacktestSymbol) return
      this.validatingBacktestSymbol = symbol
      this.$delete(this.strategyBacktestErrors, symbol)
      try {
        const endDate = this.latestSignalDate(item) || this.todayDateString()
        const startDate = this.shiftDateString(endDate, -365)
        const items = []
        for (const strategy of this.readonlyBacktestStrategies) {
          try {
            const data = this.unwrap(await runTwStockReadonlyBacktest({
              symbol,
              strategyId: strategy.id,
              startDate,
              endDate,
              initialCapital: 1000000,
              strategyConfig: { template: strategy.template || {} }
            }))
            items.push({ id: strategy.id, label: strategy.label, result: data && data.result ? data.result : data })
          } catch (error) {
            items.push({ id: strategy.id, label: strategy.label, error: this.errorText(error, '验证失败') })
          }
        }
        this.$set(this.strategyBacktestResults, symbol, { items })
        this.$message.success(`${symbol} 多策略只读历史验证完成`)
      } catch (error) {
        const message = this.errorText(error, '只读历史验证失败')
        this.$set(this.strategyBacktestErrors, symbol, message)
        this.$message.warning(`${symbol} ${message}`)
      } finally {
        this.validatingBacktestSymbol = ''
      }
    },
    latestSignalDate (item) {
      const values = [item && item.crossAsOf, item && item.qlibAsOf]
        .map(value => String(value || '').slice(0, 10))
        .filter(value => /^\d{4}-\d{2}-\d{2}$/.test(value))
      return values[0] || ''
    },
    todayDateString () {
      return new Date().toISOString().slice(0, 10)
    },
    shiftDateString (value, days) {
      const parsed = value ? new Date(`${value}T00:00:00Z`) : new Date()
      if (Number.isNaN(parsed.getTime())) return ''
      parsed.setUTCDate(parsed.getUTCDate() + Number(days || 0))
      return parsed.toISOString().slice(0, 10)
    },
    prefillStrategyDraft (item, side) {
      if (!item || !item.symbol) return
      this.tradeForm.symbol = item.symbol
      this.tradeForm.side = side === 'sell' ? 'sell' : 'buy'
      this.tradeForm.quantity = side === 'sell' ? Number(item.quantity || 10) : 10
      this.tradeForm.source_type = item.category ? 'cross_analysis' : 'qlib_rank'
      this.tradeForm.source_context = {
        symbol: item.symbol,
        qlib_rank: item.rank,
        qlib_score: item.score,
        trend_label: item.trend,
        trend_score: item.trendScore,
        cross_category: item.category,
        cross_alignment: item.alignment,
        technical_status: item.technicalStatus,
        risk_hint: item.riskHint,
        action_plan: item.actionPlanLabel,
        position_risk: item.positionRiskLabel,
        combo_label: item.comboLabel,
        combo_type: item.comboType,
        combo_reason: item.comboReason,
        backtest_strategy: item.backtest && this.bestBacktestResult(item.backtest) ? this.bestBacktestResult(item.backtest).id || 'builtin_best' : '',
        backtest_return: item.backtest && this.backtestMetricsOf((this.bestBacktestResult(item.backtest) || {}).result || this.bestBacktestResult(item.backtest)) ? this.backtestMetricsOf((this.bestBacktestResult(item.backtest) || {}).result || this.bestBacktestResult(item.backtest)).totalReturn : null,
        backtest_trades: item.backtest && this.backtestMetricsOf((this.bestBacktestResult(item.backtest) || {}).result || this.bestBacktestResult(item.backtest)) ? this.backtestMetricsOf((this.bestBacktestResult(item.backtest) || {}).result || this.bestBacktestResult(item.backtest)).totalTrades : null,
        source_label: side === 'sell' ? '低换手风险复盘候选' : '低换手模拟买入候选',
        user_edited: false
      }
      this.pendingSignalDraft = { symbol: item.symbol, source_type: this.tradeForm.source_type, user_edited: false }
      this.clearDraft()
    },
    clearDraft () {
      this.draftResponse = null
    },
    sideText (side) {
      return side === 'sell' ? '模拟卖出' : '模拟买入'
    },
    warningText (warning) {
      const labels = {
        stale_latest_close: '数据日期需复核',
        missing_latest_close: '缺少最新收盘价',
        unknown_price_date: '价格日期未知'
      }
      return labels[warning] || warning
    },
    errorText (error, fallback) {
      const response = error && error.response && error.response.data
      return (response && response.msg) || error.message || fallback
    },
    number (value, digits = 0) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return num.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    },
    money (value) {
      return this.number(value, 2)
    },
    signedMoney (value) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return `${num > 0 ? '+' : ''}${this.money(num)}`
    },
    percent (value) {
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return `${num > 0 ? '+' : ''}${(num * 100).toFixed(2)}%`
    }
  }
}
</script>

<style lang="less" scoped>
.tw-stock-sim-account {
  min-height: 100%;
  padding: 20px;
  background: #f5f7fb;
}

.topbar,
.account-toolbar,
.manual-form,
.draft-actions,
.confirm-row,
.create-form,
.marker-toolbar,
.marker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.topbar {
  justify-content: space-between;
  margin-bottom: 16px;
}

.topbar h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 650;
}

.subline,
.muted {
  color: #667085;
  font-size: 13px;
}

.boundary-alert,
.state-alert {
  margin-bottom: 12px;
}

.sim-card {
  margin-bottom: 16px;
}

.metric-grid,
.draft-grid,
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.metric-card,
.draft-grid span {
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
}

.metric-card span,
.draft-grid span {
  color: #667085;
  font-size: 12px;
}

.metric-card strong,
.draft-grid strong {
  display: block;
  color: #111827;
  font-size: 18px;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.metric-card small {
  color: #98a2b3;
}

.draft-box {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #d7e3f3;
  border-radius: 8px;
  background: #fbfdff;
}

.draft-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.warning-list,
.confirm-row,
.marker-list {
  margin-top: 12px;
}

.marker-toolbar {
  justify-content: space-between;
}

.marker-list {
  display: grid;
  gap: 8px;
}

.marker-item {
  padding: 10px 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
}

.combo-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.combo-card {
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
}

.combo-card--primary {
  border-color: #b7d6ff;
  background: #f7fbff;
}

.combo-card span,
.combo-card small {
  display: block;
  color: #667085;
  font-size: 12px;
}

.combo-card strong {
  display: block;
  margin: 3px 0;
  color: #111827;
  font-size: 18px;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.combo-rules,
.strategy-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.combo-rules {
  margin-top: 10px;
}

.today-advice-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #d8e5f5;
  border-radius: 8px;
  background: #fbfdff;
}

.today-advice-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.today-advice-head > div {
  min-width: 0;
}

.today-advice-head strong,
.today-advice-head span {
  display: block;
}

.today-advice-head span,
.today-advice-reason {
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.compact-alert {
  margin-bottom: 8px;
}

.today-advice-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 6px;
  scrollbar-gutter: stable;
}

.today-advice-item {
  min-width: 0;
  padding: 10px 0 0;
  border-top: 1px solid #eef2f7;
}

.today-advice-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.today-advice-main strong {
  color: #111827;
}

.today-advice-main span {
  color: #475467;
  font-size: 12px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.module-box {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.module-title,
.queue-head,
.rule-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.module-title {
  min-height: 28px;
  margin-bottom: 8px;
}

.module-title span,
.queue-item span,
.rule-item span {
  color: #667085;
  font-size: 12px;
}

.rule-list,
.module-list {
  display: grid;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 6px;
  scrollbar-gutter: stable;
}

.rule-item,
.queue-item {
  min-width: 0;
  padding-top: 8px;
  border-top: 1px solid #eef2f7;
}

.rule-item strong,
.queue-head strong {
  min-width: 0;
  color: #111827;
  overflow-wrap: anywhere;
}

.queue-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.strategy-box {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.strategy-title,
.strategy-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.strategy-title {
  flex: 0 0 auto;
}

.strategy-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.strategy-title span,
.strategy-item span {
  color: #667085;
  font-size: 12px;
}

.signal-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.strategy-evidence-line {
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.strategy-list {
  display: grid;
  gap: 10px;
  margin-top: 10px;
  max-height: 340px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 6px;
  scrollbar-gutter: stable;
}

.strategy-item {
  padding-top: 10px;
  border-top: 1px solid #eef2f7;
}

.strategy-item .ant-btn {
  align-self: flex-start;
}

.empty-note {
  color: #98a2b3;
  padding: 12px 0;
}

.responsive-table {
  overflow-x: auto;
}

.responsive-table /deep/ .ant-table-wrapper,
.responsive-table /deep/ .ant-table-content {
  overflow-x: auto;
}

@media (max-width: 900px) {
  .metric-grid,
  .draft-grid,
  .strategy-grid,
  .combo-overview,
  .module-grid {
    grid-template-columns: 1fr;
  }

  .strategy-list {
    max-height: 260px;
  }

  .today-advice-head {
    flex-direction: column;
  }
}
</style>
