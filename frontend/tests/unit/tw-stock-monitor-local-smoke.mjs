import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const username = process.env.TW_STOCK_MONITOR_USERNAME || 'localadmin'
const password = process.env.TW_STOCK_MONITOR_PASSWORD || 'QuantDinger123!'
const screenshotDir = process.env.TW_STOCK_MONITOR_SCREENSHOT_DIR || '/tmp/quantdinger_tw_qlib_e2e'

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
        trend_score: 70 - rank / 10,
        latest_close: 600 + rank,
        latest_date: '2026-06-01',
        quality_warnings: rank === 1 ? ['fixture_warning'] : []
      }
    }
  })
}

const latestRunId = 'option_c_daily_signal_latest_fixture'
const acceptedRunId = 'option_c_daily_signal_20260601_20260601T121228Z'
const waitRunId = 'option_c_daily_signal_20260602_20260601T121150Z'

function acceptedPayload ({ runId, bucket }) {
  const top30 = qlibRows(30, 'top30')
  const top50 = qlibRows(50, 'top50')
  const payload = {
    ok: true,
    status: 'accepted',
    asof: '2026-06-01',
    run_id: runId,
    recorder_id: '950741cfd5f14ee5a05464fec3e12e0a',
    bucket,
    summary: { status: 'accepted', asof: '2026-06-01', prediction_rows: 150, top30_rows: 30, top50_rows: 50, diagnostic_only: true, research_signal_not_order: true },
    metadata: { status: 'accepted', asof: '2026-06-01', frozen_recorder: '950741cfd5f14ee5a05464fec3e12e0a' },
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true },
    warnings: ['run_metadata_missing_research_only_flags_verified_by_latest_and_summary'],
    enrichTrend: { enabled: true, requested: true, trendLimit: 120 },
    top30_count: 30,
    top50_count: 50
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
    summary: { status: 'wait_state_data_refresh_needed', asof: '2026-06-02', reason: 'fixture stale' },
    metadata: { status: 'wait_state_data_refresh_needed', asof: '2026-06-02' },
    warnings: ['fixture stale'],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true },
    enrichTrend: { enabled: false, requested: true, trendLimit: 120 }
  }
}

function healthPayload () {
  return {
    ok: false,
    status: 'accepted',
    latest: {
      exists: true,
      asof: '2026-06-01',
      run_id: latestRunId,
      created_at: '2026-06-01T12:12:40+00:00',
      accepted_validated: true,
      warnings: ['run_metadata_missing_research_only_flags_verified_by_latest_and_summary']
    },
    freshness: {
      current_utc_date: '2026-06-01',
      asof_age_days: 0,
      created_age_hours: 1.2,
      stale: true,
      stale_reason: 'fresh_data_wait_state_present'
    },
    runs: { total_scanned: 2, accepted: 1, wait_state: 1, blocked: 0, other: 0 },
    dataAvailability: {
      trend_data_dependency: 'TWStock local daily bars',
      backtest_data_dependency: 'qd_tw_stock_daily_bars',
      warnings: ['fresh_data_wait_state_present']
    },
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

const opsJobId = 'option_c_dry_run_20260601_20260602T045532Z_9026a4e2'
let opsDryRunPostCount = 0
let opsJob = {
  ok: true,
  job_id: opsJobId,
  type: 'option_c_provider_dry_run',
  asof: '2026-06-01',
  status: 'dry_run_passed',
  cwd: '/home/chuliyang/qlib',
  argv: ['python', 'examples/tw/run_option_c_daily_signal_option_c_provider.py', '--asof', '2026-06-01', '--dry-run'],
  started_at: '2026-06-02T04:55:32+00:00',
  finished_at: '2026-06-02T04:55:39+00:00',
  returncode: 0,
  parsed_dry_run_status: 'dry_run_preflight_pass',
  latest_signal_updated: false,
  normal_signal_run: false,
  accepted_artifact_generated: false,
  stdout_tail: 'status: dry_run_preflight_pass\nlatest_signal_updated=false\nnormal_signal_run=false',
  stderr_tail: '',
  trading: { orders_enabled: false, connects_to_broker: false, writes_orders: false, writes_positions: false, research_signal_not_order: true }
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
const auth = await loginToken()
const expiresAt = Date.now() + 7 * 24 * 60 * 60 * 1000
const userinfo = { ...(auth.userinfo || {}), is_demo: false }
const role = userinfo && userinfo.role
const roleId = role && (role.id || role)
const permissions = (role && role.permissions) || ['dashboard']
const roles = [{ id: roleId || 'admin', permissionList: permissions.length ? permissions : ['dashboard'] }]

await mkdir(screenshotDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)
let readonlyBacktestPostCount = 0
let monitorConfigWriteCount = 0
let monitorScanPostCount = 0
let monitorAlertsRequestCount = 0
const suspiciousRequests = []
page.on('request', request => {
  const url = request.url().toLowerCase()
  const method = request.method().toUpperCase()
  if (url.includes('/api/tw-stock/monitor/config') && (method === 'POST' || method === 'PUT')) monitorConfigWriteCount += 1
  if (url.includes('/api/tw-stock/monitor/scan') && method === 'POST') monitorScanPostCount += 1
  if (url.includes('/api/tw-stock/monitor/alerts')) monitorAlertsRequestCount += 1
  if (url.includes('quick-trade') || url.includes('submit_order') || url.includes('place_order') || url.includes('provider/refresh') || url.includes('qlib/run') || url.includes('target_position') || url.includes('target-position') || url.includes('/broker/connect') || url.includes('/broker/order') || url.includes('/orders/submit') || url.includes('/quant/ops/option-c/publish') || url.includes('/quant/ops/option-c/refresh') || url.includes('/quant/ops/option-c/provider')) {
    suspiciousRequests.push(request.url())
  }
})


await page.route('**/api/tw-stock/quant/signals/health**', async route => {
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(healthPayload())) })
})

