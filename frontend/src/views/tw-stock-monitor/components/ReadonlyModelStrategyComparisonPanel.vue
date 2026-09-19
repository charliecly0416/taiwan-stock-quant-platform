<template>
  <section data-testid="readonly-model-strategy-comparison-panel">
    <a-card class="readonly-comparison" :bordered="false">
      <template slot="title">
        <div class="comparison-title-line">
          <div class="comparison-title-copy">
            <span>模型与策略对比</span>
            <small>在同一策略和回放窗口下查看 Model A 与 Model A+B 的历史研究结果。</small>
          </div>
          <div class="comparison-tags">
            <a-tag color="blue">只读研究</a-tag>
            <a-tag :color="statusColor">{{ statusText }}</a-tag>
          </div>
        </div>
      </template>

      <div class="comparison-toolbar">
        <div class="comparison-boundary">
          <a-icon type="eye" />
          <span>此处只查看和切换历史比较结果。Model A 与 Model A+B 都不能在本页直接应用；不会写入模拟账户，也不会改变 baseline 或生产默认值。</span>
        </div>
        <a-button size="small" :loading="loading" @click="$emit('refresh')">
          <a-icon type="reload" /> 刷新对比
        </a-button>
      </div>

      <a-alert v-if="error" class="comparison-alert" type="warning" show-icon :message="error" />
      <a-alert
        v-else-if="payload && !boundaryPass"
        class="comparison-alert"
        type="warning"
        show-icon
        message="只读边界字段不完整，本结果需要复核；页面仍不提供任何应用动作。"
      />

      <div class="comparison-controls" data-testid="strategy-workbench-selection-controls">
        <label>
          <span>模型</span>
          <a-select
            :value="selectedModelId"
            size="small"
            :disabled="loading || !modelOptions.length"
            @change="handleModelChange"
          >
            <a-select-option v-for="item in modelOptions" :key="modelId(item)" :value="modelId(item)">
              {{ modelLabel(item) }}
            </a-select-option>
          </a-select>
        </label>
        <label>
          <span>策略</span>
          <a-select
            :value="selectedStrategyId"
            size="small"
            :disabled="loading || !strategyOptions.length"
            @change="handleStrategyChange"
          >
            <a-select-option v-for="item in strategyOptions" :key="strategyId(item)" :value="strategyId(item)">
              {{ strategyLabel(item) }}
            </a-select-option>
          </a-select>
        </label>
        <label>
          <span>回放窗口</span>
          <a-select
            :value="selectedWindowId"
            size="small"
            :disabled="loading || !windowOptions.length"
            @change="handleWindowChange"
          >
            <a-select-option v-for="item in windowOptions" :key="windowId(item)" :value="windowId(item)">
              {{ windowLabel(item) }}
            </a-select-option>
          </a-select>
        </label>
      </div>

      <div v-if="loading && !payload" class="comparison-empty">正在读取只读比较结果...</div>
      <div v-else-if="payload" class="comparison-content">
        <div class="comparison-context">
          <span>当前组合</span>
          <strong>{{ selectedCombinationLabel }}</strong>
          <small>{{ comparisonSummary }}</small>
        </div>

        <div class="comparison-results" data-testid="readonly-model-comparison-results">
          <section v-for="item in comparisonItems" :key="item.key" class="comparison-result" :class="`is-${item.role}`">
            <div class="comparison-result-head">
              <div>
                <span>{{ item.roleLabel }}</span>
                <strong>{{ item.label }}</strong>
              </div>
              <a-tag :color="item.gateColor">{{ item.gateText }}</a-tag>
            </div>
            <dl class="comparison-metrics">
              <div>
                <dt>净收益</dt>
                <dd>{{ percentText(item.metrics.netReturn) }}</dd>
              </div>
              <div>
                <dt>最大回撤</dt>
                <dd>{{ percentText(item.metrics.maxDrawdown) }}</dd>
              </div>
              <div>
                <dt>费用 / 换手</dt>
                <dd>{{ numberText(item.metrics.cost) }} / {{ multipleText(item.metrics.turnover) }}</dd>
              </div>
              <div>
                <dt>收益集中度</dt>
                <dd>{{ percentText(item.metrics.concentration) }}</dd>
              </div>
              <div>
                <dt>弱市表现</dt>
                <dd>{{ item.weakMarketText }}</dd>
              </div>
            </dl>
            <p class="comparison-result-note">{{ item.note }}</p>
          </section>
        </div>

        <div class="comparison-diagnostics" data-testid="readonly-model-comparison-diagnostics">
          <div>
            <span>Bootstrap 稳定性下界</span>
            <strong>{{ diagnosticPercent(bootstrapDiagnostic) }}</strong>
            <a-tag :color="diagnosticStatusColor(bootstrapDiagnostic)">{{ diagnosticStatus(bootstrapDiagnostic) }}</a-tag>
          </div>
          <div>
            <span>弱市相对 Model A</span>
            <strong>{{ diagnosticPercent(weakMarketDiagnostic) }}</strong>
            <a-tag :color="diagnosticStatusColor(weakMarketDiagnostic)">{{ diagnosticStatus(weakMarketDiagnostic) }}</a-tag>
          </div>
          <div>
            <span>A+B Top5 收益集中度</span>
            <strong>{{ diagnosticPercent(top5ConcentrationDiagnostic) }}</strong>
            <a-tag :color="diagnosticStatusColor(top5ConcentrationDiagnostic)">{{ diagnosticStatus(top5ConcentrationDiagnostic) }}</a-tag>
          </div>
        </div>

        <div v-if="legacyStrategyCount" class="comparison-legacy-note">
          另有 {{ legacyStrategyCount }} 个旧版研究策略仅保留血缘记录，当前模型组合不可选。
        </div>

        <a-collapse class="comparison-detail" :bordered="false">
          <a-collapse-panel key="comparison-detail" header="查看技术详情">
            <div class="comparison-detail-grid">
              <span>schema <strong>{{ payload.schema_version || '-' }}</strong></span>
              <span>combination_id <strong>{{ selected.combination_id || '-' }}</strong></span>
              <span>readonly_only <strong>{{ String(payload.readonly_only === true) }}</strong></span>
              <span>no_apply <strong>{{ String(payload.no_apply === true) }}</strong></span>
              <span>runtime_effect <strong>{{ runtimeEffect }}</strong></span>
              <span>baseline_gate <strong>{{ comparisonItems[0].gateStatus }}</strong></span>
              <span>challenger_gate <strong>{{ comparisonItems[1].gateStatus }}</strong></span>
              <span>source <strong>{{ sourceText }}</strong></span>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </div>
      <div v-else class="comparison-empty">只读比较结果暂不可用。</div>
    </a-card>
  </section>
