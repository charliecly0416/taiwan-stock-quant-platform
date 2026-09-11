import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'

const root = process.cwd()
const frontendRoot = path.basename(root) === 'frontend' ? root : path.join(root, 'frontend')
const read = file => fs.readFileSync(path.join(frontendRoot, file), 'utf8')
const api = read('src/api/tw-stock-readonly.js')
const monitor = read('src/views/tw-stock-monitor/index.vue')
const panel = read('src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue')

assert.ok(api.includes('export function getTwStockPhaseYZProductizationStatus'), 'missing YZ3 API helper')
const helper = extractFunction('getTwStockPhaseYZProductizationStatus')
assert.ok(helper.includes('/phase-yz/productization-status'), 'YZ3 endpoint mismatch')
assert.ok(helper.includes("method: 'get'"), 'YZ3 endpoint must be GET')
for (const method of ["method: 'post'", "method: 'put'", "method: 'patch'", "method: 'delete'"]) {
  assert.ok(!helper.includes(method), `YZ3 helper must not use ${method}`)
}

assert.ok(monitor.includes('data-testid="strategy-workbench-overview-card"'), 'strategy workbench card missing')
assert.ok(monitor.includes('phaseYZExecutionPriceMessage'), 'pending execution-price message missing')
assert.ok(monitor.includes('phaseYZPaperApplyDisabled'), 'disabled YZ apply state missing')
assert.ok(monitor.includes('成交口径：次一交易日开盘价'), 'next_open user text missing')
assert.ok(!monitor.includes('2026-06-18 行情暂不可用'), 'frontend must not hardcode pending target date')
assert.ok(monitor.includes('phaseYZExecutionPriceMessage'), 'pending alert must read API execution_price_message')
assert.ok(monitor.includes('phaseYZTargetNextTradingDay'), 'frontend must expose target_next_trading_day from payload')
assert.ok(monitor.includes('execution_price_unavailable'), 'pending status token missing')
assert.ok(monitor.includes('e4_frozen_qlib_2018_2022'), 'Model A missing from clean fallback')
assert.ok(monitor.includes('Model B/LTR') || monitor.includes('model_b'), 'Model B reference boundary missing')
assert.ok(monitor.includes('top50_exit_one_worst_sell'), 'clean strategy missing')
assert.ok(monitor.includes(':phase-yz-status="phaseYZProductizationPayload"'), 'PaperPortfolioPanel must receive YZ3 state')

assert.ok(!monitor.includes("model_id: 'e4_frozen_qlib_2023_2025_ltr'"), 'readonly replay form must not default to old model')
assert.ok(monitor.includes("model_id: 'e4_frozen_qlib_2018_2022'"), 'readonly replay form must default to clean E4 model')
assert.ok(!monitor.includes('this.loadReadonlyReplayWindowIndex()\n    this.loadReadonlyReplayWindow()'), 'mounted must not call replay detail before index')
assert.ok(!monitor.includes('this.loadReadonlyReplayWindowIndex(), this.loadReadonlyReplayWindow()'), 'refreshAll must not race replay detail with index')
assert.ok(monitor.includes('await this.loadReadonlyReplayWindow()'), 'index loader should trigger detail only after clean preset is selected')
assert.ok(monitor.includes('loadPhaseYZProductizationStatus()'), 'YZ3 status loader missing')

assert.ok(panel.includes('phaseYzStatus'), 'PaperPortfolioPanel missing phaseYzStatus prop')
assert.ok(panel.includes('phaseYZPaperBlocked'), 'PaperPortfolioPanel missing execution price block computed')
assert.ok(panel.includes('paper_apply_allowed === false'), 'PaperPortfolioPanel must block when paper_apply_allowed is false')
assert.ok(panel.includes('phaseYZPaperBlocked'), 'paper blocked state missing')
assert.ok(panel.includes('!this.decisionReady || this.phaseYZPaperBlocked'), 'applyDisabled must include YZ block before apply')
assert.ok(panel.includes('等待开盘价'), 'blocked apply button text missing')

const cardStart = monitor.indexOf('data-testid="strategy-workbench-overview-card"')
const cardEnd = monitor.indexOf('<readonly-strategy-snapshot-panel', cardStart)
const yzCard = monitor.slice(cardStart, cardEnd)
for (const token of ['origin', 'original', 'P3', 'O4', 'fresh qlib adaptive', 'fresh qlib 2025 LTR', 'bridge', 'e4_frozen_qlib_2023_2025_ltr', 'buggy_e8r']) {
  assert.ok(!yzCard.includes(token), `old token leaked into YZ3 card: ${token}`)
}

function extractFunction (name) {
  const marker = `export function ${name} `
  const start = api.indexOf(marker)
  assert.ok(start >= 0, `missing function ${name}`)
  const next = api.indexOf('\nexport function ', start + marker.length)
  return api.slice(start, next >= 0 ? next : api.length)
}

console.log('tw-stock-phase-yz-productization static checks passed')
