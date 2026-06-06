import assert from 'node:assert/strict'
import { chromium } from '/tmp/travel-agent-e2e/node_modules/playwright/index.mjs'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.message ? data.message : 'success', data }
}

function rankTechItems () {
  return [
    {
      symbol: '2330', name: '台积电', rank: 1, rankTier: 'top10',
      qlib: { rank: 1, score: 0.31, asof: '2026-06-04' },
      trend: { label: 'uptrend', score: 76, latest_date: '2026-06-04', ok: true, warnings: [] },
      technical: { status: 'technical_strong', summary: { supportive_count: 3, neutral_count: 1, caution_count: 0, data_insufficient_count: 0 }, warnings: [], reason: '趋势和轻量指标状态一致偏支持。' },
      decision: { code: 'new_watch', label: '新增观察', reason: 'Top10 且技术状态偏强。' }
    },
    {
      symbol: '2357', name: '华硕', rank: 8, rankTier: 'top10',
      qlib: { rank: 8, score: 0.24, asof: '2026-06-04' },
      trend: { label: 'sideways', score: 55, latest_date: '2026-06-04', ok: true, warnings: [] },
      technical: { status: 'technical_neutral', summary: { supportive_count: 1, neutral_count: 2, caution_count: 1, data_insufficient_count: 0 }, warnings: [], reason: '趋势和轻量指标未形成一致强确认。' },
      decision: { code: 'manual_review', label: '人工复核', reason: '模型靠前但趋势未确认。' }
    },
    {
      symbol: '2603', name: '长荣', rank: 22, rankTier: 'top30',
      qlib: { rank: 22, score: 0.12, asof: '2026-06-04' },
      trend: { label: 'pullback', score: 38, latest_date: '2026-06-04', ok: true, warnings: ['short_history_below_60_bars'] },
      technical: { status: 'technical_weak', summary: { supportive_count: 0, neutral_count: 1, caution_count: 2, data_insufficient_count: 1 }, warnings: ['short_history_below_60_bars'], reason: '趋势或指标出现谨慎状态，降低技术确认强度。' },
      decision: { code: 'risk_review', label: '风险复盘', reason: '技术状态偏弱。' }
    }
  ]
}