</template>

<script>
export default {
  name: 'ReadonlyModelStrategyComparisonPanel',
  props: {
    payload: { type: Object, default: null },
    error: { type: String, default: '' },
    loading: { type: Boolean, default: false }
  },
  computed: {
    catalog () { return (this.payload && this.payload.catalog) || {} },
    models () { return Array.isArray(this.catalog.models) ? this.catalog.models : [] },
    strategies () { return Array.isArray(this.catalog.strategies) ? this.catalog.strategies : [] },
    windows () { return Array.isArray(this.catalog.windows) ? this.catalog.windows : [] },
    combinations () { return Array.isArray(this.catalog.combinations) ? this.catalog.combinations : [] },
    selectableCombinations () { return this.combinations.filter(item => this.isSelectable(item)) },
    selected () { return (this.payload && this.payload.selected) || {} },
    selectedModelId () { return this.selected.model_id || (this.modelOptions[0] && this.modelId(this.modelOptions[0])) || '' },
    selectedStrategyId () { return this.selected.strategy_id || (this.strategyOptions[0] && this.strategyId(this.strategyOptions[0])) || '' },
    selectedWindowId () { return this.selected.window_id || (this.windowOptions[0] && this.windowId(this.windowOptions[0])) || '' },
    modelOptions () {
      const validIds = new Set(this.selectableCombinations.map(item => this.combinationModelId(item)).filter(Boolean))
      return this.models.filter(item => this.isSelectable(item) && (!validIds.size || validIds.has(this.modelId(item))))
    },
    strategyOptions () {
      const validIds = new Set(this.selectableCombinations
        .filter(item => !this.selectedModelId || this.combinationModelId(item) === this.selectedModelId)
        .map(item => this.combinationStrategyId(item))
        .filter(Boolean))
      return this.strategies.filter(item => this.isSelectable(item) && (!validIds.size || validIds.has(this.strategyId(item))))
    },
    windowOptions () {
      const validIds = new Set(this.selectableCombinations
        .filter(item => (!this.selectedModelId || this.combinationModelId(item) === this.selectedModelId) && (!this.selectedStrategyId || this.combinationStrategyId(item) === this.selectedStrategyId))
        .map(item => this.combinationWindowId(item))
        .filter(Boolean))
      return this.windows.filter(item => this.isSelectable(item) && (!validIds.size || validIds.has(this.windowId(item))))
    },
    legacyStrategyCount () {
      return this.strategies.filter(item => item && (item.comparison_selectable === false || item.selectable === false || item.compatibility === 'legacy_lineage_only')).length
    },
    boundaryPass () {
      const safety = (this.payload && this.payload.safety) || {}
      const runtimeEffect = safety.runtime_effect || (this.payload && this.payload.runtime_effect)
      return !!this.payload && this.payload.readonly_only === true && this.payload.no_apply === true && (!runtimeEffect || runtimeEffect === 'none')
    },
    statusText () {
      if (this.error) return '读取异常'
      if (!this.payload) return '待读取'
      return this.boundaryPass ? '只读边界通过' : '需复核'
    },
    statusColor () {
      if (this.error) return 'red'
      return this.boundaryPass ? 'green' : 'orange'
    },
    selectedCombinationLabel () {
      const model = this.models.find(item => this.modelId(item) === this.selectedModelId)
      const strategy = this.strategies.find(item => this.strategyId(item) === this.selectedStrategyId)
      const windowItem = this.windows.find(item => this.windowId(item) === this.selectedWindowId)
      return [this.modelLabel(model), this.strategyLabel(strategy), this.windowLabel(windowItem)].filter(Boolean).join(' · ') || '-'
    },
    comparisonSummary () {
      const comparison = (this.payload && this.payload.comparison) || {}
      return comparison.summary || comparison.message || '同一历史窗口、同一策略口径的只读对照。'
    },
    diagnostics () {
      return (this.payload && this.payload.comparison && this.payload.comparison.diagnostics) || {}
    },
    bootstrapDiagnostic () { return this.diagnostics.bootstrap_95pct_lower_bound || {} },
    weakMarketDiagnostic () { return this.diagnostics.negative_twii20_regime_return_delta || {} },
    top5ConcentrationDiagnostic () {
      return (this.diagnostics.concentration && this.diagnostics.concentration.top5_abs_contribution_share) || {}
    },
    comparisonItems () {
      return [
        this.buildComparisonItem('baseline'),
        this.buildComparisonItem('challenger')
      ]
    },
    runtimeEffect () {
      const safety = (this.payload && this.payload.safety) || {}
      return safety.runtime_effect || (this.payload && this.payload.runtime_effect) || 'none'
    },
    sourceText () {
      const sources = (this.payload && this.payload.sources) || {}
      return sources.catalog || sources.catalog_pointer || sources.manifest || sources.comparison || sources.result || '-'
    }
  },
  methods: {
    modelId (item) { return item && (item.model_id || item.id || item.key) || '' },
    strategyId (item) { return item && (item.strategy_id || item.strategy_rule || item.id || item.key) || '' },
    windowId (item) { return item && (item.window_id || item.window_key || item.id || item.key) || '' },
    isSelectable (item) { return !!item && item.comparison_selectable !== false && item.selectable !== false },
    combinationModelId (item) { return item && (item.model_id || item.model) || '' },
    combinationStrategyId (item) { return item && (item.strategy_id || item.strategy_rule || item.strategy) || '' },
    combinationWindowId (item) { return item && (item.window_id || item.window_key || item.window) || '' },
    modelLabel (item) {
      if (!item) return ''
      const id = this.modelId(item)
      const name = item.display_name || item.label
      const role = String(item.role || item.kind || '').toLowerCase()
      if (role === 'active_baseline' || role === 'baseline') return `${name || 'Model A'}（当前基线）`
      if (role === 'research_challenger' || role === 'challenger' || id.includes('b19r2r')) return `${name || 'Model A+B'}（研究候选，联合门槛未通过）`
      return name || id
    },
    strategyLabel (item) {
      if (!item) return ''
      const id = this.strategyId(item)
      if (item.display_name || item.label) return item.display_name || item.label
      if (id === 'top50_exit_one_worst_sell') return '跌出 Top50 后最多替换一支'
      return id
    },
    windowLabel (item) {
      if (!item) return ''
      return item.display_name || item.display_label || item.label || this.windowId(item)
    },
    bestCombination (modelId, strategyId, windowId) {
      const candidates = this.selectableCombinations.filter(item => !modelId || this.combinationModelId(item) === modelId)
      return candidates.find(item => this.combinationStrategyId(item) === strategyId && this.combinationWindowId(item) === windowId) ||
        candidates.find(item => this.combinationStrategyId(item) === strategyId) || candidates[0] || null
    },
    emitSelection (combination, fallback = {}) {
      this.$emit('select', {
        model_id: combination ? this.combinationModelId(combination) : fallback.model_id,
        strategy_id: combination ? this.combinationStrategyId(combination) : fallback.strategy_id,
        window_id: combination ? this.combinationWindowId(combination) : fallback.window_id
      })
    },
    handleModelChange (modelId) {
      this.emitSelection(this.bestCombination(modelId, this.selectedStrategyId, this.selectedWindowId), { model_id: modelId })
    },
    handleStrategyChange (strategyId) {
      const candidates = this.selectableCombinations.filter(item => this.combinationModelId(item) === this.selectedModelId && this.combinationStrategyId(item) === strategyId)
      const match = candidates.find(item => this.combinationWindowId(item) === this.selectedWindowId) || candidates[0] || null
      this.emitSelection(match, { model_id: this.selectedModelId, strategy_id: strategyId })
    },
    handleWindowChange (windowId) {
      const match = this.selectableCombinations.find(item => this.combinationModelId(item) === this.selectedModelId && this.combinationStrategyId(item) === this.selectedStrategyId && this.combinationWindowId(item) === windowId)
      this.emitSelection(match, { model_id: this.selectedModelId, strategy_id: this.selectedStrategyId, window_id: windowId })
    },
    candidateRecords () {
      const comparison = (this.payload && this.payload.comparison) || {}
      const result = (this.payload && this.payload.result) || {}
      const rows = []
      ;[comparison.items, comparison.results, comparison.models, result.items, result.results, result.models].forEach(items => {
        if (Array.isArray(items)) rows.push(...items)
        else if (items && typeof items === 'object') rows.push(...Object.values(items).filter(value => value && typeof value === 'object'))
      })
      ;['baseline', 'baseline_result', 'model_a', 'challenger', 'challenger_result', 'model_a_plus_b'].forEach(key => {
        if (comparison[key] && typeof comparison[key] === 'object') rows.push(comparison[key])
        if (result[key] && typeof result[key] === 'object') rows.push(result[key])
      })
      if (result && typeof result === 'object') rows.push(result)
      return rows
    },
    modelForRole (role) {
      const acceptedRoles = role === 'baseline' ? ['baseline', 'active_baseline'] : ['challenger', 'research_challenger']
      return this.models.find(item => acceptedRoles.includes(String(item.role || item.kind || '').toLowerCase())) ||
        this.models.find(item => role === 'challenger' ? this.modelId(item).includes('b19r2r') : !this.modelId(item).includes('b19r2r')) || {}
    },
    recordForRole (role, model) {
      const modelId = this.modelId(model)
      return this.candidateRecords().find(item => {
        const itemRole = String(item.role || item.kind || item.variant || '').toLowerCase()
        const itemModelId = item.model_id || item.id || ''
        return itemRole === role || (modelId && itemModelId === modelId) || (role === 'baseline' && ['model_a', 'a_only'].includes(itemRole)) || (role === 'challenger' && ['model_a_plus_b', 'a+b'].includes(itemRole))
      }) || {}
    },
    nestedValue (record, keys) {
      const roots = [record, record.metrics, record.performance, record.diagnostics, record.robustness].filter(Boolean)
      for (const root of roots) {
        for (const key of keys) {
          if (root[key] !== null && root[key] !== undefined && root[key] !== '') return root[key]
        }
      }
      return null
    },
    buildComparisonItem (role) {
      const model = this.modelForRole(role)
      const record = this.recordForRole(role, model)
      const gate = record.gate || record.quality_gate || {}
      const gateStatus = gate.status || gate.verdict || record.gate_status || record.status || (role === 'baseline' ? 'BASELINE' : '待审查')
      const gatePass = ['pass', 'baseline', 'accepted'].includes(String(gateStatus).toLowerCase()) || gate.ok === true
      return {
        key: role,
        role,
        roleLabel: role === 'baseline' ? '当前基线' : '研究候选',
        label: this.modelLabel(model) || (role === 'baseline' ? 'Model A' : 'Model A+B'),
        gateText: role === 'baseline' ? '当前基线' : '联合门槛未通过',
        gateStatus,
        gateColor: gatePass ? 'green' : (role === 'challenger' ? 'orange' : 'blue'),
        note: record.note || record.message || (role === 'baseline' ? '作为当前研究比较基准；此页面不执行应用。' : '仅作历史研究比较；通过准入审查前不改变当前 baseline。'),
        weakMarketText: role === 'baseline' ? '比较基准' : this.diagnosticDeltaText(this.weakMarketDiagnostic),
        metrics: {
          netReturn: this.nestedValue(record, ['fee_tax_adjusted_net_return', 'net_return', 'return']),
          maxDrawdown: this.nestedValue(record, ['max_drawdown', 'drawdown']),
          cost: this.nestedValue(record, ['fee_tax', 'total_fee_tax', 'fee_tax_total', 'total_cost', 'cost']),
          turnover: this.nestedValue(record, ['turnover', 'turnover_ratio']),
          concentration: this.nestedValue(record, ['top5_abs_contribution_share', 'concentration', 'contribution_concentration', 'top_contribution_share', 'abs_contribution_hhi'])
        }
      }
    },
    percentText (value) {
      if (value === null || value === undefined || value === '') return '-'
      const number = Number(value)
      if (!Number.isFinite(number)) return String(value)
      const scaled = Math.abs(number) <= 1 ? number * 100 : number
      return `${scaled.toFixed(2)}%`
    },
    numberText (value) {
      if (value === null || value === undefined || value === '') return '-'
      const number = Number(value)
      return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value)
    },
    multipleText (value) {
      if (value === null || value === undefined || value === '') return '-'
      const number = Number(value)
      return Number.isFinite(number) ? `${number.toFixed(2)}x` : String(value)
    },
    diagnosticPercent (item) {
      return this.percentText(item && item.measured_value)
    },
    diagnosticDeltaText (item) {
      const value = item && item.measured_value
      if (value === null || value === undefined || value === '') return '-'
      const number = Number(value)
      if (!Number.isFinite(number)) return String(value)
      const scaled = Math.abs(number) <= 1 ? number * 100 : number
      return `${scaled > 0 ? '+' : ''}${scaled.toFixed(2)}% vs A`
    },
    diagnosticStatus (item) {
      return (item && item.status) || '-'
    },
    diagnosticStatusColor (item) {
      const status = String(this.diagnosticStatus(item)).toUpperCase()
      if (status === 'PASS') return 'green'
      if (status === 'FAIL') return 'orange'
      return 'default'
    }
  }
}
</script>

