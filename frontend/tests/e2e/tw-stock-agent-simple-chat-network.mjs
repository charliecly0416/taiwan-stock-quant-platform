import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_AGENT_BASE_URL || 'http://127.0.0.1:8000'
const artifactDir = process.env.TW_STOCK_AGENT_E2E_ARTIFACT_DIR || '/tmp/tw_agent_simple_chat_network'
const disclaimer = '仅供研究观察，不构成交易建议'

await mkdir(artifactDir, { recursive: true })

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: 'success', data }
}

function forbiddenReason (method, rawUrl) {
  const url = rawUrl.toLowerCase()
  if (url.includes('api.openai.com') || url.includes('chat/completions') || url.includes('openai_api_key')) return 'frontend_openai_direct'
  if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return ''
  if (url.includes('/api/quick-trade') || url.includes('/api/broker') || url.includes('/broker/')) return 'broker_quick_trade'
  if (url.includes('/order') || url.includes('order/submit') || url.includes('target_position') || url.includes('target-position') || url.includes('target_weight')) return 'order_or_target_position'
  if (url.includes('/api/tw-stock/monitor/config')) return 'monitor_config_write'
  if (url.includes('/api/tw-stock/monitor/scan')) return 'monitor_scan_post'
  if (url.includes('/api/tw-stock/monitor/alerts')) return 'monitor_alerts_write'
  if (url.includes('/api/tw-stock/quant/ops/') || url.includes('provider') || url.includes('accepted-latest') || url.includes('accepted_latest')) return 'provider_or_accepted_latest'
  return ''
}

function forbiddenPayloadReason (method, rawUrl, rawBody) {
  if (method !== 'POST') return ''
  const url = rawUrl.toLowerCase()
  if (!url.includes('/api/tw-stock/agent/simple-chat')) return ''
  let body = {}
  try {
    body = JSON.parse(rawBody || '{}')
  } catch (error) {
    return 'simple_chat_payload_invalid_json'
  }
  const allowedKeys = new Set(['question', 'symbol', 'maxItems', 'max_items'])
  for (const key of Object.keys(body)) {
    if (!allowedKeys.has(key)) return `simple_chat_unexpected_field:${key}`
    if (/target[_-]?position|target[_-]?weight|order|broker|quick[_-]?trade|provider|accepted[_-]?latest|monitor/i.test(key)) {
      return `simple_chat_forbidden_field:${key}`
    }
  }
  const controlValues = Object.entries(body)
    .filter(([key]) => key !== 'question')
    .map(([, value]) => String(value || ''))
    .join(' ')
  if (/target[_-]?position|target[_-]?weight|place order|submit order|broker|quick[_-]?trade|provider publish|accepted latest|monitor scan/i.test(controlValues)) {
    return 'simple_chat_forbidden_control_value'
  }
  return ''
}

function simpleChatPayload (question) {
  const q = String(question || '')
  const blocked = /下单|仓位|target_weight|target position|place orders/i.test(q)
  if (blocked) {
    return {
      ok: true,
      mode: 'blocked',
      intent: /target|仓位/i.test(q) ? 'target_position' : 'place_order',
      blocked: true,
      answer: '该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。',
      items: [],
      citations: [],
      warnings: ['blocked_research_boundary'],
      research_only_disclaimer: disclaimer,
      context_digest: { signal_asof: '2026-06-01', target_date: '2026-06-02', checksum: 'sha256:e2e' }
    }
  }
  return {
    ok: true,
    mode: 'disabled',
    intent: 'today_strategy',
    blocked: false,
    answer: '今天策略是只读研究排序和候选观察，不构成交易建议。',
    items: [{ symbol: '2330', rank: 1 }],
    citations: ['daily-prompt:manifest:e2e'],
    warnings: ['openai_disabled'],
    research_only_disclaimer: disclaimer,
    context_digest: {
      signal_asof: '2026-06-01',
      target_date: '2026-06-02',
      checksum: 'sha256:e2e-simple-chat-network',
      freshness_status: 'fresh'
    }
  }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const requests = []
const forbiddenRequests = []
const forbiddenPayloads = []
const failedResponses = []
const consoleMessages = []
const pageErrors = []
let simpleChatCount = 0

page.on('console', msg => consoleMessages.push({ type: msg.type(), text: msg.text() }))
page.on('pageerror', error => pageErrors.push(error.message))
page.on('request', request => {
  const method = request.method().toUpperCase()
  const url = request.url()
  const reason = forbiddenReason(method, url)
  const body = method === 'POST' ? request.postData() || '' : ''
  const payloadReason = forbiddenPayloadReason(method, url, body)
  const entry = { method, url, reason, payloadReason }
  requests.push(entry)
  if (reason) forbiddenRequests.push(entry)
  if (payloadReason) forbiddenPayloads.push(entry)
})
page.on('response', response => {
  if (response.status() >= 400) failedResponses.push({ status: response.status(), url: response.url() })
})

async function fulfillJson (route, data, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(apiResponse(data)) })
}

