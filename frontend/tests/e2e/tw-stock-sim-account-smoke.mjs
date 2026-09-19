import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const screenshotDir = process.env.TW_STOCK_SIM_ACCOUNT_SCREENSHOT_DIR || '/tmp/quantdinger_tw_sim_account_e2e'
await mkdir(screenshotDir, { recursive: true })

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.ok === false ? (data.message || data.status || 'mock_error') : 'success', data }
}

function simFlags () {
  return { real_orders_enabled: false, connects_to_broker: false, simulation_only: true }
}

const account = {
  account_uid: 'tw_sim_e2e_1',
  user_id: 1,
  name: '台股研究模拟账户',
  currency: 'TWD',
  initial_cash: 1000000,
  cash: 1000000,
  market_value: 0,
  total_equity: 1000000,
  total_pnl: 0,
  total_return: 0,
  position_count: 0,
  simulation_only: true,
  created_at: '2026-06-05T00:00:00',
  updated_at: '2026-06-05T00:00:00'
}
let positions = []
let trades = []
let lastDraft = null
let draftCounter = 0
let confirmCount = 0

function accountPayload () {
  const marketValue = positions.reduce((sum, item) => sum + Number(item.market_value || 0), 0)
  return {
    ...account,
    market_value: marketValue,
    total_equity: account.cash + marketValue,
    total_pnl: account.cash + marketValue - account.initial_cash,
    total_return: (account.cash + marketValue) / account.initial_cash - 1,
    position_count: positions.length
  }
}

function draftPayload ({ symbol, side, quantity, rejected = false, sourceType = 'manual', sourceContext = {} }) {
  draftCounter += 1
  const price = symbol === '2603' ? 0 : 100
  const qty = Number(quantity || 1000)
  const gross = qty * price
  const fee = Math.round(gross * 0.001425 * 100) / 100
  const tax = side === 'sell' ? Math.round(gross * 0.003 * 100) / 100 : 0
  const net = side === 'sell' ? gross - fee - tax : -(gross + fee)
  lastDraft = {
    sim_order_uid: `tw_sim_order_e2e_${draftCounter}`,
    account_uid: account.account_uid,
    symbol,
    side,
    quantity: qty,
    status: rejected ? 'rejected' : 'draft',
    source_type: sourceType,
    source_context: sourceContext,
    reference_price: price,
    price_source: 'latest_close',
    price_date: rejected ? null : '2026-06-04',
    gross_amount: gross,
    fee,
    tax,
    net_cash_effect: net,
    message: rejected ? 'missing_price' : 'draft_ready',
    warnings: rejected ? ['missing_latest_close'] : [],
    simulation_only: true
  }
  return { ok: !rejected, status: lastDraft.status, message: lastDraft.message, sim_order: lastDraft, simulation_only: true, trading: simFlags() }
}