<style scoped>
.readonly-comparison {
  margin-bottom: 16px;
}

.readonly-comparison /deep/ .ant-card-head-title {
  overflow: visible;
  white-space: normal;
}

.comparison-title-line,
.comparison-toolbar,
.comparison-tags,
.comparison-result-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comparison-title-line,
.comparison-toolbar,
.comparison-result-head {
  justify-content: space-between;
}

.comparison-title-copy,
.comparison-context {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.comparison-title-copy small,
.comparison-context span,
.comparison-context small,
.comparison-result-head span,
.comparison-result-note {
  color: #667085;
}

.comparison-title-copy small,
.comparison-context small,
.comparison-result-note,
.comparison-detail-grid span {
  overflow-wrap: anywhere;
}

.comparison-toolbar {
  margin-bottom: 12px;
}

.comparison-boundary {
  display: flex;
  max-width: 860px;
  align-items: flex-start;
  gap: 7px;
  color: #344054;
  line-height: 1.6;
}

.comparison-boundary .anticon {
  margin-top: 4px;
  color: #175cd3;
}

.comparison-alert {
  margin-bottom: 12px;
}

.comparison-controls {
  display: grid;
  grid-template-columns: minmax(200px, 1.25fr) minmax(190px, 1fr) minmax(220px, 1.25fr);
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid #eaecf0;
  border-bottom: 1px solid #eaecf0;
}

.comparison-controls label {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;
  color: #475467;
  font-size: 12px;
}

.comparison-controls .ant-select {
  width: 100%;
}

.comparison-context {
  margin: 12px 0;
}

.comparison-context strong {
  color: #101828;
}

.comparison-results {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 2px solid #344054;
  border-bottom: 1px solid #d0d5dd;
}

.comparison-result {
  min-width: 0;
  padding: 14px 16px 12px;
}

.comparison-result + .comparison-result {
  border-left: 1px solid #d0d5dd;
}

.comparison-result.is-baseline {
  background: #f8fafc;
}

.comparison-result.is-challenger {
  background: #f6fbf8;
}

.comparison-result-head > div {
  min-width: 0;
}

.comparison-result-head span,
.comparison-result-head strong {
  display: block;
  overflow-wrap: anywhere;
}

.comparison-result-head strong {
  margin-top: 2px;
  color: #101828;
  font-size: 15px;
}

.comparison-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 12px 0 0;
  border-top: 1px solid #d0d5dd;
}

