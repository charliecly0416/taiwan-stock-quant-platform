import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '/tmp/travel-agent-e2e/node_modules/playwright/index.mjs'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const outDir = process.env.TW_STOCK_PHASE_YZ3_E2E_DIR || '/tmp/quantdinger_tw_phase_yz3_e2e'
await mkdir(outDir, { recursive: true })

function apiResponse (data) { return { code: data && data.ok === false ? 0 : 1, msg: data && data.ok === false ? (data.message || data.status || 'mock_error') : 'success', data } }
function isWriteMethod (method) { return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) }
function forbiddenReason (method, rawUrl) {
  const url = rawUrl.toLowerCase()
  if (url.includes('/api/tw-stock/phase-yz/productization-status') && method !== 'GET') return 'phase_yz_write'
  if (url.includes('/api/tw-stock/paper-portfolio/apply-decision') && method === 'POST') return 'paper_apply_write'
  if (url.includes('/api/tw-stock/paper-portfolio/reset') && method === 'POST') return 'paper_reset_write'
  if (url.includes('/api/tw-stock/monitor/config') && isWriteMethod(method)) return 'monitor_config_write'
  if (url.includes('/api/tw-stock/monitor/scan') && method === 'POST') return 'monitor_scan_post'
  if (url.includes('/api/tw-stock/monitor/alerts') && isWriteMethod(method)) return 'monitor_alerts_write'
  if (url.includes('/api/quick-trade/') || url.includes('/api/broker/') || url.includes('/orders')) return 'broker_quick_trade_orders'
  if (url.includes('accepted_latest') || url.includes('accepted-latest') || url.includes('provider_publish') || url.includes('provider-publish') || url.includes('provider/refresh')) return 'ops_provider_publish_refresh_accepted_latest'
  if (isWriteMethod(method) && (url.includes('target_position') || url.includes('target-weight') || url.includes('target_weight'))) return 'target_position_write'
  return ''
}
function networkAudit (requests, readonlyReplayWindowRequests) {
  const forbidden = requests.map(row => ({ ...row, reason: forbiddenReason(row.method, row.url) })).filter(row => row.reason)
  const count = reason => forbidden.filter(row => row.reason === reason).length
  return {
    forbidden_requests: forbidden,
    forbidden_request_count: forbidden.length,
    monitor_config_write_count: count('monitor_config_write'),
    monitor_scan_post_count: count('monitor_scan_post'),
    monitor_alerts_write_count: count('monitor_alerts_write'),
    broker_quick_trade_orders_request_count: count('broker_quick_trade_orders'),
    ops_provider_publish_refresh_accepted_latest_request_count: count('ops_provider_publish_refresh_accepted_latest'),
    paper_apply_write_count: count('paper_apply_write'),
    paper_reset_write_count: count('paper_reset_write'),
    phase_yz_write_count: count('phase_yz_write'),
    target_position_write_count: count('target_position_write'),
    readonly_replay_window_requests: readonlyReplayWindowRequests
  }
}
const yzPending = {
  ok: true,
  schema_version: 'yz3_productization_status_v1',
  signal_asof: '2026-06-19',
  models: [
    { model_id: 'e4_frozen_qlib_2018_2022', display_name: 'Model A', frontend_selectable: true, production_default: false },
    { model_id: 'e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025', display_name: 'Model B', frontend_selectable: true, production_default: true }
  ],
  production_strategies: [{ strategy_rule_id: 'top50_exit_one_worst_sell', display_name: 'Top50 调出最弱一档（模拟策略）', frontend_selectable: true, production_default: true }],
  selected_model_id: 'e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025',
  selected_strategy_rule_id: 'top50_exit_one_worst_sell',
  execution_price_mode: 'next_open',
  execution_price_status: 'execution_price_unavailable',
  execution_price_message: '成交口径：次一交易日开盘价。2026-06-22 行情暂不可用，等待下一轮数据更新。策略信号已生成，模拟应用将在成交价可用后开放。',
  execution_price_readiness: { target_next_trading_day: '2026-06-22' },
  paper_apply_allowed: false,
  paper_apply_blocked_reason: 'next_open_unavailable',
  safety_flags: { readonly_only: true, no_broker_order: true, no_quick_trade: true, no_provider_publish: true, no_accepted_latest_switch: true, no_monitor_write: true, old_models_exposed: false, old_strategies_exposed: false }
}
const decision = {
  ok: true,
  status: 'ok',
  asof: '2026-06-19',
  model_id: 'e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025',
  strategy_rule: 'top50_exit_one_worst_sell',
  decision_id: 'yz3_pending_decision',
  paper_account_id: 'tw_sim_pending',
  paper_account_epoch: 1,
  input_checksum: 'sha256:pending',
  paper_order_intent_artifact_path: 'mock/pending/paper_order_intent.json',
  preview: { cash_before: 1000000 },
  intent: { actions: [] }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)
