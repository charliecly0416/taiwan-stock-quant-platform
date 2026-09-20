<template>
  <a-card class="paper-portfolio-panel" :bordered="false" data-testid="paper-portfolio-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>模拟账户状态</span>
        <div class="readonly-tags">
          <a-tag color="blue">模拟账户</a-tag>
          <a-tag :color="stateTagColor">{{ stateLabel }}</a-tag>
        </div>
      </div>
    </template>

    <div class="paper-toolbar">
      <a-button size="small" :loading="loading" @click="loadAll">
        <a-icon type="reload" /> 刷新模拟账户
      </a-button>
      <a-button
        size="small"
        type="primary"
        data-testid="paper-apply-button"
        :disabled="applyDisabled"
        :loading="applying"
        @click="openApplyConfirm"
      >
        <a-icon type="check-circle" /> 应用到模拟账户
      </a-button>
      <a-button
        size="small"
        type="danger"
        ghost
        data-testid="paper-reset-button"
        :disabled="resetDisabled"
        :loading="resetting"
        @click="openResetConfirm"
      >
        <a-icon type="delete" /> 重置模拟账户
      </a-button>
    </div>

    <a-alert
      class="paper-alert"
      type="info"
      show-icon
      message="只影响模拟账户，不接入券商，不产生真实交易委托。"
    />
    <a-alert v-if="error" class="paper-alert" type="warning" show-icon :message="error" />
    <a-alert
      v-if="dateContextMismatch"
      class="paper-alert"
      type="warning"
      show-icon
      :message="dateContextMismatchText"
    />

    <div v-if="loading" class="paper-empty">正在读取模拟账户状态...</div>
    <div v-else-if="!decisionReady" class="paper-empty" data-testid="paper-no-decision">{{ emptyText }}</div>
    <div v-else class="paper-content">
      <div class="paper-summary-grid">
        <div>
          <span>现金</span>
          <strong>{{ formatMoney(currentCash) }}</strong>
          <small>只用于模拟账户</small>
        </div>
        <div>
          <span>持仓数</span>
          <strong>{{ positionCount }}</strong>
          <small>当前模拟持仓</small>
        </div>
        <div>
          <span>当前决策日期</span>
          <strong>{{ currentDecisionDate }}</strong>
          <small>策略可见日期</small>
        </div>
        <div>
          <span>可否应用</span>
          <strong>{{ canApplyText }}</strong>
          <small>{{ applyBlockReasonText }}</small>
        </div>
      </div>

      <div class="paper-status-line" :class="{ blocked: applyBlocked }">
        <div>
          <span>阻断原因</span>
          <strong>{{ applyBlockReasonText }}</strong>
        </div>
        <a-button size="small" @click="$emit('ask-agent', explainPaperReasonQuestion)">
          <a-icon type="question-circle" /> 解释原因
        </a-button>
      </div>

      <div class="paper-action-grid">
        <section>
          <div class="paper-section-head"><strong>预计模拟调出</strong><span>{{ sellActions.length }}</span></div>
          <div v-if="sellActions.length" class="paper-action-list">
            <div v-for="item in sellActions" :key="`sell-${item.symbol}-${item.reason}`" class="paper-action-row">
              <strong>{{ item.instrument || item.symbol }}</strong>
              <span>{{ item.quantity }} 股 @ {{ formatMoney(item.estimated_reference_price) }}</span>
              <small>{{ friendlyReason(item.reason || item.applicability) }}</small>
            </div>
          </div>
          <div v-else class="paper-empty compact">暂无预计模拟调出。</div>
        </section>
        <section>
          <div class="paper-section-head"><strong>预计模拟调入</strong><span>{{ buyActions.length }}</span></div>
          <div v-if="buyActions.length" class="paper-action-list">
            <div v-for="item in buyActions" :key="`buy-${item.symbol}-${item.reason}`" class="paper-action-row">
              <strong>{{ item.instrument || item.symbol }}</strong>
              <span>{{ item.quantity }} 股 @ {{ formatMoney(item.estimated_reference_price) }}</span>
              <small>{{ friendlyReason(item.reason || item.applicability) }}</small>
            </div>
          </div>
          <div v-else class="paper-empty compact">暂无预计模拟调入。</div>
        </section>
        <section>
          <div class="paper-section-head"><strong>跳过与不可应用</strong><span>{{ skippedPreviewActions.length }}</span></div>
          <div v-if="skippedPreviewActions.length" class="paper-action-list">
            <div v-for="item in skippedPreviewActions" :key="`skip-${item.symbol}-${item.reason}`" class="paper-action-row muted">
              <strong>{{ item.instrument || item.symbol || '-' }}</strong>
              <span>{{ friendlyReason(item.reason || item.applicability) }}</span>
              <small>{{ actionTypeLabel(item.action_type) }}</small>
            </div>
          </div>
          <div v-else class="paper-empty compact">暂无跳过或不可应用项。</div>
        </section>
      </div>

      <a-alert v-if="alreadyApplied" class="paper-alert" type="success" show-icon message="今天已应用到模拟账户，按钮已置灰。" />
      <a-alert v-if="staleEpoch" class="paper-alert" type="warning" show-icon message="模拟账户已变化，请刷新后重新确认。" />

      <div v-if="applyResult" class="paper-result" data-testid="paper-apply-result">
        <div class="paper-section-head"><strong>模拟账户已更新</strong><span>{{ applyResult.status || '-' }}</span></div>
        <div class="paper-summary-grid compact-grid">
          <div><span>应用日期</span><strong>{{ applyResult.asof || '-' }}</strong></div>
          <div><span>现金变化</span><strong>{{ formatMoney(applyResult.cash_before) }} -> {{ formatMoney(applyResult.cash_after) }}</strong></div>
          <div><span>模拟处理</span><strong>{{ resultExecutions.length }}</strong></div>
          <div><span>跳过/拒绝</span><strong>{{ resultSkipped.length + resultRejected.length }}</strong></div>
        </div>
        <div class="paper-result-columns">
          <div><strong>模拟应用明细</strong><span v-for="item in resultExecutions" :key="item.paper_execution_id">{{ sideText(item.side) }} {{ item.symbol }} {{ item.quantity }}</span><small v-if="!resultExecutions.length">无</small></div>
          <div><strong>已跳过</strong><span v-for="item in resultSkipped" :key="`${item.symbol}-${item.reason}`">{{ item.symbol || '-' }}：{{ friendlyReason(item.reason) }}</span><small v-if="!resultSkipped.length">无</small></div>
          <div><strong>已拒绝</strong><span v-for="item in resultRejected" :key="`${item.symbol}-${item.reason}`">{{ item.symbol || '-' }}：{{ friendlyReason(item.reason) }}</span><small v-if="!resultRejected.length">无</small></div>
        </div>
      </div>

      <div v-if="resetResult" class="paper-result" data-testid="paper-reset-result">
        <div class="paper-section-head"><strong>重置结果</strong><span>模拟账户已重置</span></div>
        <span>旧状态已归档，需要重新生成策略后再应用。</span>
      </div>

      <a-collapse class="paper-tech-collapse" :bordered="false">
        <a-collapse-panel key="paper-tech" header="查看模拟账户技术详情">
          <div class="paper-tech-grid">
            <span v-for="row in technicalRows" :key="row.label"><strong>{{ row.label }}</strong>{{ row.value }}</span>
          </div>
        </a-collapse-panel>
      </a-collapse>
    </div>

    <a-modal
      v-model="applyConfirmVisible"
      title="确认应用到模拟账户"
      ok-text="确认应用到模拟账户"
      cancel-text="取消"
      :confirm-loading="applying"
      @ok="confirmApply"
    >
      <div class="paper-confirm-body" data-testid="paper-apply-confirm">
        <p>此操作只会写入模拟账户，不会产生真实交易委托。</p>
        <p>账户 {{ accountId }} / 当前决策日期 {{ currentDecisionDate }}</p>
        <p>将模拟调出 {{ sellActions.length }} 项，模拟调入 {{ buyActions.length }} 项，跳过 {{ skippedPreviewActions.length }} 项。</p>
      </div>
    </a-modal>

    <a-modal
      v-model="resetConfirmVisible"
      title="确认重置模拟账户"
      ok-text="确认重置模拟账户"
      cancel-text="取消"
      :confirm-loading="resetting"
      @ok="confirmReset"
    >
      <div class="paper-confirm-body" data-testid="paper-reset-confirm">
        <p>重置模拟账户会清空当前模拟持仓，旧状态会归档。</p>
        <p>当前现金 {{ formatMoney(currentCash) }}，当前持仓 {{ positionCount }} 项。</p>
        <p>重置后模拟初始现金 {{ formatMoney(initialCash) }}。</p>
      </div>
    </a-modal>
  </a-card>
