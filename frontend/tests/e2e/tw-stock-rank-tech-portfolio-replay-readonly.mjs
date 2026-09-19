import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.message ? data.message : 'success', data }
}

function rankTechItems () {
  return [
    {
      symbol: '2330', name: '台积电', rank: 1, rankTier: 'top10',
      qlib: { rank: 1, score: 0.31, asof: '2026-06-04' },
      trend: { label: 'uptrend', score: 76, latest_date: '2026-06-04', ok: true, warnings: [] },
      positionRisk: { status: 'reasonable', label: '位置合理', score: 32, reason: '价格位置未显示明显偏高信号。', metrics: {}, warnings: [] },
      technical: { status: 'technical_strong', summary: { supportive_count: 3, neutral_count: 1, caution_count: 0, data_insufficient_count: 0 }, warnings: [], reason: '趋势和轻量指标状态一致偏支持。', positionRisk: { status: 'reasonable', label: '位置合理', score: 32, reason: '价格位置未显示明显偏高信号。', metrics: {}, warnings: [] } },
      decision: { code: 'new_watch', label: '新增观察', reason: 'Top10 且技术状态偏强。' },
      actionPlan: { code: 'simulate_watch', label: '可模拟观察', priority: 'high', reason: '排名和趋势有支持，价格位置未显示明显偏高。', nextCheck: '只适合放入模拟观察。' }
    },
    {
      symbol: '2357', name: '华硕', rank: 8, rankTier: 'top10',
      qlib: { rank: 8, score: 0.24, asof: '2026-06-04' },
      trend: { label: 'sideways', score: 55, latest_date: '2026-06-04', ok: true, warnings: [] },
      positionRisk: { status: 'elevated', label: '强势但偏高', score: 68, reason: '趋势仍在，但价格靠近近 120 日高位。', metrics: {}, warnings: [] },
      technical: { status: 'technical_neutral', summary: { supportive_count: 1, neutral_count: 2, caution_count: 1, data_insufficient_count: 0 }, warnings: [], reason: '趋势和轻量指标未形成一致强确认。', positionRisk: { status: 'elevated', label: '强势但偏高', score: 68, reason: '趋势仍在，但价格靠近近 120 日高位。', metrics: {}, warnings: [] } },
      decision: { code: 'manual_review', label: '人工复核', reason: '模型靠前但趋势未确认。' },
      actionPlan: { code: 'wait_pullback', label: '等回调', priority: 'medium', reason: '标的值得看，但当前位置偏高。', nextCheck: '等热度降温。' }
    },
    {
      symbol: '2603', name: '长荣', rank: 22, rankTier: 'top30',
      qlib: { rank: 22, score: 0.12, asof: '2026-06-04' },
      trend: { label: 'pullback', score: 38, latest_date: '2026-06-04', ok: true, warnings: ['short_history_below_60_bars'] },
      positionRisk: { status: 'overheated', label: '过热谨慎', score: 86, reason: 'RSI 偏热且距离 20 日均线较远。', metrics: {}, warnings: [] },
      technical: { status: 'technical_weak', summary: { supportive_count: 0, neutral_count: 1, caution_count: 2, data_insufficient_count: 1 }, warnings: ['short_history_below_60_bars'], reason: '趋势或指标出现谨慎状态，降低技术确认强度。', positionRisk: { status: 'overheated', label: '过热谨慎', score: 86, reason: 'RSI 偏热且距离 20 日均线较远。', metrics: {}, warnings: [] } },
      decision: { code: 'risk_review', label: '风险复盘', reason: '技术状态偏弱。' },
      actionPlan: { code: 'chasing_review', label: '追高复核', priority: 'medium', reason: '趋势强不等于适合现在介入。', nextCheck: '先复核。' }
    }
  ]
}

