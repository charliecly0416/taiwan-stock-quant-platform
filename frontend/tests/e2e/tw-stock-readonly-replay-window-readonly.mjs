import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from '/tmp/travel-agent-e2e/node_modules/playwright/index.mjs'

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

function replayIndexPayload () {
  return {
    ok: true,
    schema_version: 'readonly_replay_window_index_d7_v1',
    readonly_only: true,
    production_trade_enabled: false,
    windows: [
      {
        window_key: '2026_ytd',
        window_type: 'fixed_standard',
        display_label: '固定 2026_ytd 标准窗口',
        model_id: 'e4_frozen_qlib_2023_2025_ltr',
        strategy_rule: 'top50_exit_one_worst_sell',
        start: '2026-01-01',
        end: '2026-05-07',
        checksum: { ok: true, checked_file_count: 5 }
      },
      {
        window_key: '20260102_20260507',
        window_type: 'generated_readonly',
        display_label: 'D6 非固定窗口 2026-01-02..2026-05-07',
        model_id: 'e4_frozen_qlib_2023_2025_ltr',
        strategy_rule: 'top50_exit_one_worst_sell',
        start: '2026-01-02',
        end: '2026-05-07',
        checksum: { ok: true, checked_file_count: 13 }
      }
    ],
    checksum: { ok: true, checked_file_count: 5 },
    sources: { manifest: 'data_tw/artifacts/readonly_replay_windows/d7/manifest.json' }
  }
}

function replayWindowPayload (url) {
  const params = new URL(url).searchParams
  const start = params.get('start') || '2026-01-01'
  const end = params.get('end') || '2026-05-07'
  const generated = start === '2026-01-02'
  return {
    ok: true,
    schema_version: 'readonly_replay_window_api_d7_v1',
    readonly_only: true,
    not_order: true,
    no_order_action: true,
    not_target_position: true,
    not_investment_advice: true,
    production_trade_enabled: false,
    model_id: 'e4_frozen_qlib_2023_2025_ltr',
    strategy_rule: 'top50_exit_one_worst_sell',
    window: { name: generated ? '20260102_20260507' : '2026_ytd', start, end },
    window_index: {
      window_key: generated ? '20260102_20260507' : '2026_ytd',
      window_type: generated ? 'generated_readonly' : 'fixed_standard',
      display_label: generated ? 'D6 非固定窗口 2026-01-02..2026-05-07' : '固定 2026_ytd 标准窗口'
    },
    validation: { ok: true, backend_window_validator_exists: true },
    summary: { final_equity: '1000000', fee_tax_adjusted_net_return: '0.01', action_count: '1' },
    generated_by: 'replay_execution_engine',
    decision_source: 'order_intent_artifact',
    execution_input_source: 'order_intent_artifact',
    checksum: { ok: true, checked_file_count: generated ? 13 : 5 },
    sources: {
      readonly_replay_manifest: generated
        ? 'data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json'
        : 'data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json',
      window_index_manifest: 'data_tw/artifacts/readonly_replay_windows/d7/manifest.json'
    },
    no_write_guarantees: {
      read_only_http_method: true,
      reads_indexed_audited_artifact_only: true,
      does_not_generate_replay_on_demand: true
    }
  }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const forbiddenRequests = []
const allRequests = []
const failedResponses = []
const consoleErrors = []
const pageErrors = []
const replayRequests = []

page.on('console', message => {
  if (message.type() === 'error') consoleErrors.push(message.text())
})
page.on('pageerror', error => pageErrors.push(String(error && (error.stack || error.message || error))))
page.on('request', request => {
  const method = request.method().toUpperCase()
  const url = request.url()
  allRequests.push({ method, url })
  if (url.toLowerCase().includes('/api/tw-stock/readonly-replay-window')) replayRequests.push({ method, url })
  const reason = classifyForbiddenRequest(method, url)
  if (reason) forbiddenRequests.push({ method, url, reason })
})
page.on('response', response => {
  if (response.status() >= 400) {
    failedResponses.push({ status: response.status(), url: response.url() })
  }
})

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'quantdinger', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))
await page.route('**/api/tw-stock/readonly-replay-window-index**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(replayIndexPayload())) })
})
await page.route('**/api/tw-stock/readonly-replay-window?**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(replayWindowPayload(route.request().url()))) })
})

