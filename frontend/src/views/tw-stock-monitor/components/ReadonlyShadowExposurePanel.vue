<template>
  <a-card class="readonly-shadow-exposure" :bordered="false" data-testid="readonly-shadow-exposure-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>影子观察</span>
        <div class="readonly-tags">
          <a-tag color="blue">只读研究</a-tag>
          <a-tag :color="statusColor">{{ statusText }}</a-tag>
          <a-tag color="purple">不是交易建议</a-tag>
        </div>
      </div>
    </template>

    <div class="shadow-toolbar">
      <div class="shadow-copy">
        <strong>候选策略只做影子观察。</strong>
        <span>不连接券商，不产生真实交易委托，不进入默认策略，也不提供模拟账户应用。</span>
      </div>
      <a-button size="small" :loading="loading" @click="$emit('refresh')">
        <a-icon type="reload" /> 刷新影子观察
      </a-button>
    </div>

    <a-alert
      v-if="error"
      class="shadow-alert"
      type="warning"
      show-icon
      :message="error"
    />
    <a-alert
      v-else
      class="shadow-alert"
      type="info"
      show-icon
      message="展示内容来自 MTRP8 静态 artifact，经 MTRP9 schema 约束；历史诊断差值不是收益承诺、胜率或上涨概率。"
    />

    <div v-if="loading" class="shadow-empty">正在读取影子观察...</div>
    <div v-else-if="payload" class="shadow-content">
      <div class="shadow-grid">
        <div class="shadow-metric">
          <span>观察状态</span>
          <strong>{{ statusText }}</strong>
          <small>{{ gateBrief }}</small>
        </div>
        <div class="shadow-metric">
          <span>策略候选</span>
          <strong>{{ payload.strategy_candidate || '-' }}</strong>
          <small>对照：{{ payload.baseline_strategy || '-' }}</small>
        </div>
        <div class="shadow-metric">
          <span>覆盖日期</span>
          <strong>{{ dateRangeText }}</strong>
          <small>{{ coveredDaysText }}</small>
        </div>
        <div class="shadow-metric">
          <span>开放阻断</span>
          <strong>{{ openBlockers.length }}</strong>
          <small>production_allowed=false</small>
        </div>
      </div>

      <div class="shadow-row-list" v-if="rows.length">
        <div v-for="row in rows" :key="row.signal_date" class="shadow-row">
          <strong>{{ row.signal_date }} -> {{ row.execution_date }}</strong>
          <span>{{ row.display_status || 'readonly_shadow_observation_only' }}</span>
          <small>candidate-baseline diagnostic difference: {{ formatNumber(row.candidate_minus_baseline_equity, 2) }}</small>
        </div>
      </div>
      <div v-else class="shadow-empty">当前响应未包含行明细。</div>

      <a-collapse class="shadow-collapse" :bordered="false">
        <a-collapse-panel key="blockers" header="查看 gates、blockers 与 citations">
          <div class="shadow-detail-grid">
            <span>schema <strong>{{ payload.schema_version || '-' }}</strong></span>
            <span>gate <strong>{{ gateStatus }}</strong></span>
            <span>rows <strong>{{ payload.row_count == null ? '-' : payload.row_count }}</strong></span>
            <span>source <strong>{{ payload.source_manifest || '-' }}</strong></span>
          </div>
          <div class="shadow-list-section">
            <strong>Open blockers</strong>
            <a-tag v-for="item in openBlockers" :key="item.blocker" color="orange">{{ item.blocker }}</a-tag>
            <span v-if="!openBlockers.length" class="shadow-muted">none</span>
          </div>
          <div class="shadow-list-section">
            <strong>Citations</strong>
            <a-tag v-for="item in citations" :key="item.citation_key" color="blue">{{ item.citation_key }}</a-tag>
            <span v-if="!citations.length" class="shadow-muted">none</span>
          </div>
        </a-collapse-panel>
      </a-collapse>
    </div>
    <div v-else class="shadow-empty">影子观察暂不可用。</div>
  </a-card>
