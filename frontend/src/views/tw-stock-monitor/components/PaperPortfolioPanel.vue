<template>
  <a-card class="paper-portfolio-panel" :bordered="false" data-testid="paper-portfolio-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>模拟策略</span>
        <div class="readonly-tags">
          <a-tag color="blue">模拟账户</a-tag>
          <a-tag color="green">纸面成交</a-tag>
          <a-tag :color="stateTagColor">{{ stateLabel }}</a-tag>
        </div>
      </div>
    </template>

    <div class="paper-toolbar">
      <a-button size="small" :loading="loading" @click="loadAll">
        <a-icon type="reload" /> 刷新模拟策略
      </a-button>
      <a-button
        size="small"
        type="primary"
        data-testid="paper-apply-button"
        :disabled="applyDisabled"
        :loading="applying"
        @click="openApplyConfirm"
      >
        <a-icon type="check-circle" /> {{ phaseYZPaperBlocked ? '等待成交价' : '应用到模拟账户' }}
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
      message="此区域只影响模拟账户；不是交易建议，不接入任何券商通道，不提交真实订单。"
    />
    <a-alert v-if="error" class="paper-alert" type="warning" show-icon :message="error" />

    <a-alert
      v-if="phaseYZPaperBlocked"
      class="paper-alert"
      type="info"
      show-icon
      data-testid="paper-apply-blocked-by-execution-price"
      :message="phaseYZPaperBlockMessage"
    />

    <div v-if="loading" class="paper-empty">正在读取模拟策略...</div>
    <div v-else-if="!decisionReady" class="paper-empty" data-testid="paper-no-decision">{{ emptyText }}</div>
    <div v-else class="paper-content">
      <div class="paper-summary-grid">
        <div>
          <span>模拟账户</span>
          <strong>{{ accountId }}</strong>
          <small>epoch {{ accountEpoch }}</small>
        </div>
        <div>
          <span>策略日期</span>
          <strong>{{ decision.asof || '-' }}</strong>
          <small>{{ decision.decision_id || '-' }}</small>
        </div>
        <div>
          <span>模型</span>
          <strong>{{ decision.model_id || '-' }}</strong>
          <small>{{ decision.strategy_rule || '-' }}</small>
        </div>
        <div>
          <span>模拟现金</span>
          <strong>{{ formatMoney(currentCash) }}</strong>
          <small>持仓 {{ positionCount }} 项</small>
        </div>
      </div>

      <div class="paper-path-line">
        <span>artifact</span>
        <code>{{ decision.paper_order_intent_artifact_path || '-' }}</code>
      </div>

      <div class="paper-action-grid">
        <section>
          <div class="paper-section-head"><strong>预计模拟卖出</strong><span>{{ sellActions.length }}</span></div>
          <div v-if="sellActions.length" class="paper-action-list">
            <div v-for="item in sellActions" :key="`sell-${item.symbol}-${item.reason}`" class="paper-action-row">
              <strong>{{ item.instrument || item.symbol }}</strong>
              <span>{{ item.quantity }} 股 @ {{ formatMoney(item.estimated_reference_price) }}</span>
              <small>{{ item.reason || '-' }}</small>
            </div>
          </div>
          <div v-else class="paper-empty compact">暂无模拟卖出。</div>
        </section>
        <section>
          <div class="paper-section-head"><strong>预计模拟买入</strong><span>{{ buyActions.length }}</span></div>
          <div v-if="buyActions.length" class="paper-action-list">
            <div v-for="item in buyActions" :key="`buy-${item.symbol}-${item.reason}`" class="paper-action-row">
              <strong>{{ item.instrument || item.symbol }}</strong>
              <span>{{ item.quantity }} 股 @ {{ formatMoney(item.estimated_reference_price) }}</span>
              <small>{{ item.reason || '-' }}</small>
            </div>
          </div>
          <div v-else class="paper-empty compact">暂无模拟买入。</div>
        </section>
        <section>
          <div class="paper-section-head"><strong>跳过与不可执行</strong><span>{{ skippedPreviewActions.length }}</span></div>
          <div v-if="skippedPreviewActions.length" class="paper-action-list">
            <div v-for="item in skippedPreviewActions" :key="`skip-${item.symbol}-${item.reason}`" class="paper-action-row muted">
              <strong>{{ item.instrument || item.symbol || '-' }}</strong>
              <span>{{ friendlyReason(item.reason || item.applicability) }}</span>
              <small>{{ item.action_type || '-' }}</small>
            </div>
          </div>
          <div v-else class="paper-empty compact">暂无跳过项。</div>
        </section>
      </div>

      <a-alert v-if="alreadyApplied" class="paper-alert" type="success" show-icon message="今天已应用到模拟账户，按钮已置灰。" />
      <a-alert v-if="staleEpoch" class="paper-alert" type="warning" show-icon message="模拟账户已变化，请重新生成或刷新策略。" />

      <div v-if="applyResult" class="paper-result" data-testid="paper-apply-result">
        <div class="paper-section-head"><strong>应用结果</strong><span>{{ applyResult.status || '-' }}</span></div>
        <div class="paper-summary-grid compact-grid">
          <div><span>apply_id</span><strong>{{ applyResult.apply_id || '-' }}</strong></div>
          <div><span>asof</span><strong>{{ applyResult.asof || '-' }}</strong></div>
          <div><span>现金变化</span><strong>{{ formatMoney(applyResult.cash_before) }} -> {{ formatMoney(applyResult.cash_after) }}</strong></div>
          <div><span>纸面成交</span><strong>{{ resultExecutions.length }}</strong></div>
        </div>
        <div class="paper-result-columns">
          <div><strong>纸面成交</strong><span v-for="item in resultExecutions" :key="item.paper_execution_id">{{ item.side }} {{ item.symbol }} {{ item.quantity }}</span><small v-if="!resultExecutions.length">无</small></div>
          <div><strong>已跳过</strong><span v-for="item in resultSkipped" :key="`${item.symbol}-${item.reason}`">{{ item.symbol || '-' }}：{{ friendlyReason(item.reason) }}</span><small v-if="!resultSkipped.length">无</small></div>
          <div><strong>已拒绝</strong><span v-for="item in resultRejected" :key="`${item.symbol}-${item.reason}`">{{ item.symbol || '-' }}：{{ friendlyReason(item.reason) }}</span><small v-if="!resultRejected.length">无</small></div>
        </div>
      </div>

      <div v-if="resetResult" class="paper-result" data-testid="paper-reset-result">
        <div class="paper-section-head"><strong>重置结果</strong><span>new_epoch {{ resetResult.new_epoch }}</span></div>
        <span>旧状态已进入 reset archive，需要重新生成策略后再应用。</span>
      </div>
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
        <p>此操作只会写入模拟账户，不会提交真实订单。</p>
        <p>账户 {{ accountId }} / epoch {{ accountEpoch }} / asof {{ decision.asof || '-' }}</p>
        <p>将模拟卖出 {{ sellActions.length }} 项，模拟买入 {{ buyActions.length }} 项，跳过 {{ skippedPreviewActions.length }} 项。</p>
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
        <p>重置模拟账户会清空当前模拟持仓，旧状态会进入 reset archive。</p>
        <p>当前现金 {{ formatMoney(currentCash) }}，当前持仓 {{ positionCount }} 项，epoch {{ accountEpoch }}。</p>
        <p>重置后 initial_cash {{ formatMoney(initialCash) }}。</p>
      </div>
    </a-modal>
  </a-card>