function rankTechPayload (bucket = 'top30') {
  return {
    ok: true,
    status: 'accepted',
    simulation_only: true,
    research_signal_not_order: true,
    bucket,
    limit: 120,
    maxItems: bucket === 'top50' ? 50 : 30,
    qlib: { asof: '2026-06-04', run_id: 'rank_tech_fixture' },
    items: rankTechItems(),
    summary: { new_watch: 1, continue_watch: 0, risk_review: 1, manual_review: 1, observe_only: 0, data_insufficient: 0 },
    warnings: [],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function portfolioPayload () {
  const base = {
    equityCurve: [{ date: '2026-01-02', equity: 1000000 }, { date: '2026-06-04', equity: 1060000 }],
    historicalActions: [
      { date: '2026-02-01', symbol: '2330', action: 'historical_add', simulation_only: true },
      { date: '2026-03-01', symbol: '2603', action: 'historical_risk_reduce', simulation_only: true }
    ],
    dataQuality: { warnings: [] }
  }
  return {
    ok: true,
    status: 'accepted',
    simulation_only: true,
    research_signal_not_order: true,
    persist: false,
    writes_business_db: false,
    orders_enabled: false,
    connects_to_broker: false,
    comparison: {
      qlib_only: { ...base, metrics: { totalReturn: 0.045, maxDrawdown: -0.021, actionCount: 8, feeAndTax: 1234.5 } },
      qlib_plus_trend: { ...base, metrics: { totalReturn: 0.052, maxDrawdown: -0.018, actionCount: 6, feeAndTax: 980.25 } },
      qlib_plus_trend_indicators: { ...base, metrics: { totalReturn: 0.061, maxDrawdown: -0.015, actionCount: 5, feeAndTax: 876.4 }, dataQuality: { warnings: ['missing_close:fixture'] } }
    },
    dataQuality: { point_in_time: true, warnings: ['missing_close:fixture'] },
    trading: { orders_enabled: false, connects_to_broker: false, writes_orders: false, writes_positions: false, research_signal_not_order: true }
  }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const requests = []
const forbiddenRequests = []
let latestRequestCount = 0
let observationRequestCount = 0
let portfolioReplayRequestCount = 0
let portfolioPersistFalseCount = 0
let simRequestCount = 0
let simWriteRequestCount = 0
let quickTradeRequestCount = 0
let brokerRequestCount = 0
let realOrderRequestCount = 0
let monitorConfigWriteCount = 0
let monitorScanPostCount = 0
let monitorAlertsWriteCount = 0
let qlibOpsPostCount = 0
let acceptedLatestSwitchCount = 0
let providerPublishRefreshCount = 0
let targetPositionRequestCount = 0
let targetWeightRequestCount = 0
const pageErrors = []
const failedResponses = []
const rankTechResponses = []

page.on('pageerror', error => pageErrors.push(String(error && (error.stack || error.message || error))))
page.on('response', response => {
  const url = response.url()
  if (response.status() >= 400) failedResponses.push({ status: response.status(), url })
  if (url.includes('/api/tw-stock/rank-tech-cross/')) rankTechResponses.push({ status: response.status(), url })
})
page.on('request', request => {
  const method = request.method().toUpperCase()
  const rawUrl = request.url()
  const url = rawUrl.toLowerCase()
  requests.push({ method, url: rawUrl })
  if (url.includes('/api/tw-stock/rank-tech-cross/latest')) latestRequestCount += 1
  if (url.includes('/api/tw-stock/rank-tech-cross/observation-replay')) observationRequestCount += 1
  if (url.includes('/api/tw-stock/rank-tech-cross/portfolio-replay')) portfolioReplayRequestCount += 1
  if (url.includes('/api/tw-stock/sim/')) simRequestCount += 1
  if (url.includes('/api/tw-stock/sim/') && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) simWriteRequestCount += 1
  if (url.includes('/api/quick-trade/')) quickTradeRequestCount += 1
  if (url.includes('/api/broker/') || url.includes('/broker/')) brokerRequestCount += 1
  if (url.includes('/api/order') || url.includes('/api/orders') || url.includes('/orders/submit')) realOrderRequestCount += 1
  if (url.includes('/api/tw-stock/monitor/config') && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) monitorConfigWriteCount += 1
  if (url.includes('/api/tw-stock/monitor/scan') && method === 'POST') monitorScanPostCount += 1
  if (url.includes('/api/tw-stock/monitor/alerts') && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) monitorAlertsWriteCount += 1
  if (url.includes('/api/tw-stock/quant/ops/') && method === 'POST') qlibOpsPostCount += 1
  if (url.includes('accepted-latest') || url.includes('accepted_latest')) acceptedLatestSwitchCount += 1
  if (/(publish|refresh-provider|provider-refresh|provider\/refresh)/.test(url)) providerPublishRefreshCount += 1
  if (url.includes('target_position') || url.includes('target-position')) targetPositionRequestCount += 1
  if (url.includes('targetweight') || url.includes('target_weight') || url.includes('target-weight')) targetWeightRequestCount += 1
  if (simWriteRequestCount || quickTradeRequestCount || brokerRequestCount || realOrderRequestCount || monitorConfigWriteCount || monitorScanPostCount || monitorAlertsWriteCount || qlibOpsPostCount || acceptedLatestSwitchCount || providerPublishRefreshCount || targetPositionRequestCount || targetWeightRequestCount) {
    forbiddenRequests.push({ method, url: rawUrl })
  }
})

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'rank-tech-e2e', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger', app_version: 'e2e' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))

await page.route('**/api/tw-stock/rank-tech-cross/latest**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  const url = new URL(route.request().url())
  const bucket = url.searchParams.get('bucket') === 'top50' ? 'top50' : 'top30'
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(rankTechPayload(bucket))) })
})

