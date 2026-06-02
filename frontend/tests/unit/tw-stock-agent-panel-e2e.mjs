import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from '/tmp/travel-agent-e2e/node_modules/playwright/index.mjs'

const baseUrl = process.env.TW_STOCK_AGENT_BASE_URL || 'http://127.0.0.1:8000'
const screenshotDir = process.env.TW_STOCK_AGENT_SCREENSHOT_DIR || '/tmp/quantdinger_tw_agent_e2e'
const latestRunId = 'option_c_daily_signal_agent_fixture'
const disclaimer = '仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或入场概率。'

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

function agentContext () {
  return {
    ok: true,
    status: 'accepted',
    qlib: { asof: '2026-06-01', run_id: latestRunId, target_horizon: 'next_trading_day_research_ranking', research_signal_not_order: true },
    cross_analysis: { summary: { category_counts: { focus_watch: 2, model_trend_divergence: 1, data_review_required: 1 } } },
    top30_preview: allItems,
    focus_watch_preview: focusItems,
    divergence_preview: divergenceItems,
    data_review_preview: reviewItems,
    freshness: { status: 'fresh', qlib: { asof: '2026-06-01', run_id: latestRunId }, quantdinger: { latest_date_min: '2026-06-01', latest_date_max: '2026-06-01' } },
    allowed_intents: ['today_top30', 'focus_watch', 'model_trend_divergence', 'single_symbol_metrics', 'freshness_and_data_basis'],
    blocked_intents: ['place_order', 'target_position', 'qlib_ops_refresh_publish'],
    disclaimers: [disclaimer],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function chatPayload (question) {
  const q = String(question || '')
  if (q.includes('API error')) return { error: true }
  if (q.includes('items 为空')) return baseChat('research_summary', '本次用于验证 items 为空状态，回答仍可见。', [], ['mock_warning_non_empty'])
  if (q.includes('下单') || q.includes('下單')) {
    return { ok: true, mode: 'disabled', intent: 'place_order', blocked: true, answer: '该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。', citations: [], items: [], warnings: ['blocked_research_boundary'], research_only_disclaimer: disclaimer, context_digest: { status: 'blocked', intent: 'place_order', qlib_asof: '2026-06-01', qlib_run_id: latestRunId, freshness_status: 'fresh' }, trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true } }
  }
  if (q.includes('仓位') || q.includes('倉位')) {
    return { ok: true, mode: 'disabled', intent: 'target_position', blocked: true, answer: '该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。', citations: [], items: [], warnings: ['blocked_research_boundary'], research_only_disclaimer: disclaimer, context_digest: { status: 'blocked', intent: 'target_position', qlib_asof: '2026-06-01', qlib_run_id: latestRunId, freshness_status: 'fresh' }, trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true } }
  }
  if (q.includes('2330')) {
    return baseChat('single_symbol_metrics', '2330 的 qlib rank=1，trend=uptrend，category=focus_watch；建议关注并人工复盘。', focusItems.slice(0, 1), [])
  }
  if (q.includes('新鲜度') || q.includes('口径')) {
    return baseChat('freshness_and_data_basis', '当前 qlib asof=2026-06-01，run_id=' + latestRunId + '；freshness=fresh，raw 日期范围 2026-06-01 到 2026-06-01。', [], [])
  }
  if (q.includes('回避') || q.includes('复盘') || q.includes('復盤')) {
    return baseChat('model_trend_divergence', '模型与 raw 趋势分歧或数据异常的项目建议人工复盘，不纳入直接判断。', divergenceItems.concat(reviewItems), ['stale_daily_bar'])
  }
  if (q.includes('支持')) {
    return baseChat('focus_watch', '模型排序与 raw 趋势都支持的项目建议关注，并保留人工复盘。', focusItems, [])
  }
  return baseChat('today_top30', '今天 top30 研究预览包含 2330、2454、2303；仅用于候选观察。', allItems.slice(0, 3), ['mock_warning_non_empty'])
}

