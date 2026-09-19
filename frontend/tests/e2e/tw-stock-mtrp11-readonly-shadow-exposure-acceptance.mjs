import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const artifactDir = process.env.MTRP11_ACCEPTANCE_ARTIFACT_DIR || path.resolve(process.cwd(), 'data_tw/ops/mtrp11_readonly_acceptance')

await mkdir(artifactDir, { recursive: true })

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.message ? data.message : 'success', data }
}

function tradingFlags () {
  return {
    orders_enabled: false,
    connects_to_broker: false,
    writes_orders: false,
    writes_positions: false,
    research_signal_not_order: true
  }
}

function isWriteMethod (method) {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
}

function classifyRequest (method, rawUrl, postData = '') {
  const url = String(rawUrl || '').toLowerCase()
  const body = String(postData || '').toLowerCase()
  if (url.includes('api.openai.com') || url.includes('chat/completions') || url.includes('openai_api_key') || url.includes('openai-api-key')) return 'frontend_openai_direct'
  if (method === 'POST' && url.includes('/api/tw-stock/agent/simple-chat')) {
    if (body.includes('target') || body.includes('target_position') || body.includes('target_weight') || body.includes('order') || body.includes('broker') || body.includes('provider') || body.includes('latest') || body.includes('quantity')) return 'agent_simple_chat_forbidden_payload'
    return ''
  }
  if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return ''
  if (url.includes('/api/tw-stock/monitor/config')) return 'monitor_config_write'
  if (url.includes('/api/tw-stock/monitor/scan')) return 'monitor_scan_post'
  if (url.includes('/api/tw-stock/monitor/alerts')) return 'monitor_alerts_write'
  if (url.includes('/api/tw-stock/quant/ops/') || url.includes('provider') || url.includes('accepted-latest') || url.includes('accepted_latest') || url.includes('publish') || url.includes('refresh')) return 'ops_dry_run_or_provider_latest'
  if (url.includes('/api/quick-trade') || url.includes('/api/broker') || url.includes('/broker/') || url.includes('/orders') || url.includes('place-order') || url.includes('submit-order') || url.includes('target-position') || url.includes('target_position') || url.includes('target-weight') || url.includes('target_weight')) return 'broker_quick_trade_order'
  if (isWriteMethod(method)) return 'unexpected_write_request'
  return ''
}

function currentStrategyContextPayload () {
  return {
    ok: true,
    status: 'ready',
    signal_asof: '2026-06-18',
    target_trade_date: '2026-06-19',
    default_model_id: 'e4_frozen_qlib_2018_2022',
    display_model_id: 'e4_frozen_qlib_2023_2025_ltr',
    strategy_rule: 'top50_exit_one_worst_sell',
    ranking_source: 'ltr_rerank_within_qlib_top50',
    candidate_boundary: 'qlib_top50',
    qlib_top50_count: 50,
    qlib_top150_count: 150,
    ltr_top50_count: 50,
    ltr_top_symbol: '2330',
    top_ltr_symbol: '2330',
    trading: tradingFlags()
  }
}

function readonlyShadowExposurePayload () {
  return {
    ok: true,
    schema_version: 'readonly_shadow_exposure.v1',
    strategy_candidate: 'top50_hold_rank_buffer_100',
    baseline_strategy: 'top50_exit_one_worst_sell',
    readonly_only: true,
    simulation_only: true,
    not_order: true,
    not_target_position: true,
    not_investment_advice: true,
    production_allowed: false,
    production_ready: false,
    default_switch_allowed: false,
    paper_apply_allowed: false,
    row_count: 3,
    source_manifest: 'fixture/mtrp8/readonly_shadow_exposure/manifest.json',
    dates: {
      covered_dates: ['2026-06-15', '2026-06-16', '2026-06-17'],
      covered_shadow_signal_days: 3
    },
    gate: {
      ok: true,
      status: 'pass',
      validator: { verdict: 'PASS_MTRP11_FIXTURE_READONLY' }
    },
    rows: [
      { signal_date: '2026-06-15', execution_date: '2026-06-16', display_status: 'readonly_shadow_observation_only', candidate_minus_baseline_equity: 1250.25 },
      { signal_date: '2026-06-16', execution_date: '2026-06-17', display_status: 'readonly_shadow_observation_only', candidate_minus_baseline_equity: -340.5 },
      { signal_date: '2026-06-17', execution_date: '2026-06-18', display_status: 'readonly_shadow_observation_only', candidate_minus_baseline_equity: 880.0 }
    ],
    open_blockers: [
      { blocker: 'mtrp11_acceptance_required', status: 'open', required_next_step: 'readonly_acceptance_and_safety_review' }
    ],
    citations: [
      { citation_key: 'readonly_exposure_index', artifact_type: 'csv', path: 'fixture/readonly_exposure_index.csv' },
      { citation_key: 'shadow_review_gate', artifact_type: 'csv', path: 'fixture/shadow_review_gate.csv' }
    ]
  }
}

