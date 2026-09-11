<template>
  <a-card class="readonly-replay-window" :bordered="false" data-testid="readonly-replay-window-panel">
    <template slot="title">
      <div class="card-title-line">
        <span>历史模拟</span>
        <div class="readonly-tags">
          <a-tag color="blue">只读研究</a-tag>
          <a-tag :color="presetColor">{{ presetText }}</a-tag>
        </div>
      </div>
    </template>
    <div class="readonly-window-toolbar" data-testid="readonly-replay-window-controls">
      <a-select :value="selectedKey" size="small" style="width: 320px; max-width: 100%" @change="$emit('select-window', $event)">
        <a-select-option v-for="item in options" :key="item.window_key" :value="item.window_key">
          {{ item.display_label || item.window_key }}
        </a-select-option>
      </a-select>
      <span class="readonly-window-note">只用于研究复盘，不代表未来收益。</span>
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
      message="窗口来自只读索引；详情仍由后端测试窗口规则校验，未登记窗口会被拒绝，不在前端本地回放。"
    />
    <div v-if="loadingWindow" class="readonly-snapshot-empty">正在读取历史模拟...</div>
    <div v-else-if="payload" class="readonly-snapshot-content">
      <div class="readonly-replay-track" aria-label="历史模拟阅读顺序">
        <span>合法窗口</span>
        <span>手续费/税费</span>
        <span>结果指标</span>
        <span>覆盖状态</span>
        <span>审计状态</span>
      </div>
      <div class="readonly-snapshot-grid readonly-primary-grid">
        <div class="readonly-snapshot-metric primary">
          <span>合法窗口</span>
          <strong>{{ windowText }}</strong>
          <small>{{ payload.window && payload.window.name || presetText }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>净收益</span>
          <strong>{{ percentText(summary.fee_tax_adjusted_net_return) }}</strong>
          <small>已扣除可用费用口径</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>最大回撤</span>
          <strong>{{ percentText(summary.max_drawdown) }}</strong>
          <small>窗口内模拟回撤</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>交易次数</span>
          <strong>{{ valueText(summary.action_count) }}</strong>
          <small>只读模拟动作计数</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>手续费/税费</span>
          <strong>{{ feeText }}</strong>
          <small>模拟成本合计</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>覆盖状态</span>
          <strong>{{ coverageText }}</strong>
          <small>{{ statusText }}</small>
        </div>
        <div class="readonly-snapshot-metric">
          <span>审计状态</span>
          <strong>{{ auditStatusText }}</strong>
          <small>{{ auditStatusDetail }}</small>
        </div>
      </div>
      <replay-audit-detail :rows="auditRows" title="查看技术详情" />
    </div>
    <div v-else class="readonly-snapshot-empty">尚未查询历史模拟。</div>
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
    selectedKey: { type: String, default: '' },
    activeModelId: { type: String, default: 'e4_frozen_qlib_2018_2022' }
  },
  computed: {
    options () {
      const items = this.indexPayload && this.indexPayload.windows
      if (!Array.isArray(items)) return []
      const activeModel = this.activeModelId || 'e4_frozen_qlib_2018_2022'
      return items.filter(item => !item || !item.model_id || item.model_id === activeModel)
    },
    selectedPreset () {
      return this.options.find(item => item && item.window_key === this.selectedKey) || this.options[0] || null
    },
    presetText () {
      const preset = this.selectedPreset || {}
      if (preset.window_type === 'generated_readonly') return '已审计窗口'
      if (preset.window_type === 'fixed_standard') return '标准测试窗口'
      return '测试窗口'
    },
    presetColor () {
      const preset = this.selectedPreset || {}
      if (preset.window_type === 'generated_readonly') return 'green'
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
    auditStatusText () {
      if (!this.payload) return '-'
      if (this.payload.ok === true && this.payload.readonly_only === true && this.checksumText === 'pass') return '通过'
      if (this.payload.ok === false || this.checksumText === 'fail') return '需复核'
      return this.statusText
    },
    auditStatusDetail () {
      const schema = this.payload && this.payload.schema_version
      return schema ? `schema ${schema}` : '只读校验'
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
        { label: '模型', value: this.payload && this.payload.model_id },
        { label: '策略', value: this.payload && this.payload.strategy_rule },
        { label: 'generated by', value: this.payload && this.payload.generated_by },
        { label: 'decision source', value: this.payload && this.payload.decision_source },
        { label: '期末模拟资产', value: this.valueText(this.summary.final_equity) },
        { label: '换手强度', value: this.valueText(this.summary.turnover_proxy_by_notional_over_avg_equity) },
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