function baseChat (intent, answer, items, warnings) {
  return {
    ok: true,
    mode: 'disabled',
    intent,
    blocked: false,
    answer: `${answer}${answer.includes('仅供') ? '' : ' ' + disclaimer}`,
    citations: [`qlib:accepted_latest:${latestRunId}:2026-06-01`, 'cross-analysis:latest:top30'],
    items,
    warnings,
    research_only_disclaimer: disclaimer,
    context_digest: { status: 'accepted', qlib_asof: '2026-06-01', qlib_run_id: latestRunId, target_horizon: 'next_trading_day_research_ranking', freshness_status: 'fresh', item_count: items.length },
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

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

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
const consoleMessages = []
const pageErrors = []
page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`))
page.on('pageerror', error => pageErrors.push(error.message))
page.setDefaultTimeout(45000)

const allRequests = []
const agentPhaseRequests = []
let captureAgentPhase = false
let agentContextCount = 0
let agentChatCount = 0
let forbiddenAgentRequests = []

function isForbiddenAgentUrl (url) {
  const lower = url.toLowerCase()
  return lower.includes('api.openai.com') || lower.includes('openai_api_key') || lower.includes('/api/tw-stock/quant/ops/') || lower.includes('/api/tw-stock/cross-analysis/history/import-latest') || lower.includes('/api/tw-stock/cross-analysis/reviews') || lower.includes('/api/indicator/backtest') || lower.includes('/api/quick-trade') || lower.includes('broker') || lower.includes('order/submit') || lower.includes('paper') || lower.includes('live')
}

page.on('request', request => {
  const entry = `${request.method().toUpperCase()} ${request.url()}`
  allRequests.push(entry)
  if (captureAgentPhase) {
    agentPhaseRequests.push(entry)
    if (isForbiddenAgentUrl(request.url())) forbiddenAgentRequests.push(entry)
  }
})

await page.route('**/api/auth/info**', async route => {
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'agent-e2e', nickname: 'Agent E2E', is_demo: false, role: { id: 'default', permissions: ['dashboard'] } })) })
})
await page.route('**/api/tw-stock/agent/context**', async route => {
  agentContextCount += 1
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(agentContext())) })
})
await page.route('**/api/tw-stock/agent/chat**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  agentChatCount += 1
  const body = JSON.parse(route.request().postData() || '{}')
  const payload = chatPayload(body.question)
  if (payload.error) {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ code: 0, msg: 'fixture agent api error', data: null }) })
    return
  }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(payload)) })
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

await page.addInitScript(() => {
  const expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000
  const info = { id: 1, username: 'agent-e2e', nickname: 'Agent E2E', is_demo: false, role: { id: 'default', permissions: ['dashboard'] } }
  const roles = [{ id: 'default', permissionList: ['dashboard'] }]
  window.localStorage.setItem('Access-Token', JSON.stringify('agent-e2e-token'))
  window.localStorage.setItem('User-Info', JSON.stringify(info))
  window.localStorage.setItem('User-Roles', JSON.stringify(roles))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-TW')
})

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
try {
  await page.waitForSelector('.tw-stock-agent-panel')
} catch (error) {
  const diagnostic = await page.evaluate(() => ({
    href: window.location.href,
    hash: window.location.hash,
    storageKeys: Object.keys(window.localStorage).filter(key => key.includes('Access') || key.includes('User') || key.includes('storejs')),
    body: document.body.innerText.slice(0, 1800),
    appHtml: (document.querySelector('#app') && document.querySelector('#app').innerHTML.slice(0, 1200)) || '',
    scripts: Array.from(document.scripts).map(script => script.src || script.textContent.slice(0, 80)).slice(0, 8)
  }))
  diagnostic.consoleMessages = consoleMessages.slice(-20)
  diagnostic.pageErrors = pageErrors
  console.error('tw-stock-agent e2e diagnostic:', JSON.stringify(diagnostic, null, 2))
  throw error
}
await page.waitForFunction(() => document.body.innerText.includes('台股研究助手'))
await page.waitForFunction(() => document.body.innerText.includes('qlib asof') && document.body.innerText.includes('2026-06-01'))
await page.screenshot({ path: `${screenshotDir}/agent-initial-context.png`, fullPage: true })

captureAgentPhase = true
const agent = page.locator('.tw-stock-agent-panel')
assert.ok(await agent.getByText('今天 top30 是哪些？', { exact: true }).count(), 'missing top30 suggestion')
assert.ok(await agent.locator('textarea').count(), 'missing agent input')
assert.ok(await agent.getByRole('button', { name: /发送/ }).count(), 'missing send button')

async function askAndAssert ({ question, expect, blocked = false, error = false, itemText = '' }) {
  const before = agentChatCount
  await agent.locator('textarea').fill(question)
  await agent.getByRole('button', { name: /发送/ }).click()
  await page.waitForFunction(beforeCount => window.__agentWait = true || true, before)
  await page.waitForTimeout(250)
  await page.waitForFunction(args => document.body.innerText.includes(args.expect), { expect }, { timeout: 10000 }).catch(async err => {
    const text = await agent.innerText().catch(() => '')
    console.error('agent panel text:', text)
    throw err
  })
  if (!error) {
    await page.waitForFunction(() => document.body.innerText.includes('仅供研究观察，不构成交易建议'))
    await page.waitForFunction(() => document.body.innerText.includes('qlib:accepted_latest') || document.body.innerText.includes('run_id') || document.body.innerText.includes('freshness'))
    await page.waitForFunction(() => document.body.innerText.includes('当前使用后端 deterministic fallback / 未启用 OpenAI。'))
  }
  if (blocked) await page.waitForFunction(() => document.body.innerText.includes('该问题已被研究边界阻断'))
  if (itemText) await page.waitForFunction(text => document.body.innerText.includes(text), itemText)
  assert.equal(agentChatCount, before + 1, `chat count mismatch for ${question}`)
}

await askAndAssert({ question: '今天 top30 是哪些？', expect: '今天 top30 研究预览', itemText: 'rank 1' })
await askAndAssert({ question: '今天模型和趋势都支持的股票有哪些？', expect: '模型排序与 raw 趋势都支持', itemText: 'focus_watch' })
await askAndAssert({ question: '今天建议回避或人工复盘的股票有哪些？', expect: '模型与 raw 趋势分歧', itemText: 'data_review_required' })
await askAndAssert({ question: '2330 的指标是多少？', expect: '2330 的 qlib rank=1', itemText: '2330' })
await askAndAssert({ question: '当前数据新鲜度和口径是什么？', expect: 'freshness=fresh' })
await askAndAssert({ question: '帮我下单买入 2330', expect: '不支持下单', blocked: true })
await askAndAssert({ question: '2330 买入多少仓位？', expect: '不支持下单', blocked: true })
await askAndAssert({ question: '请返回 warnings 非空', expect: 'mock_warning_non_empty', itemText: 'mock_warning_non_empty' })
await askAndAssert({ question: '请验证 items 为空', expect: '本次回答没有附带项目列表。' })

const normalPanelText = await agent.innerText()
for (const required of ['台股研究助手', '引用来源', 'warnings', 'qlib asof', 'run_id', 'freshness']) {
  assert.ok(normalPanelText.includes(required), `agent panel missing ${required}`)
}
for (const forbidden of ['交易按钮', '下单按钮', '仓位按钮', '立即买入', '立即卖出', 'OpenAI API Key']) {
  assert.ok(!normalPanelText.includes(forbidden), `agent panel contains forbidden UI text ${forbidden}`)
}

const beforeError = agentChatCount
await agent.locator('textarea').fill('触发 API error')
await agent.getByRole('button', { name: /发送/ }).click()
await page.waitForFunction(() => document.body.innerText.includes('fixture agent api error') || document.body.innerText.includes('台股研究助手回答失败'))
assert.equal(agentChatCount, beforeError + 1)
await page.screenshot({ path: `${screenshotDir}/agent-after-scenarios.png`, fullPage: true })

assert.equal(forbiddenAgentRequests.length, 0, `forbidden agent requests: ${forbiddenAgentRequests.join('\n')}`)
assert.ok(agentPhaseRequests.some(item => item.includes('/api/tw-stock/agent/chat')), 'agent chat request not captured')
assert.ok(agentContextCount >= 1, 'agent context was not requested')
assert.ok(agentChatCount >= 10, 'not all agent chat scenarios executed')

const requestSummary = {
  totalRequests: allRequests.length,
  agentPhaseRequests: agentPhaseRequests.length,
  agentContextCount,
  agentChatCount,
  uniqueAgentPhasePaths: Array.from(new Set(agentPhaseRequests.map(item => {
    try { const url = new URL(item.split(' ').slice(1).join(' ')); return `${item.split(' ')[0]} ${url.pathname}` } catch { return item }
  }))).sort(),
  screenshotDir
}

await browser.close()
console.log(`tw-stock-agent panel e2e passed: ${JSON.stringify(requestSummary)}`)