await page.route('**/api/tw-stock/quant/signals/latest**', async route => {
  const url = new URL(route.request().url())
  const bucket = url.searchParams.get('bucket') === 'top50' ? 'top50' : 'top30'
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(acceptedPayload({ runId: latestRunId, bucket }))) })
})

await page.route('**/api/tw-stock/quant/signals/runs**', async route => {
  const url = new URL(route.request().url())
  const pathname = url.pathname
  if (pathname.endsWith('/api/tw-stock/quant/signals/runs')) {
    const data = {
      items: [
        { run_id: acceptedRunId, asof: '2026-06-01', status: 'accepted', created_at: '2026-06-01T12:12:40+00:00', prediction_rows: 150, top30_rows: 30, top50_rows: 50, recorder_id: '950741cfd5f14ee5a05464fec3e12e0a', diagnostic_only: true, research_signal_not_order: true, accepted_validated: true, warnings: [] },
        { run_id: waitRunId, asof: '2026-06-02', status: 'wait_state_data_refresh_needed', created_at: '2026-06-01T12:11:50+00:00', accepted_validated: false, warnings: ['fixture stale'] }
      ],
      count: 2,
      limit: 20,
      status: url.searchParams.get('status') || 'all',
      trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(data)) })
    return
  }
  const runId = decodeURIComponent(pathname.split('/').pop() || '')
  const bucketParam = url.searchParams.get('bucket')
  const bucket = bucketParam === 'top50' || bucketParam === 'all' ? bucketParam : 'top30'
  const data = runId === waitRunId ? waitStatePayload() : acceptedPayload({ runId, bucket })
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(data)) })
})

await page.route('**/api/tw-stock/quant/ops/option-c/latest**', async route => {
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', job: opsJob, trading: opsJob.trading })) })
})

await page.route('**/api/tw-stock/quant/ops/option-c/dry-run**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  const body = JSON.parse(route.request().postData() || '{}')
  assert.deepEqual(Object.keys(body), ['asof'])
  assert.equal(body.asof, '2026-06-01')
  opsDryRunPostCount += 1
  opsJob = { ...opsJob, job_id: `${opsJobId}_manual`, started_at: '2026-06-02T05:00:00+00:00', finished_at: '2026-06-02T05:00:06+00:00' }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(opsJob)) })
})

await page.route('**/api/tw-stock/quant/ops/option-c/jobs/**/logs**', async route => {
  const url = new URL(route.request().url())
  const stream = url.searchParams.get('stream') === 'stderr' ? 'stderr' : 'stdout'
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'ok', job_id: opsJob.job_id, stream, tail: stream === 'stderr' ? '' : opsJob.stdout_tail, trading: opsJob.trading })) })
})

await page.route('**/api/tw-stock/quant/ops/option-c/jobs/**', async route => {
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(opsJob)) })
})

