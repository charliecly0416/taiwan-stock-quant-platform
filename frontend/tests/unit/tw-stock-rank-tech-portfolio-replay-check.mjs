import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const api = read('src/api/tw-stock.js')
const page = read('src/views/tw-stock-monitor/index.vue')

for (const required of [
  'getTwStockRankTechCrossLatest',
  'getTwStockObservationReplay',
  'runTwStockPortfolioReplay',
  '/rank-tech-cross/latest',
  '/rank-tech-cross/observation-replay',
  '/rank-tech-cross/portfolio-replay'
]) {
  assert.ok(api.includes(required), `api missing ${required}`)
}

const latestMatch = api.match(/export function getTwStockRankTechCrossLatest[\s\S]*?\n\}/)
assert.ok(latestMatch, 'missing getTwStockRankTechCrossLatest body')
assert.match(latestMatch[0], /method:\s*'get'/)
assert.match(latestMatch[0], /bucket:\s*normalizedBucket/)
assert.match(latestMatch[0], /maxItems/)

const observationMatch = api.match(/export function getTwStockObservationReplay[\s\S]*?\n\}/)
assert.ok(observationMatch, 'missing getTwStockObservationReplay body')
assert.match(observationMatch[0], /method:\s*'get'/)

const portfolioMatch = api.match(/export function runTwStockPortfolioReplay[\s\S]*?\n\}/)
assert.ok(portfolioMatch, 'missing runTwStockPortfolioReplay body')
assert.match(portfolioMatch[0], /method:\s*'post'/)
assert.match(portfolioMatch[0], /persist:\s*false/)
for (const forbidden of ['/sim/', 'quick-trade', 'broker', 'target_position', 'targetWeight', 'target_weight', 'order']) {
  assert.ok(!portfolioMatch[0].includes(forbidden), `portfolio wrapper contains forbidden token ${forbidden}`)
}

const blockMatch = page.match(/<a-card class="rank-tech-replay-card"[\s\S]*?<\/a-card>\n\n\s*<a-card ref="readonlyBacktestPanel"/)
assert.ok(blockMatch, 'missing Step5 rank-tech portfolio replay card')
const block = blockMatch[0]

for (const required of [
  '今日复盘与历史模拟',
  '今天先看什么',
  '为什么',
  '过去表现',
  '只读历史模拟，不是投资建议，不连接券商，不生成订单。',
  '只看模型排名',
  '加入趋势确认',
  '加入技术指标确认',
  '加入追高风险过滤',
  '位置过滤',
  '策略规则回放',
  'portfolioReplayStrategyItems',
  'portfolioStrategyBrief',
  '总收益',
  '最大回撤',
  '动作次数',
  '费用税费估算'
]) {
  assert.ok(block.includes(required), `Step5 block missing ${required}`)
}


for (const required of ['新增观察', '继续观察', '风险复盘', '人工复核', '仅观察', '数据不足', '数据提示', '可模拟观察', '等回调', '追高复核', '跌出 Top30 轮动', '跌出 Top50 轮动', '连续转弱才复盘', '10 支上限', '默认低频策略', '进阶高收益策略', 'rankTechActionLabel', 'rankTechActionColor']) {
  assert.ok(page.includes(required), `page missing decision label ${required}`)
}

for (const forbidden of [
  '立即买入', '立即卖出', '自动买入', '自动卖出', '下单', '提交订单', '目标仓位', '上涨概率', '收益承诺',
  'draftTwStockSimOrder', 'confirmTwStockSimOrder', 'createTwStockSimAccount',
  'scanTwStockMonitor', 'scanAllTwStockMonitors', 'saveTwStockMonitorConfig', 'saveTwStockCrossAnalysisReview',
  'quick-trade', 'broker', 'target_position', 'targetWeight', 'target_weight'
]) {
  assert.ok(!block.toLowerCase().includes(forbidden.toLowerCase()), `Step5 block contains forbidden token ${forbidden}`)
}

for (const required of [
  'loadingRankTechCross',
  'runningPortfolioReplay',
  'rankTechLatestPayload',
  'portfolioReplayPayload',
  'loadRankTechCrossLatest',
  'loadPortfolioReplay',
  'loadRankTechPortfolioPanel',
  'handleRankTechReplayControlChange',
  'handlePortfolioReplayControlChange',
  'rankTechPriorityItems',
  'portfolioReplayComparisonItems',
  'portfolioReplayDateRange',
  'positionRiskLabel',
  'positionRiskColor',
  'portfolioPositionRiskText',
  'qlib_plus_trend_position_risk',
  'initialCash: 1000000',
  'maxHoldings: 10',
  'lotSize: 10',
  'persist: false'
]) {
  assert.ok(page.includes(required), `page missing Step5 state or method ${required}`)
}

const loadLatestMatch = page.match(/async loadRankTechCrossLatest \(\) \{[\s\S]*?\n    \},\n    observationReplayReader/)
assert.ok(loadLatestMatch, 'missing loadRankTechCrossLatest method')
assert.match(loadLatestMatch[0], /getTwStockRankTechCrossLatest/)
assert.doesNotMatch(loadLatestMatch[0], /sim|quick-trade|broker|saveTwStock|scanTwStock|triggerQlib|publish|refresh-provider/i)

const replayMatch = page.match(/async loadPortfolioReplay \(\) \{[\s\S]*?\n    \},\n    async loadRankTechPortfolioPanel/)
assert.ok(replayMatch, 'missing loadPortfolioReplay method')
assert.match(replayMatch[0], /runTwStockPortfolioReplay/)
assert.match(replayMatch[0], /persist:\s*false/)
assert.doesNotMatch(replayMatch[0], /getTwStockSim|draftTwStockSimOrder|confirmTwStockSimOrder|quick-trade|broker\/|\/broker|saveTwStock|scanTwStock|triggerQlib|publish|refresh-provider/i)

assert.match(page, /this\.loadRankTechPortfolioPanel\(\)/)
assert.match(page, /\.rank-tech-grid,\n\s*\.portfolio-replay-grid \{\n\s*grid-template-columns: 1fr;/)

console.log('tw-stock rank-tech portfolio replay checks passed')
