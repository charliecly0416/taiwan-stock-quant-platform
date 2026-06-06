import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '/tmp/travel-agent-e2e/node_modules/playwright/index.mjs'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const screenshotDir = process.env.TW_STOCK_SIM_FULL_FLOW_SCREENSHOT_DIR || '/tmp/quantdinger_tw_sim_full_flow_e2e'
await mkdir(screenshotDir, { recursive: true })

function apiResponse (data) { return { code: data && data.ok === false ? 0 : 1, msg: data && data.ok === false ? (data.message || data.status || 'mock_error') : 'success', data } }
function simFlags () { return { real_orders_enabled: false, connects_to_broker: false, simulation_only: true } }
function researchTrading () { return { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true } }

const latestRunId = 'phase5_full_flow_run'
const account = { account_uid: 'tw_sim_full_flow', name: '台股研究模拟账户', currency: 'TWD', initial_cash: 1000000, cash: 1000000, market_value: 0, total_equity: 1000000, total_pnl: 0, total_return: 0, simulation_only: true }
let positions = []
let trades = []
let lastDraft = null
let draftPostCount = 0
let confirmPostCount = 0
let orderSeq = 0

function accountPayload () {
  const marketValue = positions.reduce((sum, item) => sum + Number(item.market_value || 0), 0)
  return { ...account, market_value: marketValue, total_equity: account.cash + marketValue, total_pnl: account.cash + marketValue - account.initial_cash, total_return: (account.cash + marketValue) / account.initial_cash - 1, position_count: positions.length }
}
function makeDraft (body) {
  orderSeq += 1
  const symbol = String(body.symbol || '').replace(/^TW/i, '')
  const qty = Number(body.quantity || 1000)
  const price = 100
  const gross = qty * price
  const fee = 142.5
  lastDraft = { sim_order_uid: `tw_sim_order_full_${orderSeq}`, account_uid: account.account_uid, symbol, side: body.side || 'buy', quantity: qty, status: 'draft', source_type: body.source_type || 'manual', source_context: body.source_context || {}, reference_price: price, price_source: 'latest_close', price_date: '2026-06-04', gross_amount: gross, fee, tax: 0, net_cash_effect: -(gross + fee), message: 'draft_ready', warnings: [], simulation_only: true }
  return { ok: true, status: 'draft', sim_order: lastDraft, simulation_only: true, trading: simFlags() }
}
function fillDraft () {
  confirmPostCount += 1
  account.cash -= 100142.5
  positions = [{ symbol: lastDraft.symbol, quantity: 1000, avg_cost: 100.1425, cost_value: 100142.5, latest_close: 100, latest_date: '2026-06-04', market_value: 100000, unrealized_pnl: -142.5, simulation_only: true }]
  const trade = { sim_trade_uid: `tw_sim_trade_full_${confirmPostCount}`, sim_order_uid: lastDraft.sim_order_uid, account_uid: account.account_uid, symbol: lastDraft.symbol, side: lastDraft.side, quantity: lastDraft.quantity, price: lastDraft.reference_price, price_source: 'latest_close', price_date: '2026-06-04', gross_amount: lastDraft.gross_amount, fee: lastDraft.fee, tax: 0, net_cash_effect: lastDraft.net_cash_effect, source_type: lastDraft.source_type, source_context: lastDraft.source_context, simulation_only: true, created_at: `2026-06-05T00:0${confirmPostCount}:00` }
  trades.unshift(trade)
  return { ok: true, status: 'filled', sim_order: { ...lastDraft, status: 'filled' }, trade, account: accountPayload(), simulation_only: true, trading: simFlags() }
}
function qlibSignalsPayload () {
  return { ok: true, status: 'accepted', bucket: 'top30', asof: '2026-06-04', run_id: latestRunId, signals: [{ rank: 1, symbol: '2330', instrument: 'TW2330', name: '台积电', qlib_score: 0.42, research_signal_not_order: true, diagnostic_only: true, trend: { ok: true, latest_close: 100, latest_date: '2026-06-04', trend_label: 'uptrend', trend_score: 80, quality_warnings: [] } }], warnings: [], trading: researchTrading() }
}
function crossPayload () {
  return { ok: true, status: 'accepted', bucket: 'top30', qlib: { asof: '2026-06-04', run_id: latestRunId }, items: [
    { symbol: '2454', instrument: 'TW2454', name: '联发科', qlib: { rank: 2, bucket: 'top30', score: 0.33, asof: '2026-06-04', run_id: latestRunId }, quantdinger: { trend_label: 'uptrend', trend_score: 78, latest_date: '2026-06-04', quality_warnings: [] }, cross: { category: 'focus_watch', alignment: 'aligned', priority: 'high', human_action: 'manual_review_watchlist', summary: '研究信号与趋势同向' }, data_basis: { data_basis_status: 'ok', date_gap_days: 0 } },
    { symbol: '2303', instrument: 'TW2303', name: '联电', qlib: { rank: 3, bucket: 'top30', score: 0.2, asof: '2026-06-04', run_id: latestRunId }, quantdinger: { trend_label: 'downtrend', trend_score: 30, latest_date: '2026-06-04', quality_warnings: [] }, cross: { category: 'model_trend_divergence', alignment: 'divergent', priority: 'blocked', human_action: 'manual_review_required', summary: '模型趋势分歧' }, data_basis: { data_basis_status: 'ok', date_gap_days: 0 } }
  ], summary: { category_counts: { focus_watch: 1, model_trend_divergence: 1 }, item_count: 2 }, freshness: { status: 'fresh', qlib: { asof: '2026-06-04', run_id: latestRunId }, quantdinger: { latest_date_min: '2026-06-04', latest_date_max: '2026-06-04' }, warnings: [] }, basis: { note: 'full-flow fixture' }, trading: researchTrading() }
}
function dangerousCounters (requests) {
  const c = { sim_request_count: 0, forbidden_request_count: 0, quick_trade_request_count: 0, broker_request_count: 0, real_order_request_count: 0, monitor_scan_post_count: 0, monitor_alerts_write_count: 0, qlib_ops_post_count: 0, agent_chat_request_count: 0, accepted_latest_switch_count: 0, provider_publish_refresh_count: 0 }
  for (const item of requests) {
    const lower = item.url.toLowerCase(); const method = item.method.toUpperCase()
    if (lower.includes('/api/tw-stock/sim/')) c.sim_request_count += 1
    if (lower.includes('/api/quick-trade')) c.quick_trade_request_count += 1
    if (lower.includes('/api/broker') || lower.includes('/broker/')) c.broker_request_count += 1
    if (lower.includes('/api/order') || lower.includes('/api/orders')) c.real_order_request_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/monitor/scan')) c.monitor_scan_post_count += 1
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && lower.includes('/api/tw-stock/monitor/alerts')) c.monitor_alerts_write_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/quant/ops/')) c.qlib_ops_post_count += 1
    if (lower.includes('/api/tw-stock/agent/chat')) c.agent_chat_request_count += 1
    if (method !== 'GET' && lower.includes('accepted-latest')) c.accepted_latest_switch_count += 1
    if (method !== 'GET' && (lower.includes('publish') || lower.includes('refresh-provider') || lower.includes('provider_refresh'))) c.provider_publish_refresh_count += 1
  }
  c.forbidden_request_count = c.quick_trade_request_count + c.broker_request_count + c.real_order_request_count + c.monitor_scan_post_count + c.monitor_alerts_write_count + c.qlib_ops_post_count + c.agent_chat_request_count + c.accepted_latest_switch_count + c.provider_publish_refresh_count
  return c
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)
const requests = []; const pageErrors = []
page.on('request', request => requests.push({ method: request.method(), url: request.url() }))
page.on('pageerror', err => pageErrors.push(err.message))