</template>

<script>
import {
  getTwStockPaperPortfolioLatestDecision,
  getTwStockPaperPortfolioState,
  getTwStockPaperPortfolioApplyRuns,
  applyTwStockPaperPortfolioDecision,
  resetTwStockPaperPortfolio
} from '@/api/tw-stock'

export default {
  name: 'PaperPortfolioPanel',
  props: {
    phaseYzStatus: {
      type: Object,
      default: null
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
      resetConfirmVisible: false
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
    phaseYZPaperBlocked () { return this.phaseYzStatus && this.phaseYzStatus.paper_apply_allowed === false },
    phaseYZPaperBlockMessage () {
      return (this.phaseYzStatus && this.phaseYzStatus.execution_price_message) || '成交口径：次一交易日开盘价。行情暂不可用，等待下一轮数据更新。'
    },
    applyDisabled () { return !this.decisionReady || this.phaseYZPaperBlocked || this.alreadyApplied || this.staleEpoch || this.applying || this.resetting },
    resetDisabled () { return !this.account.account_uid || this.applying || this.resetting },
    resultExecutions () { return (this.applyResult && this.applyResult.paper_executions) || [] },
    resultSkipped () { return (this.applyResult && this.applyResult.skipped_actions) || [] },
    resultRejected () { return (this.applyResult && this.applyResult.rejected_actions) || [] },
    stateLabel () {
      if (this.loading) return 'loading'
      if (this.error) return 'apply_failed'
      if (!this.decisionReady) return 'no_decision'
      if (this.phaseYZPaperBlocked) return 'execution_price_unavailable'
      if (this.alreadyApplied) return 'already_applied'
      if (this.staleEpoch) return 'stale_epoch'
      if (this.applyResult) return 'applied'
      return 'ready_to_apply'
    },
    stateTagColor () {
      if (this.stateLabel === 'ready_to_apply') return 'green'
      if (this.stateLabel === 'applied' || this.stateLabel === 'already_applied') return 'blue'
      if (this.stateLabel === 'loading') return 'cyan'
      return 'orange'
    },
    emptyText () {
      if (this.error) return this.error
      if (this.latestPayload && this.latestPayload.status === 'no_account') return '暂无匹配的模拟账户。'
      return '暂无可应用策略。'
    }
  },
  mounted () {
    this.loadAll()
  },
  methods: {
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
        const latest = this.unwrap(await getTwStockPaperPortfolioLatestDecision())
        this.latestPayload = latest
        if (latest && latest.ok === true && latest.paper_account_id) {
          const [state, runs] = await Promise.all([
            getTwStockPaperPortfolioState({ paper_account_id: latest.paper_account_id }),
            getTwStockPaperPortfolioApplyRuns({ paper_account_id: latest.paper_account_id, limit: 20 })
          ])
          this.statePayload = this.unwrap(state)
          this.applyRunsPayload = this.unwrap(runs)
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
        const result = this.unwrap(await applyTwStockPaperPortfolioDecision(payload))
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
        this.resetResult = this.unwrap(await resetTwStockPaperPortfolio(payload))
        this.applyResult = null
        this.resetConfirmVisible = false
        await this.loadAll()
      } catch (error) {
        this.error = this.friendlyError(error)
      } finally {
        this.resetting = false
      }
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
        stale_epoch: '模拟账户已重置或变更，请重新加载策略。',
        invalid_artifact: '策略文件校验失败，请重新生成策略。',
        idempotency_conflict: '重复请求冲突，请刷新后重试。',
        not_found: '未找到当前用户的模拟账户。',
        no_decision: '暂无可应用策略。'
      }
      return map[status] || (payload && payload.message) || (error && error.message) || '模拟策略操作失败。'
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
.paper-action-row strong { color: #111827; word-break: break-word; }
.paper-path-line {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  min-width: 0;
}
.paper-path-line code {
  word-break: break-all;
  color: #475467;
}
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
.paper-confirm-body p { margin-bottom: 8px; }
@media (max-width: 900px) {
  .paper-summary-grid,
  .paper-action-grid,
  .paper-result-columns,
  .compact-grid { grid-template-columns: 1fr; }
}
</style>
