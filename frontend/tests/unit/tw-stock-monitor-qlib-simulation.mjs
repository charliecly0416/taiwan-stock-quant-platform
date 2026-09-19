import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const username = process.env.TW_STOCK_MONITOR_USERNAME || 'localadmin'
const password = process.env.TW_STOCK_MONITOR_PASSWORD || 'QuantDinger123!'
const screenshotDir = process.env.TW_STOCK_MONITOR_SCREENSHOT_DIR || '/tmp/quantdinger_tw_qlib_simulation'
const draftKey = 'tw-stock-monitor-qlib-watch-draft'

const latestRunId = 'option_c_daily_signal_latest_simulation'
const acceptedRunId = 'option_c_daily_signal_20260601_20260601T121228Z'
const waitRunId = 'option_c_daily_signal_20260602_20260602T010203Z'
const blockedRunId = 'option_c_daily_signal_20260601_blocked_fixture'

function qlibRows (count, bucket) {
  return Array.from({ length: count }, (_, index) => {
    const rank = index + 1
    const symbol = rank === 1 ? '2330' : String(2300 + rank)
    return {
      asof: '2026-06-01',
      instrument: `TW${symbol}`,
      symbol,
      qlib_score: Number((0.2 - rank / 1000).toFixed(12)),
      rank,
      bucket,
      source_model_recorder: '950741cfd5f14ee5a05464fec3e12e0a',
      diagnostic_only: true,
      research_signal_not_order: true,
      trend: {
        ok: true,
        trend_label: rank % 2 ? 'uptrend' : 'sideways',
        trend_score: Number((70 - rank / 10).toFixed(2)),
        latest_close: 600 + rank,
        latest_date: '2026-06-01',
        quality_warnings: rank === 1 ? ['simulation_fixture_warning'] : []
      }
    }
  })
}

function acceptedPayload ({ runId = latestRunId, bucket = 'top30', count = null } = {}) {
  const top30 = qlibRows(count == null ? 30 : count, 'top30')
  const top50 = qlibRows(count == null ? 50 : count, 'top50')
  const payload = {
    ok: true,
    status: 'accepted',
    asof: '2026-06-01',
    run_id: runId,
    recorder_id: '950741cfd5f14ee5a05464fec3e12e0a',
    bucket,
    summary: { status: 'accepted', asof: '2026-06-01', prediction_rows: 150, top30_rows: count == null ? 30 : count, top50_rows: count == null ? 50 : count, diagnostic_only: true, research_signal_not_order: true },
    metadata: { status: 'accepted', asof: '2026-06-01', frozen_recorder: '950741cfd5f14ee5a05464fec3e12e0a' },
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true },
    warnings: count === 0 ? ['simulation_empty_accepted_signals'] : ['run_metadata_missing_research_only_flags_verified_by_latest_and_summary'],
    enrichTrend: { enabled: true, requested: true, trendLimit: 120 },
    top30_count: count == null ? 30 : count,
    top50_count: count == null ? 50 : count
  }
  if (bucket === 'top50') payload.signals = top50
  else if (bucket === 'all') {
    payload.top30 = top30
    payload.top50 = top50
  } else payload.signals = top30
  return payload
}

function waitStatePayload () {
  return {
    ok: false,
    status: 'wait_state_data_refresh_needed',
    message: 'historical qlib run is not an accepted signal run',
    asof: '2026-06-02',
    run_id: waitRunId,
    bucket: 'top30',
    signals: [],
    top30: [],
    top50: [],
    summary: { status: 'wait_state_data_refresh_needed', asof: '2026-06-02', reason: 'simulation newer data requires manual review' },
    metadata: { status: 'wait_state_data_refresh_needed', asof: '2026-06-02' },
    warnings: ['simulation newer data requires manual review'],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true },
    enrichTrend: { enabled: false, requested: true, trendLimit: 120 }
  }
}

