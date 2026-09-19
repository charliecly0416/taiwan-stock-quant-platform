import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const outDir = process.env.TW_STOCK_PAPER_PORTFOLIO_E2E_DIR || '/tmp/quantdinger_tw_paper_portfolio_e2e'
await mkdir(outDir, { recursive: true })

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.ok === false ? (data.message || data.status || 'mock_error') : 'success', data }
}
function simFlags () { return { real_orders_enabled: false, connects_to_broker: false, simulation_only: true } }

const decisionId = 'paper_decision_e2e_001'
const accountId = 'tw_sim_paper_e2e'
const artifactPath = 'e2e_run/paper_order_intent.json'
let epoch = 1
let cash = 200000
let positions = [{ symbol: '9999', quantity: 1000, avg_cost: 50, cost_value: 50000, simulation_only: true }]
let applied = false
let resetDone = false
let applyPostCount = 0
let resetPostCount = 0

function actions () {
  return [
    { action_type: 'paper_sell_intent', instrument: 'TW9999', symbol: '9999', quantity: 1000, reason: 'top50_exit_one_worst_sell_sell_outside_top50_worst_rank', estimated_reference_price: 80, price_date: '2026-06-18', applicability: 'applicable' },
    { action_type: 'paper_buy_intent', instrument: 'TW1111', symbol: '1111', quantity: 10, reason: 'top50_exit_one_worst_sell_buy_best_available_candidate', estimated_reference_price: 100, price_date: '2026-06-18', applicability: 'applicable' },
    { action_type: 'paper_skip', instrument: 'TW2330', symbol: '2330', quantity: 0, reason: 'current_paper_holding_kept_by_strategy', applicability: 'not_applicable' }
  ]
}
function latestDecision () {
  return {
    ok: true,
    status: 'ok',
    asof: '2026-06-18',
    model_id: 'e4_frozen_qlib_2023_2025_ltr',
    strategy_rule: 'top50_exit_one_worst_sell',
    decision_id: decisionId,
    paper_account_id: accountId,
    paper_account_epoch: epoch,
    input_checksum: 'sha256:e2e-input-checksum',
    paper_order_intent_artifact_path: artifactPath,
    preview: { readonly_preview_only: true, not_applied: true, cash_before: cash, cash_after_preview: 279657, preview_rows: actions() },
    intent: { artifact_type: 'PaperOrderIntentArtifact', decision_id: decisionId, model_id: 'e4_frozen_qlib_2023_2025_ltr', strategy_rule: 'top50_exit_one_worst_sell', paper_account_id: accountId, paper_account_epoch: epoch, asof: '2026-06-18', input_checksum: 'sha256:e2e-input-checksum', readonly_decision_only: true, not_real_order: true, not_target_position: true, not_investment_advice: true, actions: actions() },
    simulation_only: true,
    trading: simFlags()
  }
}
function statePayload () {
  return { ok: true, status: 'ok', paper_account: { account_uid: accountId, user_id: 1, currency: 'TWD', initial_cash: 500000, cash, paper_account_epoch: epoch, simulation_only: true }, positions, simulation_only: true, trading: simFlags() }
}
function applyRunsPayload () {
  return { ok: true, status: 'ok', items: applied ? [{ apply_id: 'paper_apply_e2e_1', decision_id: decisionId, paper_account_id: accountId, paper_account_epoch: epoch, idempotency_key: 'e2e', input_checksum: 'sha256:e2e-input-checksum', status: 'applied', already_applied: false, result: { decision_id: decisionId } }] : [], count: applied ? 1 : 0, simulation_only: true, trading: simFlags() }
}
function networkCounters (requests) {
  const counters = { forbidden_request_count: 0, quick_trade_request_count: 0, broker_request_count: 0, provider_ops_post_count: 0, monitor_config_write_count: 0, monitor_scan_post_count: 0, monitor_alerts_write_count: 0, target_position_write_count: 0, allowed_paper_apply_post_count: 0, allowed_paper_reset_post_count: 0, unexpected_post_count: 0 }
  const allowedPosts = ['/api/tw-stock/paper-portfolio/apply-decision', '/api/tw-stock/paper-portfolio/reset']
  for (const req of requests) {
    const lower = req.url.toLowerCase()
    const method = req.method.toUpperCase()
    if (method === 'POST' && lower.includes('/api/tw-stock/paper-portfolio/apply-decision')) counters.allowed_paper_apply_post_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/paper-portfolio/reset')) counters.allowed_paper_reset_post_count += 1
    if (method === 'POST' && lower.includes('/api/quick-trade')) counters.quick_trade_request_count += 1
    if (lower.includes('/api/agent/v1/quick-trade')) counters.quick_trade_request_count += 1
    if (lower.includes('/api/broker') || lower.includes('/broker/')) counters.broker_request_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/quant/ops/')) counters.provider_ops_post_count += 1
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && lower.includes('/api/tw-stock/monitor/config')) counters.monitor_config_write_count += 1
    if (method === 'POST' && lower.includes('/api/tw-stock/monitor/scan')) counters.monitor_scan_post_count += 1
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && lower.includes('/api/tw-stock/monitor/alerts')) counters.monitor_alerts_write_count += 1
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && (lower.includes('target_position') || lower.includes('target-weight') || lower.includes('target_weight'))) counters.target_position_write_count += 1
    if (method === 'POST' && lower.includes('/api/') && !allowedPosts.some(item => lower.includes(item))) counters.unexpected_post_count += 1
  }
  counters.forbidden_request_count = counters.quick_trade_request_count + counters.broker_request_count + counters.provider_ops_post_count + counters.monitor_config_write_count + counters.monitor_scan_post_count + counters.monitor_alerts_write_count + counters.target_position_write_count + counters.unexpected_post_count
  return counters
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1360, height: 920 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)
const requests = []
const consoleMessages = []
const pageErrors = []
page.on('request', request => requests.push({ method: request.method(), url: request.url() }))
page.on('console', msg => consoleMessages.push({ type: msg.type(), text: msg.text() }))
page.on('pageerror', err => pageErrors.push(err.message))

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'paper-e2e', nickname: 'Paper E2E', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger', app_version: 'e2e' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))

