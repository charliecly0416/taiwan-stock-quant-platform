<template>
  <a-card class="readonly-strategy-snapshot" :bordered="false" data-testid="readonly-strategy-snapshot-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>策略快照</span>
        <div class="readonly-tags">
          <a-tag color="blue">只读候选</a-tag>
          <a-tag color="cyan">研究排名</a-tag>
          <a-tag :color="statusColor">审计状态</a-tag>
        </div>
      </div>
    </template>
    <div class="readonly-snapshot-toolbar">
      <div class="readonly-snapshot-title-block">
        <strong>当前展示的最新已发布快照</strong>
        <span>{{ snapshotFreshnessText }}</span>
      </div>
      <a-button size="small" :loading="loading" @click="$emit('refresh')">
        <a-icon type="reload" /> 刷新快照
      </a-button>
    </div>
    <a-alert
      v-if="error"
      class="readonly-snapshot-alert"
      type="warning"
      show-icon
      :message="error"
    />
    <a-alert
      v-else-if="payload && freshnessWarning"
      class="readonly-snapshot-alert"
      type="warning"
      show-icon
      :message="freshnessWarning"
    />
    <a-alert
      v-else
      class="readonly-snapshot-alert"
      type="info"
      show-icon
      message="只读研究排名，仅用于人工复盘，不构成投资建议。"
    />
    <div v-if="loading" class="readonly-snapshot-empty">正在读取策略快照...</div>
    <div v-else-if="payload" class="readonly-snapshot-content">
      <div class="readonly-snapshot-grid readonly-primary-grid">
        <div class="readonly-snapshot-metric primary">
          <span>数据日期</span>
          <strong>{{ signalDateText }}</strong>
          <small>排名使用这一天可见的数据</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>快照发布时间</span>
          <strong>{{ snapshotDateText }}</strong>
          <small>{{ snapshotAgeText }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>当前模型</span>
          <strong>{{ modelLabel }}</strong>
          <small>{{ modelSubtitle }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>排序口径</span>
          <strong>{{ rankingLabel }}</strong>
          <small>{{ strategyLabel }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>覆盖状态</span>
          <strong>{{ coverageText }}</strong>
          <small>来自只读快照候选清单</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>审计状态</span>
          <strong>{{ statusText }}</strong>
          <small>{{ auditBriefText }}</small>
        </div>
      </div>

      <div class="readonly-candidate-layout">
        <section class="readonly-candidate-section">
          <div class="readonly-section-head">
            <div>
              <strong>优先观察调入</strong>
              <small>LTR 重排后的前 {{ topCandidates.length }} 名候选</small>
            </div>
            <a-tag color="blue">候选清单</a-tag>
          </div>
          <div v-if="topCandidates.length" class="readonly-candidate-list">
            <div v-for="item in topCandidates" :key="`readonly-top-${item.symbol}`" class="readonly-candidate-row">
              <div class="readonly-candidate-main">
                <strong>{{ displaySymbol(item) }}</strong>
                <span>重排 #{{ rankText(item.score_rank) }}</span>
              </div>
              <div class="readonly-candidate-meta">
                <span>Qlib Top50 内 #{{ rankText(item.candidate_rank) }}</span>
                <span>全量 #{{ rankText(item.full_qlib_rank) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="readonly-snapshot-empty">暂无调入候选。</div>
        </section>
        <section class="readonly-candidate-section">
          <div class="readonly-section-head">
            <div>
              <strong>调出复核</strong>
              <small>当前持仓中已跌出候选边界的项目</small>
            </div>
            <a-tag :color="exitCandidates.length ? 'orange' : 'green'">{{ exitCandidates.length }} 项</a-tag>
          </div>
          <div v-if="exitCandidates.length" class="readonly-candidate-list compact">
            <div v-for="item in exitCandidates" :key="`readonly-exit-${item.symbol}`" class="readonly-candidate-row">
              <div class="readonly-candidate-main">
                <strong>{{ displaySymbol(item) }}</strong>
                <span>{{ item.in_qlib_top50_candidate ? '仍在 Top50' : '已跌出 Top50' }}</span>
              </div>
              <div class="readonly-candidate-meta">
                <span>全量 #{{ rankText(item.full_qlib_rank) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="readonly-snapshot-empty">暂无调出观察。</div>
        </section>
      </div>

      <replay-audit-detail :rows="auditRows" title="查看策略快照审计详情" />
    </div>
    <div v-else class="readonly-snapshot-empty">策略快照暂不可用。</div>
  </a-card>
</template>

<script>
import ReplayAuditDetail from './ReplayAuditDetail.vue'

export default {
  name: 'ReadonlyStrategySnapshotPanel',
  components: { ReplayAuditDetail },
  props: {
    payload: { type: Object, default: null },
    error: { type: String, default: '' },
    loading: { type: Boolean, default: false }
  },
  computed: {
    snapshot () { return (this.payload && this.payload.snapshot) || {} },
    manifest () { return (this.payload && this.payload.manifest) || {} },
    validation () { return (this.payload && this.payload.validation) || {} },
    checksum () { return (this.payload && this.payload.checksum) || {} },
    topCandidates () {
      const items = this.snapshot.top_candidates
      return Array.isArray(items) ? items.slice(0, 10) : []
    },
    exitCandidates () {
      const items = this.snapshot.exit_candidates
      return Array.isArray(items) ? items : []
    },
    gatePass () {
      const payload = this.payload || {}
      return payload.ok === true &&
        payload.readonly_only === true &&
        payload.production_trade_enabled === false &&
        payload.not_order === true &&
        payload.no_order_action === true &&
        payload.not_target_position === true &&
        payload.not_investment_advice === true &&
        this.validation.ok === true &&
        this.checksum.ok === true
    },
    statusText () {
      if (this.error) return '读取异常'
      if (!this.payload) return '待读取'
      return this.gatePass ? '通过' : '需复核'
    },
    statusColor () {
      if (this.gatePass) return 'green'
      if (this.error) return 'red'
      return 'orange'
    },
    checksumText () {
      if (this.checksum.ok === true) return 'pass'
      if (this.checksum.ok === false) return 'fail'
      return '-'
    },
    signalDateText () {
      return this.snapshot.signal_asof || this.snapshot.data_asof || '-'
    },
    snapshotDateText () {
      return this.snapshot.asof || (this.payload && this.payload.asof) || '-'
    },
    todayText () {
      const now = new Date()
      if (Number.isNaN(now.getTime())) return ''
      const year = now.getFullYear()
      const month = String(now.getMonth() + 1).padStart(2, '0')
      const day = String(now.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    },
    snapshotLagDays () {
      return this.daysBetween(this.snapshotDateText, this.todayText)
    },
    signalLagDays () {
      return this.daysBetween(this.signalDateText, this.todayText)
    },
    snapshotFreshnessText () {
      if (!this.payload) return '等待读取只读快照'
      return `信号 ${this.signalDateText}，发布 ${this.snapshotDateText}`
    },
    snapshotAgeText () {
      if (this.snapshotLagDays == null) return '最新指针指向的只读产物'
      if (this.snapshotLagDays <= 0) return '今日发布'
      return `距今天 ${this.snapshotLagDays} 天`
    },
    freshnessWarning () {
      if (!this.payload) return ''
      if (this.signalLagDays != null && this.signalLagDays > 1) {
        return `当前快照使用 ${this.signalDateText} 的信号数据，尚不是今天 ${this.todayText} 的策略快照；需要完成日更数据、模型预测和只读快照发布后才会更新。`
      }
      if (this.snapshotLagDays != null && this.snapshotLagDays > 0) {
        return `当前最新已发布快照为 ${this.snapshotDateText}，不是今天 ${this.todayText} 的快照。`
      }
      return ''
    },
    modelLabel () {
      const id = this.snapshot.model_id || ''
      if (id === 'e4_frozen_qlib_2023_2025_ltr') return 'E4 冻结 Qlib + 正交 LTR'
      return id || '-'
    },
    modelSubtitle () {
      const base = this.snapshot.base_model_id || '-'
      return `底座 ${base}`
    },
    rankingLabel () {
      const source = this.snapshot.ranking_source || ''
      if (source === 'ltr_rerank_within_qlib_top50') return 'Qlib Top50 内 LTR 重排'
      return source || '-'
    },
    strategyLabel () {
      const rule = this.snapshot.strategy_rule || ''
      if (rule === 'top50_exit_one_worst_sell') return '跌出 Top50 时，只复核最弱一项'
      return rule || '-'
    },
    coverageText () {
      return `调入 ${this.topCandidates.length} / 调出 ${this.exitCandidates.length}`
    },
    auditBriefText () {
      const checked = this.checksum.checked_file_count == null ? '-' : this.checksum.checked_file_count
      return `校验 ${this.checksumText}，文件 ${checked}`
    },
    sourceManifest () {
      const sources = (this.payload && this.payload.sources) || {}
      return sources.manifest || this.manifest.snapshot || '-'
    },
    flagText () {
      const payload = this.payload || {}
      return [`readonly=${String(payload.readonly_only === true)}`, `production=${String(payload.production_trade_enabled === true)}`].join(' / ')
    },
    auditRows () {
      return [
        { label: 'source manifest', value: this.sourceManifest },
        { label: 'schema version', value: this.manifest.schema_version },
        { label: 'validation', value: this.validation.status || (this.validation.ok === true ? 'pass' : '-') },
        { label: 'checksum', value: this.checksumText },
        { label: 'checked files', value: this.checksum.checked_file_count == null ? '-' : this.checksum.checked_file_count },
        { label: 'readonly flags', value: this.flagText }
      ]
    }
  },
  methods: {
    displaySymbol (item) {
      if (!item) return '-'
      return item.instrument || item.symbol || '-'
    },
    rankText (value) {
      return value == null ? '-' : value
    },
    daysBetween (start, end) {
      if (!start || !end || start === '-' || end === '-') return null
      const startMs = Date.parse(`${start}T00:00:00`)
      const endMs = Date.parse(`${end}T00:00:00`)
      if (Number.isNaN(startMs) || Number.isNaN(endMs)) return null
      return Math.round((endMs - startMs) / 86400000)
    }
  }
}
</script>