await page.route('**/api/tw-stock/rank-tech-cross/observation-replay**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', daily: [], comparison: {}, simulation_only: true })) })
})

await page.route('**/api/tw-stock/rank-tech-cross/portfolio-replay', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  const body = JSON.parse(route.request().postData() || '{}')
  assert.equal(body.persist, false, 'portfolio replay must force persist=false')
  assert.equal(body.initialCash, 1000000)
  assert.equal(body.maxHoldings, 10)
  assert.equal(body.lotSize, 10)
  portfolioPersistFalseCount += 1
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(portfolioPayload())) })
})

await page.route('**/api/tw-stock/monitor/config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ name: 'default', symbols: ['2330'], limit_bars: 120, refresh_interval_sec: 0, enabled: false })) }))
await page.route('**/api/tw-stock/monitor/history**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/alerts**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/scan-logs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ health: { status: 'ok' } })) }))
await page.route('**/api/tw-stock/trends**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/quant/signals/health**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', latest: { asof: '2026-06-04', exists: true, accepted_validated: true }, freshness: {}, runs: {}, dataAvailability: {} })) }))
await page.route('**/api/tw-stock/quant/signals/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', asof: '2026-06-04', bucket: 'top30', signals: [], trading: { orders_enabled: false, connects_to_broker: false } })) }))
await page.route('**/api/tw-stock/quant/signals/rank-changes**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, entered: [], exited: [], stayed: [], top_gainers: [], top_decliners: [], watch_candidates: [], summary: {} })) }))
await page.route('**/api/tw-stock/quant/signals/runs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, job: null })) }))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, latest_status: 'accepted', latest_asof: '2026-06-04', trading: { orders_enabled: false, connects_to_broker: false } })) }))
await page.route('**/api/tw-stock/cross-analysis/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-04' }, freshness: { warnings: [] } })) }))
await page.route('**/api/tw-stock/agent/context**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ qlib: { asof: '2026-06-04' }, freshness: { status: 'accepted' }, top30_preview: [] })) }))
await page.route('**/api/tw-stock/sim/accounts**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/indicator/kline**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse([])) }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'rank-tech-e2e-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'rank-tech-e2e', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
}, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-testid="rank-tech-portfolio-replay-readonly"]')
await page.waitForFunction(() => document.body.innerText.includes('今日复盘与历史模拟'))
try {
  await page.waitForFunction(() => document.body.innerText.includes('新增观察') && document.body.innerText.includes('过去表现'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('qlib + trend + indicators'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('总收益') && document.body.innerText.includes('最大回撤') && document.body.innerText.includes('费用税费估算'), null, { timeout: 15000 })
} catch (error) {
  const diagnostic = await page.evaluate(() => ({
    href: window.location.href,
    text: document.querySelector('[data-testid="rank-tech-portfolio-replay-readonly"]')?.innerText || document.body.innerText.slice(0, 2000)
  }))
  const state = await page.evaluate(() => {
    const el = document.querySelector('.tw-stock-monitor')
    const vm = el && el.__vue__
    return vm ? {
      rankTechLatestPayload: vm.rankTechLatestPayload,
      rankTechAccepted: vm.rankTechAccepted,
      rankTechItemsLength: vm.rankTechItems && vm.rankTechItems.length,
      rankTechPriorityItemsLength: vm.rankTechPriorityItems && vm.rankTechPriorityItems.length,
      rankTechStatusText: vm.rankTechStatusText,
      portfolioReplayComparisonItemsLength: vm.portfolioReplayComparisonItems && vm.portfolioReplayComparisonItems.length,
      rankTechLatestError: vm.rankTechLatestError,
      portfolioReplayPayload: vm.portfolioReplayPayload,
      portfolioReplayError: vm.portfolioReplayError,
      loadingRankTechCross: vm.loadingRankTechCross,
      runningPortfolioReplay: vm.runningPortfolioReplay
    } : null
  })
  console.error('rank-tech e2e diagnostic:', JSON.stringify({ diagnostic, state, latestRequestCount, portfolioReplayRequestCount, rankTechResponses, failedResponses, pageErrors, requests: requests.slice(-20) }, null, 2))
  throw error
}

const text = await page.locator('[data-testid="rank-tech-portfolio-replay-readonly"]').innerText()
for (const required of ['只读历史模拟', '不是投资建议', '不连接券商', '不生成订单', '今天先看什么', '为什么', '总收益', '最大回撤', '费用税费估算']) {
  assert.ok(text.includes(required), `missing rendered text: ${required}`)
}
for (const forbidden of ['立即买入', '立即卖出', '自动买入', '自动卖出', '下单', '提交订单', '目标仓位', '上涨概率', '收益承诺']) {
  assert.ok(!text.includes(forbidden), `forbidden rendered text: ${forbidden}`)
}

await page.getByTestId('rank-tech-replay-controls').getByText('Top50', { exact: true }).click()
await page.waitForTimeout(300)
await page.getByTestId('rank-tech-replay-controls').getByText('近一年', { exact: true }).click()
await page.waitForTimeout(300)
await page.locator('[data-testid="rank-tech-replay-controls"] .ant-select').click()
await page.getByText('qlib + trend', { exact: true }).click()
await page.waitForTimeout(300)

const summary = {
  latest_request_count: latestRequestCount,
  observation_replay_request_count: observationRequestCount,
  portfolio_replay_request_count: portfolioReplayRequestCount,
  portfolio_persist_false_count: portfolioPersistFalseCount,
  sim_request_count: simRequestCount,
  sim_write_request_count: simWriteRequestCount,
  quick_trade_request_count: quickTradeRequestCount,
  broker_request_count: brokerRequestCount,
  real_order_request_count: realOrderRequestCount,
  monitor_config_write_count: monitorConfigWriteCount,
  monitor_scan_post_count: monitorScanPostCount,
  monitor_alerts_write_count: monitorAlertsWriteCount,
  qlib_ops_post_count: qlibOpsPostCount,
  accepted_latest_switch_count: acceptedLatestSwitchCount,
  provider_publish_refresh_count: providerPublishRefreshCount,
  target_position_request_count: targetPositionRequestCount,
  target_weight_request_count: targetWeightRequestCount,
  forbidden_request_count: forbiddenRequests.length,
  page_error_count: pageErrors.length
}

assert.ok(summary.latest_request_count >= 1, 'rank-tech latest was not requested')
assert.ok(summary.portfolio_replay_request_count >= 1, 'portfolio replay was not requested')
assert.equal(summary.portfolio_replay_request_count, summary.portfolio_persist_false_count, 'each portfolio replay request must persist=false')
assert.equal(summary.sim_write_request_count, 0)
assert.equal(summary.quick_trade_request_count, 0)
assert.equal(summary.broker_request_count, 0)
assert.equal(summary.real_order_request_count, 0)
assert.equal(summary.monitor_config_write_count, 0)
assert.equal(summary.monitor_scan_post_count, 0)
assert.equal(summary.monitor_alerts_write_count, 0)
assert.equal(summary.qlib_ops_post_count, 0)
assert.equal(summary.accepted_latest_switch_count, 0)
assert.equal(summary.provider_publish_refresh_count, 0)
assert.equal(summary.target_position_request_count, 0)
assert.equal(summary.target_weight_request_count, 0)
assert.equal(summary.forbidden_request_count, 0, JSON.stringify(forbiddenRequests, null, 2))
assert.equal(summary.page_error_count, 0, pageErrors.join('\n'))

await browser.close()
console.log(`tw-stock rank-tech portfolio replay readonly e2e passed: ${JSON.stringify(summary)}`)