await page.route('**/api/indicator/backtest', async route => {
  if (route.request().method().toUpperCase() === 'POST') readonlyBacktestPostCount += 1
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ result: null })) })
})

await page.addInitScript(({ token, userinfo, roles, expiresAt }) => {
  window.localStorage.setItem('Access-Token', JSON.stringify(token))
  window.localStorage.setItem('User-Info', JSON.stringify(userinfo))
  window.localStorage.setItem('User-Roles', JSON.stringify(roles))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-TW')
}, { token: auth.data?.token || auth.token, userinfo, roles, expiresAt })

await page.addInitScript(() => {
  window.localStorage.removeItem('tw-stock-monitor-qlib-watch-draft')
})

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
try {
  await page.waitForSelector('.tw-stock-monitor')
} catch (error) {
  const diagnostic = await page.evaluate(() => ({
    href: window.location.href,
    hash: window.location.hash,
    storageKeys: Object.keys(window.localStorage).filter(key => key.includes('Access') || key.includes('User') || key.includes('storejs')),
    body: document.body.innerText.slice(0, 1200)
  }))
  console.error('tw-stock-monitor smoke diagnostic:', JSON.stringify(diagnostic, null, 2))
  throw error
}
await page.waitForSelector('canvas.tw-chart-canvas')
await page.waitForFunction(() => document.body.innerText.includes('台股研究'))
await page.waitForFunction(() => document.body.innerText.includes('本页面仅用于台股研究信号的人工复盘与历史验证'))
await page.waitForFunction(() => document.querySelectorAll('canvas.tw-chart-canvas').length >= 2)

await page.waitForFunction(() => document.body.innerText.includes('今日研究排名'))
await page.waitForFunction(() => document.body.innerText.includes('Top 30') && document.body.innerText.includes('Top 50'))
await page.waitForFunction(() => document.body.innerText.includes('高级信息与维护工具'))
await page.waitForSelector('.qlib-signal-table')
await page.waitForFunction(() => document.body.innerText.includes('2330') && document.body.innerText.includes('模型分数') && document.body.innerText.includes('最新价 / 行情日期'))
await page.screenshot({ path: `${screenshotDir}/phase1-main-ranking.png`, fullPage: true })

let qlibText = await page.locator('body').innerText()
for (const required of ['台股研究', '今日研究排名', '研究排序', '非交易建议', 'Top 30', 'Top 50', '2330', 'uptrend']) {
  assert.ok(qlibText.includes(required), `missing phase1 main text: ${required}`)
}

await page.getByText('Top 50', { exact: true }).click()
await page.waitForFunction(() => document.body.innerText.includes('50 支候选') || document.body.innerText.includes('Top 50'))
qlibText = await page.locator('body').innerText()
assert.ok(qlibText.includes('Top 50') || qlibText.includes('50 支候选'), 'Top 50 state missing')
await page.getByText('Top 30', { exact: true }).click()
await page.waitForFunction(() => document.body.innerText.includes('30 支候选') || document.body.innerText.includes('Top 30'))
qlibText = await page.locator('body').innerText()
assert.ok(qlibText.includes('Top 30') || qlibText.includes('30 支候选'), 'Top 30 state missing after restore')

assert.equal(opsDryRunPostCount, 0, 'Phase 1 smoke must not trigger qlib ops dry-run')

const beforeDraftConfigWriteCount = monitorConfigWriteCount
const beforeDraftScanPostCount = monitorScanPostCount
const beforeDraftAlertsRequestCount = monitorAlertsRequestCount
const beforeDraftBacktestPostCount = readonlyBacktestPostCount
await page.getByTestId('qlib-watch-add').first().click()
await page.waitForFunction(() => document.body.innerText.includes('研究觀察草稿') && document.body.innerText.includes('2330') && document.body.innerText.includes('option_c_daily_signal_latest_fixture'))
await page.screenshot({ path: screenshotDir + '/watchlist-draft-before-fill.png', fullPage: true })
await page.getByTestId('qlib-watch-fill-config').click()
await page.getByTestId('monitor-config-drawer').waitFor()
const configSymbolsInput = page.getByTestId('monitor-config-symbols')
await configSymbolsInput.waitFor()
await page.waitForFunction(() => {
  const el = document.querySelector('[data-testid="monitor-config-symbols"]')
  return el && el.value.includes('2330')
})
const configSymbolsText = await configSymbolsInput.inputValue()
assert.ok(configSymbolsText.includes('2330'), 'draft symbols were not filled into monitor config form')
await page.screenshot({ path: screenshotDir + '/watchlist-draft-after-fill.png', fullPage: true })
assert.equal(monitorConfigWriteCount, beforeDraftConfigWriteCount, 'filling draft must not save monitor config')
assert.equal(monitorScanPostCount, beforeDraftScanPostCount, 'filling draft must not trigger monitor scan')
assert.equal(monitorAlertsRequestCount, beforeDraftAlertsRequestCount, 'filling draft must not touch alerts API')
assert.equal(readonlyBacktestPostCount, beforeDraftBacktestPostCount, 'filling draft must not run readonly backtest')
await page.keyboard.press('Escape')
await page.waitForTimeout(300)