</template>

<script>
export default {
  name: 'ReadonlyShadowExposurePanel',
  props: {
    payload: { type: Object, default: null },
    error: { type: String, default: '' },
    loading: { type: Boolean, default: false }
  },
  computed: {
    gate () {
      return (this.payload && this.payload.gate) || {}
    },
    gateStatus () {
      return this.gate.status || (this.gate.ok === true ? 'pass' : '-')
    },
    gatePass () {
      const payload = this.payload || {}
      return payload.ok === true &&
        payload.readonly_only === true &&
        payload.simulation_only === true &&
        payload.not_order === true &&
        payload.not_target_position === true &&
        payload.not_investment_advice === true &&
        payload.production_allowed === false &&
        payload.production_ready === false &&
        payload.default_switch_allowed === false &&
        payload.paper_apply_allowed === false &&
        this.gate.ok === true
    },
    statusText () {
      if (this.error) return '读取异常'
      if (!this.payload) return '待读取'
      return this.gatePass ? '影子观察通过' : '需复核'
    },
    statusColor () {
      if (this.error) return 'red'
      if (this.gatePass) return 'green'
      return 'orange'
    },
    gateBrief () {
      const validator = (this.gate && this.gate.validator) || {}
      return validator.verdict || this.gateStatus
    },
    rows () {
      const rows = this.payload && this.payload.rows
      return Array.isArray(rows) ? rows : []
    },
    citations () {
      const rows = this.payload && this.payload.citations
      return Array.isArray(rows) ? rows : []
    },
    openBlockers () {
      const rows = this.payload && this.payload.open_blockers
      return Array.isArray(rows) ? rows : []
    },
    coveredDates () {
      const dates = this.payload && this.payload.dates && this.payload.dates.covered_dates
      return Array.isArray(dates) ? dates : []
    },
    dateRangeText () {
      if (!this.coveredDates.length) return '-'
      return `${this.coveredDates[0]}..${this.coveredDates[this.coveredDates.length - 1]}`
    },
    coveredDaysText () {
      const count = this.payload && this.payload.dates && this.payload.dates.covered_shadow_signal_days
      return count == null ? 'shadow days -' : `shadow days ${count}`
    }
  },
  methods: {
    formatNumber (value, digits = 2) {
      const n = Number(value)
      if (!Number.isFinite(n)) return value == null || value === '' ? '-' : String(value)
      return n.toFixed(digits)
    }
  }
}
</script>

<style scoped>
.readonly-shadow-exposure {
  margin-bottom: 16px;
}

.shadow-toolbar,
.shadow-copy,
.shadow-list-section {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.shadow-toolbar {
  justify-content: space-between;
  margin-bottom: 10px;
}

.shadow-copy {
  flex-direction: column;
  align-items: flex-start;
  color: #475467;
}

.shadow-alert {
  margin-bottom: 12px;
}

.shadow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.shadow-metric,
.shadow-row {
  min-width: 0;
  border: 1px solid #e8eef5;
  border-radius: 6px;
  background: #ffffff;
  padding: 10px;
}

.shadow-metric span,
.shadow-metric small,
.shadow-row span,
.shadow-row small {
  display: block;
  color: #667085;
  overflow-wrap: anywhere;
}

.shadow-metric strong,
.shadow-row strong {
  display: block;
  color: #111827;
  overflow-wrap: anywhere;
}

.shadow-row-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.shadow-collapse {
  margin-top: 12px;
}

.shadow-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.shadow-detail-grid span {
  min-width: 0;
  overflow-wrap: anywhere;
  color: #475467;
}

.shadow-empty,
.shadow-muted {
  color: #667085;
  font-size: 13px;
}

.shadow-list-section {
  justify-content: flex-start;
  margin-top: 8px;
}
</style>
