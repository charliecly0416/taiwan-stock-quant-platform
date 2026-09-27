<template>
  <a-card class="dynamic-readonly-replay" :bordered="false" data-testid="dynamic-readonly-replay-panel">
    <template slot="title">
      <div class="title-line">
        <span>自定义历史回放</span>
        <a-tag color="blue">统一任务入口</a-tag>
        <a-tag color="green">只读</a-tag>
      </div>
    </template>
    <div class="form-grid">
      <label><span>模型</span><a-select v-model="form.modelTrackId" size="small" :loading="loadingOptions" :disabled="running" style="width: 230px"><a-select-option v-for="item in models" :key="item.track_id" :value="item.track_id">{{ item.display_name || item.model_id || item.track_id }}</a-select-option></a-select></label>
      <label><span>策略</span><a-select v-model="form.strategyRule" size="small" :loading="loadingOptions" :disabled="running" style="width: 250px"><a-select-option v-for="item in strategies" :key="item.strategy_rule" :value="item.strategy_rule">{{ item.display_name || item.strategy_rule }}</a-select-option></a-select></label>
      <label><span>开始日期</span><a-date-picker v-model="form.startDate" size="small" :disabled="running" style="width: 145px" /></label>
      <label><span>结束日期</span><a-date-picker v-model="form.endDate" size="small" :disabled="running" style="width: 145px" /></label>
      <a-button type="primary" size="small" :loading="running" :disabled="!ready" @click="submit"><a-icon type="line-chart" />运行动态回放</a-button>
    </div>
    <a-alert class="note" type="info" show-icon message="系统会把模型、策略和日期传给统一 readonly_backtest 任务，按交易日生成隔离的回放结果；不会修改 baseline、latest、模拟账户或订单。" />
    <a-alert v-if="error" class="note" type="warning" show-icon :message="error" />
    <div v-if="task" class="task-status"><a-tag :color="statusColor">{{ task.status }}</a-tag><span>任务 {{ task.run_id }}</span><a-button v-if="running" size="small" @click="poll">刷新状态</a-button></div>
    <div v-if="result" class="result-box">
      <div class="result-heading">
        <strong>回放完成</strong>
        <a-tag :color="artifactStatus === 'CANDIDATE_HOLD' ? 'orange' : 'green'">{{ artifactStatus }}</a-tag>
        <span class="result-run">任务 {{ task && task.run_id }}</span>
      </div>
      <div class="result-metric-grid">
        <div v-for="item in resultMetricItems" :key="item.key" class="result-metric">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </div>
      </div>
      <div class="result-meta">
        <span>模型 {{ replayMetrics.model_name || form.modelTrackId }}</span>
        <span>策略 {{ replayMetrics.strategy_rule || form.strategyRule }}</span>
        <span>实际窗口 {{ replayMetrics.start_date || '-' }} 至 {{ replayMetrics.end_date || '-' }}</span>
        <span>manifest {{ result.replay_manifest || '-' }}</span>
      </div>
      <small>结果写入统一任务隔离目录，可从任务记录追溯模型、策略、时间段和 ReplayResult；CANDIDATE_HOLD 仅表示独立回放结果，不代表产品准入。</small>
    </div>
  </a-card>
</template>

<script>
import moment from 'moment'
import { getTwStockReadonlyReplayOptions, getTwStockReadonlyReplayTask } from '@/api/tw-stock-readonly'
import { createTwStockReadonlyReplay } from '@/api/tw-stock-action'