function blockedPayload () {
  return {
    ok: false,
    status: 'blocked_validation_failed',
    message: 'simulation blocked validation failed',
    asof: '2026-06-01',
    run_id: blockedRunId,
    bucket: 'top30',
    signals: [],
    top30: [],
    top50: [],
    summary: { status: 'blocked_validation_failed', asof: '2026-06-01', reason: 'simulation blocked validation failed' },
    metadata: { status: 'blocked_validation_failed', asof: '2026-06-01' },
    warnings: ['simulation blocked validation failed'],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true },
    enrichTrend: { enabled: false, requested: true, trendLimit: 120 }
  }
}

function missingLatestPayload () {
  return {
    ok: false,
    status: 'missing_latest_signal',
    message: 'latest_signal.json not found in simulation fixture',
    bucket: null,
    signals: [],
    top30: [],
    top50: [],
    warnings: ['latest_signal.json not found in simulation fixture'],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function healthPayload ({ stale = false, missing = false, apiFailure = false } = {}) {
  if (apiFailure) return null
  if (missing) {
    return {
      ok: false,
      status: 'missing_latest_signal',
      latest: { exists: false, asof: null, run_id: null, created_at: null, accepted_validated: false, warnings: ['latest_signal.json not found in simulation fixture'] },
      freshness: { current_utc_date: '2026-06-02', asof_age_days: null, created_age_hours: null, stale: true, stale_reason: 'missing_latest_signal' },
      runs: { total_scanned: 3, accepted: 1, wait_state: 1, blocked: 1, other: 0 },
      dataAvailability: { trend_data_dependency: 'TWStock local daily bars', backtest_data_dependency: 'qd_tw_stock_daily_bars', warnings: [] },
      trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
    }
  }
  return {
    ok: !stale,
    status: 'accepted',
    latest: { exists: true, asof: '2026-06-01', run_id: latestRunId, created_at: '2026-06-01T12:12:40+00:00', accepted_validated: true, warnings: ['run_metadata_missing_research_only_flags_verified_by_latest_and_summary'] },
    freshness: { current_utc_date: '2026-06-02', asof_age_days: 1, created_age_hours: 10.2, stale, stale_reason: stale ? 'fresh_data_wait_state_present' : '' },
    runs: { total_scanned: 3, accepted: 1, wait_state: 1, blocked: 1, other: 0 },
    dataAvailability: { trend_data_dependency: 'TWStock local daily bars', backtest_data_dependency: 'qd_tw_stock_daily_bars', warnings: stale ? ['fresh_data_wait_state_present'] : [] },
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function runsPayload () {
  return {
    items: [
      { run_id: acceptedRunId, asof: '2026-06-01', status: 'accepted', created_at: '2026-06-01T12:12:40+00:00', prediction_rows: 150, top30_rows: 30, top50_rows: 50, recorder_id: '950741cfd5f14ee5a05464fec3e12e0a', diagnostic_only: true, research_signal_not_order: true, accepted_validated: true, warnings: [] },
      { run_id: waitRunId, asof: '2026-06-02', status: 'wait_state_data_refresh_needed', created_at: '2026-06-02T01:02:03+00:00', accepted_validated: false, warnings: ['simulation newer data requires manual review'] },
      { run_id: blockedRunId, asof: '2026-06-01', status: 'blocked_validation_failed', created_at: '2026-06-01T10:00:00+00:00', accepted_validated: false, warnings: ['simulation blocked validation failed'] }
    ],
    count: 3,
    limit: 20,
    status: 'all',
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function apiResponse (data) {
  return { code: 1, msg: 'success', data }
}

async function loginToken () {
  const response = await fetch(`${baseUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  const payload = await response.json()
  assert.equal(payload.code, 1, payload.msg || 'login failed')
  assert.ok(payload.data && payload.data.token, 'login response missing token')
  return payload.data
}

function isDangerousWrite (request) {
  const url = request.url().toLowerCase()
  const method = request.method().toUpperCase()
  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) return false
  if (url.includes('/api/tw-stock/monitor/config')) return true
  if (url.includes('/api/tw-stock/monitor/scan')) return true
  if (url.includes('/api/tw-stock/monitor/alerts')) return true
  if (url.includes('/api/tw-stock/backtest') || url.includes('/api/indicator/backtest')) return true
  if (/order|orders|trade|trading|position|positions|target-position|quick-trade|broker/.test(url)) return true
  if (/qlib\/(run|generate)|generate|refresh|provider|retrain|tune/.test(url)) return true
  return false
}

async function installRoutes (page, mode) {
  await page.route('**/api/tw-stock/quant/signals/health**', async route => {
    if (mode === 'api-failure') {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ code: 0, msg: 'simulation health failure', data: null }) })
      return
    }
    const data = healthPayload({ stale: mode === 'stale', missing: mode === 'missing' })
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(data)) })
  })

  await page.route('**/api/tw-stock/quant/signals/latest**', async route => {
    if (mode === 'api-failure') {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ code: 0, msg: 'simulation latest failure', data: missingLatestPayload() }) })
      return
    }
    if (mode === 'missing') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, msg: 'latest missing', data: missingLatestPayload() }) })
      return
    }
    const url = new URL(route.request().url())
    const bucketParam = url.searchParams.get('bucket')
    const bucket = bucketParam === 'top50' || bucketParam === 'all' ? bucketParam : 'top30'
    const count = mode === 'empty' ? 0 : null
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(acceptedPayload({ runId: latestRunId, bucket, count }))) })
  })

  await page.route('**/api/tw-stock/quant/signals/runs**', async route => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    if (pathname.endsWith('/api/tw-stock/quant/signals/runs')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(runsPayload())) })
      return
    }
    const runId = decodeURIComponent(pathname.split('/').pop() || '')
    const bucketParam = url.searchParams.get('bucket')
    const bucket = bucketParam === 'top50' || bucketParam === 'all' ? bucketParam : 'top30'
    const data = runId === waitRunId ? waitStatePayload() : runId === blockedRunId ? blockedPayload() : acceptedPayload({ runId, bucket })
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(data)) })
  })

  await page.route('**/api/indicator/backtest', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ result: null })) })
  })
}

async function bootstrapPage ({ browser, auth, roles, mode = 'accepted', viewport = { width: 1440, height: 980 }, clearDraft = true }) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 })
  page.setDefaultTimeout(45000)
  const counters = { dangerous: 0, dangerousUrls: [], readonlyReads: {}, backtestPosts: 0, configWrites: 0, scanPosts: 0, alertWrites: 0 }
  page.on('request', request => {
    const url = request.url().toLowerCase()
    const method = request.method().toUpperCase()
    if (method === 'GET' && (url.includes('/api/tw-stock/monitor/config') || url.includes('/api/tw-stock/monitor/alerts') || url.includes('/api/tw-stock/monitor/scan-logs'))) {
      counters.readonlyReads[url] = (counters.readonlyReads[url] || 0) + 1
    }
    if (url.includes('/api/indicator/backtest') && method === 'POST') counters.backtestPosts += 1
    if (url.includes('/api/tw-stock/monitor/config') && ['POST', 'PUT', 'PATCH'].includes(method)) counters.configWrites += 1
    if (url.includes('/api/tw-stock/monitor/scan') && method === 'POST') counters.scanPosts += 1
    if (url.includes('/api/tw-stock/monitor/alerts') && ['POST', 'PUT', 'PATCH'].includes(method)) counters.alertWrites += 1
    if (isDangerousWrite(request)) {
      counters.dangerous += 1
      counters.dangerousUrls.push(`${method} ${request.url()}`)
    }
  })
  await installRoutes(page, mode)
  const expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000
  await page.addInitScript(({ token, userinfo, roles, expiresAt, clearDraft, draftKey }) => {
    window.localStorage.setItem('Access-Token', JSON.stringify(token))
    window.localStorage.setItem('User-Info', JSON.stringify(userinfo))
    window.localStorage.setItem('User-Roles', JSON.stringify(roles))
    window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
    window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
    window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
    window.localStorage.setItem('lang', 'zh-TW')
    if (clearDraft && window.sessionStorage.getItem('__preserve_qlib_draft') !== '1') window.localStorage.removeItem(draftKey)
  }, { token: auth.data?.token || auth.token, userinfo: { ...(auth.userinfo || {}), is_demo: false }, roles, expiresAt, clearDraft, draftKey })
  await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.tw-stock-monitor')
  await page.waitForFunction(() => document.body.innerText.includes('台股趨勢監控'))
  await page.waitForFunction(() => document.body.innerText.includes('qlib Option C 研究排序'))
  await page.waitForFunction(() => document.body.innerText.includes('qlib Option C 数据状态'))
  return { page, counters }
}

function forbidTradingText (text) {
  const forbidden = ['quick-trade', 'broker-accounts', 'paper order', 'live order', 'submit order', 'auto buy', 'auto sell', '下單', '买入', '買入', '卖出', '賣出', '提交订单', '提交訂單', 'quick trade', 'target position', 'target weight', 'automatic trading', '刷新 qlib provider', '重新生成 qlib 信号', '自动补数据', '買入概率', '买入概率', '預測收益', '预测收益', '建議倉位', '建议仓位']
  for (const word of forbidden) assert.ok(!text.toLowerCase().includes(word.toLowerCase()), `forbidden text visible: ${word}`)
}

async function expectNoDanger (counters, label) {
  assert.equal(counters.dangerous, 0, `${label} dangerous writes: ${counters.dangerousUrls.join(', ')}`)
  assert.equal(counters.configWrites, 0, `${label} config writes should be 0`)
  assert.equal(counters.scanPosts, 0, `${label} scan posts should be 0`)
  assert.equal(counters.alertWrites, 0, `${label} alert writes should be 0`)
}

async function closeScenario (record, page, counters, screenshot) {
  await expectNoDanger(counters, record.name)
  record.dangerous = counters.dangerous
  record.screenshot = screenshot
  await page.close()
}

const auth = await loginToken()
const role = auth.userinfo && auth.userinfo.role
const roleId = role && (role.id || role)
const permissions = (role && role.permissions) || ['dashboard']
const roles = [{ id: roleId || 'admin', permissionList: permissions.length ? permissions : ['dashboard'] }]
await mkdir(screenshotDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const results = []

async function runScenario (name, fn) {
  const record = { name, ok: false, dangerous: null, screenshot: '', note: '' }
  results.push(record)
  try {
    await fn(record)
    record.ok = true
  } catch (error) {
    record.note = error && error.message ? error.message : String(error)
    throw error
  }
}

await runScenario('5.1 accepted latest happy path', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.waitForFunction(() => document.body.innerText.includes('rows 30'))
  await page.waitForFunction(() => document.body.innerText.includes('qlib_score') && document.body.innerText.includes('trend_label') && document.body.innerText.includes('trend_score'))
  const text = await page.locator('body').innerText()
  for (const required of ['Research only', 'Not order', 'Read-only', 'Rank', '2330', 'uptrend']) assert.ok(text.includes(required), `missing accepted text: ${required}`)
  forbidTradingText(text)
  const screenshot = `${screenshotDir}/01-accepted-latest.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.2 top30 top50 switch', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.waitForFunction(() => document.body.innerText.includes('rows 30'))
  await page.getByText('Top 50', { exact: true }).click()
  await page.waitForFunction(() => document.body.innerText.includes('rows 50'))
  await page.getByText('Top 30', { exact: true }).click()
  await page.waitForFunction(() => document.body.innerText.includes('rows 30'))
  const screenshot = `${screenshotDir}/02-bucket-switch.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  record.note = '页面无 all bucket 入口，按文档要求仅验证 Top30/Top50。'
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.3 historical accepted run', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.locator('.qlib-run-table tr.ant-table-row').filter({ hasText: acceptedRunId }).first().click()
  await page.waitForFunction(runId => document.body.innerText.includes(`歷史 run ${runId}`), acceptedRunId)
  await page.waitForFunction(runId => document.body.innerText.includes(runId) && document.body.innerText.includes('rows 30'), acceptedRunId)
  await page.getByText('回到 latest', { exact: true }).click()
  await page.waitForFunction(runId => document.body.innerText.includes(runId) && document.body.innerText.includes('latest'), latestRunId)
  const screenshot = `${screenshotDir}/03-historical-accepted.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  assert.equal(counters.backtestPosts, 0, 'historical accepted must not auto-run backtest')
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.4 wait-state run', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.locator('.qlib-run-table tr.ant-table-row').filter({ hasText: waitRunId }).first().click()
  await page.waitForFunction(() => document.body.innerText.includes('wait_state_data_refresh_needed'))
  await page.waitForFunction(() => document.body.innerText.includes('simulation newer data requires manual review') || document.body.innerText.includes('historical qlib run is not an accepted signal run'))
  assert.equal(await page.locator('.qlib-signal-table').count(), 0, 'wait-state must not show signal table')
  assert.equal(await page.locator('button').filter({ hasText: '加入觀察' }).count(), 0, 'wait-state must not show add watch buttons')
  const screenshot = `${screenshotDir}/04-wait-state.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  forbidTradingText(await page.locator('body').innerText())
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.5 blocked run', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.locator('.qlib-run-table tr.ant-table-row').filter({ hasText: blockedRunId }).first().click()
  await page.waitForFunction(() => document.body.innerText.includes('blocked_validation_failed'))
  await page.waitForFunction(() => document.body.innerText.includes('simulation blocked validation failed'))
  assert.equal(await page.locator('.qlib-signal-table').count(), 0, 'blocked must not show signal table')
  assert.equal(await page.locator('button').filter({ hasText: '加入觀察' }).count(), 0, 'blocked must not show add watch buttons')
  const screenshot = `${screenshotDir}/05-blocked.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  forbidTradingText(await page.locator('body').innerText())
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.6 missing latest', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'missing' })
  await page.waitForFunction(() => document.body.innerText.includes('missing_latest_signal'))
  await page.waitForFunction(() => document.body.innerText.includes('latest_signal.json not found in simulation fixture'))
  assert.equal(await page.locator('.qlib-signal-table').count(), 0, 'missing latest must not show signal table')
  assert.ok(await page.locator('.qlib-run-table tr.ant-table-row').filter({ hasText: acceptedRunId }).count(), 'historical accepted run should remain browseable')
  const screenshot = `${screenshotDir}/06-missing-latest.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  forbidTradingText(await page.locator('body').innerText())
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.7 stale health with newer wait-state', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'stale' })
  await page.waitForFunction(() => document.body.innerText.includes('accepted') && document.body.innerText.includes('stale'))
  await page.waitForFunction(() => document.body.innerText.includes('fresh_data_wait_state_present'))
  await page.waitForFunction(() => document.body.innerText.includes('rows 30'))
  const screenshot = `${screenshotDir}/07-stale-wait-state.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  forbidTradingText(await page.locator('body').innerText())
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.8 api failure', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'api-failure' })
  await page.waitForFunction(() => document.body.innerText.includes('qlib Option C 研究排序'))
  await page.waitForFunction(() => document.body.innerText.includes('simulation latest failure') || document.body.innerText.includes('qlib Option C 研究排序讀取失敗'))
  assert.equal(await page.locator('.qlib-signal-table').count(), 0, 'api failure must not show stale accepted signal table')
  const screenshot = `${screenshotDir}/08-api-failure.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.9 empty accepted signals', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'empty' })
  await page.waitForFunction(() => document.body.innerText.includes('rows 0'))
  await page.waitForFunction(() => document.body.innerText.includes('simulation_empty_accepted_signals'))
  assert.equal(await page.locator('.qlib-signal-table button').filter({ hasText: '加入觀察' }).count(), 0, 'empty accepted must not offer row watch actions')
  const screenshot = `${screenshotDir}/09-empty-accepted.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  forbidTradingText(await page.locator('body').innerText())
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.10 watch draft localStorage', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.waitForSelector('.qlib-signal-table')
  await page.locator('.qlib-signal-table button').filter({ hasText: '加入觀察' }).nth(0).click()
  await page.locator('.qlib-signal-table button').filter({ hasText: '加入觀察' }).nth(1).click()
  await page.locator('.qlib-signal-table button').filter({ hasText: '加入觀察' }).nth(2).click()
  await page.waitForFunction(key => {
    const parsed = JSON.parse(window.localStorage.getItem(key) || '[]')
    return Array.isArray(parsed) && parsed.length >= 3
  }, draftKey)
  const stored = await page.evaluate(key => JSON.parse(window.localStorage.getItem(key) || '[]'), draftKey)
  for (const item of stored) {
    for (const key of ['symbol', 'run_id', 'rank', 'qlib_score', 'trend_label', 'trend_score']) assert.ok(Object.prototype.hasOwnProperty.call(item, key), `draft item missing ${key}`)
    for (const forbidden of ['order', 'position', 'target_weight', 'target_position']) assert.ok(!Object.prototype.hasOwnProperty.call(item, forbidden), `draft item includes forbidden ${forbidden}`)
  }
  await page.evaluate(() => window.sessionStorage.setItem('__preserve_qlib_draft', '1'))
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.tw-stock-monitor')
  await page.waitForFunction(() => document.querySelectorAll('.qlib-watch-draft-item').length >= 3)
  await page.getByText('清空草稿', { exact: true }).click()
  await page.waitForFunction(key => {
    const parsed = JSON.parse(window.localStorage.getItem(key) || '[]')
    return Array.isArray(parsed) && parsed.length === 0
  }, draftKey)
  const screenshot = `${screenshotDir}/10-watch-draft.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.11 fill monitor config manual only', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.locator('.qlib-signal-table button').filter({ hasText: '加入觀察' }).nth(0).click()
  await page.locator('.qlib-signal-table button').filter({ hasText: '加入觀察' }).nth(1).click()
  await page.getByText('填入監控配置', { exact: true }).click()
  await page.waitForFunction(() => document.body.innerText.includes('監控配置'))
  await page.waitForFunction(() => Array.from(document.querySelectorAll('textarea')).some(el => el.value.includes('2330')))
  const screenshot = `${screenshotDir}/11-fill-config-manual-only.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.12 readonly backtest linkage', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted' })
  await page.locator('.qlib-signal-table button').filter({ hasText: '回測驗證' }).first().click()
  await page.waitForFunction(() => document.body.innerText.includes('台股只讀回測驗證'))
  await page.waitForFunction(() => document.body.innerText.includes('歷史模擬') && document.body.innerText.includes('orders_enabled=false') && document.body.innerText.includes('connects_to_broker=false'))
  assert.equal(counters.backtestPosts, 0, 'row backtest action must not auto-post backtest')
  const screenshot = `${screenshotDir}/12-readonly-backtest.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  forbidTradingText(await page.locator('body').innerText())
  await closeScenario(record, page, counters, screenshot)
})

await runScenario('5.13 mobile narrow viewport', async record => {
  const { page, counters } = await bootstrapPage({ browser, auth, roles, mode: 'accepted', viewport: { width: 390, height: 844 } })
  await page.waitForFunction(() => document.body.innerText.includes('qlib Option C 数据状态') && document.body.innerText.includes('Research only') && document.body.innerText.includes('Not order'))
  await page.waitForSelector('.qlib-run-table')
  await page.waitForSelector('.qlib-signal-table')
  const screenshot = `${screenshotDir}/13-mobile.png`
  await page.screenshot({ path: screenshot, fullPage: true })
  const overlap = await page.evaluate(() => {
    const selectors = ['.qlib-health-panel', '.qlib-run-browser', '.qlib-watch-draft', '.qlib-signal-table']
    return selectors.map(selector => {
      const el = document.querySelector(selector)
      if (!el) return { selector, ok: false }
      const box = el.getBoundingClientRect()
      return { selector, ok: box.width > 0 && box.height > 0 && box.left < window.innerWidth }
    })
  })
  assert.ok(overlap.every(item => item.ok), `mobile key qlib sections not visible: ${JSON.stringify(overlap)}`)
  await closeScenario(record, page, counters, screenshot)
})

await browser.close()

assert.equal(results.length, 13, 'simulation should cover 13 Playwright scenarios plus real artifact smoke outside this script')
assert.ok(results.every(item => item.ok), `failed scenarios: ${JSON.stringify(results.filter(item => !item.ok))}`)
const totalDangerous = results.reduce((sum, item) => sum + Number(item.dangerous || 0), 0)
assert.equal(totalDangerous, 0, 'dangerous request count must remain zero')
console.log(`tw-stock-monitor qlib simulation passed: ${JSON.stringify({ screenshotDir, scenarios: results, totalDangerous })}`)