await page.route('**/api/indicator/backtest/tw-stock/templates**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, templates: [], items: [] })) }))

await page.route('**/api/tw-stock/paper-portfolio/latest-decision**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(latestDecision())) }))
await page.route('**/api/tw-stock/paper-portfolio/state**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(statePayload())) }))
await page.route('**/api/tw-stock/paper-portfolio/apply-runs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(applyRunsPayload())) }))
await page.route('**/api/tw-stock/paper-portfolio/apply-decision', async route => {
  applyPostCount += 1
  const body = JSON.parse(route.request().postData() || '{}')
  assert.equal(body.paper_order_intent_artifact_path, artifactPath)
  assert.ok(!Object.prototype.hasOwnProperty.call(body, 'paper_order_intent'))
  applied = true
  cash = 279657
  positions = [{ symbol: '1111', quantity: 10, avg_cost: 100.1425, cost_value: 1001.43, simulation_only: true }]
  const result = { ok: true, status: 'applied', apply_id: 'paper_apply_e2e_1', decision_id: decisionId, asof: '2026-06-18', cash_before: 200000, cash_after: cash, paper_executions: [{ paper_execution_id: 'trade-sell', side: 'sell', symbol: '9999', quantity: 1000 }, { paper_execution_id: 'trade-buy', side: 'buy', symbol: '1111', quantity: 10 }], skipped_actions: [{ status: 'skipped', reason: 'paper_skip', symbol: '2330' }], rejected_actions: [], positions_after: positions, simulation_only: true, trading: simFlags() }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(result)) })
})
await page.route('**/api/tw-stock/paper-portfolio/reset', async route => {
  resetPostCount += 1
  const body = JSON.parse(route.request().postData() || '{}')
  assert.ok(String(body.confirm_text || '').includes('重置模拟账户'))
  resetDone = true
  applied = false
  epoch += 1
  cash = 500000
  positions = []
  const result = { ok: true, status: 'reset', reset_id: 'paper_reset_e2e_1', previous_epoch: epoch - 1, new_epoch: epoch, archive_snapshot: {}, initial_cash: 500000, already_reset: false, simulation_only: true, trading: simFlags() }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(result)) })
})

await page.route('**/api/tw-stock/**', async route => {
  const method = route.request().method().toUpperCase()
  const url = route.request().url()
  if (url.includes('/api/tw-stock/paper-portfolio/')) return route.fallback()
  if (method !== 'GET') {
    return route.fulfill({ status: 405, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: false, status: 'unexpected_post', message: url })) })
  }
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', items: [], signals: [], rankings: [], simulation_only: true, trading: simFlags() })) })
})

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'paper-e2e-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'paper-e2e', nickname: 'Paper E2E' }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
}, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-testid="paper-portfolio-panel"]')
await page.waitForFunction(() => document.body.innerText.includes('模拟策略') && document.body.innerText.includes('应用到模拟账户'))
await page.screenshot({ path: path.join(outDir, '01_paper_panel_loaded.png'), fullPage: true })

await page.getByTestId('paper-apply-button').click()
await page.waitForSelector('[data-testid="paper-apply-confirm"]')
await page.locator('.ant-modal:visible').getByText('确认应用到模拟账户').last().click()
await page.waitForFunction(() => document.body.innerText.includes('应用结果') && document.body.innerText.includes('paper_apply_e2e_1'))
assert.equal(applyPostCount, 1)
await page.screenshot({ path: path.join(outDir, '02_paper_applied.png'), fullPage: true })

await page.getByTestId('paper-reset-button').click()
await page.waitForSelector('[data-testid="paper-reset-confirm"]')
await page.locator('.ant-modal:visible').getByText('确认重置模拟账户').last().click()
await page.waitForFunction(() => document.body.innerText.includes('重置结果') && document.body.innerText.includes('new_epoch 2'))
assert.equal(resetPostCount, 1)
await page.screenshot({ path: path.join(outDir, '03_paper_reset.png'), fullPage: true })

const networkAudit = networkCounters(requests)
const consoleAudit = { console_messages: consoleMessages, page_errors: pageErrors }
await writeFile(path.join(outDir, 'network_audit.json'), JSON.stringify(networkAudit, null, 2), 'utf8')
await writeFile(path.join(outDir, 'console_audit.json'), JSON.stringify(consoleAudit, null, 2), 'utf8')
console.log(JSON.stringify({ outDir, networkAudit, consoleAudit }, null, 2))

assert.equal(networkAudit.forbidden_request_count, 0)
assert.equal(networkAudit.quick_trade_request_count, 0)
assert.equal(networkAudit.broker_request_count, 0)
assert.equal(networkAudit.provider_ops_post_count, 0)
assert.equal(networkAudit.monitor_config_write_count, 0)
assert.equal(networkAudit.monitor_scan_post_count, 0)
assert.equal(networkAudit.monitor_alerts_write_count, 0)
assert.equal(networkAudit.target_position_write_count, 0)
assert.equal(networkAudit.allowed_paper_apply_post_count, 1)
assert.equal(networkAudit.allowed_paper_reset_post_count, 1)
assert.equal(pageErrors.length, 0)
assert.equal(resetDone, true)

await browser.close()