function dangerousCounters (requests) {
  const counters = {
    sim_request_count: 0,
    forbidden_request_count: 0,
    quick_trade_request_count: 0,
    broker_request_count: 0,
    real_order_request_count: 0,
    monitor_scan_post_count: 0,
    monitor_alerts_write_count: 0,
    qlib_ops_post_count: 0,
    agent_chat_request_count: 0
  }
  for (const item of requests) {
    const lower = item.url.toLowerCase()
    const method = item.method.toUpperCase()
    if (lower.includes('/api/tw-stock/sim/')) counters.sim_request_count += 1
    if (lower.includes('/api/quick-trade')) counters.quick_trade_request_count += 1
    if (lower.includes('/api/broker') || lower.includes('/broker/')) counters.broker_request_count += 1
    if (lower.includes('/api/order') || lower.includes('/api/orders')) counters.real_order_request_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/monitor/scan')) counters.monitor_scan_post_count += 1
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && lower.includes('/api/tw-stock/monitor/alerts')) counters.monitor_alerts_write_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/quant/ops/')) counters.qlib_ops_post_count += 1
    if (lower.includes('/api/tw-stock/agent/chat')) counters.agent_chat_request_count += 1
  }
  counters.forbidden_request_count = counters.quick_trade_request_count + counters.broker_request_count + counters.real_order_request_count + counters.monitor_scan_post_count + counters.monitor_alerts_write_count + counters.qlib_ops_post_count + counters.agent_chat_request_count
  return counters
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1360, height: 920 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const requests = []
const consoleMessages = []
const pageErrors = []
page.on('request', request => requests.push({ method: request.method(), url: request.url() }))
page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`))
page.on('pageerror', err => pageErrors.push(err.message))

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'sim-e2e', nickname: 'Sim E2E', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger', app_version: 'e2e' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))

await page.route(/\/api\/tw-stock\/sim\/accounts\/?(?:\?.*)?$/, async route => {
  const method = route.request().method().toUpperCase()
  if (method === 'GET') {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', items: [accountPayload()], count: 1, simulation_only: true, trading: simFlags() })) })
    return
  }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'created', account: accountPayload(), simulation_only: true, trading: simFlags() })) })
})
await page.route('**/api/tw-stock/sim/accounts/*/positions', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', items: positions, count: positions.length, simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/accounts/*/trades**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', items: trades, count: trades.length, simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/accounts/*', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', account: accountPayload(), simulation_only: true, trading: simFlags() })) }))
await page.route('**/api/tw-stock/sim/orders/draft', async route => {
  const body = JSON.parse(route.request().postData() || '{}')
  const payload = draftPayload({ symbol: String(body.symbol || '').replace(/^TW/i, ''), side: body.side || 'buy', quantity: body.quantity || 1000, rejected: String(body.symbol || '').includes('2603'), sourceType: body.source_type || 'manual', sourceContext: body.source_context || {} })
  await route.fulfill({ status: payload.ok ? 200 : 400, contentType: 'application/json', body: JSON.stringify(apiResponse(payload)) })
})
await page.route(/\/api\/tw-stock\/sim\/orders\/[^/]+\/confirm(?:\?.*)?$/, async route => {
  confirmCount += 1
  account.cash = 899857.5
  positions = [{ symbol: '2330', quantity: 1000, avg_cost: 100.1425, cost_value: 100142.5, latest_close: 100, latest_date: '2026-06-04', market_value: 100000, unrealized_pnl: -142.5, simulation_only: true }]
  trades = [{ sim_trade_uid: 'tw_sim_trade_e2e_1', sim_order_uid: lastDraft.sim_order_uid, account_uid: account.account_uid, symbol: '2330', side: 'buy', quantity: 1000, price: 100, price_source: 'latest_close', price_date: '2026-06-04', gross_amount: 100000, fee: 142.5, tax: 0, net_cash_effect: -100142.5, source_type: lastDraft.source_type, source_context: lastDraft.source_context, simulation_only: true, created_at: '2026-06-05T00:00:00' }]
  const payload = { ok: true, status: 'filled', sim_order: { ...lastDraft, status: 'filled' }, trade: trades[0], account: accountPayload(), simulation_only: true, trading: simFlags() }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(payload)) })
})
await page.route(/\/api\/tw-stock\/sim\/orders\/[^/]+\/cancel(?:\?.*)?$/, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'cancelled', sim_order: { ...lastDraft, status: 'cancelled' }, simulation_only: true, trading: simFlags() })) }))

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => {
  const token = { token: 'sim-e2e-token' }
  const userinfo = { id: 1, username: 'sim-e2e', nickname: 'Sim E2E' }
  const roles = ['dashboard']
  window.localStorage.setItem('Access-Token', JSON.stringify(token))
  window.localStorage.setItem('User-Info', JSON.stringify(userinfo))
  window.localStorage.setItem('User-Roles', JSON.stringify(roles))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
}, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-sim-account`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.tw-stock-sim-account')
await page.waitForFunction(() => document.body.innerText.includes('本页面仅用于台股研究信号的历史与模拟验证'))
await page.screenshot({ path: path.join(screenshotDir, '01_loaded.png'), fullPage: true })

await page.locator('input[placeholder="股票代码，例如 2330 或 TW6290"]').fill('2603')
await page.getByText('生成模拟买入草稿').click()
await page.waitForFunction(() => document.body.innerText.includes('missing_price') || document.body.innerText.includes('缺少最新收盘价'))
assert.equal(await page.getByText('确认模拟成交').count(), 0, 'rejected draft must not show confirm button')
await page.screenshot({ path: path.join(screenshotDir, '02_rejected.png'), fullPage: true })

await page.locator('input[placeholder="股票代码，例如 2330 或 TW6290"]').fill('2330')
await page.getByText('生成模拟买入草稿').click()
await page.waitForFunction(() => document.body.innerText.includes('草稿状态：draft'))
assert.ok(await page.getByText('确认模拟成交').isVisible(), 'draft must show confirm button')
assert.ok(await page.getByText('取消草稿').isVisible(), 'draft must show cancel button')
await page.screenshot({ path: path.join(screenshotDir, '03_draft.png'), fullPage: true })

const beforeConfirmRequestCount = requests.length
await page.getByText('确认模拟成交').click()
await page.waitForTimeout(1500)
assert.equal(confirmCount, 1, 'confirm endpoint should be called exactly once after explicit click')
const afterConfirmRequests = requests.slice(beforeConfirmRequestCount).map(item => item.url.toLowerCase())
assert.ok(afterConfirmRequests.some(url => url.includes('/api/tw-stock/sim/accounts/') && !url.includes('/positions') && !url.includes('/trades')), 'confirm should refresh account detail')
assert.ok(afterConfirmRequests.some(url => url.includes('/api/tw-stock/sim/accounts/') && url.includes('/positions')), 'confirm should refresh positions')
assert.ok(afterConfirmRequests.some(url => url.includes('/api/tw-stock/sim/accounts/') && url.includes('/trades')), 'confirm should refresh trades')
await page.screenshot({ path: path.join(screenshotDir, '04_confirmed.png'), fullPage: true })

const counters = dangerousCounters(requests)
console.log(JSON.stringify(counters, null, 2))
assert.ok(counters.sim_request_count > 0, 'sim_request_count must be > 0')
assert.equal(counters.forbidden_request_count, 0, 'forbidden_request_count must be 0')
assert.equal(counters.quick_trade_request_count, 0)
assert.equal(counters.broker_request_count, 0)
assert.equal(counters.real_order_request_count, 0)
assert.equal(counters.monitor_scan_post_count, 0)
assert.equal(counters.monitor_alerts_write_count, 0)
assert.equal(counters.qlib_ops_post_count, 0)
assert.equal(counters.agent_chat_request_count, 0)
assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join('\n')}`)

await browser.close()