</template>

<script>
import { usePaperPortfolio } from '../composables/usePaperPortfolio'
// Legacy API ownership remains explicit while the composable delegates to these helpers.
import {
  getTwStockPaperPortfolioLatestDecision,
  getTwStockPaperPortfolioState,
  getTwStockPaperPortfolioApplyRuns
} from '@/api/tw-stock-readonly'
import {
  applyTwStockPaperPortfolioDecision,
  resetTwStockPaperPortfolio
} from '@/api/tw-stock-action'

export default {
  name: 'PaperPortfolioPanel',
  props: {
    phaseYzStatus: {
      type: Object,
      default: null
    },
    activeSignalAsOf: {
      type: String,
      default: ''
    }
  },
  data () {
    return {
      loading: false,
      applying: false,
      resetting: false,
      latestPayload: null,
      statePayload: null,
      applyRunsPayload: null,
      applyResult: null,
      resetResult: null,
      error: '',
      applyConfirmVisible: false,
      resetConfirmVisible: false,
      paperPortfolioComposable: null
    }
  },
  computed: {
    decision () { return this.latestPayload || {} },
    intent () { return this.decision.intent || {} },
    preview () { return this.decision.preview || {} },
    account () { return (this.statePayload && this.statePayload.paper_account) || {} },
    positions () { return (this.statePayload && this.statePayload.positions) || [] },
    applyRuns () { return (this.applyRunsPayload && this.applyRunsPayload.items) || [] },
    decisionReady () { return this.latestPayload && this.latestPayload.ok === true && this.decision.paper_order_intent_artifact_path },
    accountId () { return this.decision.paper_account_id || this.account.account_uid || '-' },
    accountEpoch () { return this.decision.paper_account_epoch || this.account.paper_account_epoch || '-' },
    currentCash () { return this.account.cash == null ? this.preview.cash_before : this.account.cash },
    initialCash () { return this.account.initial_cash == null ? this.currentCash : this.account.initial_cash },
    positionCount () { return this.positions.length },
    actions () { return Array.isArray(this.intent.actions) ? this.intent.actions : [] },
    sellActions () { return this.actions.filter(item => item.action_type === 'paper_sell_intent' && item.applicability === 'applicable') },
    buyActions () { return this.actions.filter(item => item.action_type === 'paper_buy_intent' && item.applicability === 'applicable') },
    skippedPreviewActions () { return this.actions.filter(item => item.action_type === 'paper_skip' || item.applicability !== 'applicable') },
    alreadyApplied () { return this.applyRuns.some(item => item.decision_id === this.decision.decision_id || (item.result && item.result.decision_id === this.decision.decision_id)) },
    staleEpoch () { return this.decisionReady && Number(this.account.paper_account_epoch || this.decision.paper_account_epoch) !== Number(this.decision.paper_account_epoch) },
    decisionDateMismatch () {
      return this.hasComparableDate(this.activeSignalAsOf) && this.hasComparableDate(this.decision.asof) && this.decision.asof !== this.activeSignalAsOf
    },
    phaseYZDateMismatch () {
      const phaseDate = this.phaseYzStatus && this.phaseYzStatus.signal_asof
      return this.hasComparableDate(this.activeSignalAsOf) && this.hasComparableDate(phaseDate) && phaseDate !== this.activeSignalAsOf
    },
    dateContextMismatch () { return this.decisionDateMismatch || this.phaseYZDateMismatch },
    dateContextMismatchText () {
      const dates = []
      if (this.decisionDateMismatch) dates.push(`模拟决策 ${this.decision.asof}`)
      if (this.phaseYZDateMismatch) dates.push(`模拟状态 ${this.phaseYzStatus.signal_asof}`)
      return `${dates.join('、')} 与当前信号 ${this.activeSignalAsOf} 不属于同一日期，已作为历史状态隔离，不能应用。`
    },
    phaseYZPaperBlocked () { return this.phaseYzStatus && this.phaseYzStatus.paper_apply_allowed === false },
    phaseYZPaperBlockMessage () {
      return this.userFacingBlockReason(this.phaseYzStatus && (this.phaseYzStatus.paper_apply_blocked_reason || this.phaseYzStatus.execution_price_status))
    },
    currentDecisionDate () { return this.decision.asof || '-' },
    applyBlocked () { return this.dateContextMismatch || this.phaseYZPaperBlocked || this.staleEpoch || !this.decisionReady || this.alreadyApplied },
    canApplyText () {
      if (!this.decisionReady) return '暂无策略'
      if (this.dateContextMismatch) return '历史状态'
      if (this.phaseYZPaperBlocked) return '暂不能应用'
      if (this.staleEpoch) return '需刷新确认'
      if (this.alreadyApplied) return '今日已应用'
      return '可以应用'
    },
    applyBlockReasonText () {
      if (!this.decisionReady) return '暂无可应用到模拟账户的策略。'
      if (this.dateContextMismatch) return this.dateContextMismatchText
      if (this.phaseYZPaperBlocked) return this.phaseYZPaperBlockMessage
      if (this.staleEpoch) return '模拟账户已变化，请刷新后重新确认。'
      if (this.alreadyApplied) return '今天已应用到模拟账户。'
      return '仅影响模拟账户，不接入券商。'
    },
    explainPaperReasonQuestion () { return '为什么模拟账户不能应用？' },
    technicalRows () {
      return [
        { label: 'paper_account_id', value: this.accountId },
        { label: 'paper_account_epoch', value: this.accountEpoch },
        { label: 'decision_id', value: this.decision.decision_id },
        { label: 'model_id', value: this.decision.model_id },
        { label: 'strategy_rule', value: this.decision.strategy_rule },
        { label: 'paper_order_intent_artifact_path', value: this.decision.paper_order_intent_artifact_path },
        { label: 'input_checksum', value: this.decision.input_checksum },
        { label: 'active_signal_asof', value: this.activeSignalAsOf },
        { label: 'initial_cash', value: this.formatMoney(this.initialCash) },
        { label: 'apply_id', value: this.applyResult && this.applyResult.apply_id },
        { label: 'raw_block_reason', value: this.phaseYzStatus && (this.phaseYzStatus.paper_apply_blocked_reason || this.phaseYzStatus.execution_price_status) }
      ].map(row => ({ label: row.label, value: row.value === null || row.value === undefined || row.value === '' ? '-' : row.value }))
    },
    applyDisabled () { return !this.decisionReady || this.dateContextMismatch || this.phaseYZPaperBlocked || this.alreadyApplied || this.staleEpoch || this.applying || this.resetting },
    resetDisabled () { return !this.account.account_uid || this.applying || this.resetting },
    resultExecutions () { return (this.applyResult && this.applyResult.paper_executions) || [] },
    resultSkipped () { return (this.applyResult && this.applyResult.skipped_actions) || [] },
    resultRejected () { return (this.applyResult && this.applyResult.rejected_actions) || [] },
    stateLabel () {
      if (this.loading) return '读取中'
      if (this.error) return '需复核'
      if (!this.decisionReady) return '暂无策略'
      if (this.dateContextMismatch) return '历史状态'
      if (this.phaseYZPaperBlocked) return '等待开盘价'
      if (this.alreadyApplied) return '今日已应用'
      if (this.staleEpoch) return '需刷新确认'
      if (this.applyResult) return '已更新'
      return '可应用'
    },
    stateTagColor () {
      if (this.stateLabel === '可应用') return 'green'
      if (this.stateLabel === '已更新' || this.stateLabel === '今日已应用') return 'blue'
      if (this.stateLabel === '读取中') return 'cyan'
      return 'orange'
    },
    emptyText () {
      if (this.error) return this.error
      if (this.latestPayload && this.latestPayload.status === 'no_account') return '暂无匹配的模拟账户。'
      return '暂无可应用到模拟账户的策略。'
    }
  },
  mounted () {
    this.loadAll()
  },
  methods: {
    hasComparableDate (value) {
      return !!value && value !== '-'
    },
    unwrap (response) {
      if (response && Object.prototype.hasOwnProperty.call(response, 'code') && Object.prototype.hasOwnProperty.call(response, 'data')) return response.data
      if (response && response.data && Object.prototype.hasOwnProperty.call(response.data, 'data')) return response.data.data
      if (response && Object.prototype.hasOwnProperty.call(response, 'data')) return response.data
      return response
    },
    async loadAll () {
      this.loading = true
      this.error = ''
      try {
        if (!this.paperPortfolioComposable) this.paperPortfolioComposable = usePaperPortfolio()
        const bundle = await this.paperPortfolioComposable.load()
        const latest = this.unwrap(bundle && bundle.latest)
        this.latestPayload = latest
        if (latest && latest.ok === true && latest.paper_account_id) {
          this.statePayload = this.unwrap(bundle.account)
          this.applyRunsPayload = this.unwrap(bundle.runs)
        }
      } catch (error) {
        this.error = this.friendlyError(error)
      } finally {
        this.loading = false
      }
    },
    openApplyConfirm () { if (!this.applyDisabled) this.applyConfirmVisible = true },
    openResetConfirm () { if (!this.resetDisabled) this.resetConfirmVisible = true },
    async confirmApply () {
      this.applying = true
      this.error = ''
      try {
        const payload = {
          paper_account_id: this.decision.paper_account_id,
          paper_account_epoch: this.decision.paper_account_epoch,
          decision_id: this.decision.decision_id,
          paper_order_intent_artifact_path: this.decision.paper_order_intent_artifact_path,
          input_checksum: this.decision.input_checksum,
          idempotency_key: `paper_apply_${this.decision.decision_id}_${Date.now()}`,
          confirmed_by_user: true,
          confirm_text: '确认应用到模拟账户，此操作只影响模拟账户'
        }
        if (!this.paperPortfolioComposable) this.paperPortfolioComposable = usePaperPortfolio()
        const result = this.unwrap(await this.paperPortfolioComposable.apply(payload))
        this.applyResult = result
        this.applyConfirmVisible = false
        await this.loadAll()
      } catch (error) {
        this.error = this.friendlyError(error)
      } finally {
        this.applying = false
      }
    },
    async confirmReset () {
      this.resetting = true
      this.error = ''
      try {
        const payload = {
          paper_account_id: this.accountId,
          current_epoch: this.account.paper_account_epoch || this.decision.paper_account_epoch,
          idempotency_key: `paper_reset_${this.accountId}_${Date.now()}`,
          input_checksum: `reset:${this.accountId}:${this.account.paper_account_epoch || this.decision.paper_account_epoch}:${Date.now()}`,
          confirmed_by_user: true,
          confirm_text: '确认重置模拟账户',
          reset_initial_cash: this.initialCash
        }
        if (!this.paperPortfolioComposable) this.paperPortfolioComposable = usePaperPortfolio()
        this.resetResult = this.unwrap(await this.paperPortfolioComposable.reset(payload))
        this.applyResult = null
        this.resetConfirmVisible = false
        await this.loadAll()
      } catch (error) {
        this.error = this.friendlyError(error)
      } finally {
        this.resetting = false
      }
    },
    userFacingBlockReason (reason) {
      const key = String(reason || '').trim()
      const map = {
        next_open_unavailable: '等待目标交易日开盘价，暂不能应用到模拟账户。',
        execution_price_pending: '等待目标交易日开盘价，暂不能应用到模拟账户。',
        execution_price_unavailable: '等待目标交易日开盘价，暂不能应用到模拟账户。'
      }
      return map[key] || '等待目标交易日开盘价，暂不能应用到模拟账户。'
    },
    actionTypeLabel (type) {
      const map = {
        paper_buy_intent: '预计模拟调入',
        paper_sell_intent: '预计模拟调出',
        paper_skip: '跳过'
      }
      return map[type] || '不可应用'
    },
    sideText (side) {
      const key = String(side || '').toLowerCase()
      if (key === 'buy') return '调入'
      if (key === 'sell') return '调出'
      return side || '-'
    },
    friendlyReason (reason) {
      const map = {
        cash_insufficient: '模拟现金不足，未执行',
        oversell: '模拟持仓不足，未执行',
        action_unavailable: '当前持仓或策略条件不满足，已跳过',
        missing_reference_price: '缺少参考价格，暂不可执行',
        paper_skip: '策略选择继续观察',
        not_applicable: '当前不需要处理'
      }
      return map[reason] || reason || '-'
    },
    friendlyError (error) {
      const payload = error && error.response && error.response.data && error.response.data.data
      const status = payload && payload.status
      const map = {
        same_day_apply_rejected: '今天这个模拟账户已经应用过其他策略。',
        stale_epoch: '模拟账户已变化，请刷新后重新确认。',
        invalid_artifact: '策略文件校验失败，请重新生成策略。',
        idempotency_conflict: '重复请求冲突，请刷新后重试。',
        not_found: '未找到当前用户的模拟账户。',
        no_decision: '暂无可应用到模拟账户的策略。',
        next_open_unavailable: '等待目标交易日开盘价，暂不能应用到模拟账户。',
        execution_price_pending: '等待目标交易日开盘价，暂不能应用到模拟账户。',
        execution_price_unavailable: '等待目标交易日开盘价，暂不能应用到模拟账户。'
      }
      return map[status] || (payload && payload.message) || (error && error.message) || '模拟账户操作失败。'
    },
    formatMoney (value) {
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    }
  }
}
</script>