function readonlyStrategySnapshotPayload () {
  return {
    ok: true,
    readonly_only: true,
    production_trade_enabled: false,
    not_order: true,
    no_order_action: true,
    not_target_position: true,
    not_investment_advice: true,
    asof: '2026-06-18',
    manifest: { schema_version: 'readonly_strategy_snapshot.v1', snapshot: 'fixture/readonly_strategy_snapshot/manifest.json' },
    snapshot: {
      asof: '2026-06-18',
      data_asof: '2026-06-18',
      signal_asof: '2026-06-18',
      model_id: 'e4_frozen_qlib_2023_2025_ltr',
      base_model_id: 'e4_frozen_qlib_2018_2022',
      strategy_rule: 'top50_exit_one_worst_sell',
      ranking_source: 'ltr_rerank_within_qlib_top50',
      top_candidates: [
        { symbol: '2330', stock_name: '台积电', candidate_rank: 1, score_rank: 1, full_qlib_rank: 2 },
        { symbol: '2317', stock_name: '鸿海', candidate_rank: 3, score_rank: 2, full_qlib_rank: 8 },
        { symbol: '2454', stock_name: '联发科', candidate_rank: 7, score_rank: 3, full_qlib_rank: 16 }
      ],
      exit_candidates: [{ symbol: '2357', stock_name: '华硕', full_qlib_rank: 67, in_qlib_top50_candidate: false }]
    },
    validation: { ok: true, status: 'pass' },
    checksum: { ok: true, checked_file_count: 8 },
    sources: { manifest: 'fixture/readonly_strategy_snapshot/manifest.json' }
  }
}

function replayIndexPayload () {
  return {
    ok: true,
    readonly_only: true,
    windows: [
      { window_key: '2026_ytd', display_label: '2026 年初至今', window_type: 'generated_readonly' },
      { window_key: '2025_full', display_label: '2025 全年', window_type: 'fixed_standard' }
    ],
    sources: { manifest: 'fixture/replay/window_index.json' }
  }
}

function replayWindowPayload () {
  return {
    ok: true,
    readonly_only: true,
    coverage_status: '可用',
    model_id: 'e4_frozen_qlib_2023_2025_ltr',
    strategy_rule: 'top50_exit_one_worst_sell',
    generated_by: 'generated_readonly',
    decision_source: 'fixture',
    schema_version: 'readonly_replay_window.v1',
    run_id: 'replay-fixture-001',
    window: { name: '2026 年初至今', start: '2026-01-02', end: '2026-06-18' },
    summary: {
      fee_tax_adjusted_net_return: 0.0834,
      max_drawdown: -0.041,
      action_count: 12,
      fee_tax_total: 1288,
      final_equity: 1083400,
      turnover_proxy_by_notional_over_avg_equity: 1.72
    },
    checksum: { ok: true, checked_file_count: 6 },
    sources: { readonly_replay_manifest: 'fixture/replay/manifest.json', window_index_manifest: 'fixture/replay/index.json' }
  }
}

function paperLatestDecision () {
  return {
    ok: true,
    status: 'ok',
    asof: '2026-06-18',
    model_id: 'e4_frozen_qlib_2023_2025_ltr',
    strategy_rule: 'top50_exit_one_worst_sell',
    decision_id: 'paper-decision-mtrp11',
    paper_account_id: 'paper-mtrp11',
    paper_account_epoch: 7,
    input_checksum: 'sha256:mtrp11-paper-fixture',
    paper_order_intent_artifact_path: 'fixture/paper/order_intent.json',
    preview: { cash_before: 500000, readonly_preview_only: true },
    intent: {
      actions: [
        { action_type: 'paper_sell_intent', instrument: 'TW2357', symbol: '2357', quantity: 1000, reason: 'outside_top50_review', estimated_reference_price: 342, applicability: 'applicable' },
        { action_type: 'paper_buy_intent', instrument: 'TW2330', symbol: '2330', quantity: 100, reason: 'top_ltr_candidate', estimated_reference_price: 920, applicability: 'applicable' }
      ]
    },
    trading: tradingFlags(),
    simulation_only: true
  }
}