export default {
  name: 'DynamicReadonlyReplayPanel',
  data () {
    return { loadingOptions: false, running: false, task: null, result: null, error: '', timer: null, models: [], strategies: [], form: { modelTrackId: 'model_a_only', strategyRule: 'top50_exit_one_worst_sell', startDate: moment('2026-01-01'), endDate: moment('2026-05-07') } }
  },
  computed: {
    ready () { return Boolean(this.form.modelTrackId && this.form.strategyRule && this.form.startDate && this.form.endDate) },
    statusColor () { return !this.task || ['QUEUED', 'RUNNING'].includes(this.task.status) ? 'blue' : this.task.status === 'SUCCEEDED' ? 'green' : 'red' },
    replayMetrics () { return (this.result && this.result.replay_metrics) || {} },
    artifactStatus () { return (this.result && this.result.artifact && this.result.artifact.status) || (this.result && this.result.status) || '-' },
    resultMetricItems () {
      return [
        { key: 'total_return', label: '净收益率', value: this.percentText(this.replayMetrics.total_return), note: '已包含手续费/税费' },
        { key: 'max_drawdown', label: '最大回撤', value: this.percentText(this.replayMetrics.max_drawdown), note: '窗口内净值回撤' },
        { key: 'final_equity', label: '期末资产', value: this.moneyText(this.replayMetrics.final_equity), note: `初始现金 ${this.moneyText(this.replayMetrics.initial_cash)}` },
        { key: 'fee_and_tax', label: '手续费/税费', value: this.moneyText(this.replayMetrics.fee_and_tax), note: '模拟成本合计' },
        { key: 'action_count', label: '交易动作', value: this.numberText(this.replayMetrics.action_count), note: `买 ${this.numberText(this.replayMetrics.buy_count)} / 卖 ${this.numberText(this.replayMetrics.sell_count)}` },
        { key: 'trading_days', label: '交易日', value: this.numberText(this.replayMetrics.trading_days), note: `缺失价格 ${this.numberText(this.replayMetrics.missing_price_count)}` }
      ]
    }
  },
  created () { this.loadOptions() },
  beforeDestroy () { this.stopPolling() },
  methods: {
    unwrap (response) { return response && response.data ? response.data : response },
    async loadOptions () {
      this.loadingOptions = true
      try {
        const payload = this.unwrap(await getTwStockReadonlyReplayOptions())
        this.models = payload.models || []; this.strategies = payload.strategies || []
        if (!this.models.some(item => item.track_id === this.form.modelTrackId) && this.models[0]) this.form.modelTrackId = this.models[0].track_id
        if (!this.strategies.some(item => item.strategy_rule === this.form.strategyRule) && this.strategies[0]) this.form.strategyRule = this.strategies[0].strategy_rule
      } catch (error) { this.error = (error && error.message) || '动态回放选项读取失败。' } finally { this.loadingOptions = false }
    },
    dateValue (value) { return value && value.format ? value.format('YYYY-MM-DD') : value },
    async submit () {
      if (!this.ready) return
      this.stopPolling(); this.error = ''; this.result = null; this.task = null
      try {
        const payload = this.unwrap(await createTwStockReadonlyReplay({ modelTrackId: this.form.modelTrackId, strategyRule: this.form.strategyRule, startDate: this.dateValue(this.form.startDate), endDate: this.dateValue(this.form.endDate) }))
        this.task = payload; this.running = ['QUEUED', 'RUNNING'].includes(payload.status)
        if (this.running) this.startPolling(); else this.finish(payload)
      } catch (error) { const response = error && error.response && error.response.data; this.error = (response && response.msg) || error.message || '动态回放任务提交失败。' }
    },
    startPolling () { this.stopPolling(); this.timer = setInterval(this.poll, 1500) },
    stopPolling () { if (this.timer) clearInterval(this.timer); this.timer = null },
    async poll () {
      if (!this.task || !this.task.run_id) return
      try { const payload = this.unwrap(await getTwStockReadonlyReplayTask(this.task.run_id)); this.task = payload; if (!['QUEUED', 'RUNNING'].includes(payload.status)) this.finish(payload) } catch (error) { this.error = (error && error.message) || '动态回放状态读取失败。'; this.stopPolling() }
    },
    finish (payload) { this.running = false; this.stopPolling(); this.result = payload.result && payload.result.execution ? payload.result.execution : payload.result || null; if (payload.status === 'FAILED' || payload.status === 'REJECTED') this.error = payload.error || '动态回放未完成。' },
    metricText (key) { const value = this.replayMetrics[key]; return value === undefined || value === null || value === '' ? '' : String(value) },
    numberText (value) {
      if (value === undefined || value === null || value === '') return '-'
      const number = Number(value)
      return Number.isFinite(number) ? number.toLocaleString('zh-TW') : String(value)
    },
    moneyText (value) {
      if (value === undefined || value === null || value === '') return '-'
      const number = Number(value)
      return Number.isFinite(number) ? number.toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : String(value)
    },
    percentText (value) {
      if (value === undefined || value === null || value === '') return '-'
      const number = Number(value)
      if (!Number.isFinite(number)) return String(value)
      const scaled = Math.abs(number) <= 1 ? number * 100 : number
      return `${scaled.toFixed(2)}%`
    }
  }
}
</script>

<style scoped>
.dynamic-readonly-replay { margin-bottom: 16px; }
.title-line, .form-grid, .task-status { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.form-grid { margin-bottom: 12px; }
.form-grid label { display: flex; align-items: center; gap: 6px; }
.form-grid label > span { color: #344054; font-size: 12px; }
.note { margin-top: 10px; }
.task-status { margin-top: 12px; color: #667085; font-size: 12px; }
.result-box { margin-top: 12px; padding: 12px; border: 1px solid #b7eb8f; background: #f6ffed; }
.result-heading, .result-meta { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.result-run, .result-meta, .result-box > small { color: #667085; font-size: 12px; }
.result-metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; margin-top: 10px; }
.result-metric { min-width: 0; padding: 9px 10px; border: 1px solid #d9f7be; background: #fff; }
.result-metric span, .result-metric strong, .result-metric small { display: block; }
.result-metric span { color: #344054; font-size: 12px; }
.result-metric strong { margin-top: 3px; color: #111827; font-size: 16px; line-height: 1.35; overflow-wrap: anywhere; }
.result-metric small { margin-top: 3px; color: #667085; font-size: 11px; overflow-wrap: anywhere; }
.result-meta { margin-top: 10px; overflow-wrap: anywhere; }
.result-box > small { display: block; margin-top: 10px; }
</style>
