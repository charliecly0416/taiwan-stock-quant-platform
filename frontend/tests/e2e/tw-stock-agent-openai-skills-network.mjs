import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from '/tmp/travel-agent-e2e/node_modules/playwright/index.mjs'

const baseUrl = process.env.TW_STOCK_AGENT_BASE_URL || 'http://127.0.0.1:8000'
const backendUrl = process.env.TW_STOCK_AGENT_BACKEND_URL || 'http://127.0.0.1:5094'
const screenshotDir = process.env.TW_STOCK_AGENT_SCREENSHOT_DIR || '/tmp/tw_stock_agent_openai_skills'
const latestRunId = 'option_c_daily_signal_openai_skills_fixture'
const disclaimer = '仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。'

await mkdir(screenshotDir, { recursive: true })

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.ok === false ? (data.message || data.status || 'mock_error') : 'success', data }
}

function agentItem (symbol, rank, score, trend, category, action = '加入重点观察并人工复盘', warnings = []) {
  return {
    symbol,
    instrument: `TW${symbol}`,
    qlib_rank: rank,
    qlib_bucket: rank <= 30 ? 'top30' : 'top50',
    qlib_score: score,
    trend_label: trend,
    trend_score: trend ? 70 - rank : null,
    latest_date: '2026-06-01',
    quality_warnings: warnings,
    cross_category: category,
    alignment: category === 'model_trend_divergence' ? 'divergent' : 'aligned',
    priority: rank <= 3 ? 'high' : 'medium',
    human_action: action,
    data_basis_status: warnings.length ? 'date_gap' : 'ok',
    date_gap_days: warnings.length ? 2 : 0
  }
}

const focusItems = [agentItem('2330', 1, 0.421, 'uptrend', 'focus_watch'), agentItem('2454', 2, 0.318, 'rebound', 'focus_watch')]
const divergenceItems = [agentItem('2303', 3, 0.221, 'downtrend', 'model_trend_divergence', '趋势分歧，建议人工复盘')]
const reviewItems = [agentItem('2603', 4, 0.111, null, 'data_review_required', '数据异常，暂不纳入判断', ['stale_daily_bar'])]
const allItems = focusItems.concat(divergenceItems, reviewItems)