<style lang="less" scoped>
.paper-portfolio-panel { margin-bottom: 16px; }
.paper-toolbar,
.readonly-tags,
.paper-section-head,
.card-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.card-title-line { justify-content: space-between; }
.paper-toolbar { margin-bottom: 12px; }
.paper-alert { margin-bottom: 12px; }
.paper-empty {
  color: #667085;
  padding: 18px 0;
}
.paper-empty.compact { padding: 8px 0; font-size: 12px; }
.paper-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.paper-summary-grid > div {
  min-height: 76px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #fff;
}
.paper-summary-grid span,
.paper-path-line span,
.paper-action-row small,
.paper-result-columns small { color: #667085; font-size: 12px; }
.paper-summary-grid strong,
.paper-summary-grid small,
.paper-action-row strong,
.paper-action-row span,
.paper-action-row small { min-width: 0; overflow-wrap: anywhere; word-break: break-word; }
.paper-summary-grid strong,
.paper-action-row strong { color: #111827; }
.paper-action-row span,
.paper-action-row small { color: #667085; }
.paper-status-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-left: 4px solid #1d4ed8;
  border-radius: 8px;
  background: #fbfdff;
}
.paper-status-line.blocked {
  border-color: #fde68a;
  border-left-color: #f59e0b;
  background: #fffdf7;
}
.paper-status-line > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.paper-status-line span { color: #667085; font-size: 12px; }
.paper-status-line strong { color: #111827; overflow-wrap: anywhere; }
.paper-action-grid,
.paper-result-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.paper-action-grid section,
.paper-result {
  border-top: 1px solid #edf1f7;
  padding-top: 12px;
}
.paper-section-head {
  justify-content: space-between;
  margin-bottom: 8px;
}
.paper-action-list,
.paper-result-columns > div {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}
.paper-action-row {
  display: grid;
  grid-template-columns: minmax(70px, .7fr) minmax(120px, 1fr);
  gap: 4px 8px;
  font-size: 13px;
}
.paper-action-row small { grid-column: 1 / -1; }
.paper-action-row.muted { color: #667085; }
.paper-result { margin-top: 14px; }
.compact-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.paper-tech-collapse {
  margin-top: 12px;
  background: #fff;
}
.paper-tech-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.paper-tech-grid span {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #f8fafc;
  color: #667085;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.paper-tech-grid strong {
  display: block;
  color: #111827;
  font-weight: 600;
}
.paper-confirm-body p { margin-bottom: 8px; }
@media (max-width: 900px) {
  .paper-summary-grid,
  .paper-action-grid,
  .paper-result-columns,
  .paper-tech-grid,
  .compact-grid { grid-template-columns: 1fr; }
  .paper-status-line {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