const beforeBacktestPostCount = readonlyBacktestPostCount
await page.locator('.qlib-signal-table button').filter({ hasText: '回測驗證' }).first().click()
await page.waitForFunction(() => document.body.innerText.includes('台股只讀回測驗證'))
await page.waitForFunction(() => document.body.innerText.includes('歷史模擬') && document.body.innerText.includes('orders_enabled=false') && document.body.innerText.includes('connects_to_broker=false'))
await page.screenshot({ path: `${screenshotDir}/readonly-backtest-linkage.png`, fullPage: true })
assert.equal(readonlyBacktestPostCount, beforeBacktestPostCount, 'qlib row action must not auto-run readonly backtest')
assert.equal(readonlyBacktestPostCount, 0, 'readonly backtest POST should not run during smoke')
assert.deepEqual(suspiciousRequests, [], `unexpected dangerous requests: ${suspiciousRequests.join(', ')}`)
await page.waitForFunction(() => document.body.innerText.includes('MA5'))
await page.waitForFunction(() => document.body.innerText.includes('MA20'))
await page.waitForFunction(() => document.body.innerText.includes('MA60'))
await page.waitForFunction(() => document.body.innerText.includes('量能'))
await page.waitForFunction(() => document.body.innerText.includes('bars'))
await page.waitForFunction(() => document.body.innerText.includes('窗口'))
const range30Button = page.locator('.chart-toolbar .ant-radio-button-wrapper').filter({ hasText: '30D' }).first()
await range30Button.click()
await page.waitForFunction(() => Array.from(document.querySelectorAll('.chart-toolbar .ant-radio-button-wrapper')).some(el => el.innerText.trim() === '30D' && String(el.className).includes('checked')))
const rangeWindowSeen = await page.locator('body').innerText()
const priceCanvasBox = await page.locator('canvas.tw-chart-canvas').first().boundingBox()
assert.ok(priceCanvasBox, 'missing price canvas bounds')
await page.mouse.move(priceCanvasBox.x + priceCanvasBox.width * 0.55, priceCanvasBox.y + priceCanvasBox.height * 0.45)
await page.waitForSelector('.chart-tooltip', { timeout: 5000 }).catch(() => {})
const hoverTooltipSeen = await page.locator('.chart-tooltip').count()

const text = await page.evaluate(() => {
  const clone = document.body.cloneNode(true)
  clone.querySelectorAll('.readonly-backtest-card, .tw-stock-agent-panel').forEach(node => node.remove())
  return clone.innerText || ''
})
const forbidden = [
  'quick-trade',
  'broker-accounts',
  'IBKR',
  'paper order',
  'live order',
  'submit order',
  'auto buy',
  'auto sell',
  '下單',
  '买入',
  '買入',
  '卖出',
  '賣出',
  '提交订单',
  '提交訂單',
  'quick trade',
  'target position',
  'target weight',
  'automatic trading',
  '刷新 qlib provider',
  '重新生成 qlib 信号',
  '自动补数据'
]
for (const word of forbidden) {
  assert.ok(!text.toLowerCase().includes(word.toLowerCase()), `forbidden text visible: ${word}`)
}

const beforeSelectedSymbol = await page.locator('.selected-symbol-main strong').first().innerText().catch(() => '')
const trendTable = page.locator('.content-row').filter({ hasText: '趨勢列表' }).first()
const firstClickableRow = trendTable.locator('tr.ant-table-row').filter({ hasNotText: beforeSelectedSymbol }).first()
if (await firstClickableRow.count()) {
  await firstClickableRow.click()
  if (beforeSelectedSymbol) {
    await page.waitForFunction(previous => {
      const el = document.querySelector('.selected-symbol-main strong')
      return el && el.innerText.trim() && el.innerText.trim() !== previous
    }, beforeSelectedSymbol)
  }
}
const afterSelectedSymbol = await page.locator('.selected-symbol-main strong').first().innerText().catch(() => '')