const ok = (payload = {}) => JSON.stringify(apiResponse(payload))
for (const pattern of [
  '**/api/tw-stock/readonly-strategy-snapshot**',
  '**/api/tw-stock/ltr-readonly-explanation**',
  '**/api/tw-stock/ltr-optional-sim-strategies**',
  '**/api/tw-stock/rank-tech-cross/latest**',
  '**/api/tw-stock/rank-tech-cross/portfolio-replay**',
  '**/api/tw-stock/quant/signals/latest**',
  '**/api/tw-stock/quant/signals/health**',
  '**/api/tw-stock/quant/signals/rank-changes**',
  '**/api/tw-stock/quant/signals/runs**',
  '**/api/tw-stock/quant/ops/option-c/latest**',
  '**/api/tw-stock/quant/ops/option-c/scheduler**',
  '**/api/tw-stock/quant/ops/daily-auto-update/status**',
  '**/api/tw-stock/cross-analysis/latest**',
  '**/api/tw-stock/agent/context**',
  '**/api/tw-stock/sim/accounts**',
  '**/api/tw-stock/trends**',
  '**/api/tw-stock/monitor/config**',
  '**/api/tw-stock/monitor/history**',
  '**/api/tw-stock/monitor/alerts**',
  '**/api/tw-stock/monitor/scan-logs**',
  '**/api/indicator/kline**',
  '**/api/indicator/backtest/tw-stock/templates**'
]) {
  await page.route(pattern, route => route.fulfill({ status: 200, contentType: 'application/json', body: ok({ ok: true, items: [], strategies: [], methods: [] }) }))
}

await page.addInitScript(() => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'readonly-replay-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'quantdinger', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('lang', 'zh-CN')
})

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-testid="readonly-replay-window-panel"]')
await page.waitForFunction(() => document.body.innerText.includes('只读回放窗口') && document.body.innerText.includes('净收益'), null, { timeout: 15000 })

await page.screenshot({ path: path.join(artifactDir, 'readonly_replay_window_desktop_collapsed.png'), fullPage: true })
await page.getByText('查看回放窗口审计详情').click()
await page.waitForFunction(() => document.body.innerText.includes('window index') && document.body.innerText.includes('source manifest'), null, { timeout: 5000 })
await page.screenshot({ path: path.join(artifactDir, 'readonly_replay_window_desktop_expanded.png'), fullPage: true })
await page.setViewportSize({ width: 390, height: 900 })
await page.screenshot({ path: path.join(artifactDir, 'readonly_replay_window_mobile.png'), fullPage: true })

const panelText = await page.getByTestId('readonly-replay-window-panel').innerText()
for (const required of ['只读回放窗口', 'D4 固定标准窗口', '后端校验', '净收益', '最大回撤', '交易次数', '手续费/税费', 'window index', 'checksum', 'replay_execution_engine']) {
  assert.ok(panelText.includes(required), `missing replay window text: ${required}`)
}
for (const forbidden of ['下单', '买入指令', '卖出指令', '目标仓位', '自动交易', '一键交易', '券商同步', '保证收益', '胜率承诺', '上涨概率']) {
  assert.ok(!panelText.includes(forbidden), `forbidden readonly text: ${forbidden}`)
}

assert.ok(replayRequests.some(row => row.url.includes('/readonly-replay-window-index')), 'missing replay index request')
assert.ok(replayRequests.some(row => row.url.includes('/readonly-replay-window?')), 'missing replay detail request')
const networkAudit = buildNetworkAudit('readonly_replay_window', allRequests, forbiddenRequests, failedResponses)
fs.writeFileSync(path.join(artifactDir, 'readonly_replay_window_network_audit.json'), JSON.stringify(networkAudit, null, 2))
fs.writeFileSync(path.join(artifactDir, 'network_audit_readonly_replay_window.json'), JSON.stringify(networkAudit, null, 2))

assert.equal(forbiddenRequests.length, 0, JSON.stringify(forbiddenRequests, null, 2))
assert.equal(consoleErrors.length, 0, consoleErrors.join('\n'))
assert.equal(pageErrors.length, 0, pageErrors.join('\n'))

await browser.close()
console.log('tw-stock readonly replay window e2e passed')