.comparison-metrics > div {
  min-width: 0;
  padding: 9px 8px 8px 0;
  border-bottom: 1px solid #eaecf0;
}

.comparison-metrics dt {
  color: #667085;
  font-size: 12px;
}

.comparison-metrics dd {
  margin: 2px 0 0;
  color: #101828;
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.comparison-result-note {
  min-height: 42px;
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.6;
}

.comparison-legacy-note {
  margin-top: 10px;
  color: #667085;
  font-size: 12px;
}

.comparison-diagnostics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin-top: 10px;
  background: #d0d5dd;
  border: 1px solid #d0d5dd;
}

.comparison-diagnostics > div {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 3px 8px;
  padding: 10px 12px;
  background: #ffffff;
}

.comparison-diagnostics span {
  grid-column: 1 / -1;
  color: #667085;
  font-size: 12px;
}

.comparison-diagnostics strong {
  color: #101828;
  overflow-wrap: anywhere;
}

.comparison-detail {
  margin-top: 10px;
}

.comparison-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
  color: #475467;
}

.comparison-empty {
  padding: 22px 0;
  color: #667085;
  text-align: center;
}

@media (max-width: 900px) {
  .comparison-controls,
  .comparison-diagnostics {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .comparison-title-line,
  .comparison-toolbar,
  .comparison-result-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .comparison-tags {
    flex-wrap: wrap;
  }

  .comparison-results {
    grid-template-columns: 1fr;
  }

  .comparison-result + .comparison-result {
    border-top: 1px solid #98a2b3;
    border-left: 0;
  }

  .comparison-metrics {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