function rankTechPayload (bucket = 'top30') {
  return {
    ok: true,
    status: 'accepted',
    simulation_only: true,
    research_signal_not_order: true,
    bucket,
    limit: 120,
    maxItems: bucket === 'top50' ? 50 : 30,
    qlib: { asof: '2026-06-04', run_id: 'rank_tech_fixture' },
    items: rankTechItems(),
    summary: { new_watch: 1, continue_watch: 0, risk_review: 1, manual_review: 1, observe_only: 0, data_insufficient: 0 },
    warnings: [],
    trading: { orders_enabled: false, connects_to_broker: false, research_signal_not_order: true }
  }
}

function ltrReadonlyExplanationPayload () {
  const disclaimer = '仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。'
  return {
    ok: true,
    schema_version: 'phase5_product_readonly_view_v1',
    payload_source: 'phase3c_readonly_explanation_payload',
    research_only: true,
    readonly_disclaimer: disclaimer,
    no_write_guarantees: { read_only_http_method: true, reads_static_payload_only: true, does_not_change_runtime_state: true },
    methods: [
      {
        method_key: 'phase1c_ltr_turnover_controlled_daily',
        method_label: 'Phase1C LTR turnover controlled daily',
        research_role_label: '少动作观察',
        why_no_action: '今天不动作的主要原因：最近窗口动作预算不足。',
        tradeoff_summary: '历史回放取舍：动作偏少，换手压力较低，回撤较低。',
        readonly_disclaimer: disclaimer,
        detail: {
          net_return_summary: 'common full range 历史回放费用后净值变化约为 +465.27%。',
          drawdown_summary: 'common full range 历史回放最大回撤约为 19.93%，回撤水平为较低。',
          action_count_summary: 'common full range 历史回放动作次数为 315，动作频率为较少。',
          turnover_summary: 'common full range 历史回放 notional turnover proxy 为 31.85，换手 proxy 水平为较低。',
          relative_to_top50_adaptive: '相对 Top50 adaptive，历史回放费用后净值差异为 -1131.10%；本方法动作次数为 315，notional turnover proxy 为 31.85，历史回放最大回撤为 19.93%。',
          detail_disclaimer: '这些数值只用于历史回放复盘，必须和动作、换手、回撤取舍一起阅读。'
        }
      }
    ]
  }
}

