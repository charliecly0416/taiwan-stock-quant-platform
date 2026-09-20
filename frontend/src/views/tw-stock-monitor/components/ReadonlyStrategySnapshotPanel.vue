<template>
  <a-card class="readonly-strategy-snapshot" :bordered="false" data-testid="readonly-strategy-snapshot-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>候选名单</span>
        <div class="readonly-tags">
          <a-tag color="blue">只读研究</a-tag>
          <a-tag :color="statusColor">{{ statusText }}</a-tag>
        </div>
      </div>
    </template>
    <div class="readonly-snapshot-toolbar">
      <div class="readonly-snapshot-title-block">
        <strong>根据当前模型排序生成，仅供研究复盘。</strong>
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
      <div class="readonly-candidate-layout">
        <div class="readonly-snapshot-grid readonly-primary-grid">
          <div class="readonly-snapshot-metric">
            <span>审计状态</span>
            <strong>{{ statusText }}</strong>
            <small>{{ auditBriefText }}</small>
          </div>
          <div class="readonly-snapshot-metric">
            <span>覆盖状态</span>
            <strong>{{ coverageText }}</strong>
            <small>{{ snapshotAgeText }}</small>
          </div>
        </div>
        <section class="readonly-candidate-section">
          <div class="readonly-section-head">
            <div>
              <strong>候选调入</strong>
              <small>{{ rankingLabel }}前 {{ topCandidates.length }} 名候选</small>
            </div>
            <a-tag color="blue">候选</a-tag>
          </div>
          <div v-if="topCandidates.length" class="readonly-candidate-list">
            <div v-for="item in topCandidates" :key="`readonly-top-${item.symbol}`" class="readonly-candidate-row">
              <span class="readonly-candidate-rank">#{{ candidateRank(item) }}</span>
              <div class="readonly-candidate-main">
                <strong>
                  <span class="readonly-candidate-symbol">{{ displaySymbol(item) }}</span>
                  <span v-if="displayName(item)" class="readonly-candidate-name">{{ displayName(item) }}</span>
                </strong>
                <span>{{ candidateMetaText(item) }}</span>
              </div>
              <a-tag class="readonly-candidate-status" color="blue">待复盘</a-tag>
            </div>
          </div>
          <div v-else class="readonly-snapshot-empty">暂无候选调入。</div>
        </section>
        <section class="readonly-candidate-section">
          <div class="readonly-section-head">
            <div>
              <strong>调出复核</strong>
              <small>当前组合中需要人工复核的观察项</small>
            </div>
            <a-tag :color="exitCandidates.length ? 'orange' : 'green'">{{ exitCandidates.length }} 项</a-tag>
          </div>
          <div v-if="exitCandidates.length" class="readonly-candidate-list compact">
            <div v-for="item in exitCandidates" :key="`readonly-exit-${item.symbol}`" class="readonly-candidate-row">
              <span class="readonly-candidate-rank">复核</span>
              <div class="readonly-candidate-main">
                <strong>
                  <span class="readonly-candidate-symbol">{{ displaySymbol(item) }}</span>
                  <span v-if="displayName(item)" class="readonly-candidate-name">{{ displayName(item) }}</span>
                </strong>
                <span>{{ exitMetaText(item) }}</span>
              </div>
              <a-tag class="readonly-candidate-status" color="orange">观察</a-tag>
            </div>
          </div>
          <div v-else class="readonly-snapshot-empty">暂无调出复核。</div>
        </section>
      </div>

      <replay-audit-detail :rows="auditRows" title="查看技术详情" />
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
    isReranked () {
      const source = String(this.snapshot.ranking_source || '').toLowerCase()
      const modelId = String(this.snapshot.model_id || '').toLowerCase()
      return source.includes('ltr') || modelId.includes('ltr')
    },
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
      if (this.isReranked) return 'Model A+B 重排后的'
      if (source === 'qlib_rank_controlled_signal') return 'Model A 排序的'
      return source ? `${source} 的` : '当前模型排序的'
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
        { label: 'signal date', value: this.signalDateText },
        { label: 'snapshot date', value: this.snapshotDateText },
        { label: 'model', value: this.modelLabel },
        { label: 'base model', value: this.snapshot.base_model_id },
        { label: 'ranking', value: this.rankingLabel },
        { label: 'strategy', value: this.strategyLabel },
        { label: 'coverage', value: this.coverageText },
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
    displayName (item) {
      if (!item) return ''
      return item.name || item.stock_name || item.symbol_name || item.company_name || ''
    },
    candidateRank (item) {
      if (!item) return '-'
      return this.rankText(item.score_rank || item.ltr_rank || item.candidate_rank)
    },
    candidateMetaText (item) {
      if (!item) return '-'
      const scoreRank = item.score_rank || item.ltr_rank || item.candidate_rank
      const parts = this.isReranked
        ? [
            scoreRank ? `A+B #${this.rankText(scoreRank)}` : '',
            item.candidate_rank ? `Model A Top50 #${this.rankText(item.candidate_rank)}` : '',
            item.full_qlib_rank ? `全市场 #${this.rankText(item.full_qlib_rank)}` : ''
          ]
        : [
            scoreRank ? `Model A #${this.rankText(scoreRank)}` : '',
            item.full_qlib_rank ? `全市场 #${this.rankText(item.full_qlib_rank)}` : ''
          ]
      return parts.length ? parts.join(' · ') : '-'
    },
    exitMetaText (item) {
      if (!item) return '-'
      const boundary = item.in_qlib_top50_candidate ? '仍在 Qlib Top50，需复核' : '跌出 Qlib Top50'
      const fullRank = item.full_qlib_rank ? `当前全市场 #${this.rankText(item.full_qlib_rank)}` : ''
      return [boundary, fullRank].filter(Boolean).join(' · ')
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

<style scoped>
.readonly-strategy-snapshot {
  margin-top: 16px;
}

.readonly-strategy-snapshot /deep/ .ant-card-head-title {
  overflow: visible;
  white-space: normal;
}

.card-title-line,
.readonly-tags,
.readonly-snapshot-toolbar,
.readonly-section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title-line,
.readonly-snapshot-toolbar,
.readonly-section-head {
  justify-content: space-between;
}

.readonly-snapshot-toolbar {
  margin-bottom: 10px;
  color: #475467;
  font-size: 12px;
}

.readonly-snapshot-title-block,
.readonly-section-head > div,
.readonly-candidate-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.readonly-snapshot-title-block strong,
.readonly-section-head strong,
.readonly-candidate-main strong {
  color: #111827;
}

.readonly-snapshot-title-block span,
.readonly-section-head small,
.readonly-candidate-main > span,
.readonly-snapshot-metric small,
.readonly-snapshot-empty {
  color: #667085;
  font-size: 12px;
}

.readonly-snapshot-alert {
  margin-bottom: 12px;
}

.readonly-snapshot-content,
.readonly-candidate-section,
.readonly-candidate-list {
  display: flex;
  flex-direction: column;
}

.readonly-snapshot-content,
.readonly-candidate-layout {
  gap: 12px;
}

.readonly-candidate-section,
.readonly-candidate-list {
  gap: 8px;
}

.readonly-candidate-layout,
.readonly-snapshot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.readonly-snapshot-grid {
  gap: 10px;
}

.readonly-snapshot-metric,
.readonly-candidate-section {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fbfdff;
  overflow-wrap: anywhere;
}

.readonly-snapshot-metric span,
.readonly-snapshot-metric strong,
.readonly-snapshot-metric small {
  display: block;
}

.readonly-snapshot-metric strong {
  margin-top: 4px;
  color: #111827;
  font-size: 16px;
  line-height: 1.35;
}

.readonly-snapshot-metric span {
  color: #111827;
  font-weight: 600;
}

.readonly-candidate-row {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
  padding: 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #fff;
}

.readonly-candidate-rank,
.readonly-candidate-symbol {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.readonly-candidate-rank {
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.6;
}

.readonly-candidate-main strong {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  font-size: 14px;
}

.readonly-candidate-symbol {
  font-size: 15px;
}

.readonly-candidate-name {
  color: #344054;
  font-size: 13px;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.readonly-candidate-status {
  margin-right: 0;
}

.readonly-snapshot-empty {
  padding: 10px 0;
}

@media (max-width: 640px) {
  .readonly-candidate-layout,
  .readonly-snapshot-grid {
    grid-template-columns: 1fr;
  }

  .readonly-candidate-row {
    grid-template-columns: 44px minmax(0, 1fr);
  }

  .readonly-candidate-status {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
