<template>
  <section data-testid="readonly-model-strategy-comparison-panel">
    <a-card class="readonly-comparison" :bordered="false">
      <template slot="title">
        <div class="comparison-title-line">
          <div class="comparison-title-copy">
            <span>模型与策略对比</span>
            <small>在同一策略和回放窗口下比较已登记模型轨道的历史研究结果。</small>
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
          <span>此处只查看和切换历史比较结果，所有模型轨道都不能在本页直接应用；不会写入模拟账户，也不会改变 baseline 或生产默认值。{{ virtualAccountPolicyText }}</span>
        </div>
        <a-button size="small" :loading="loading" @click="$emit('refresh')">
          <a-icon type="reload" /> 刷新对比
        </a-button>
      </div>

      <a-alert v-if="error" class="comparison-alert" type="warning" show-icon :message="error" />
      <a-alert
        v-else-if="challengerUnavailable"
        class="comparison-alert"
        type="warning"
        show-icon
        message="部分研究模型本次暂不可用；当前基线的只读结果仍可独立查看。"
      />
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

        <div v-if="hasB19Comparison" class="comparison-diagnostics" data-testid="readonly-model-comparison-diagnostics">
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

        <div class="comparison-conclusion" data-testid="readonly-model-comparison-conclusion">
          <a-icon type="read" />
          <div>
            <strong>怎么理解这次对比</strong>
            <span>{{ plainLanguageConclusion }}</span>
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
              <span v-for="item in comparisonItems" :key="`gate-${item.key}`">{{ item.key }} gate <strong>{{ item.gateStatus }}</strong></span>
              <span v-for="item in comparisonItems" :key="`role-${item.key}`">{{ item.key }} role <strong>{{ item.frameworkRole }}</strong></span>
              <span v-for="item in comparisonItems" :key="`chain-${item.key}`">{{ item.key }} artifacts <strong>{{ item.artifactCount }}/3</strong></span>
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
    virtualAccountPolicy () { return this.catalog.virtual_account_policy || {} },
    virtualAccountPolicyText () {
      const allowedIds = Array.isArray(this.virtualAccountPolicy.allowed_track_ids) ? this.virtualAccountPolicy.allowed_track_ids : []
      const labels = allowedIds.map(id => {
        const model = this.models.find(item => this.modelId(item) === id)
        return (model && (model.display_name || model.label)) || id
      }).filter(Boolean)
      const defaultId = this.virtualAccountPolicy.default_track_id
      const defaultModel = this.models.find(item => this.modelId(item) === defaultId)
      const defaultLabel = (defaultModel && (defaultModel.display_name || defaultModel.label)) || defaultId
      if (!labels.length) return '虚拟账户当前没有获准使用的模型轨道。'
      return `虚拟账户由独立允许列表控制，当前允许列表只有 ${labels.join('、')}，默认使用 ${defaultLabel || labels[0]}。`
    },
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
      const results = (this.payload && this.payload.comparison && this.payload.comparison.results) || []
      return results.map(record => {
        const model = this.models.find(item => this.modelId(item) === record.model_id) || {}
        return this.buildComparisonItem(model, record)
      }).filter(item => item.available)
    },
    baselineItem () {
      return this.comparisonItems.find(item => item.isDefault) || this.comparisonItems[0] || this.emptyComparisonItem()
    },
    selectedComparisonItem () {
      return this.comparisonItems.find(item => item.key === this.selectedModelId) || this.baselineItem
    },
    researchComparisonItem () {
      return this.selectedComparisonItem.isDefault
        ? (this.comparisonItems.find(item => !item.isDefault) || this.emptyComparisonItem())
        : this.selectedComparisonItem
    },
    challengerUnavailable () {
      const status = (this.payload && this.payload.status) || {}
      return !!(status.unavailable_tracks && Object.keys(status.unavailable_tracks).length)
    },
    hasB19Comparison () { return this.comparisonItems.some(item => item.key === 'model_a_plus_b_b19r2r') },
    failedDiagnosticLabels () {
      return [
        ['稳定性', this.bootstrapDiagnostic],
        ['弱市表现', this.weakMarketDiagnostic],
        ['收益集中度', this.top5ConcentrationDiagnostic]
      ].filter(([, item]) => String(this.diagnosticStatus(item)).toUpperCase() === 'FAIL').map(([label]) => label)
    },
    plainLanguageConclusion () {
      const baselineValue = this.baselineItem.metrics.netReturn
      const researchItem = this.researchComparisonItem
      const challengerValue = researchItem.metrics.netReturn
      if (!researchItem.available) return '当前仅有基线模型可供比较；虚拟账户默认和准入状态没有改变。'
      const baselineReturn = Number(baselineValue)
      const challengerReturn = Number(challengerValue)
      const hasReturns = baselineValue !== null && baselineValue !== undefined && baselineValue !== '' && challengerValue !== null && challengerValue !== undefined && challengerValue !== '' && Number.isFinite(baselineReturn) && Number.isFinite(challengerReturn)
      const returnFinding = !hasReturns
        ? `当前历史收益数据不足，暂时不能判断${researchItem.label}是否优于当前基线`
        : challengerReturn > baselineReturn
          ? `${researchItem.label}在这段历史回放中的净收益高于当前基线`
          : challengerReturn < baselineReturn
            ? `${researchItem.label}在这段历史回放中的净收益低于当前基线`
            : `${researchItem.label}与当前基线在这段历史回放中的净收益相同`
      if (researchItem.key === 'model_a_plus_b_b19r2r' && this.failedDiagnosticLabels.length) {
        return `${returnFinding}，但${this.failedDiagnosticLabels.join('、')}未通过，因此继续作为研究候选，不进入虚拟账户允许列表。`
      }
      return `${returnFinding}；现有诊断没有失败项，仍需完成准入审查后才能加入虚拟账户允许列表或调整默认模型。`
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
      const governance = String(item.governance_status || role).toLowerCase()
      if (governance === 'active_baseline' || role === 'baseline') return `${name || id}（当前基线）`
      if (governance === 'research_candidate' || role === 'research_challenger' || role === 'challenger') return `${name || id}（研究候选）`
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
    nestedValue (record, keys) {
      const roots = [record, record.metrics, record.performance, record.diagnostics, record.robustness].filter(Boolean)
      for (const root of roots) {
        for (const key of keys) {
          if (root[key] !== null && root[key] !== undefined && root[key] !== '') return root[key]
        }
      }
      return null
    },
    emptyComparisonItem () {
      return { key: '', available: false, isDefault: false, metrics: {} }
    },
    buildComparisonItem (model, record) {
      const governance = String(record.governance_status || model.governance_status || model.role || '').toLowerCase()
      const isDefault = model.production_default === true || governance === 'active_baseline'
      const role = isDefault ? 'baseline' : 'research'
      const available = !!this.modelId(model) && !!(record.combination_id || record.model_id)
      const gate = record.gate || record.quality_gate || {}
      const gateStatus = gate.status || gate.verdict || record.gate_status || record.status || (role === 'baseline' ? 'BASELINE' : '待审查')
      const gatePass = ['pass', 'baseline', 'accepted'].includes(String(gateStatus).toLowerCase()) || gate.ok === true
      return {
        key: this.modelId(model),
        role,
        roleLabel: isDefault ? '当前基线' : '研究候选',
        label: this.modelLabel(model) || this.modelId(model),
        available,
        isDefault,
        gateText: isDefault
          ? '当前基线'
          : String(gateStatus).includes('NOT_EVALUATED') || String(gateStatus).includes('PENDING')
            ? '尚未重新评估'
            : '准入门槛未通过',
        gateStatus,
        gateColor: gatePass ? 'green' : (isDefault ? 'blue' : 'orange'),
        frameworkRole: record.framework_role || model.framework_role || '-',
        artifactCount: Object.keys(record.artifacts || {}).filter(key => ['model_signal', 'order_intent', 'replay_result'].includes(key)).length,
        note: record.note || record.message || (isDefault ? '作为当前研究比较基准；此页面不执行应用。' : '仅作历史研究比较；通过准入审查前不改变当前 baseline。'),
        weakMarketText: isDefault ? '比较基准' : (this.modelId(model) === 'model_a_plus_b_b19r2r' ? this.diagnosticDeltaText(this.weakMarketDiagnostic) : '尚未评估'),
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

.comparison-conclusion {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 10px;
  padding: 11px 12px;
  border-left: 4px solid #175cd3;
  background: #f8fbff;
  color: #344054;
}

.comparison-conclusion .anticon {
  margin-top: 3px;
  color: #175cd3;
}

.comparison-conclusion div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.comparison-conclusion strong {
  color: #101828;
}

.comparison-conclusion span {
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