function paperState () {
  return {
    ok: true,
    paper_account: { account_uid: 'paper-mtrp11', cash: 500000, initial_cash: 500000, paper_account_epoch: 7, simulation_only: true },
    positions: [{ symbol: '2357', quantity: 1000, avg_cost: 320 }],
    trading: tradingFlags()
  }
}

function simpleChatPayload () {
  return {
    ok: true,
    mode: 'disabled',
    blocked: false,
    answer: '模拟账户暂不能应用，因为等待目标交易日开盘价。该回答只解释策略工作台状态，不构成交易建议。',
    items: [{ symbol: '2330', qlib_rank: 1, qlib_score: 0.58, human_action: '人工复盘' }],
    citations: ['fixture:daily_prompt'],
    warnings: ['readonly_fixture'],
    invoked_skills: [{ name: 'tw-stock-research-context-analyst', status: 'readonly' }],
    research_only_disclaimer: '仅供研究观察，不构成交易建议；不连接券商，不提交真实订单。',
    context_digest: { signal_asof: '2026-06-18', target_date: '2026-06-19', checksum: 'sha256:mtrp11-agent-fixture', freshness_status: 'accepted' }
  }
}

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
const page = await context.newPage()
page.setDefaultTimeout(60000)

const allRequests = []
const forbiddenRequests = []
const suspiciousRequests = []
const failedResponses = []
const consoleMessages = []
const consoleErrors = []
const pageErrors = []
const simpleChatPayloads = []
let simpleChatCount = 0
let shadowExposureGetCount = 0

page.on('console', message => {
  const entry = { type: message.type(), text: message.text() }
  consoleMessages.push(entry)
  if (message.type() === 'error' && !message.text().includes('Failed to load resource')) consoleErrors.push(entry)
})
page.on('pageerror', error => pageErrors.push(String(error && (error.stack || error.message || error))))
page.on('request', request => {
  const method = request.method().toUpperCase()
  const url = request.url()
  const postData = request.postData() || ''
  const reason = classifyRequest(method, url, postData)
  const entry = { method, url, reason }
  allRequests.push(entry)
  if (reason) forbiddenRequests.push(entry)
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS' && !url.includes('/api/tw-stock/agent/simple-chat')) suspiciousRequests.push(entry)
})
page.on('response', response => {
  if (response.status() >= 400) failedResponses.push({ status: response.status(), url: response.url() })
})

async function fulfillJson (route, data, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(apiResponse(data)) })
}