function crossAnalysisPayload () {
  return {
    ok: true,
    status: 'accepted',
    bucket: 'top30',
    qlib: { asof: '2026-06-01', run_id: latestRunId, target_horizon: 'next_trading_day_research_ranking', research_signal_not_order: true },
    items: allItems.map(item => ({
      symbol: item.symbol,
      instrument: item.instrument,
      qlib: { rank: item.qlib_rank, bucket: item.qlib_bucket, score: item.qlib_score },
      quantdinger: { trend_label: item.trend_label, trend_score: item.trend_score, latest_date: item.latest_date, quality_warnings: item.quality_warnings },
      cross: { category: item.cross_category, alignment: item.alignment, priority: item.priority, human_action: item.human_action },
      data_basis: { data_basis_status: item.data_basis_status, date_gap_days: item.date_gap_days }
    })),
    summary: { category_counts: { focus_watch: 2, model_trend_divergence: 1, data_review_required: 1 }, item_count: 4 },
    freshness: { status: 'fresh', qlib: { asof: '2026-06-01', run_id: latestRunId, target_horizon: 'next_trading_day_research_ranking' }, quantdinger: { latest_date_min: '2026-06-01', latest_date_max: '2026-06-01', source: 'raw TWStock daily KlineService data' }, warnings: [] },
    basis: { note: 'fixture basis note' },
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function monitorConfig () {
  return { name: 'default', symbols: ['2330', '2454', '2303'], limit_bars: 120, refresh_interval_sec: 0, score_change_threshold: 8, enabled: true }
}

function trendPayload () {
  return { market: 'TWStock', count: 3, ok_count: 3, items: ['2330', '2454', '2303'].map((symbol, index) => ({ ok: true, symbol, exchange: 'TWSE', trend: { label: index === 2 ? 'downtrend' : 'uptrend', score: 75 - index * 5 }, latest: { date: '2026-06-01', close: 600 - index * 10 }, returns: { ret_20d: 0.02, ret_60d: 0.05 }, risk: { volatility_20d_annualized: 0.2 }, volume: { ratio_to_avg20: 1.1 }, quality: { bar_count: 120, warnings: [] } })) }
}

function klinePayload () {
  const start = Date.UTC(2026, 0, 1) / 1000
  return Array.from({ length: 120 }, (_, i) => ({ time: start + i * 86400, open: 560 + i * 0.8, high: 565 + i * 0.8, low: 555 + i * 0.8, close: 562 + i * 0.8, volume: 1000000 + i * 1000 }))
}

function backendTarget (requestUrl) {
  const url = new URL(requestUrl)
  return `${backendUrl}${url.pathname}${url.search}`
}

function isDirectOpenAIUrl (url) {
  const lower = url.toLowerCase()
  return lower.includes('api.openai.com') || lower.includes('chat.pku.edu.cn')
}

function dangerousUrl (method, url) {
  const lower = url.toLowerCase()
  if (isDirectOpenAIUrl(url) || lower.includes('openai_api_key')) return true
  if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return false
  return lower.includes('/api/tw-stock/quant/ops/') || lower.includes('/api/tw-stock/cross-analysis/history/import-latest') || lower.includes('/api/tw-stock/cross-analysis/reviews') || lower.includes('/api/quick-trade') || lower.includes('broker') || lower.includes('order/submit') || lower.includes('target_position') || lower.includes('targetposition')
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const consoleMessages = []
const pageErrors = []
const allRequests = []
const forwardedBackendRequests = []
const dangerousRequests = []
const agentResponses = []
let directOpenAIRequests = 0
let agentChatStatus = 0

page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`))
page.on('pageerror', error => pageErrors.push(error.message))
page.on('request', request => {
  const entry = `${request.method().toUpperCase()} ${request.url()}`
  allRequests.push(entry)
  if (isDirectOpenAIUrl(request.url())) directOpenAIRequests += 1
  if (dangerousUrl(request.method().toUpperCase(), request.url()) && !request.url().includes('/api/tw-stock/agent/')) dangerousRequests.push(entry)
})

await page.route('**/api/auth/info**', async route => {
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'agent-openai-e2e', nickname: 'Agent OpenAI E2E', is_demo: false, role: { id: 'default', permissions: ['dashboard'] } })) })
})
await page.route('**/api/auth/security-config**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false, oauth_google_enabled: false, oauth_github_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger', app_version: 'e2e', copyright: 'QuantDinger E2E' })) }))
await page.route('**/api/policy/broker-market**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, policy: 'disabled_in_e2e' })) }))

async function forwardAgentRoute (route, { timeoutMs = 60000 } = {}) {
  const request = route.request()
  const method = request.method().toUpperCase()
  const target = backendTarget(request.url())
  forwardedBackendRequests.push(`${method} ${target}`)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(target, {
      method,
      headers: { 'content-type': 'application/json' },
      body: method === 'GET' ? undefined : (request.postData() || '{}'),
      signal: controller.signal
    })
    const text = await response.text()
    return { status: response.status, text }
  } finally {
    clearTimeout(timer)
  }
}

await page.route('**/api/tw-stock/agent/context**', async route => {
  const result = await forwardAgentRoute(route, { timeoutMs: 30000 })
  await route.fulfill({ status: result.status, contentType: 'application/json', body: result.text })
})
await page.route('**/api/tw-stock/agent/chat**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  const result = await forwardAgentRoute(route, { timeoutMs: 70000 })
  agentChatStatus = result.status
  const payload = JSON.parse(result.text || '{}')
  agentResponses.push(payload)
  await route.fulfill({ status: result.status, contentType: 'application/json', body: result.text })
})

await page.route('**/api/tw-stock/cross-analysis/latest**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(crossAnalysisPayload())) }))
await page.route('**/api/tw-stock/cross-analysis/symbol/**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', symbol: '2330', item: crossAnalysisPayload().items[0], qlib: crossAnalysisPayload().qlib, trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true } })) }))
await page.route('**/api/tw-stock/monitor/config**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(monitorConfig())) }))
await page.route('**/api/tw-stock/trends**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(trendPayload())) }))
await page.route('**/api/tw-stock/monitor/alerts**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/scan-logs**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ health: { status: 'healthy', success_count: 1, failed_count: 0, total_scanned_count: 3, total_alert_count: 0, success_rate: 1 } })) }))
await page.route('**/api/tw-stock/monitor/history**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/indicator/kline**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(klinePayload())) }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [{ id: 'ma_cross_builtin', name: 'MA Cross' }] })) }))
await page.route('**/api/tw-stock/quant/signals/health**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', latest: { exists: true, asof: '2026-06-01', run_id: latestRunId, accepted_validated: true, warnings: [] }, freshness: { stale: false }, runs: { accepted: 1, wait_state: 0, blocked: 0 }, dataAvailability: { trend_data_dependency: 'TWStock local daily bars', backtest_data_dependency: 'qd_tw_stock_daily_bars', warnings: [] }, trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true } })) }))
await page.route('**/api/tw-stock/quant/signals/latest**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', asof: '2026-06-01', run_id: latestRunId, bucket: 'top30', recorder_id: 'fixture', signals: [], warnings: [], trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true } })) }))
await page.route('**/api/tw-stock/quant/signals/runs**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [], count: 0 })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/scheduler**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, enabled: false, mode: 'disabled' })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', job: null })) }))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, enabled: false, status: 'disabled', warnings: [] })) }))

const seedAgentAuth = () => {
  const expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000
  const info = { id: 1, username: 'agent-openai-e2e', nickname: 'Agent OpenAI E2E', is_demo: false, role: { id: 'default', permissions: ['dashboard'] } }
  const roles = [{ id: 'default', permissionList: ['dashboard'] }]
  window.localStorage.setItem('Access-Token', JSON.stringify('agent-openai-e2e-token'))
  window.localStorage.setItem('User-Info', JSON.stringify(info))
  window.localStorage.setItem('User-Roles', JSON.stringify(roles))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-TW')
}

await page.addInitScript(seedAgentAuth)
await page.goto(baseUrl, { waitUntil: 'domcontentloaded' })
await page.evaluate(seedAgentAuth)
await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.tw-stock-agent-panel')
await page.waitForFunction(() => document.body.innerText.includes('台股研究助手'))

const agent = page.locator('.tw-stock-agent-panel')
await agent.locator('textarea').fill('今天模型和趋势都支持的股票有哪些？')
await Promise.all([
  page.waitForResponse(response => response.url().includes('/api/tw-stock/agent/chat') && response.status() === 200, { timeout: 70000 }),
  agent.getByRole('button', { name: /发送/ }).click()
])

await page.waitForFunction(() => document.body.innerText.includes('skills'), null, { timeout: 20000 })
await page.waitForFunction(() => document.body.innerText.includes('Safety Boundary Review'), null, { timeout: 20000 })
await page.waitForFunction(() => document.body.innerText.includes('Research Context Analyst'), null, { timeout: 20000 })
await page.screenshot({ path: `${screenshotDir}/openai-skills-network.png`, fullPage: true })

assert.equal(agentChatStatus, 200, 'agent chat backend response should be HTTP 200')
assert.ok(agentResponses.length >= 1, 'missing forwarded agent chat response')
const data = agentResponses.at(-1).data
assert.equal(data.mode, 'openai', `expected mode=openai, got ${data.mode}`)
assert.equal(data.blocked, false, 'research question should not be blocked')
assert.ok(Array.isArray(data.invoked_skills), 'missing invoked_skills')
const skillNames = data.invoked_skills.map(item => item.name)
assert.ok(skillNames.includes('tw-stock-safety-boundary-review'), 'missing safety skill')
assert.ok(skillNames.includes('tw-stock-research-context-analyst'), 'missing research skill')
assert.equal(directOpenAIRequests, 0, 'browser must not directly request OpenAI-compatible endpoint')
assert.equal(dangerousRequests.length, 0, `dangerous requests: ${dangerousRequests.join('\n')}`)
assert.ok(!JSON.stringify(agentResponses).includes('OPENAI_API_KEY'), 'response leaked OPENAI_API_KEY token name')
assert.doesNotMatch(JSON.stringify(agentResponses), /Bearer\s+[A-Za-z0-9_\-]{8,}/, 'response leaked bearer-like secret')

const forwardedPaths = Array.from(new Set(forwardedBackendRequests.map(item => {
  const [method, raw] = item.split(' ')
  const url = new URL(raw)
  return `${method} ${url.pathname}`
}))).sort()
assert.deepEqual(forwardedPaths, ['GET /api/tw-stock/agent/context', 'POST /api/tw-stock/agent/chat'])

const summary = {
  baseUrl,
  backendUrl,
  forwardedPaths,
  agentChatStatus,
  mode: data.mode,
  invokedSkills: skillNames,
  directOpenAIRequests,
  dangerousRequests: dangerousRequests.length,
  consoleErrors: consoleMessages.filter(item => item.startsWith('error:')).length,
  pageErrors: pageErrors.length,
  screenshotDir
}

await browser.close()
console.log(`tw-stock-agent openai skills network e2e passed: ${JSON.stringify(summary)}`)