const requests = []
const readonlyReplayWindowRequests = []
const consoleErrors = []
const pageErrors = []
page.on('request', request => {
  const row = { method: request.method().toUpperCase(), url: request.url() }
  requests.push(row)
  if (row.url.includes('/api/tw-stock/readonly-replay-window?')) readonlyReplayWindowRequests.push(row)
})
page.on('console', msg => { if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) consoleErrors.push(msg.text()) })
page.on('pageerror', err => pageErrors.push(err.message))

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'yz3-e2e', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, items: [] })) }))
await page.route('**/api/indicator/kline**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse([])) }))
await page.route('**/api/tw-stock/phase-yz/productization-status**', route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(yzPending)) })
})
await page.route('**/api/tw-stock/paper-portfolio/latest-decision**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(decision)) }))
await page.route('**/api/tw-stock/paper-portfolio/state**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, paper_account: { account_uid: 'tw_sim_pending', cash: 1000000, initial_cash: 1000000, paper_account_epoch: 1 }, positions: [] })) }))
await page.route('**/api/tw-stock/paper-portfolio/apply-runs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, items: [] })) }))
await page.route('**/api/tw-stock/readonly-replay-window-index**', route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({
    ok: true,
    schema_version: 'readonly_replay_window_index_d7_v1',
    readonly_only: true,
    production_trade_enabled: false,
    windows: [{
      window_key: '2026_ytd_clean',
      window_type: 'fixed_standard',
      display_label: 'clean E4 2026_ytd',
      model_id: 'e4_frozen_qlib_2018_2022',
      strategy_rule: 'top50_exit_one_worst_sell',
      start: '2026-01-01',
      end: '2026-05-07'
    }]
  })) })
})
await page.route('**/api/tw-stock/readonly-replay-window?**', route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  const url = new URL(route.request().url())
  assert.equal(url.searchParams.get('model_id'), 'e4_frozen_qlib_2018_2022')
  assert.equal(url.searchParams.get('strategy_rule'), 'top50_exit_one_worst_sell')
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({
    ok: true,
    schema_version: 'readonly_replay_window_api_d7r_v1',
    readonly_only: true,
    production_trade_enabled: false,
    model_id: 'e4_frozen_qlib_2018_2022',
    strategy_rule: 'top50_exit_one_worst_sell',
    window: { start: '2026-01-01', end: '2026-05-07' },
    summary: {},
    checksum: { ok: true },
    no_write_guarantees: { read_only_http_method: true }
  })) })
})
await page.route('**/api/tw-stock/**', route => {
  const url = route.request().url()
  if (url.includes('/api/tw-stock/phase-yz/productization-status') || url.includes('/api/tw-stock/paper-portfolio/') || url.includes('/api/tw-stock/readonly-replay-window')) return route.fallback()
  if (route.request().method().toUpperCase() !== 'GET') return route.fulfill({ status: 405, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: false, status: 'unexpected_write' })) })
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, items: [], signals: [], entered: [], exited: [], stayed: [], top_gainers: [], top_decliners: [], watch_candidates: [], rankings: [], windows: [] })) })
})
await page.addInitScript(() => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'yz3-e2e-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'yz3-e2e', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('lang', 'zh-CN')
})

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-testid="phase-yz-productization-card"]')
await page.waitForSelector('[data-testid="phase-yz-execution-price-pending"]')
await page.waitForSelector('[data-testid="paper-portfolio-panel"]')
await page.waitForSelector('[data-testid="paper-apply-blocked-by-execution-price"]')
const bodyText = await page.locator('body').innerText()
assert.ok(bodyText.includes('成交口径：次一交易日开盘价'))
assert.ok(bodyText.includes('2026-06-22 行情暂不可用，等待下一轮数据更新'))
assert.ok(!bodyText.includes('2026-06-18 行情暂不可用'))
assert.ok(bodyText.includes('策略信号已生成，模拟应用将在成交价可用后开放'))
assert.ok(bodyText.includes('e4_frozen_qlib_2018_2022'))
assert.ok(bodyText.includes('e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025'))
assert.ok(bodyText.includes('top50_exit_one_worst_sell'))
assert.equal(await page.getByTestId('phase-yz-paper-apply-disabled').isDisabled(), true)
assert.equal(await page.getByTestId('paper-apply-button').isDisabled(), true)
await page.screenshot({ path: path.join(outDir, 'phase_yz3_pending.png'), fullPage: true })

const audit = networkAudit(requests, readonlyReplayWindowRequests)
const consoleAudit = { console_errors: consoleErrors, page_errors: pageErrors }
assert.ok(readonlyReplayWindowRequests.length >= 1, 'expected clean readonly replay window detail request after index')
for (const req of readonlyReplayWindowRequests) {
  assert.ok(!req.url.includes('e4_frozen_qlib_2023_2025_ltr'), `old replay model leaked into request: ${req.url}`)
  assert.ok(req.url.includes('e4_frozen_qlib_2018_2022'), `clean replay model missing from request: ${req.url}`)
}
await writeFile(path.join(outDir, 'network_audit.json'), JSON.stringify(audit, null, 2), 'utf8')
await writeFile(path.join(outDir, 'console_audit.json'), JSON.stringify(consoleAudit, null, 2), 'utf8')
console.log(JSON.stringify({ outDir, audit, consoleAudit }, null, 2))
assert.equal(audit.forbidden_request_count, 0)
assert.equal(audit.monitor_config_write_count, 0)
assert.equal(audit.monitor_scan_post_count, 0)
assert.equal(audit.monitor_alerts_write_count, 0)
assert.equal(audit.broker_quick_trade_orders_request_count, 0)
assert.equal(audit.ops_provider_publish_refresh_accepted_latest_request_count, 0)
assert.equal(audit.paper_apply_write_count, 0)
assert.equal(audit.paper_reset_write_count, 0)
assert.equal(audit.phase_yz_write_count, 0)
assert.equal(audit.target_position_write_count, 0)
assert.equal(consoleErrors.length, 0)
assert.equal(pageErrors.length, 0)
await browser.close()
