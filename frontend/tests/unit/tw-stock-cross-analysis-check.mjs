import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const api = read('src/api/tw-stock.js')
const page = read('src/views/tw-stock-monitor/index.vue')

for (const required of [
  'getTwStockCrossAnalysisLatest',
  'getTwStockCrossAnalysisSymbol',
  'getTwStockCrossAnalysisReviews',
  'saveTwStockCrossAnalysisReview',
  '/cross-analysis/reviews',
  '/cross-analysis/latest',
  '/cross-analysis/symbol/'
]) {
  assert.ok(api.includes(required), `api missing ${required}`)
}

for (const required of [
  '台股交叉分析',
  'Top30',
  'Top50',
  'All',
  'crossAnalysisBucket',
  'crossAnalysisCategory',
  'crossAnalysisColumns',
  'category',
  'human_action',
  'data_basis',
  'date_gap',
  '日期差',
  'Yahoo adjusted 研究信号',
  'raw 行情',
  '不是交易建议',
  '观察名单',
  '人工复盘',
  '数据口径差异',
  'trend_unavailable',
  'data_review_required',
  'crossAnalysisStateNotice',
  'crossAnalysisEmptyText',
  'loadCrossAnalysisDetail',
  '只读详情',
  'crossFreshnessStatusColor',
  'crossAnalysisQlib',
  'run_id',
  'crossRawDateRangeText',
  'crossDateGapRangeText',
  'crossFreshness',
  'crossRawDateRangeText',
  'crossDateGapRangeText',
  'crossBasisNote',
  'fresh',
  'historical',
  'stale',
  'blocked',
  'unknown',
  'adjusted',
  '数据口径差异',
  'pending asof',
  '不触发补数、委托或持仓',
  '保存复盘',
  '历史模拟',
  '人工复盘备注',
  '多策略验证会比较多个内置日线策略',
  '只用于模拟复盘，不是收益承诺，也不是实盘指令。',
  'crossReviewForm',
  'saveCrossAnalysisReview',
  'openCrossAnalysisHistoricalSimulation',
]) {
  assert.ok(page.includes(required), `page missing ${required}`)
}

const latestMatch = api.match(/function getTwStockCrossAnalysisLatest[\s\S]*?\n\}/)
assert.ok(latestMatch, 'missing getTwStockCrossAnalysisLatest body')
assert.match(latestMatch[0], /method:\s*"get"/)
assert.doesNotMatch(latestMatch[0], /ops|dry-run|scheduler|pipeline|automation|publish|refresh-provider|provider_uri|providerPath|backtest|quick-trade|broker|paper|live|position/i)

const symbolMatch = api.match(/function getTwStockCrossAnalysisSymbol[\s\S]*?\n\}/)
assert.ok(symbolMatch, 'missing getTwStockCrossAnalysisSymbol body')
assert.match(symbolMatch[0], /method:\s*"get"/)
assert.doesNotMatch(symbolMatch[0], /ops|dry-run|scheduler|pipeline|automation|publish|refresh-provider|provider_uri|providerPath|backtest|quick-trade|broker|paper|live|position/i)

const reviewGetMatch = api.match(/function getTwStockCrossAnalysisReviews[\s\S]*?\n\}/)
assert.ok(reviewGetMatch, 'missing getTwStockCrossAnalysisReviews body')
assert.match(reviewGetMatch[0], /method:\s*"get"/)
const reviewSaveMatch = api.match(/function saveTwStockCrossAnalysisReview[\s\S]*?\n\}/)
assert.ok(reviewSaveMatch, 'missing saveTwStockCrossAnalysisReview body')
assert.match(reviewSaveMatch[0], /method:\s*"put"/)
assert.doesNotMatch(reviewSaveMatch[0], /order|position|target_weight|targetPosition|broker|quick-trade/i)

