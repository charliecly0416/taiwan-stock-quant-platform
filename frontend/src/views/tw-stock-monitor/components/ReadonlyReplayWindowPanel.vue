<template>
  <a-card class="readonly-replay-window" :bordered="false" data-testid="readonly-replay-window-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>只读回放窗口</span>
        <div class="readonly-tags">
          <a-tag color="blue">后端校验</a-tag>
          <a-tag color="purple">标准产物</a-tag>
        </div>
      </div>
    </template>
    <div class="readonly-window-toolbar" data-testid="readonly-replay-window-controls">
      <a-select :value="selectedKey" size="small" style="width: 320px" @change="$emit('select-window', $event)">
        <a-select-option v-for="item in options" :key="item.window_key" :value="item.window_key">
          {{ item.display_label || item.window_key }}
        </a-select-option>
      </a-select>
      <a-tag :color="presetColor">{{ presetText }}</a-tag>
      <a-button size="small" :loading="loadingIndex" @click="$emit('refresh-index')">
        <a-icon type="reload" /> 刷新索引
      </a-button>
      <a-button size="small" :loading="loadingWindow" @click="$emit('query')">
        <a-icon type="search" /> 查询只读回放
      </a-button>
    </div>
    <a-alert
      v-if="indexError"
      class="readonly-snapshot-alert"
      type="warning"
      show-icon
      :message="indexError"
    />
    <a-alert
      v-else-if="error"
      class="readonly-snapshot-alert"
      type="warning"
      show-icon
      :message="error"
    />
    <a-alert
      v-else
      class="readonly-snapshot-alert"
      type="info"
      show-icon
      message="窗口来自只读索引；详情仍由后端 ReplayWindowPolicy 校验，未登记窗口会被拒绝，不在前端本地回放。"
    />
    <div v-if="loadingWindow" class="readonly-snapshot-empty">正在读取只读回放窗口...</div>
    <div v-else-if="payload" class="readonly-snapshot-content">
      <div class="readonly-snapshot-grid readonly-primary-grid">
        <div class="readonly-snapshot-metric">
          <span>模型</span>
          <strong>{{ payload.model_id || '-' }}</strong>
          <small>{{ payload.strategy_rule || '-' }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>策略</span>
          <strong>{{ payload.strategy_rule || '-' }}</strong>
          <small>{{ payload.generated_by || '-' }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>合法窗口</span>
          <strong>{{ windowText }}</strong>
          <small>{{ payload.window && payload.window.name }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>净收益</span>
          <strong>{{ percentText(summary.fee_tax_adjusted_net_return) }}</strong>
          <small>final equity {{ valueText(summary.final_equity) }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>最大回撤</span>
          <strong>{{ percentText(summary.max_drawdown) }}</strong>
          <small>交易次数 {{ valueText(summary.action_count) }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>手续费/税费</span>
          <strong>{{ feeText }}</strong>
          <small>turnover {{ valueText(summary.turnover_proxy_by_notional_over_avg_equity) }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>覆盖状态</span>
          <strong>{{ coverageText }}</strong>
          <small>{{ payload.decision_source || '-' }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>审计状态</span>
          <strong>{{ statusText }}</strong>
          <small>checksum {{ checksumText }}</small>
        </div>
      </div>
      <replay-audit-detail :rows="auditRows" title="查看回放窗口审计详情" />
    </div>
    <div v-else class="readonly-snapshot-empty">尚未查询只读回放窗口。</div>
  </a-card>
</template>

<script>
import ReplayAuditDetail from './ReplayAuditDetail.vue'

export default {
  name: 'ReadonlyReplayWindowPanel',
  components: { ReplayAuditDetail },
  props: {
    indexPayload: { type: Object, default: null },
    payload: { type: Object, default: null },
    indexError: { type: String, default: '' },
    error: { type: String, default: '' },
    loadingIndex: { type: Boolean, default: false },
    loadingWindow: { type: Boolean, default: false },
    selectedKey: { type: String, default: '' }
  },
  computed: {
    options () {
      const items = this.indexPayload && this.indexPayload.windows
      return Array.isArray(items) ? items : []
    },
    selectedPreset () {
      return this.options.find(item => item && item.window_key === this.selectedKey) || this.options[0] || null
    },
    presetText () {
      const preset = this.selectedPreset || {}
      if (preset.window_type === 'generated_readonly') return 'D6 已审计非固定窗口'
      if (preset.window_type === 'fixed_standard') return 'D4 固定标准窗口'
      return '索引窗口'
    },
    presetColor () {
      const preset = this.selectedPreset || {}
      if (preset.window_type === 'generated_readonly') return 'purple'
      if (preset.window_type === 'fixed_standard') return 'blue'
      return 'default'
    },
    summary () { return (this.payload && this.payload.summary) || {} },
    windowText () {
      const window = (this.payload && this.payload.window) || {}
      return window.start && window.end ? `${window.start}..${window.end}` : '-'
    },
    checksumText () {
      const checksum = (this.payload && this.payload.checksum) || {}
      if (checksum.ok === true) return 'pass'
      if (checksum.ok === false) return 'fail'
      return '-'
    },
    statusText () {
      if (this.error) return '后端拒绝'
      if (!this.payload) return '待读取'
      return this.payload.ok === true && this.payload.readonly_only === true ? '通过' : '需复核'
    },
    coverageText () {
      if (!this.payload) return '-'
      if (this.payload.coverage_status) return this.payload.coverage_status
      if (this.payload.ok === true) return '可用'
      return '需复核'
    },
    feeText () {
      const candidates = [this.summary.fee_tax_total, this.summary.total_fee_tax, this.summary.fee_and_tax, this.summary.total_cost]
      const found = candidates.find(value => value !== null && value !== undefined && value !== '')
      return this.valueText(found)
    },
    sourceManifest () {
      const sources = (this.payload && this.payload.sources) || {}
      return sources.readonly_replay_manifest || sources.standard_artifact_index_manifest || '-'
    },
    indexManifest () {
      const sources = (this.payload && this.payload.sources) || {}
      return sources.window_index_manifest || (this.indexPayload && this.indexPayload.sources && this.indexPayload.sources.manifest) || '-'
    },
    auditRows () {
      const checksum = (this.payload && this.payload.checksum) || {}
      return [
        { label: 'source manifest', value: this.sourceManifest },
        { label: 'window index', value: this.indexManifest },
        { label: 'schema version', value: this.payload && this.payload.schema_version },
        { label: 'run id', value: this.payload && (this.payload.run_id || this.payload.artifact_run_id) },
        { label: 'checksum', value: this.checksumText },
        { label: 'checked files', value: checksum.checked_file_count == null ? '-' : checksum.checked_file_count },
        { label: 'readonly flags', value: this.payload ? `readonly=${String(this.payload.readonly_only === true)}` : '-' }
      ]
    }
  },
  methods: {
    valueText (value) {
      return value === null || value === undefined || value === '' ? '-' : value
    },
    percentText (value) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return String(value)
      const scaled = Math.abs(n) <= 1 ? n * 100 : n
      return `${scaled.toFixed(2)}%`
    }
  }
}
</script>