// Playwright applies the last matching route first. Register broad fallbacks first,
// then the specific Agent route that this audit is validating.
await page.route('**/api/**', route => fulfillJson(route, { ok: true, status: 'fixture' }))
await page.route('**/api/indicator/**', route => fulfillJson(route, []))
await page.route('**/api/tw-stock/**', route => fulfillJson(route, { ok: true, status: 'fixture', items: [] }))
await page.route('**/api/auth/info**', route => fulfillJson(route, { id: 1, username: 'agent-e2e', role: { permissions: ['dashboard'] } }))
await page.route('**/api/auth/security-config**', route => fulfillJson(route, { turnstile_enabled: false }))
await page.route('**/api/settings/brand-config**', route => fulfillJson(route, { app_name: 'QuantDinger' }))
await page.route('**/api/strategies/notifications/unread-count**', route => fulfillJson(route, { count: 0 }))
await page.route('**/api/policy/broker-market**', route => fulfillJson(route, { ok: true, policy: 'disabled_in_e2e' }))
await page.route('**/api/tw-stock/agent/context**', route => fulfillJson(route, { ok: true, status: 'fixture' }))
await page.route('**/api/tw-stock/agent/simple-chat**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  simpleChatCount += 1
  const body = JSON.parse(route.request().postData() || '{}')
  await fulfillJson(route, simpleChatPayload(body.question))
})

const seedAuth = () => {
  const expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000
  window.localStorage.setItem('Access-Token', JSON.stringify('agent-e2e-token'))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'agent-e2e', role: { permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify([{ id: 'default', permissionList: ['dashboard'] }]))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
}

await page.addInitScript(seedAuth)
await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.evaluate(seedAuth)
await page.waitForSelector('.tw-stock-agent-panel')
await page.waitForFunction(() => document.body.innerText.includes('策略解释助手'))

const agent = page.locator('.tw-stock-agent-panel')
await agent.locator('textarea').fill('今天策略是什么？')
await Promise.all([
  page.waitForResponse(response => response.url().includes('/api/tw-stock/agent/simple-chat') && response.status() === 200),
  agent.getByRole('button', { name: /发送|送出|Send/i }).click()
])
await page.waitForFunction(() => {
  const text = document.body.innerText
  return text.includes('回答') && text.includes('只读研究排序')
})

await agent.locator('textarea').fill('数据新鲜度如何？')
await Promise.all([
  page.waitForResponse(response => response.url().includes('/api/tw-stock/agent/simple-chat') && response.status() === 200),
  agent.getByRole('button', { name: /发送|送出|Send/i }).click()
])
await page.waitForFunction(() => {
  const text = document.body.innerText
  return text.includes('回答') && text.includes('只读研究排序')
})

await page.screenshot({ path: path.join(artifactDir, 'tw-stock-agent-simple-chat-network.png'), fullPage: true })

const networkAudit = {
  schema_version: 'tw_agent_simple_chat_network_audit.v1',
  base_url: baseUrl,
  request_count: requests.length,
  simple_chat_request_count: simpleChatCount,
  forbidden_request_count: forbiddenRequests.length,
  forbidden_requests: forbiddenRequests,
  forbidden_payload_count: forbiddenPayloads.length,
  forbidden_payloads: forbiddenPayloads,
  failed_response_count: failedResponses.length,
  failed_responses: failedResponses,
  monitor_config_write_count: forbiddenRequests.filter(item => item.reason === 'monitor_config_write').length,
  monitor_scan_post_count: forbiddenRequests.filter(item => item.reason === 'monitor_scan_post').length,
  monitor_alerts_write_count: forbiddenRequests.filter(item => item.reason === 'monitor_alerts_write').length,
  ops_dry_run_post_count: forbiddenRequests.filter(item => item.reason === 'provider_or_accepted_latest').length,
  frontend_openai_direct_request_count: forbiddenRequests.filter(item => item.reason === 'frontend_openai_direct').length,
  broker_quick_trade_order_request_count: forbiddenRequests.filter(item => ['broker_quick_trade', 'order_or_target_position'].includes(item.reason)).length
}
const consoleAudit = {
  schema_version: 'tw_agent_simple_chat_console_audit.v1',
  console_error_count: consoleMessages.filter(item => item.type === 'error').length,
  page_error_count: pageErrors.length,
  console_messages: consoleMessages,
  page_errors: pageErrors
}

await writeFile(path.join(artifactDir, 'network_audit.json'), JSON.stringify(networkAudit, null, 2))
await writeFile(path.join(artifactDir, 'console_audit.json'), JSON.stringify(consoleAudit, null, 2))

await browser.close()

assert.equal(networkAudit.simple_chat_request_count, 2)
assert.equal(networkAudit.forbidden_request_count, 0)
assert.equal(networkAudit.forbidden_payload_count, 0)
assert.equal(networkAudit.monitor_config_write_count, 0)
assert.equal(networkAudit.monitor_scan_post_count, 0)
assert.equal(networkAudit.monitor_alerts_write_count, 0)
assert.equal(networkAudit.ops_dry_run_post_count, 0)
assert.equal(networkAudit.frontend_openai_direct_request_count, 0)
assert.equal(networkAudit.broker_quick_trade_order_request_count, 0)
assert.equal(consoleAudit.page_error_count, 0)

console.log(`tw-stock-agent-simple-chat-network passed: ${JSON.stringify({ artifactDir, networkAudit, consoleAudit })}`)