function ltrOptionalSimPayload () {
  const boundary = '仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。'
  const slice = { fold_id: 'phase1c_independent_test_range', period: 'phase1c_independent_test_range', test_period: 'phase1c_independent_test_range：2025-06-25 至 2026-05-07', walk_forward_mode: 'phaseb1_fixed_candidate_replay', fee_tax_adjusted_net_return: 3.550601, max_drawdown: -0.160298, action_count: 384, turnover_proxy_by_notional_over_avg_equity: 36.664086, oos_interpretation_allowed: true }
  const fullRange = { ...slice, fold_id: 'common_full_range_shared_by_all_compared_methods', period: 'common_full_range_shared_by_all_compared_methods', test_period: 'common_full_range_shared_by_all_compared_methods：2022-01-01 至 2026-05-07', fee_tax_adjusted_net_return: 40.01822, max_drawdown: -0.387816, action_count: 1978, turnover_proxy_by_notional_over_avg_equity: 199.489876 }
  const summary = { period_count: 8, positive_period_count: 7, detail_layer_only: true }
  return {
    ok: true,
    schema_version: 'phaseb2_ltr_simple_default_readonly_product_view_v1',
    payload_source: 'phaseb1_conservative_replay_artifacts',
    default_method_key: 'phase1c_ltr_simple_daily',
    boundary_text: boundary,
    selection_policy: { default_selected: true, ltr_auto_enabled: false, ltr_simple_default: true, top50_adaptive_reference_only: true, readonly_only: true },
    strategies: [
      { method_key: 'phase1c_ltr_simple_daily', display_name: 'LTR simple 默认主策略', role: 'default_main_strategy', status_label: '默认 / 独立测试较强 / 动作较多', is_default_baseline: true, is_default_main_strategy: true, is_optional_ltr: true, note: '在固定候选的独立测试区间表现较强，动作和换手略高；历史混合区间只作复盘参考。', sample_scope: slice.test_period, oos_interpretation_allowed: true, metrics: slice, primary_evidence_period: 'phase1c_independent_test_range', full_range_metrics: fullRange, split_purity_note: '首屏主指标使用独立测试区间；common full range 为 train/validation/independent_test 混合历史复盘，不作为样本外泛化证明。', method_summary: summary, walk_forward: [slice, fullRange], rolling_summary: summary, boundary_text: boundary },
      { method_key: 'rank_rotate_top50_adaptive_score', display_name: 'Top50 自适应规则参考', role: 'rule_based_reference', status_label: '规则简单 / 换手略低', is_default_baseline: false, is_default_main_strategy: false, is_optional_ltr: false, note: '规则更容易理解；独立测试区间表现低于默认 LTR，但动作和换手略低。', sample_scope: slice.test_period, oos_interpretation_allowed: true, metrics: { ...slice, fee_tax_adjusted_net_return: 2.450848, max_drawdown: -0.167457, action_count: 386, turnover_proxy_by_notional_over_avg_equity: 37.15186 }, method_summary: summary, walk_forward: [{ ...slice, fee_tax_adjusted_net_return: 15.963677, action_count: 1932, turnover_proxy_by_notional_over_avg_equity: 184.497379 }], rolling_summary: summary, boundary_text: boundary },
      { method_key: 'phase1c_ltr_conservative_top30_2day_confirm_daily', display_name: 'LTR Top30 连续确认', role: 'conservative_reference', status_label: '保守 / 低动作 / 低换手', is_default_baseline: false, is_default_main_strategy: false, is_optional_ltr: true, note: '连续确认后才动作；独立测试区间表现低于默认 LTR，但动作明显更少。', sample_scope: slice.test_period, oos_interpretation_allowed: true, metrics: { ...slice, fee_tax_adjusted_net_return: 1.257516, max_drawdown: -0.098271, action_count: 63, turnover_proxy_by_notional_over_avg_equity: 6.17243 }, method_summary: summary, walk_forward: [{ ...slice, fee_tax_adjusted_net_return: 7.42078, action_count: 312, turnover_proxy_by_notional_over_avg_equity: 30.456281 }], rolling_summary: summary, boundary_text: boundary },
      { method_key: 'phase1c_ltr_conservative_top20_entry_2day_exit_daily', display_name: 'LTR Top20 严格入选', role: 'conservative_reference', status_label: '更严格入选 / 低动作', is_default_baseline: false, is_default_main_strategy: false, is_optional_ltr: true, note: '入选更严格，动作明显更少，作为低频参考；历史混合区间不代表未来收益。', sample_scope: slice.test_period, oos_interpretation_allowed: true, metrics: { ...slice, fee_tax_adjusted_net_return: 0.65007, max_drawdown: -0.143129, action_count: 63, turnover_proxy_by_notional_over_avg_equity: 6.207663 }, method_summary: summary, walk_forward: [{ ...slice, fee_tax_adjusted_net_return: 8.060574, action_count: 314, turnover_proxy_by_notional_over_avg_equity: 29.893958 }], rolling_summary: summary, boundary_text: boundary }
    ],
    no_write_guarantees: { read_only_http_method: true, reads_static_artifacts_only: true, does_not_change_runtime_state: true, does_not_touch_monitor_or_execution_paths: true, does_not_touch_broker_or_orders: true },
    research_only: true
  }
}

