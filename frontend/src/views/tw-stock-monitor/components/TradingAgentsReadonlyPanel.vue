<template>
  <a-card class="tradingagents-readonly-panel" :bordered="false" data-testid="tradingagents-readonly-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>外部研究摘要</span>
        <div class="readonly-tags">
          <a-tag color="blue">只读研究</a-tag>
          <a-tag :color="statusColor">{{ statusText }}</a-tag>
        </div>
      </div>
    </template>

    <div class="ta-toolbar">
      <div class="ta-copy">
        <strong>TradingAgents 摘要仅作人工复核线索。</strong>
        <span>这里展示已净化的研究论点，不改变 QuantDinger 排名、策略和模拟账户状态。</span>
      </div>
      <a-button size="small" :loading="loading" @click="$emit('refresh')">
        <a-icon type="reload" /> 刷新摘要
      </a-button>
    </div>

    <a-alert
      v-if="error"
      class="ta-alert"
      type="info"
      show-icon
      message="外部研究摘要暂不可用。"
    />
    <a-alert
      v-else
      class="ta-alert"
      type="info"
      show-icon
      message="摘要来自 validated sanitized artifact；不代表策略证据、默认选择或收益承诺。"
    />

    <div v-if="loading" class="ta-empty">正在读取外部研究摘要...</div>
    <div v-else-if="available" class="ta-content">
      <div class="ta-meta-grid">
        <span>run_id <strong>{{ runId }}</strong></span>
        <span>signal_asof <strong>{{ payload.signal_asof || '-' }}</strong></span>
        <span>target_date <strong>{{ payload.target_date || '-' }}</strong></span>
        <span>symbols <strong>{{ symbols.length }}</strong></span>
      </div>

      <div class="ta-symbol-list">
        <section v-for="item in symbols" :key="item.symbol" class="ta-symbol-item">
          <div class="ta-symbol-head">
            <strong>{{ item.symbol }}</strong>
            <span>{{ item.instrument || '-' }}</span>
          </div>
          <p>{{ item.research_summary || '暂无摘要。' }}</p>
          <div class="ta-point-grid">
            <div>
              <span>支持线索</span>
              <small v-for="point in item.bull_points || []" :key="`bull-${item.symbol}-${point}`">{{ point }}</small>
            </div>
            <div>
              <span>压力线索</span>
              <small v-for="point in item.bear_points || []" :key="`bear-${item.symbol}-${point}`">{{ point }}</small>
            </div>
            <div>
              <span>复核问题</span>
              <small v-for="point in item.human_review_questions || []" :key="`review-${item.symbol}-${point}`">{{ point }}</small>
            </div>
          </div>
        </section>
      </div>

      <a-collapse class="ta-collapse" :bordered="false">
        <a-collapse-panel key="ta-boundary" header="查看数据限制与校验摘要">
          <div class="ta-limit-list">
            <a-tag v-for="item in limitationTags" :key="item" color="orange">{{ item }}</a-tag>
            <span v-if="!limitationTags.length" class="ta-muted">none</span>
          </div>
          <div class="ta-meta-grid compact">
            <span>validation <strong>{{ validationStatus }}</strong></span>
            <span>claim support <strong>{{ claimSupportStatus }}</strong></span>
            <span>raw files <strong>{{ rawFilesText }}</strong></span>
            <span>source <strong>{{ sourceText }}</strong></span>
          </div>
        </a-collapse-panel>
      </a-collapse>
    </div>
    <div v-else class="ta-empty">外部研究摘要暂不可用。</div>
  </a-card>
</template>

<script>
export default {
  name: 'TradingAgentsReadonlyPanel',
  props: {
    payload: { type: Object, default: null },
    error: { type: String, default: '' },
    loading: { type: Boolean, default: false }
  },
  computed: {
    report () {
      return (this.payload && this.payload.sanitized_report) || {}
    },
    symbols () {
      const rows = this.report && this.report.symbols
      return Array.isArray(rows) ? rows.slice(0, 6) : []
    },
    available () {
      return !!(this.payload && this.payload.ok === true && this.symbols.length)
    },
    statusText () {
      if (this.error) return '暂不可用'
      if (!this.payload) return '待读取'
      return this.available ? '已验证' : '无摘要'
    },
    statusColor () {
      if (this.error) return 'orange'
      if (this.available) return 'green'
      return 'default'
    },
    runId () {
      return (this.payload && this.payload.run_id) || '-'
    },
    validationStatus () {
      const validation = (this.payload && this.payload.validation) || {}
      return validation.ok === true ? 'pass' : 'unavailable'
    },
    claimSupportStatus () {
      const audit = (this.payload && this.payload.claim_support_audit) || {}
      return audit.ok === true ? 'pass' : 'unavailable'
    },
    rawFilesText () {
      return this.payload && this.payload.raw_files_included === false ? 'excluded' : 'unavailable'
    },
    sourceText () {
      const source = (this.payload && this.payload.source) || {}
      return source.project_path || source.project || '-'
    },
    limitationTags () {
      const values = []
      this.symbols.forEach(item => {
        const limitations = Array.isArray(item.data_limitations) ? item.data_limitations : []
        limitations.forEach(text => {
          const clean = String(text || '').trim()
          if (clean && !values.includes(clean)) values.push(clean)
        })
      })
      return values.slice(0, 8)
    }
  }
}
</script>

<style scoped>
.tradingagents-readonly-panel {
  margin-bottom: 16px;
}

.ta-toolbar,
.ta-copy,
.ta-symbol-head,
.ta-limit-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.ta-toolbar {
  justify-content: space-between;
  margin-bottom: 10px;
}

.ta-copy {
  flex-direction: column;
  align-items: flex-start;
  color: #475467;
}

.ta-alert {
  margin-bottom: 12px;
}

.ta-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.ta-meta-grid span {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #fff;
  color: #667085;
  overflow-wrap: anywhere;
}

.ta-meta-grid strong {
  display: block;
  color: #111827;
}

.ta-symbol-list {
  display: grid;
  gap: 10px;
}

.ta-symbol-item {
  min-width: 0;
  border: 1px solid #e8eef5;
  border-radius: 6px;
  background: #ffffff;
  padding: 12px;
}

.ta-symbol-head {
  margin-bottom: 6px;
}

.ta-symbol-head strong {
  color: #111827;
}

.ta-symbol-head span,
.ta-symbol-item p,
.ta-point-grid small,
.ta-empty,
.ta-muted {
  color: #667085;
}

.ta-symbol-item p {
  margin: 0 0 10px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.ta-point-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}

.ta-point-grid div {
  min-width: 0;
  padding: 8px;
  border-radius: 6px;
  background: #f8fafc;
}

.ta-point-grid span,
.ta-point-grid small {
  display: block;
  overflow-wrap: anywhere;
}

.ta-point-grid span {
  margin-bottom: 4px;
  color: #344054;
  font-weight: 600;
}

.ta-collapse {
  margin-top: 10px;
}

.ta-meta-grid.compact {
  margin-top: 10px;
  margin-bottom: 0;
}

.ta-empty {
  padding: 12px;
  border: 1px dashed #d8e1ec;
  border-radius: 6px;
  background: #fbfdff;
}
</style>
