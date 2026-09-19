import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const artifactDir = path.resolve(process.cwd(), '../data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly')
fs.mkdirSync(artifactDir, { recursive: true })


function isWriteMethod (method) {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
}

function classifyForbiddenRequest (method, rawUrl) {
  const url = rawUrl.toLowerCase()
  if (url.includes('/api/tw-stock/rank-tech-cross/portfolio-replay') && isWriteMethod(method)) return 'replay_strategy_write'
  if (url.includes('/api/indicator/backtest') && !url.includes('/api/indicator/backtest/tw-stock/templates') && isWriteMethod(method)) return 'replay_strategy_write'
  if (url.includes('/api/tw-stock/readonly-replay-window') && method !== 'GET') return 'replay_strategy_write'
  if (url.includes('/api/tw-stock/readonly-strategy-snapshot') && method !== 'GET') return 'replay_strategy_write'
  if (url.includes('/api/tw-stock/monitor/scan') && method === 'POST') return 'monitor_scan_post'
  if (url.includes('/api/tw-stock/monitor/config') && isWriteMethod(method)) return 'monitor_config_write'
  if (url.includes('/api/tw-stock/monitor/alerts') && isWriteMethod(method)) return 'monitor_alerts_write'
  if (url.includes('/api/quick-trade/') || url.includes('/api/broker/') || url.includes('/orders')) return 'broker_quick_trade_orders'
  if (url.includes('accepted_latest') || url.includes('accepted-latest') || url.includes('provider_publish') || url.includes('provider-publish') || url.includes('provider/refresh')) return 'ops_provider_publish_refresh_accepted_latest'
  return ''
}

function buildNetworkAudit (scenario, allRequests, forbiddenRequests, failedResponses) {
  const count = reason => forbiddenRequests.filter(row => row.reason === reason).length
  return {
    scenario,
    all_requests: allRequests,
    forbidden_requests: forbiddenRequests,
    forbidden_request_count: forbiddenRequests.length,
    monitor_config_write_count: count('monitor_config_write'),
    monitor_scan_post_count: count('monitor_scan_post'),
    monitor_alerts_write_count: count('monitor_alerts_write'),
    ops_provider_publish_refresh_accepted_latest_request_count: count('ops_provider_publish_refresh_accepted_latest'),
    replay_strategy_write_count: count('replay_strategy_write'),
    broker_quick_trade_orders_request_count: count('broker_quick_trade_orders'),
    failed_responses: failedResponses,
    failed_response_count: failedResponses.length
  }
}

function apiResponse (data) {
  return { code: 1, msg: 'success', data }
}

function readonlyStrategySnapshotPayload () {
  return {
    ok: true,
    schema_version: 'readonly_strategy_snapshot_api_r14_v1',
    asof: '2026-06-16',
    readonly_only: true,
    not_order: true,
    no_order_action: true,
    not_target_position: true,
    not_investment_advice: true,
    production_trade_enabled: false,
    manifest: {
      asof: '2026-06-16',
      artifact_type: 'readonly_strategy_snapshot',
      strategy_rule: 'top50_exit_one_worst_sell'
    },
    snapshot: {
      asof: '2026-06-16',
      data_asof: '2026-05-07',
      signal_asof: '2026-05-07',
      model_id: 'e4_frozen_qlib_2023_2025_ltr',
      base_model_id: 'frozen_qlib_2018_2022',
      strategy_rule: 'top50_exit_one_worst_sell',
      candidate_boundary: 'qlib_top50',
      ranking_source: 'ltr_rerank_within_qlib_top50',
      display_role: 'primary_readonly_candidate',
      top_candidates: [
        { symbol: 'TW1711', candidate_rank: 5, score_rank: 1, full_qlib_rank: 5 },
        { symbol: 'TW1785', candidate_rank: 23, score_rank: 2, full_qlib_rank: 23 },
        { symbol: 'TW3044', candidate_rank: 17, score_rank: 3, full_qlib_rank: 17 }
      ],
      exit_candidates: [
        { symbol: 'TW2337', full_qlib_rank: null, in_qlib_top50_candidate: false },
        { symbol: 'TW4919', full_qlib_rank: null, in_qlib_top50_candidate: false }
      ],
      hold_candidates: [
        { symbol: 'TW1711', full_qlib_rank: 5, in_qlib_top50_candidate: true }
      ]
    },
    validation: { ok: true, status: 'pass', manifest: 'data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/validation_report.json' },
    checksum: { ok: true, checked_file_count: 8, manifest: 'data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/checksum_manifest.json' },
    sources: { manifest: 'data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json' }
  }
}

const auth = {
  userinfo: { id: 1, username: 'quantdinger', role: { id: 'default', permissions: ['dashboard'] } }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const forbiddenRequests = []
const allRequests = []
const failedResponses = []
const consoleErrors = []
const pageErrors = []
const requests = []

page.on('console', message => {
  if (message.type() === 'error' && !message.text().includes('Failed to load resource')) consoleErrors.push(message.text())
})
page.on('pageerror', error => pageErrors.push(String(error && (error.stack || error.message || error))))
page.on('request', request => {
  const method = request.method().toUpperCase()
  const url = request.url()
  allRequests.push({ method, url })
  const reason = classifyForbiddenRequest(method, url)
  if (reason) forbiddenRequests.push({ method, url, reason })
})
page.on('response', response => {
  if (response.status() >= 400) {
    failedResponses.push({ status: response.status(), url: response.url() })
  }
})

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: auth.userinfo && auth.userinfo.id || 1, username: auth.userinfo && auth.userinfo.username || 'quantdinger', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))