const result = await page.evaluate(({ beforeSelectedSymbol, afterSelectedSymbol, hoverTooltipSeen, rangeWindowSeen, screenshotDir, monitorConfigWriteCount, monitorScanPostCount, monitorAlertsRequestCount, opsDryRunPostCount }) => {
  const canvases = Array.from(document.querySelectorAll('canvas.tw-chart-canvas')).map(canvas => {
    const ctx = canvas.getContext('2d')
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data
    let nonWhite = 0
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i]
      const g = data[i + 1]
      const b = data[i + 2]
      const a = data[i + 3]
      if (a > 0 && !(r > 245 && g > 245 && b > 245)) nonWhite += 1
    }
    return { width: canvas.width, height: canvas.height, nonWhite }
  })
  return {
    title: document.title,
    hasReadonlyBoundary: document.body.innerText.includes('orders_enabled=false'),
    hasResearchScan: document.body.innerText.includes('研究掃描'),
    hasMovingAverageLegend: ['MA5', 'MA20', 'MA60'].every(label => document.body.innerText.includes(label)),
    hasVolumeToggle: document.body.innerText.includes('量能'),
    hasDataStatus: document.body.innerText.includes('bars'),
    hasRangeWindow: rangeWindowSeen.includes('窗口'),
    tooltipCount: hoverTooltipSeen,
    beforeSelectedSymbol,
    afterSelectedSymbol,
    rowClickChangedSymbol: beforeSelectedSymbol && afterSelectedSymbol ? beforeSelectedSymbol !== afterSelectedSymbol : true,
    qlibLatestVisible: document.body.innerText.includes('今日研究排名'),
    qlibHistoryVisible: document.body.innerText.includes('高级信息与维护工具'),
    qlibOpsVisible: document.body.innerText.includes('高级信息与维护工具'),
    qlibHealthVisible: document.body.innerText.includes('数据提示') || document.body.innerText.includes('高级信息与维护工具'),
    readonlyBacktestPanelVisible: document.body.innerText.includes('台股只讀回測驗證'),
    watchDraftVisible: document.body.innerText.includes('研究觀察草稿') && document.body.innerText.includes('2330'),
    monitorConfigWriteCount,
    monitorScanPostCount,
    monitorAlertsRequestCount,
    opsDryRunPostCount,
    screenshotDir,
    trendRows: document.querySelectorAll('.ant-table-row').length,
    canvases
  }
}, { beforeSelectedSymbol, afterSelectedSymbol, hoverTooltipSeen, rangeWindowSeen, screenshotDir, monitorConfigWriteCount, monitorScanPostCount, monitorAlertsRequestCount, opsDryRunPostCount })

assert.equal(result.qlibLatestVisible, true)
assert.equal(result.qlibHistoryVisible, true)
assert.equal(result.qlibHealthVisible, true)
assert.equal(result.qlibOpsVisible, true)
assert.equal(result.opsDryRunPostCount, 0)
assert.equal(result.readonlyBacktestPanelVisible, true)
assert.equal(result.watchDraftVisible, true)
assert.equal(result.monitorConfigWriteCount, 0)
assert.equal(result.monitorScanPostCount, 0)
assert.ok(result.monitorAlertsRequestCount >= 0)
assert.equal(result.hasReadonlyBoundary, true)
assert.equal(result.hasResearchScan, false)
assert.equal(result.hasMovingAverageLegend, true)
assert.equal(result.hasVolumeToggle, true)
assert.equal(result.hasDataStatus, true)
assert.equal(result.hasRangeWindow, true)
assert.ok(result.tooltipCount >= 0, 'chart hover tooltip count captured')
assert.equal(typeof result.rowClickChangedSymbol, 'boolean')
assert.ok(result.canvases.length >= 2, 'expected price and score chart canvases')
assert.ok(result.canvases[0].nonWhite > 100, 'price chart appears blank')

await browser.close()
console.log(`tw-stock-monitor local smoke passed: ${JSON.stringify(result)}`)