const crossTemplateMatch = page.match(/<a-card class="tw-cross-analysis-card"[\s\S]*?<\/a-card>/)
assert.ok(crossTemplateMatch, 'missing cross-analysis card')
const crossTemplate = crossTemplateMatch[0]
const crossTemplateForForbidden = crossTemplate.replace(/不是收益承诺/g, '').replace(/不是未來收益承諾/g, '').replace(/不是未来收益承诺/g, '')
for (const forbidden of [
  '買入', '买入', '賣出', '卖出', '下單', '下单', '提交订单', '提交訂單',
  '目標倉位', '目标仓位', '建議倉位', '建议仓位', '明日上涨概率', '收益承诺', '勝率承諾', '胜率承诺', '自动交易',
  'quick-trade', 'broker', 'paper order', 'live order', 'target_position', 'targetPosition', 'target_weight', 'targetWeight'
]) {
  assert.ok(!crossTemplateForForbidden.toLowerCase().includes(forbidden.toLowerCase()), `cross module contains forbidden text: ${forbidden}`)
}

for (const forbiddenEndpoint of [
  '/quant/ops/option-c/dry-run',
  '/quant/ops/option-c/scheduler',
  '/quant/ops/option-c/eod-pipeline',
  '/quant/ops/option-c/eod-automation',
  '/quant/ops/option-c/normal-publish',
  '/api/indicator/backtest',
  '/api/quick-trade'
]) {
  assert.ok(!latestMatch[0].includes(forbiddenEndpoint), `latest helper references forbidden endpoint ${forbiddenEndpoint}`)
  assert.ok(!symbolMatch[0].includes(forbiddenEndpoint), `symbol helper references forbidden endpoint ${forbiddenEndpoint}`)
}

const loadMatch = page.match(/async loadCrossAnalysis \(\) \{[\s\S]*?\n    \},\n    handleCrossAnalysisBucketChange/)
assert.ok(loadMatch, 'missing loadCrossAnalysis method')
assert.match(loadMatch[0], /getTwStockCrossAnalysisLatest/)
assert.doesNotMatch(loadMatch[0], /triggerQlib|DryRun|scheduler|pipeline|automation|normalPublish|runTwStockReadonlyBacktest|scanTwStockMonitor|saveTwStockMonitorConfig/)

const detailMatch = page.match(/async loadCrossAnalysisDetail \(row\) \{[\s\S]*?\n    \},\n    prepareCrossReviewForm/)
assert.ok(detailMatch, 'missing loadCrossAnalysisDetail method')
assert.match(detailMatch[0], /getTwStockCrossAnalysisSymbol/)
assert.doesNotMatch(detailMatch[0], /triggerQlib|DryRun|scheduler|pipeline|automation|normalPublish|runTwStockReadonlyBacktest|scanTwStockMonitor|saveTwStockMonitorConfig/)

const saveReviewMatch = page.match(/async saveCrossAnalysisReview \(\) \{[\s\S]*?\n    \},\n    restoreCrossBacktestValidation/)
assert.ok(saveReviewMatch, 'missing saveCrossAnalysisReview method')
assert.match(saveReviewMatch[0], /saveTwStockCrossAnalysisReview/)
assert.doesNotMatch(saveReviewMatch[0], /order|position|target_weight|targetPosition|broker|quick-trade/i)

const historicalSimulationMatch = page.match(/async openCrossAnalysisHistoricalSimulation \(\) \{[\s\S]*?\n    \},\n    crossAnalysisCustomRow/)
assert.ok(historicalSimulationMatch, 'missing openCrossAnalysisHistoricalSimulation method')
assert.match(historicalSimulationMatch[0], /strategyId:\s*'ma_cross_builtin'/)
assert.match(historicalSimulationMatch[0], /initialCapital:\s*1000000/)
assert.match(historicalSimulationMatch[0], /runReadonlyBacktest\(\)/)
assert.doesNotMatch(historicalSimulationMatch[0], /runTwStockReadonlyBacktest|saveTwStockCrossAnalysisReview|triggerQlib|DryRun|scheduler|pipeline|automation|normalPublish/)

console.log('tw-stock cross-analysis checks passed')