await page.route('**/api/**', route => fulfillJson(route, { ok: true, status: 'fixture', items: [], trading: tradingFlags() }))
await page.route('**/api/auth/info**', route => fulfillJson(route, { id: 1, username: 'mtrp11', role: { id: 'default', permissions: ['dashboard'] } }))
await page.route('**/api/auth/security-config**', route => fulfillJson(route, { turnstile_enabled: false }))
await page.route('**/api/settings/brand-config**', route => fulfillJson(route, { app_name: 'QuantDinger' }))
await page.route('**/api/strategies/notifications/unread-count**', route => fulfillJson(route, { count: 0 }))
await page.route('**/api/policy/broker-market**', route => fulfillJson(route, { ok: true, disabled: true }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', route => fulfillJson(route, { ok: true, templates: [], items: [] }))
await page.route('**/api/indicator/kline**', route => fulfillJson(route, []))

await page.route('**/api/tw-stock/current-strategy-context**', route => fulfillJson(route, currentStrategyContextPayload()))
await page.route('**/api/tw-stock/phase-yz/productization-status**', route => fulfillJson(route, {
  ok: true,
  state: 'pending_execution_price',
  signal_asof: '2026-06-18',
  target_next_trading_day: '2026-06-19',
  execution_price_status: 'execution_price_pending',
  paper_apply_allowed: false,
  paper_apply_blocked_reason: 'execution_price_pending',
  selected_strategy_rule_id: 'top50_exit_one_worst_sell',
  trading: tradingFlags()
}))
await page.route('**/api/tw-stock/readonly-shadow-exposure**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  shadowExposureGetCount += 1
  await fulfillJson(route, readonlyShadowExposurePayload())
})
await page.route('**/api/tw-stock/readonly-strategy-snapshot**', route => fulfillJson(route, readonlyStrategySnapshotPayload()))
await page.route('**/api/tw-stock/readonly-replay-window-index**', route => fulfillJson(route, replayIndexPayload()))
await page.route('**/api/tw-stock/readonly-replay-window**', route => fulfillJson(route, replayWindowPayload()))
await page.route('**/api/tw-stock/paper-portfolio/latest-decision**', route => fulfillJson(route, paperLatestDecision()))
await page.route('**/api/tw-stock/paper-portfolio/state**', route => fulfillJson(route, paperState()))
await page.route('**/api/tw-stock/paper-portfolio/apply-runs**', route => fulfillJson(route, { ok: true, items: [] }))
await page.route('**/api/tw-stock/agent/context**', route => fulfillJson(route, { ok: true, qlib: { asof: '2026-06-18' }, freshness: { status: 'accepted' }, disclaimers: ['仅供研究观察，不构成交易建议。'] }))
await page.route('**/api/tw-stock/agent/simple-chat**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  simpleChatCount += 1
  const body = JSON.parse(route.request().postData() || '{}')
  simpleChatPayloads.push(body)
  assert.deepEqual(Object.keys(body).sort(), ['maxItems', 'question', 'symbol'])
  assert.equal(body.question, '为什么模拟账户不能应用？')
  for (const field of ['target', 'order', 'broker', 'provider', 'latest', 'target_position', 'target_weight', 'quantity']) {
    assert.ok(!Object.prototype.hasOwnProperty.call(body, field), `simple-chat payload must not include ${field}`)
  }
  await fulfillJson(route, simpleChatPayload())
})
await page.route('**/api/tw-stock/quant/signals/health**', route => fulfillJson(route, { ok: true, latest: { exists: true, asof: '2026-06-18' }, trading: tradingFlags() }))
await page.route('**/api/tw-stock/quant/signals/latest**', route => fulfillJson(route, { ok: true, status: 'accepted', bucket: 'top30', signals: [{ symbol: '2330', rank: 1, score: 0.58 }], trading: tradingFlags() }))
await page.route('**/api/tw-stock/quant/signals/rank-changes**', route => fulfillJson(route, { ok: true, entered: [], exited: [], stayed: [], summary: {} }))
await page.route('**/api/tw-stock/quant/signals/runs**', route => fulfillJson(route, { ok: true, items: [] }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', route => fulfillJson(route, { ok: true, job: null, trading: tradingFlags() }))
await page.route('**/api/tw-stock/quant/ops/option-c/scheduler**', route => fulfillJson(route, { ok: true, enabled: false }))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', route => fulfillJson(route, { ok: true, latest_status: 'accepted', latest_asof: '2026-06-18', trading: tradingFlags() }))
await page.route('**/api/tw-stock/cross-analysis/latest**', route => fulfillJson(route, { ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-18' }, freshness: { warnings: [] } }))
await page.route('**/api/tw-stock/rank-tech-cross/latest**', route => fulfillJson(route, { ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-18' }, trading: tradingFlags() }))
await page.route('**/api/tw-stock/ltr-readonly-explanation**', route => fulfillJson(route, { ok: true, methods: [] }))
await page.route('**/api/tw-stock/ltr-optional-sim-strategies**', route => fulfillJson(route, { ok: true, strategies: [] }))
await page.route('**/api/tw-stock/monitor/config**', route => fulfillJson(route, { name: 'default', symbols: ['2330'], enabled: false }))
await page.route('**/api/tw-stock/monitor/alerts**', route => fulfillJson(route, { items: [] }))
await page.route('**/api/tw-stock/monitor/history**', route => fulfillJson(route, { items: [] }))
await page.route('**/api/tw-stock/monitor/scan-logs**', route => fulfillJson(route, { health: { status: 'ok' } }))
await page.route('**/api/tw-stock/trends**', route => fulfillJson(route, { items: [] }))
await page.route('**/api/tw-stock/sim/accounts**', route => fulfillJson(route, { items: [] }))

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'mtrp11-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'mtrp11', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
}, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForFunction(() => {
  const text = document.body.innerText
  return text.includes('今日策略总览') &&
    text.includes('候选名单') &&
    text.includes('历史模拟') &&
    text.includes('模拟账户状态') &&
    text.includes('策略解释助手') &&
    text.includes('影子观察') &&
    text.includes('top50_hold_rank_buffer_100')
}, null, { timeout: 45000 })
await Promise.all([
  page.waitForResponse(response => response.url().includes('/api/tw-stock/agent/simple-chat') && response.status() === 200),
  page.getByTestId('paper-portfolio-panel').getByText('解释原因').click()
])
await page.waitForFunction(() => document.body.innerText.includes('模拟账户暂不能应用，因为等待目标交易日开盘价'))

async function viewportAudit (name, width, height) {
  await page.setViewportSize({ width, height })
  await page.waitForTimeout(500)
  const metrics = await page.evaluate(() => {
    const text = document.body.innerText
    const required = [
      '今日策略总览',
      '候选名单',
      '历史模拟',
      '模拟账户状态',
      '策略解释助手',
      '影子观察',
      '只读研究',
      '不是交易建议',
      '不连接券商',
      '不提交真实订单',
      'top50_hold_rank_buffer_100',
      '影子观察通过'
    ]
    const forbiddenVisible = [
      '目标仓位',
      '目标权重',
      '连接券商',
      '自动下单',
      '收益承诺',
      '胜率承诺',
      '上涨概率承诺',
      'OpenAI API key',
      'OPENAI_API_KEY'
    ]
    const isAllowedNegatedPhrase = item => {
      return text.includes(`不是${item}`) ||
        text.includes(`不${item}`) ||
        text.includes(`不提供${item}`) ||
        text.includes(`不提交${item}`) ||
        text.includes(`不进入${item}`)
    }
    const shadowPanel = document.querySelector('[data-testid="readonly-shadow-exposure-panel"]')
    const shadowText = shadowPanel ? shadowPanel.innerText : ''
    const buttons = shadowPanel ? Array.from(shadowPanel.querySelectorAll('button')).map(el => el.innerText.trim()).filter(Boolean) : []
    const openTechPanelCount = Array.from(document.querySelectorAll('.ant-collapse-item-active')).length
    const buttonOverflow = Array.from(document.querySelectorAll('button')).filter(el => el.scrollWidth > el.clientWidth + 2).map(el => el.innerText.trim()).filter(Boolean)
    return {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      required_missing: required.filter(item => !text.includes(item)),
      forbidden_visible: forbiddenVisible.filter(item => text.includes(item) && !isAllowedNegatedPhrase(item)),
      shadow_panel_visible: Boolean(shadowPanel),
      shadow_panel_text_sample: shadowText.slice(0, 500),
      shadow_panel_buttons: buttons,
      shadow_panel_forbidden_controls: buttons.filter(item => /apply|下单|订单|目标|仓位|权重|数量|券商|交易/i.test(item)),
      open_tech_panel_count: openTechPanelCount,
      button_overflow: buttonOverflow
    }
  })
  await page.screenshot({ path: path.join(artifactDir, `${name}.png`), fullPage: true })
  return metrics
}

const viewportResults = {
  desktop: await viewportAudit('desktop', 1440, 980),
  tablet: await viewportAudit('tablet', 1024, 768),
  mobile: await viewportAudit('mobile', 390, 900)
}

const countReason = reason => forbiddenRequests.filter(item => item.reason === reason).length
const networkAudit = {
  schema_version: 'mtrp11_readonly_shadow_exposure_network_audit.v1',
  base_url: baseUrl,
  request_count: allRequests.length,
  readonly_shadow_exposure_get_count: shadowExposureGetCount,
  forbidden_request_count: forbiddenRequests.length,
  forbidden_requests: forbiddenRequests,
  suspicious_requests: suspiciousRequests,
  monitor_config_write_count: countReason('monitor_config_write'),
  monitor_scan_post_count: countReason('monitor_scan_post'),
  monitor_alerts_write_count: countReason('monitor_alerts_write'),
  ops_dry_run_post_count: countReason('ops_dry_run_or_provider_latest'),
  failed_response_count: failedResponses.length,
  failed_responses: failedResponses,
  simple_chat_request_count: simpleChatCount,
  simple_chat_payloads: simpleChatPayloads,
  simple_chat_payload_forbidden_field_count: forbiddenRequests.filter(item => item.reason === 'agent_simple_chat_forbidden_payload').length,
  frontend_openai_direct_request_count: countReason('frontend_openai_direct'),
  broker_quick_trade_order_request_count: countReason('broker_quick_trade_order')
}
const consoleAudit = {
  schema_version: 'mtrp11_readonly_shadow_exposure_console_audit.v1',
  console_error_count: consoleErrors.length,
  page_error_count: pageErrors.length,
  console_messages: consoleMessages,
  console_errors: consoleErrors,
  page_errors: pageErrors
}
const summary = {
  schema_version: 'mtrp11_readonly_shadow_exposure_summary.v1',
  base_url: baseUrl,
  artifact_dir: artifactDir,
  screenshots: {
    desktop: path.join(artifactDir, 'desktop.png'),
    tablet: path.join(artifactDir, 'tablet.png'),
    mobile: path.join(artifactDir, 'mobile.png')
  },
  viewport_results: viewportResults,
  readonly_shadow_exposure_visible: Object.values(viewportResults).every(row => row.shadow_panel_visible === true),
  readonly_shadow_exposure_route_mocked: shadowExposureGetCount > 0,
  required_text_passed: Object.values(viewportResults).every(row => row.required_missing.length === 0),
  forbidden_visible_passed: Object.values(viewportResults).every(row => row.forbidden_visible.length === 0),
  shadow_panel_forbidden_controls_passed: Object.values(viewportResults).every(row => row.shadow_panel_forbidden_controls.length === 0),
  overflow_passed: Object.values(viewportResults).every(row => row.overflowX === false),
  button_overflow_passed: Object.values(viewportResults).every(row => row.button_overflow.length === 0),
  technical_details_default_collapsed: Object.values(viewportResults).every(row => row.open_tech_panel_count === 0),
  network_passed: networkAudit.forbidden_request_count === 0 &&
    networkAudit.monitor_config_write_count === 0 &&
    networkAudit.monitor_scan_post_count === 0 &&
    networkAudit.monitor_alerts_write_count === 0 &&
    networkAudit.ops_dry_run_post_count === 0 &&
    networkAudit.failed_response_count === 0 &&
    networkAudit.frontend_openai_direct_request_count === 0 &&
    networkAudit.broker_quick_trade_order_request_count === 0,
  console_passed: consoleAudit.console_error_count === 0 && consoleAudit.page_error_count === 0,
  simple_chat_passed: networkAudit.simple_chat_request_count === 1 && networkAudit.simple_chat_payload_forbidden_field_count === 0,
  overall_passed: false
}
summary.overall_passed = summary.readonly_shadow_exposure_visible &&
  summary.readonly_shadow_exposure_route_mocked &&
  summary.required_text_passed &&
  summary.forbidden_visible_passed &&
  summary.shadow_panel_forbidden_controls_passed &&
  summary.overflow_passed &&
  summary.button_overflow_passed &&
  summary.technical_details_default_collapsed &&
  summary.network_passed &&
  summary.console_passed &&
  summary.simple_chat_passed

await writeFile(path.join(artifactDir, 'summary.json'), JSON.stringify(summary, null, 2))
await writeFile(path.join(artifactDir, 'network_audit.json'), JSON.stringify(networkAudit, null, 2))
await writeFile(path.join(artifactDir, 'console_audit.json'), JSON.stringify(consoleAudit, null, 2))

await browser.close()

assert.equal(summary.overall_passed, true, JSON.stringify(summary, null, 2))
assert.equal(networkAudit.readonly_shadow_exposure_get_count > 0, true)
assert.equal(networkAudit.forbidden_request_count, 0, JSON.stringify(networkAudit.forbidden_requests, null, 2))
assert.equal(networkAudit.monitor_config_write_count, 0)
assert.equal(networkAudit.monitor_scan_post_count, 0)
assert.equal(networkAudit.monitor_alerts_write_count, 0)
assert.equal(networkAudit.ops_dry_run_post_count, 0)
assert.equal(networkAudit.failed_response_count, 0, JSON.stringify(networkAudit.failed_responses, null, 2))
assert.equal(networkAudit.simple_chat_request_count, 1)
assert.equal(networkAudit.frontend_openai_direct_request_count, 0)
assert.equal(networkAudit.broker_quick_trade_order_request_count, 0)
assert.equal(consoleAudit.console_error_count, 0, JSON.stringify(consoleAudit.console_errors, null, 2))
assert.equal(consoleAudit.page_error_count, 0, JSON.stringify(consoleAudit.page_errors, null, 2))

console.log(JSON.stringify({ artifactDir, summary, networkAudit, consoleAudit }, null, 2))