await page.route('**/api/auth/info**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'phase5', nickname: 'Phase5', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({})) }))
await page.route('**/api/strategies/notifications/unread-count**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger' })) }))
await page.route('**/api/policy/broker-market**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))
await page.route('**/api/tw-stock/monitor/config**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ name: 'default', symbols: ['2330'], limit_bars: 120, enabled: true })) }))
await page.route('**/api/tw-stock/monitor/alerts**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [], count: 0 })) }))
await page.route('**/api/tw-stock/monitor/history**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [], count: 0 })) }))
await page.route('**/api/tw-stock/monitor/scan-logs**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [], count: 0 })) }))
await page.route('**/api/tw-stock/trends**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [], count: 0 })) }))
await page.route('**/api/tw-stock/quant/signals/latest**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(qlibSignalsPayload())) }))
await page.route('**/api/tw-stock/quant/signals/rank-changes**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, asof: '2026-06-04', previous_asof: '2026-06-03', summary: {}, entered: [], exited: [], stayed: [] })) }))
await page.route('**/api/tw-stock/quant/signals/health**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted' })) }))
await page.route('**/api/tw-stock/quant/signals/runs**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [], count: 0 })) }))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'idle' })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'none' })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/scheduler**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, enabled: false })) }))
await page.route('**/api/tw-stock/cross-analysis/latest**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(crossPayload())) }))
await page.route('**/api/tw-stock/cross-analysis/symbol/**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', item: crossPayload().items[0], qlib: crossPayload().qlib })) }))
await page.route('**/api/tw-stock/agent/context**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', top30_preview: [{ symbol: '2330' }], cross_analysis: { summary: {} }, freshness: { status: 'fresh' }, qlib: { asof: '2026-06-04', run_id: latestRunId } })) }))
await page.route('**/api/indicator/kline**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse([])) }))

await page.route(/\/api\/tw-stock\/sim\/accounts\/?(?:\?.*)?$/, async r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', items: [accountPayload()], count: 1, simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/accounts/*/positions', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, items: positions, count: positions.length, simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/accounts/*/trades**', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, items: trades, count: trades.length, simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/accounts/*', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, account: accountPayload(), simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/orders/draft', async r => { draftPostCount += 1; const payload = makeDraft(JSON.parse(r.request().postData() || '{}')); await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(payload)) }) })
await page.route(/\/api\/tw-stock\/sim\/orders\/[^/]+\/confirm(?:\?.*)?$/, async r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(fillDraft())) }))
await page.route(/\/api\/tw-stock\/sim\/orders\/[^/]+\/cancel(?:\?.*)?$/, async r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'cancelled', sim_order: { ...lastDraft, status: 'cancelled' }, simulation_only: true, trading: simFlags() })) }))

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => { const token = { token: 'phase5-token' }; localStorage.setItem('Access-Token', JSON.stringify(token)); localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'phase5' })); localStorage.setItem('User-Roles', JSON.stringify(['dashboard'])); localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt)); localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt)); localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt)); localStorage.setItem('lang', 'zh-CN') }, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.tw-stock-monitor')
await page.waitForSelector('[data-testid="qlib-sim-draft"]')
const beforeQlibDraft = draftPostCount
await page.locator('[data-testid="qlib-sim-draft"]').first().click()
await page.waitForURL(/tw-stock-sim-account/)
await page.waitForSelector('.tw-stock-sim-account')
await page.waitForFunction(() => document.body.innerText.includes('source_type qlib_rank'))
assert.equal(draftPostCount, beforeQlibDraft, 'qlib prefill must not call draft API before user click')
assert.equal(await page.locator('input[placeholder="股票代码，例如 2330 或 TW6290"]').inputValue(), '2330')
await page.getByText('生成模拟买入草稿').click()
await page.waitForFunction(() => document.body.innerText.includes('草稿状态：draft'))
assert.equal(lastDraft.source_type, 'qlib_rank')
await page.getByText('确认模拟成交').click()
await page.waitForTimeout(1000)
assert.equal(confirmPostCount, 1, 'qlib flow confirm should require explicit click')
await page.waitForFunction(() => document.body.innerText.includes('绩效复盘') && document.body.innerText.includes('模拟成交标记'))
await page.screenshot({ path: path.join(screenshotDir, '01_qlib_full_flow.png'), fullPage: true })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.tw-stock-monitor')
await page.waitForFunction(() => document.body.innerText.includes('模拟成交标记'))
await page.waitForSelector('[data-testid="cross-sim-draft"]')
const crossButtons = page.locator('[data-testid="cross-sim-draft"]')
assert.equal(await crossButtons.nth(1).isDisabled(), true, 'divergence row must not default prefill simulated buy draft')
const beforeCrossDraft = draftPostCount
await crossButtons.first().click()
await page.waitForURL(/tw-stock-sim-account/)
await page.waitForFunction(() => document.body.innerText.includes('source_type cross_analysis'))
assert.equal(draftPostCount, beforeCrossDraft, 'cross prefill must not call draft API before user click')
assert.equal(await page.locator('input[placeholder="股票代码，例如 2330 或 TW6290"]').inputValue(), '2454')
await page.getByText('生成模拟买入草稿').click()
await page.waitForFunction(() => document.body.innerText.includes('草稿状态：draft'))
assert.equal(lastDraft.source_type, 'cross_analysis')
await page.screenshot({ path: path.join(screenshotDir, '02_cross_prefill.png'), fullPage: true })

const counters = dangerousCounters(requests)
console.log(JSON.stringify(counters, null, 2))
assert.ok(counters.sim_request_count > 0)
assert.equal(counters.forbidden_request_count, 0)
assert.equal(counters.quick_trade_request_count, 0)
assert.equal(counters.broker_request_count, 0)
assert.equal(counters.real_order_request_count, 0)
assert.equal(counters.monitor_scan_post_count, 0)
assert.equal(counters.monitor_alerts_write_count, 0)
assert.equal(counters.qlib_ops_post_count, 0)
assert.equal(counters.agent_chat_request_count, 0)
assert.equal(counters.accepted_latest_switch_count, 0)
assert.equal(counters.provider_publish_refresh_count, 0)
assert.equal(pageErrors.length, 0, pageErrors.join('\n'))
await browser.close()