function portfolioPayload () {
  const base = {
    equityCurve: [{ date: '2026-01-02', equity: 1000000 }, { date: '2026-06-04', equity: 1060000 }],
    historicalActions: [
      { date: '2026-02-01', symbol: '2330', action: 'historical_add', simulation_only: true },
      { date: '2026-03-01', symbol: '2603', action: 'historical_risk_reduce', simulation_only: true }
    ],
    dataQuality: { warnings: [] }
  }
  return {
    ok: true,
    status: 'accepted',
    simulation_only: true,
    research_signal_not_order: true,
    persist: false,
    writes_business_db: false,
    orders_enabled: false,
    connects_to_broker: false,
    comparison: {
      qlib_only: { ...base, metrics: { totalReturn: 0.045, maxDrawdown: -0.021, actionCount: 8, feeAndTax: 1234.5 } },
      qlib_plus_trend: { ...base, metrics: { totalReturn: 0.052, maxDrawdown: -0.018, actionCount: 6, feeAndTax: 980.25 } },
      qlib_plus_trend_indicators: { ...base, metrics: { totalReturn: 0.061, maxDrawdown: -0.015, actionCount: 5, feeAndTax: 876.4 }, dataQuality: { warnings: ['missing_close:fixture'] } },
      qlib_plus_trend_position_risk: { ...base, metrics: { totalReturn: 0.058, maxDrawdown: -0.012, actionCount: 4, feeAndTax: 720.1 }, positionRiskSummary: { blocked_overheated_adds: 2, deprioritized_elevated_adds: 1, risk_review_events: 1 } }
    },
    strategyComparison: {
      confirmed_exit: { ...base, profile: { key: 'confirmed_exit', label: '连续转弱才复盘', description: '不因单日排名波动退出，连续转弱后才做风险复盘。' }, metrics: { totalReturn: 0.055, maxDrawdown: -0.017, actionCount: 3, feeAndTax: 610 } },
      rank_rotate_top50_adaptive_score: { ...base, profile: { key: 'rank_rotate_top50_adaptive_score', label: 'Top50 自适应 score', description: '继承 Top50 轮动；正常市况不干预，谨慎/下跌市况只从 qlib score 0.04-0.08 的 Top10 候选补仓。' }, metrics: { totalReturn: 0.052, maxDrawdown: -0.019, actionCount: 10, feeAndTax: 1450 }, adaptiveScoreSummary: { enabled: true, blocked_adds: 2 } },
      rank_rotate_top50_adaptive_score_risk_control: { ...base, profile: { key: 'rank_rotate_top50_adaptive_score_risk_control', label: 'Top50 自适应 score + 风控', description: '继承 Top50 自适应 score；市场谨慎/下跌且组合回撤扩大时暂停补仓。' }, metrics: { totalReturn: 0.039, maxDrawdown: -0.014, actionCount: 8, feeAndTax: 1200 }, adaptiveScoreSummary: { enabled: true, blocked_adds: 2 }, portfolioRiskSummary: { enabled: true, blocked_adds: 1 } },
      rank_rotate_top50: { ...base, profile: { key: 'rank_rotate_top50', label: '跌出 Top50 轮动', description: '持仓跌出 Top50 时才卖出排名最低的一支，再从 Top10 最高排名补一支。' }, metrics: { totalReturn: 0.044, maxDrawdown: -0.026, actionCount: 12, feeAndTax: 1800 } },
      rank_rotate_top30: { ...base, profile: { key: 'rank_rotate_top30', label: '跌出 Top30 轮动', description: '持仓跌出 Top30 时卖出排名最低的一支，再从 Top10 最高排名补一支。' }, metrics: { totalReturn: 0.036, maxDrawdown: -0.021, actionCount: 16, feeAndTax: 2200 } }
    },
    dataQuality: { point_in_time: true, warnings: ['missing_close:fixture'] },
    trading: { orders_enabled: false, connects_to_broker: false, writes_orders: false, writes_positions: false, research_signal_not_order: true }
  }
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(45000)

const requests = []
const forbiddenRequests = []
let latestRequestCount = 0
let observationRequestCount = 0
let portfolioReplayRequestCount = 0
let ltrReadonlyExplanationRequestCount = 0
let ltrOptionalSimStrategiesRequestCount = 0
let portfolioPersistFalseCount = 0
let simRequestCount = 0
let simWriteRequestCount = 0
let quickTradeRequestCount = 0
let brokerRequestCount = 0
let realOrderRequestCount = 0
let monitorConfigWriteCount = 0
let monitorScanPostCount = 0
let monitorAlertsWriteCount = 0
let qlibOpsPostCount = 0
let acceptedLatestSwitchCount = 0
let providerPublishRefreshCount = 0
let targetPositionRequestCount = 0
let targetWeightRequestCount = 0
const pageErrors = []
const failedResponses = []
const rankTechResponses = []

page.on('pageerror', error => pageErrors.push(String(error && (error.stack || error.message || error))))
page.on('response', response => {
  const url = response.url()
  if (response.status() >= 400) failedResponses.push({ status: response.status(), url })
  if (url.includes('/api/tw-stock/rank-tech-cross/')) rankTechResponses.push({ status: response.status(), url })
})
page.on('request', request => {
  const method = request.method().toUpperCase()
  const rawUrl = request.url()
  const url = rawUrl.toLowerCase()
  requests.push({ method, url: rawUrl })
  if (url.includes('/api/tw-stock/rank-tech-cross/latest')) latestRequestCount += 1
  if (url.includes('/api/tw-stock/rank-tech-cross/observation-replay')) observationRequestCount += 1
  if (url.includes('/api/tw-stock/rank-tech-cross/portfolio-replay')) portfolioReplayRequestCount += 1
  if (url.includes('/api/tw-stock/ltr-readonly-explanation')) ltrReadonlyExplanationRequestCount += 1
  if (url.includes('/api/tw-stock/ltr-optional-sim-strategies')) ltrOptionalSimStrategiesRequestCount += 1
  if (url.includes('/api/tw-stock/sim/')) simRequestCount += 1
  if (url.includes('/api/tw-stock/sim/') && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) simWriteRequestCount += 1
  if (url.includes('/api/quick-trade/')) quickTradeRequestCount += 1
  if (url.includes('/api/broker/') || url.includes('/broker/')) brokerRequestCount += 1
  if (url.includes('/api/order') || url.includes('/api/orders') || url.includes('/orders/submit')) realOrderRequestCount += 1
  if (url.includes('/api/tw-stock/monitor/config') && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) monitorConfigWriteCount += 1
  if (url.includes('/api/tw-stock/monitor/scan') && method === 'POST') monitorScanPostCount += 1
  if (url.includes('/api/tw-stock/monitor/alerts') && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) monitorAlertsWriteCount += 1
  if (url.includes('/api/tw-stock/quant/ops/') && method === 'POST') qlibOpsPostCount += 1
  if (url.includes('accepted-latest') || url.includes('accepted_latest')) acceptedLatestSwitchCount += 1
  if (/(publish|refresh-provider|provider-refresh|provider\/refresh)/.test(url)) providerPublishRefreshCount += 1
  if (url.includes('target_position') || url.includes('target-position')) targetPositionRequestCount += 1
  if (url.includes('targetweight') || url.includes('target_weight') || url.includes('target-weight')) targetWeightRequestCount += 1
  if (simWriteRequestCount || quickTradeRequestCount || brokerRequestCount || realOrderRequestCount || monitorConfigWriteCount || monitorScanPostCount || monitorAlertsWriteCount || qlibOpsPostCount || acceptedLatestSwitchCount || providerPublishRefreshCount || targetPositionRequestCount || targetWeightRequestCount) {
    forbiddenRequests.push({ method, url: rawUrl })
  }
})

await page.route('**/api/auth/info**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ id: 1, username: 'rank-tech-e2e', role: { id: 'default', permissions: ['dashboard'] } })) }))
await page.route('**/api/auth/security-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ turnstile_enabled: false })) }))
await page.route('**/api/strategies/notifications/unread-count**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ count: 0 })) }))
await page.route('**/api/settings/brand-config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ app_name: 'QuantDinger', app_version: 'e2e' })) }))
await page.route('**/api/policy/broker-market**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, disabled: true })) }))

await page.route('**/api/tw-stock/ltr-readonly-explanation**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(ltrReadonlyExplanationPayload())) })
})

await page.route('**/api/tw-stock/ltr-optional-sim-strategies**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(ltrOptionalSimPayload())) })
})

await page.route('**/api/tw-stock/rank-tech-cross/latest**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  const url = new URL(route.request().url())
  const bucket = url.searchParams.get('bucket') === 'top50' ? 'top50' : 'top30'
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(rankTechPayload(bucket))) })
})