await page.route('**/api/tw-stock/readonly-strategy-snapshot**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  const url = new URL(route.request().url())
  const asof = url.pathname.split('/').pop()
  const payload = readonlyStrategySnapshotPayload()
  if (asof && asof !== 'readonly-strategy-snapshot') payload.asof = asof
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(payload)) })
})
await page.route('**/api/tw-stock/readonly-replay-window-index**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, readonly_only: true, windows: [], checksum: { ok: true }, sources: { manifest: 'mock' } })) })
})
await page.route('**/api/tw-stock/readonly-replay-window**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, readonly_only: true, model_id: 'e4_frozen_qlib_2023_2025_ltr', strategy_rule: 'top50_exit_one_worst_sell', window: { start: '2026-01-01', end: '2026-05-07' }, summary: { fee_tax_adjusted_net_return: '0.01', action_count: '1' }, checksum: { ok: true }, sources: { readonly_replay_manifest: 'mock' }, validation: { ok: true } })) })
})
await page.route('**/api/tw-stock/ltr-readonly-explanation**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, methods: [] })) }))
await page.route('**/api/tw-stock/ltr-optional-sim-strategies**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, strategies: [] })) }))
await page.route('**/api/tw-stock/rank-tech-cross/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-16' } })) }))
await page.route('**/api/tw-stock/rank-tech-cross/portfolio-replay**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, simulation_only: true, persist: false, trading: { connects_to_broker: false } })) }))
await page.route('**/api/tw-stock/quant/signals/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', bucket: 'top30', signals: [] })) }))
await page.route('**/api/tw-stock/quant/signals/health**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', latest: { exists: true, asof: '2026-06-16' }, freshness: {}, runs: {}, dataAvailability: {} })) }))
await page.route('**/api/tw-stock/quant/signals/rank-changes**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, entered: [], exited: [], stayed: [], top_gainers: [], top_decliners: [], watch_candidates: [], summary: {} })) }))
await page.route('**/api/tw-stock/quant/signals/runs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, job: null })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/scheduler**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, enabled: false })) }))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, latest_status: 'accepted', latest_asof: '2026-06-16', trading: { orders_enabled: false, connects_to_broker: false } })) }))
await page.route('**/api/tw-stock/cross-analysis/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-16' }, freshness: { warnings: [] } })) }))
await page.route('**/api/tw-stock/agent/context**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ qlib: { asof: '2026-06-16' }, freshness: { status: 'accepted' }, top30_preview: [] })) }))
await page.route('**/api/tw-stock/sim/accounts**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/trends**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ name: 'default', symbols: ['2330'], limit_bars: 120, refresh_interval_sec: 0, enabled: false })) }))
await page.route('**/api/tw-stock/monitor/history**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/alerts**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/scan-logs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ health: { status: 'ok' } })) }))
await page.route('**/api/indicator/kline**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse([])) }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))

await page.addInitScript(() => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'readonly-snapshot-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'quantdinger', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('lang', 'zh-CN')
})

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-testid="readonly-strategy-snapshot-panel"]')
try {
  await page.waitForFunction(() => document.body.innerText.includes('策略快照') && document.body.innerText.includes('调入候选') && document.body.innerText.includes('调出观察'), null, { timeout: 15000 })
} catch (error) {
  const diagnostic = await page.evaluate(() => ({
    href: window.location.href,
    panel: document.querySelector('[data-testid="readonly-strategy-snapshot-panel"]')?.innerText || '',
    body: document.body.innerText.slice(0, 2000)
  }))
  console.error('readonly snapshot e2e diagnostic:', JSON.stringify({ diagnostic, requests, consoleErrors, pageErrors }, null, 2))
  throw error
}

await page.screenshot({ path: path.join(artifactDir, 'readonly_strategy_snapshot_desktop_collapsed.png'), fullPage: true })
await page.getByText('查看策略快照审计详情').click()
await page.waitForFunction(() => document.body.innerText.includes('source manifest') && document.body.innerText.includes('checked files'), null, { timeout: 5000 })
await page.screenshot({ path: path.join(artifactDir, 'readonly_strategy_snapshot_desktop_expanded.png'), fullPage: true })
await page.setViewportSize({ width: 390, height: 900 })
await page.screenshot({ path: path.join(artifactDir, 'readonly_strategy_snapshot_mobile.png'), fullPage: true })

const panelText = await page.getByTestId('readonly-strategy-snapshot-panel').innerText()
for (const required of ['策略快照', '只读候选', '研究排名', '调入候选', '调出观察', '数据日期', '模型', '审计状态', 'source manifest', 'TW1711', 'TW2337']) {
  assert.ok(panelText.includes(required), `missing readonly snapshot text: ${required}`)
}
for (const forbidden of ['下单', '买入指令', '卖出指令', '目标仓位', '自动交易', '一键交易', '券商同步', '保证收益', '胜率承诺']) {
  assert.ok(!panelText.includes(forbidden), `forbidden readonly text: ${forbidden}`)
}

const networkAudit = buildNetworkAudit('readonly_strategy_snapshot', allRequests, forbiddenRequests, failedResponses)
fs.writeFileSync(path.join(artifactDir, 'readonly_strategy_snapshot_network_audit.json'), JSON.stringify(networkAudit, null, 2))
fs.writeFileSync(path.join(artifactDir, 'network_audit_readonly_strategy_snapshot.json'), JSON.stringify(networkAudit, null, 2))

assert.equal(forbiddenRequests.length, 0, JSON.stringify(forbiddenRequests, null, 2))
assert.equal(consoleErrors.length, 0, consoleErrors.join('\n'))
assert.equal(pageErrors.length, 0, pageErrors.join('\n'))

await browser.close()
console.log('tw-stock readonly strategy snapshot e2e passed')