await page.route('**/api/tw-stock/rank-tech-cross/observation-replay**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', daily: [], comparison: {}, simulation_only: true })) })
})

await page.route('**/api/tw-stock/rank-tech-cross/portfolio-replay', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  const body = JSON.parse(route.request().postData() || '{}')
  assert.equal(body.persist, false, 'portfolio replay must force persist=false')
  assert.equal(body.initialCash, 1000000)
  assert.equal(body.maxHoldings, 10)
  assert.equal(body.lotSize, 10)
  portfolioPersistFalseCount += 1
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse(portfolioPayload())) })
})

await page.route('**/api/tw-stock/monitor/config**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ name: 'default', symbols: ['2330'], limit_bars: 120, refresh_interval_sec: 0, enabled: false })) }))
await page.route('**/api/tw-stock/monitor/history**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/alerts**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/monitor/scan-logs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ health: { status: 'ok' } })) }))
await page.route('**/api/tw-stock/trends**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/quant/signals/health**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', latest: { asof: '2026-06-04', exists: true, accepted_validated: true }, freshness: {}, runs: {}, dataAvailability: {} })) }))
await page.route('**/api/tw-stock/quant/signals/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', asof: '2026-06-04', bucket: 'top30', signals: [], trading: { orders_enabled: false, connects_to_broker: false } })) }))
await page.route('**/api/tw-stock/quant/signals/rank-changes**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, entered: [], exited: [], stayed: [], top_gainers: [], top_decliners: [], watch_candidates: [], summary: {} })) }))
await page.route('**/api/tw-stock/quant/signals/runs**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, job: null })) }))
await page.route('**/api/tw-stock/quant/ops/option-c/scheduler**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, enabled: false, dry_run_only: true })) }))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, latest_status: 'accepted', latest_asof: '2026-06-04', trading: { orders_enabled: false, connects_to_broker: false } })) }))
await page.route('**/api/tw-stock/cross-analysis/latest**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-04' }, freshness: { warnings: [] } })) }))
await page.route('**/api/tw-stock/agent/context**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ qlib: { asof: '2026-06-04' }, freshness: { status: 'accepted' }, top30_preview: [] })) }))
await page.route('**/api/tw-stock/sim/accounts**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))
await page.route('**/api/indicator/kline**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse([])) }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(apiResponse({ items: [] })) }))

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'rank-tech-e2e-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'rank-tech-e2e', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
}, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-testid="rank-tech-portfolio-replay-readonly"]')
await page.waitForFunction(() => document.body.innerText.includes('今日复盘与历史模拟'))
try {
  await page.waitForFunction(() => document.body.innerText.includes('可模拟观察') && document.body.innerText.includes('过去表现'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('加入技术指标确认'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('加入追高风险过滤') && document.body.innerText.includes('位置过滤'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('总收益') && document.body.innerText.includes('最大回撤') && document.body.innerText.includes('费用税费估算'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('为什么现在不动') && document.body.innerText.includes('今天不动作的主要原因') && document.body.innerText.includes('历史回放取舍') && document.body.innerText.includes('少动作观察'), null, { timeout: 15000 })
  await page.waitForFunction(() => document.body.innerText.includes('可选模拟策略') && document.body.innerText.includes('默认主策略') && document.body.innerText.includes('LTR simple 默认主策略'), null, { timeout: 15000 })
} catch (error) {
  const diagnostic = await page.evaluate(() => ({
    href: window.location.href,
    text: document.querySelector('[data-testid="rank-tech-portfolio-replay-readonly"]')?.innerText || document.body.innerText.slice(0, 2000)
  }))
  const state = await page.evaluate(() => {
    const el = document.querySelector('.tw-stock-monitor')
    const vm = el && el.__vue__
    return vm ? {
      rankTechLatestPayload: vm.rankTechLatestPayload,
      rankTechAccepted: vm.rankTechAccepted,
      rankTechItemsLength: vm.rankTechItems && vm.rankTechItems.length,
      rankTechPriorityItemsLength: vm.rankTechPriorityItems && vm.rankTechPriorityItems.length,
      rankTechStatusText: vm.rankTechStatusText,
      portfolioReplayComparisonItemsLength: vm.portfolioReplayComparisonItems && vm.portfolioReplayComparisonItems.length,
      rankTechLatestError: vm.rankTechLatestError,
      portfolioReplayPayload: vm.portfolioReplayPayload,
      portfolioReplayError: vm.portfolioReplayError,
      loadingRankTechCross: vm.loadingRankTechCross,
      runningPortfolioReplay: vm.runningPortfolioReplay
    } : null
  })
  console.error('rank-tech e2e diagnostic:', JSON.stringify({ diagnostic, state, latestRequestCount, portfolioReplayRequestCount, rankTechResponses, failedResponses, pageErrors, requests: requests.slice(-20) }, null, 2))
  throw error
}

const ltrPanelText = await page.getByTestId('ltr-readonly-explanation-panel').innerText()
const ltrPanelBox = await page.getByTestId('ltr-readonly-explanation-panel').boundingBox()
const portfolioSectionBox = await page.locator('.portfolio-replay-section').boundingBox()
assert.ok(ltrPanelBox && portfolioSectionBox && ltrPanelBox.y < portfolioSectionBox.y, 'LTR explanation should stay inside the replay card before detailed replay metrics')
for (const required of ['为什么现在不动', '今天不动作的主要原因', '历史回放取舍', '少动作观察', '仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。']) {
  assert.ok(ltrPanelText.includes(required), `missing LTR first-screen text: ${required}`)
}
for (const forbidden of ['费用后净值变化', '+465.27%', '最大回撤约为', 'notional turnover proxy', '胜率', '上涨概率', '目标仓位']) {
  assert.ok(!ltrPanelText.includes(forbidden), `LTR first screen should not expose high-risk detail: ${forbidden}`)
}
const optionalSimPanelText = await page.getByTestId('ltr-optional-sim-strategy-panel').innerText()
for (const required of ['可选模拟策略', '默认主策略', 'LTR simple 默认主策略', '费用后历史模拟', '最大回撤', '动作数', '换手 proxy', 'independent_test 切片', '首屏主指标使用独立测试区间', '样本内/验证/样本外混合结果', '仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。']) {
  assert.ok(optionalSimPanelText.includes(required), `missing optional sim text: ${required}`)
}
for (const forbidden of ['推荐策略', '更优策略', '最佳策略', '建议买入', '建议卖出', '目标权重', '胜率', '上涨概率', '自动执行', '替代默认策略']) {
  assert.ok(!optionalSimPanelText.includes(forbidden), `optional sim panel contains forbidden text: ${forbidden}`)
}

const replayCardTextBeforeDetails = await page.getByTestId('rank-tech-portfolio-replay-readonly').innerText()
assert.ok(replayCardTextBeforeDetails.indexOf('今日复盘与历史模拟') < replayCardTextBeforeDetails.indexOf('为什么现在不动'), 'main replay title should precede LTR explanation')
assert.ok(replayCardTextBeforeDetails.indexOf('今天先看什么') < replayCardTextBeforeDetails.indexOf('为什么现在不动'), 'daily review flow should precede LTR explanation')

const text = await page.locator('[data-testid="rank-tech-portfolio-replay-readonly"]').innerText()
for (const required of ['只读历史模拟', '不是投资建议', '不连接券商', '不生成订单', '今天先看什么', '为什么', '可模拟观察', '等回调', '追高复核', '策略规则回放', '连续转弱才复盘', 'Top50 自适应 score', 'Top50 自适应 score + 风控', '跌出 Top50 轮动', '跌出 Top30 轮动', '位置合理', '强势但偏高', '过热谨慎', '位置过滤', '总收益', '最大回撤', '费用税费估算']) {
  assert.ok(text.includes(required), `missing rendered text: ${required}`)
}
for (const forbidden of ['立即买入', '立即卖出', '自动买入', '自动卖出', '下单', '提交订单', '目标仓位', '上涨概率', '收益承诺', '直接跟排名', '加入追高过滤', '等回调再观察']) {
  assert.ok(!text.includes(forbidden), `forbidden rendered text: ${forbidden}`)
}

await page.getByTestId('rank-tech-replay-controls').getByText('Top50', { exact: true }).click()
await page.waitForTimeout(300)
await page.getByTestId('rank-tech-replay-controls').getByText('近一年', { exact: true }).click()
await page.waitForTimeout(300)
await page.locator('[data-testid="rank-tech-replay-controls"] .ant-select').click()
await page.getByRole('option', { name: '加入趋势确认' }).click()
await page.waitForTimeout(300)

const summary = {
  latest_request_count: latestRequestCount,
  observation_replay_request_count: observationRequestCount,
  portfolio_replay_request_count: portfolioReplayRequestCount,
  ltr_readonly_explanation_request_count: ltrReadonlyExplanationRequestCount,
  ltr_optional_sim_strategies_request_count: ltrOptionalSimStrategiesRequestCount,
  portfolio_persist_false_count: portfolioPersistFalseCount,
  sim_request_count: simRequestCount,
  sim_write_request_count: simWriteRequestCount,
  quick_trade_request_count: quickTradeRequestCount,
  broker_request_count: brokerRequestCount,
  real_order_request_count: realOrderRequestCount,
  monitor_config_write_count: monitorConfigWriteCount,
  monitor_scan_post_count: monitorScanPostCount,
  monitor_alerts_write_count: monitorAlertsWriteCount,
  qlib_ops_post_count: qlibOpsPostCount,
  accepted_latest_switch_count: acceptedLatestSwitchCount,
  provider_publish_refresh_count: providerPublishRefreshCount,
  target_position_request_count: targetPositionRequestCount,
  target_weight_request_count: targetWeightRequestCount,
  forbidden_request_count: forbiddenRequests.length,
  page_error_count: pageErrors.length
}

assert.ok(summary.latest_request_count >= 1, 'rank-tech latest was not requested')
assert.ok(summary.portfolio_replay_request_count >= 1, 'portfolio replay was not requested')
assert.ok(summary.ltr_readonly_explanation_request_count >= 1, 'LTR readonly explanation endpoint should be requested')
assert.ok(summary.ltr_optional_sim_strategies_request_count >= 1, 'LTR optional sim endpoint should be requested')
assert.equal(summary.portfolio_replay_request_count, summary.portfolio_persist_false_count, 'each portfolio replay request must persist=false')
assert.equal(summary.sim_write_request_count, 0)
assert.equal(summary.quick_trade_request_count, 0)
assert.equal(summary.broker_request_count, 0)
assert.equal(summary.real_order_request_count, 0)
assert.equal(summary.monitor_config_write_count, 0)
assert.equal(summary.monitor_scan_post_count, 0)
assert.equal(summary.monitor_alerts_write_count, 0)
assert.equal(summary.qlib_ops_post_count, 0)
assert.equal(summary.accepted_latest_switch_count, 0)
assert.equal(summary.provider_publish_refresh_count, 0)
assert.equal(summary.target_position_request_count, 0)
assert.equal(summary.target_weight_request_count, 0)
assert.equal(summary.forbidden_request_count, 0, JSON.stringify(forbiddenRequests, null, 2))
assert.equal(summary.page_error_count, 0, pageErrors.join('\n'))

await browser.close()
console.log(`tw-stock rank-tech portfolio replay readonly e2e passed: ${JSON.stringify(summary)}`)
