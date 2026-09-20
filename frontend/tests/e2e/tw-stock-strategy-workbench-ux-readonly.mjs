import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.TW_STOCK_MONITOR_BASE_URL || 'http://127.0.0.1:8000'
const artifactDir = process.env.TW_UI2D_WORKBENCH_ARTIFACT_DIR || path.resolve(process.cwd(), '../tmp/tw_ui2d_workbench_acceptance')
const faultIsolation = process.env.TW_UI2D_FAULT_ISOLATION === 'true'
await mkdir(artifactDir, { recursive: true })

function apiResponse (data) {
  return { code: data && data.ok === false ? 0 : 1, msg: data && data.message ? data.message : 'success', data }
}

function tradingFlags () {
  return { orders_enabled: false, connects_to_broker: false, writes_orders: false, writes_positions: false, research_signal_not_order: true }
}

function isWriteMethod (method) {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
}

function classifyForbiddenRequest (method, rawUrl, postData = '') {
  const url = rawUrl.toLowerCase()
  const body = String(postData || '').toLowerCase()
  if (
    url.includes('api.openai.com') ||
    url.includes('/v1/chat/completions') ||
    url.includes('/v1/responses') ||
    body.includes('openai_api_key') ||
    body.includes('openai api key')
  ) return 'frontend_openai_direct'
  if (method === 'POST' && url.includes('/api/tw-stock/agent/simple-chat')) {
    if (body.includes('order') || body.includes('target_position') || body.includes('target_weight') || body.includes('broker') || body.includes('quick-trade')) return 'agent_simple_chat_trade_payload'
    return ''
  }
  if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return ''
  if (url.includes('/api/tw-stock/monitor/config')) return 'monitor_config_write'
  if (url.includes('/api/tw-stock/monitor/scan')) return 'monitor_scan_post'
  if (url.includes('/api/tw-stock/monitor/alerts')) return 'monitor_alerts_write'
  if (url.includes('/api/tw-stock/quant/ops/') && (url.includes('publish') || url.includes('refresh') || url.includes('provider') || url.includes('accepted'))) return 'provider_publish_refresh_accepted'
  if (url.includes('/api/quick-trade') || url.includes('/api/broker') || url.includes('/broker/')) return 'broker_quick_trade'
  if (url.includes('order/submit') || url.includes('/orders') || url.includes('target-position') || url.includes('target_position') || url.includes('target_weight')) return 'order_or_target_position'
  if (isWriteMethod(method)) return 'unexpected_write_request'
  return ''
}

function currentStrategyContextPayload () {
  return {
    ok: true,
    status: 'ready',
    context: {
      signal_asof: '2026-06-18',
      target_date: '2026-06-19',
      default_model_id: 'e4_frozen_qlib_2018_2022',
      display_model_id: 'e4_frozen_qlib_2018_2022',
      strategy_rule: 'top50_exit_one_worst_sell',
      ranking_source: 'qlib_model_a',
      candidate_boundary: 'qlib_top50',
      qlib_top50_count: 50,
      qlib_top150_count: 150,
      ltr_top50_count: 50,
      ltr_top_symbol: '2330',
      top_ltr_symbol: '2330'
    },
    rankings: { qlib_top50: [{ instrument: 'TW2330', score_rank: 1 }], qlib_top150: [] },
    trading: tradingFlags()
  }
}

function phaseYZStatusPayload () {
  return {
    ok: true,
    state: 'pending_execution_price',
    signal_asof: '2026-06-17',
    target_next_trading_day: '2026-06-18',
    execution_price_mode: 'next_open',
    execution_price_status: 'execution_price_pending',
    paper_apply_allowed: false,
    paper_apply_blocked_reason: 'execution_price_pending',
    selected_strategy_rule_id: 'top50_exit_one_worst_sell',
    models: [
      { model_id: 'e4_frozen_qlib_2018_2022' },
      { model_id: 'e4_frozen_qlib_2023_2025_ltr' }
    ],
    strategies: [{ strategy_rule_id: 'top50_exit_one_worst_sell' }],
    trading: tradingFlags()
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
      exit_candidates: [
        { symbol: '2357', stock_name: '华硕', full_qlib_rank: 67, in_qlib_top50_candidate: false }
      ]
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

function modelStrategyComparisonPayload (rawUrl) {
  const params = new URL(rawUrl).searchParams
  const modelId = params.get('model_id') || 'model_a_only'
  return {
    ok: true,
    schema_version: 'readonly_model_strategy_comparison_api_v1',
    readonly_only: true,
    no_apply: true,
    runtime_effect: 'none',
    catalog: {
      models: [
        { model_id: 'model_a_only', display_name: 'Model A', framework_role: 'model_track', governance_status: 'active_baseline', workflow_policy: 'required', virtual_account_eligible: true, production_default: true, role: 'active_baseline', comparison_selectable: true },
        { model_id: 'model_a_plus_b_b19r2r', display_name: 'Model A + Model B (B19R2R)', framework_role: 'model_track', governance_status: 'research_candidate', workflow_policy: 'nonblocking', virtual_account_eligible: false, production_default: false, role: 'research_candidate', comparison_selectable: true }
      ],
      strategies: [
        { strategy_id: 'top50_exit_one_worst_sell', display_name: 'Top 50 / exit one worst', comparison_selectable: true },
        { strategy_id: 'phase1c_ltr_simple_daily', display_name: 'Legacy LTR simple daily', compatibility: 'legacy_lineage_only', comparison_selectable: false, compatible_model_ids: [] }
      ],
      windows: [{ window_id: 'b19r2r_retrospective_complete_20260813_20260901', display_name: '完整特征历史回放（14 日）' }],
      combinations: [
        { combination_id: 'model_a_only__top50_exit_one_worst_sell__b19r2r_complete_14d', model_id: 'model_a_only', strategy_id: 'top50_exit_one_worst_sell', window_id: 'b19r2r_retrospective_complete_20260813_20260901', comparison_selectable: true },
        { combination_id: 'model_a_plus_b_b19r2r__top50_exit_one_worst_sell__b19r2r_complete_14d', model_id: 'model_a_plus_b_b19r2r', strategy_id: 'top50_exit_one_worst_sell', window_id: 'b19r2r_retrospective_complete_20260813_20260901', comparison_selectable: true }
      ],
      virtual_account_policy: {
        default_track_id: 'model_a_only',
        selection_parameter: 'model_track_id',
        allowed_track_ids: ['model_a_only'],
        extension_requires_admission_review: true
      }
    },
    selected: {
      model_id: modelId,
      strategy_id: 'top50_exit_one_worst_sell',
      window_id: 'b19r2r_retrospective_complete_20260813_20260901',
      combination_id: modelId === 'model_a_only' ? 'model_a_only__top50_exit_one_worst_sell__b19r2r_complete_14d' : 'model_a_plus_b_b19r2r__top50_exit_one_worst_sell__b19r2r_complete_14d'
    },
    result: { model_id: modelId },
    comparison: {
      results: [
        { model_id: 'model_a_only', framework_role: 'model_track', governance_status: 'active_baseline', workflow_policy: 'required', metrics: { net_return: -0.003394721942222456, max_drawdown: -0.02293822433302306, fee_tax: 3499.721331871033, turnover: 1.4944290048217774, top5_abs_contribution_share: 0.7665576923271123 }, gate_status: 'BASELINE_DESCRIPTOR_ACTIVE_MODEL_A_ONLY', artifacts: { model_signal: {}, order_intent: {}, replay_result: {} } },
        { model_id: 'model_a_plus_b_b19r2r', framework_role: 'model_track', governance_status: 'research_candidate', workflow_policy: 'nonblocking', metrics: { net_return: 0.062462478661684306, max_drawdown: -0.013392308393651242, fee_tax: 4427.477011533738, turnover: 1.7575382537078856, top5_abs_contribution_share: 0.7309891627334426 }, gate_status: 'NOT_EVALUATED_FOR_ORIGINAL_TOP50_NO_REPLACEMENT', artifacts: { model_signal: {}, order_intent: {}, replay_result: {} } }
      ],
      delta: { net_return_b_minus_a: 0.06585720060390676 },
      deltas_from_default: { model_a_plus_b_b19r2r: { net_return_minus_default: 0.06585720060390676 } },
      diagnostics: {
        joint_status: 'NOT_EVALUATED_FOR_CURRENT_BOUNDARY',
        admission_effect: 'NONE_NOT_EVALUATED',
        bootstrap_95pct_lower_bound: null,
        negative_twii20_regime_return_delta: null,
        concentration: { top5_abs_contribution_share: null },
        failed_gate_ids: []
      }
    },
    status: { selection_changes_display_only: true, can_apply: false, baseline_admission_allowed: false },
    safety: { http_method: 'GET_ONLY', paper_portfolio_write: false, runtime_write: false, baseline_or_production_change: false },
    sources: { catalog: 'fixture/readonly_model_strategy_comparison/catalog.json' }
  }
}

const paperAccountId = 'paper-ui2d'
const paperDecisionId = 'paper-decision-ui2d'
function paperLatestDecision () {
  return {
    ok: true,
    status: 'ok',
    asof: '2026-06-17',
    model_id: 'e4_frozen_qlib_2023_2025_ltr',
    strategy_rule: 'top50_exit_one_worst_sell',
    decision_id: paperDecisionId,
    paper_account_id: paperAccountId,
    paper_account_epoch: 7,
    input_checksum: 'sha256:ui2d-paper-fixture',
    paper_order_intent_artifact_path: 'fixture/paper/order_intent.json',
    preview: { cash_before: 500000, readonly_preview_only: true },
    intent: {
      actions: [
        { action_type: 'paper_sell_intent', instrument: 'TW2357', symbol: '2357', quantity: 1000, reason: 'outside_top50_review', estimated_reference_price: 342, applicability: 'applicable' },
        { action_type: 'paper_buy_intent', instrument: 'TW2330', symbol: '2330', quantity: 100, reason: 'top_ltr_candidate', estimated_reference_price: 920, applicability: 'applicable' },
        { action_type: 'paper_skip', instrument: 'TW2317', symbol: '2317', quantity: 0, reason: 'paper_skip', applicability: 'not_applicable' }
      ]
    },
    trading: tradingFlags(),
    simulation_only: true
  }
}

function paperState () {
  return {
    ok: true,
    paper_account: { account_uid: paperAccountId, cash: 500000, initial_cash: 500000, paper_account_epoch: 7, simulation_only: true },
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
    context_digest: { signal_asof: '2026-06-18', target_date: '2026-06-19', checksum: 'sha256:ui2d-agent-fixture', freshness_status: 'accepted' }
  }
}

function readonlyOpsStatusPayload () {
  return {
    ok: true,
    schema_version: 'daov1.readonly_ops_status.v1',
    status: 'readonly_status_available',
    readonly_only: true,
    provider_raw_latest: {
      source: 'fixture raw daily bars',
      asof: '2026-06-21',
      source_max_date: '2026-06-21',
      raw_status: 'READY',
      evidence_path: 'fixture/finmind_stdout.txt',
      caveat: 'raw evidence may be newer than formal qlib provider calendar max 2026-06-18'
    },
    qlib_accepted_latest: {
      source: 'fixture/latest_signal.json',
      asof: '2026-06-18',
      run_id: 'ui2d-accepted-fixture',
      status: 'accepted',
      stale: true,
      freshness: { pending_asof: '2026-06-21', pending_reason: 'fresh_data_wait', next_retry_hint: 'fixture retry next scheduled daily auto run' },
      evidence_path: 'fixture/latest_signal.json',
      separate_from_controlled_signal_latest: true
    },
    controlled_signal_latest: {
      source: 'fixture/controlled_signal/latest.json',
      signal_asof: '2026-06-18',
      run_id: 'controlled-signal-ui2d',
      readonly_only: true,
      pointer_sha256: 'sha256-controlled-fixture',
      evidence_path: 'fixture/controlled_signal/latest.json',
      caveat: 'controlled signal latest is distinct from qlib accepted latest'
    },
    readonly_strategy_snapshot_latest: {
      source: 'fixture/readonly_strategy_snapshot/latest.json',
      signal_asof: '2026-06-18',
      target_date: '2026-06-19',
      checksum: 'sha256-snapshot-fixture',
      pointer_sha256: 'sha256-snapshot-pointer-fixture',
      validation: { readonly_only: true, candidate_only: true, not_provider_accepted_latest: true, production_trade_enabled: false },
      evidence_path: 'fixture/readonly_strategy_snapshot/latest.json'
    },
    agent_prompt_latest: {
      source: 'fixture/agent_daily_prompt/latest.json',
      signal_asof: '2026-06-18',
      target_date: '2026-06-19',
      checksum: 'sha256-agent-fixture',
      pointer_sha256: 'sha256-agent-pointer-fixture',
      validation: { readonly_only: true, production_trade_enabled: false, manifest: 'fixture/agent_daily_prompt/manifest.json' },
      evidence_path: 'fixture/agent_daily_prompt/latest.json'
    },
    latest_natural_cron_job: {
      job_id: 'daily_tw_stock_auto_update_20260621_fixture',
      asof: '2026-06-21',
      started_at: '2026-06-21T10:30:00Z',
      finished_at: '2026-06-21T10:31:00Z',
      status: 'daily_auto_update_passed',
      daily_chain_state: 'RAW_READY_PROVIDER_STALE',
      blocker: { status: 'RAW_READY_PROVIDER_STALE', blockers: ['qlib_provider_view_or_formal_calendar'], blocked_at: 'qlib_provider_view_or_formal_calendar', reason: 'formal provider calendar is stale' },
      next_retry_hint: 'retry next scheduled daily auto run',
      evidence_path: 'fixture/job.json'
    },
    latest_dapr18_evidence_job: {
      job_id: 'daily_tw_stock_auto_update_20260621_fixture',
      asof: '2026-06-21',
      job_status: 'daily_auto_update_passed',
      dapr18_status: 'dry_run_plan_recorded',
      readiness_state: 'BLOCKED_WITH_REASON',
      attempted: true,
      dry_run: true,
      blockers: ['controlled_signal_latest_asof_mismatch_or_missing'],
      evidence_dir: 'fixture/dapr18'
    },
    dapr18_controls: {
      enabled: true,
      dry_run: true,
      build_candidates: false,
      publish_controlled_signal_latest: false,
      publish_readonly_snapshot_latest: false,
      publish_agent_prompt_latest: false,
      exact_authorization_present: false,
      latest_pointer_write_performed: false
    },
    protected_pointers: {
      all_unchanged: true,
      fingerprints: {}
    },
    forbidden_actions: {
      all_false: true,
      actions: {},
      audit_path: 'fixture/dapr18_forbidden_action_audit.json',
      route_scope: 'GET only'
    },
    next_action_hint: 'provider/raw latest 已到 2026-06-21，qlib accepted latest 仍为 2026-06-18；等待桥接验证通过后才会推进。',
    b19r2r_shadow: { state: 'BLOCKED', asof: '2026-06-18', last_ready_asof: null, mainline_blocking: false, production_allowed: false, no_apply: true },
    ui_wording_contract: {
      warnings: ['本状态只读，不刷新 provider、不切换 accepted/latest、不发布 controlled signal/snapshot/Agent prompt。']
    },
    trading: tradingFlags(),
    all_readonly_guards: true
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
let simpleChatCount = 0

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
  const reason = classifyForbiddenRequest(method, url, postData)
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

// Broad readonly fallbacks first; specific fixtures below override them.
await page.route('**/api/**', route => {
  const url = route.request().url()
  if (url.includes('/src/api/')) return route.continue()
  return fulfillJson(route, { ok: true, status: 'fixture', items: [], trading: tradingFlags() })
})
await page.route('**/api/auth/info**', route => fulfillJson(route, { id: 1, username: 'ui2d', role: { id: 'default', permissions: ['dashboard'] } }))
await page.route('**/api/auth/security-config**', route => fulfillJson(route, { turnstile_enabled: false }))
await page.route('**/api/settings/brand-config**', route => fulfillJson(route, { app_name: 'QuantDinger' }))
await page.route('**/api/strategies/notifications/unread-count**', route => fulfillJson(route, { count: 0 }))
await page.route('**/api/policy/broker-market**', route => fulfillJson(route, { ok: true, disabled: true }))
await page.route('**/api/indicator/backtest/tw-stock/templates**', route => fulfillJson(route, { ok: true, templates: [], items: [] }))
await page.route('**/api/indicator/kline**', route => fulfillJson(route, []))

await page.route('**/api/tw-stock/current-strategy-context**', route => fulfillJson(route, currentStrategyContextPayload()))
await page.route('**/api/tw-stock/phase-yz/productization-status**', route => faultIsolation
  ? fulfillJson(route, { ok: false, message: '模拟账户状态暂不可读' }, 503)
  : fulfillJson(route, phaseYZStatusPayload()))
await page.route('**/api/tw-stock/readonly-strategy-snapshot**', route => fulfillJson(route, readonlyStrategySnapshotPayload()))
await page.route('**/api/tw-stock/tradingagents-readonly-analysis/latest**', route => fulfillJson(route, {
  ok: true,
  status: 'pass',
  readonly_only: true,
  not_order: true,
  not_target_position: true,
  not_investment_advice: true,
  production_trade_enabled: false,
  raw_files_included: false,
  run_id: 'ta-ui-fixture',
  signal_asof: '2026-06-18',
  target_date: '2026-06-19',
  source: { project: 'TradingAgents', project_path: 'third_party/tradingagents', vendored: true },
  sanitized_report: {
    schema_version: 'tradingagents_sanitized_report_v1',
    run_id: 'ta-ui-fixture',
    signal_asof: '2026-06-18',
    target_date: '2026-06-19',
    symbols: [{
      symbol: '2330',
      instrument: 'TW2330',
      research_summary: '外部多智能体研究摘要指出，产业新闻与基本面线索需要人工复核。',
      bull_points: ['先进制程需求仍是支持线索。'],
      bear_points: ['汇率与库存变化是压力线索。'],
      risk_review_points: ['事件风险需要人工复核。'],
      data_limitations: ['fixture 不联网，不代表实时资讯。'],
      human_review_questions: ['利多与利空线索是否有足够只读证据支持？']
    }]
  },
  validation: { ok: true, check_count: 20, failed_checks: [] },
  claim_support_audit: { ok: true, claim_count: 1 }
}))
await page.route('**/api/tw-stock/readonly-replay-window-index**', route => fulfillJson(route, replayIndexPayload()))
await page.route(/\/api\/tw-stock\/readonly-replay-window(?:\?.*)?$/, route => fulfillJson(route, replayWindowPayload()))
await page.route('**/api/tw-stock/readonly/model-strategy-comparison**', route => {
  assert.equal(route.request().method().toUpperCase(), 'GET')
  return fulfillJson(route, modelStrategyComparisonPayload(route.request().url()))
})
await page.route('**/api/tw-stock/paper-portfolio/latest-decision**', route => fulfillJson(route, paperLatestDecision()))
await page.route('**/api/tw-stock/paper-portfolio/state**', route => fulfillJson(route, paperState()))
await page.route('**/api/tw-stock/paper-portfolio/apply-runs**', route => fulfillJson(route, { ok: true, items: [] }))
await page.route('**/api/tw-stock/agent/context**', route => fulfillJson(route, { ok: true, qlib: { asof: '2026-06-18' }, freshness: { status: 'accepted' }, disclaimers: ['仅供研究观察，不构成交易建议。'] }))
await page.route('**/api/tw-stock/agent/simple-chat**', async route => {
  assert.equal(route.request().method().toUpperCase(), 'POST')
  simpleChatCount += 1
  const body = JSON.parse(route.request().postData() || '{}')
  assert.equal(body.question, '为什么模拟账户不能应用？')
  assert.ok(!Object.prototype.hasOwnProperty.call(body, 'target_position'))
  assert.ok(!Object.prototype.hasOwnProperty.call(body, 'target_weight'))
  await fulfillJson(route, simpleChatPayload())
})
await page.route('**/api/tw-stock/quant/signals/health**', route => fulfillJson(route, { ok: true, status: 'accepted', latest: { exists: true, asof: '2026-06-18', run_id: 'ui2d-accepted-fixture', accepted_validated: true }, freshness: { stale: true, stale_reason: 'asof_age_gt_3', asof_age_days: 3 }, trading: tradingFlags() }))
await page.route('**/api/tw-stock/quant/signals/latest**', route => fulfillJson(route, { ok: true, status: 'accepted', bucket: 'top30', signals: [{ symbol: '2330', rank: 1, score: 0.58 }], trading: tradingFlags() }))
await page.route('**/api/tw-stock/quant/signals/rank-changes**', route => fulfillJson(route, { ok: true, entered: [], exited: [], stayed: [], summary: {} }))
await page.route('**/api/tw-stock/quant/signals/runs**', route => fulfillJson(route, { ok: true, items: [] }))
await page.route('**/api/tw-stock/quant/ops/option-c/latest**', route => fulfillJson(route, { ok: true, job: null, trading: tradingFlags() }))
await page.route('**/api/tw-stock/quant/ops/option-c/scheduler**', route => fulfillJson(route, { ok: true, enabled: false }))
await page.route('**/api/tw-stock/quant/ops/readonly-status**', route => fulfillJson(route, readonlyOpsStatusPayload()))
await page.route('**/api/tw-stock/quant/ops/daily-auto-update/status**', route => fulfillJson(route, { ok: true, latest_status: 'accepted', latest_asof: '2026-06-18', latest_run_id: 'ui2d-accepted-fixture', last_job_status: 'daily_auto_update_passed', trading: tradingFlags() }))
await page.route('**/api/tw-stock/cross-analysis/latest**', route => fulfillJson(route, { ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-18' }, freshness: { status: 'stale', qlib: { asof: '2026-06-18' }, quantdinger: { latest_date_min: '2026-06-21', latest_date_max: '2026-06-21', source: 'fixture raw daily bars' }, warnings: ['qlib_raw_date_gap_gt_1'] } }))
await page.route('**/api/tw-stock/rank-tech-cross/latest**', route => fulfillJson(route, { ok: true, status: 'accepted', items: [], qlib: { asof: '2026-06-18' }, trading: tradingFlags() }))
await page.route('**/api/tw-stock/ltr-readonly-explanation**', route => fulfillJson(route, { ok: true, methods: [] }))
await page.route('**/api/tw-stock/ltr-optional-sim-strategies**', route => fulfillJson(route, { ok: true, strategies: [] }))
await page.route('**/api/tw-stock/monitor/config**', route => faultIsolation
  ? fulfillJson(route, { ok: false, message: '监控配置暂不可读' }, 503)
  : fulfillJson(route, { name: 'default', symbols: ['2330'], enabled: false }))
await page.route('**/api/tw-stock/monitor/alerts**', route => fulfillJson(route, { items: [] }))
await page.route('**/api/tw-stock/monitor/history**', route => fulfillJson(route, { items: [] }))
await page.route('**/api/tw-stock/monitor/scan-logs**', route => fulfillJson(route, { health: { status: 'ok' } }))
await page.route('**/api/tw-stock/trends**', route => fulfillJson(route, { items: [] }))
await page.route('**/api/tw-stock/sim/accounts**', route => fulfillJson(route, { items: [] }))

const expiresAt = Date.now() + 3600_000
await page.addInitScript(({ expiresAt }) => {
  window.localStorage.setItem('Access-Token', JSON.stringify({ token: 'ui2d-token' }))
  window.localStorage.setItem('User-Info', JSON.stringify({ id: 1, username: 'ui2d', role: { id: 'default', permissions: ['dashboard'] } }))
  window.localStorage.setItem('User-Roles', JSON.stringify(['dashboard']))
  window.localStorage.setItem('__storejs_expire_mixin_Access-Token', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Info', String(expiresAt))
  window.localStorage.setItem('__storejs_expire_mixin_User-Roles', String(expiresAt))
  window.localStorage.setItem('lang', 'zh-CN')
  window.localStorage.removeItem('tw-stock-sim-draft-context')
}, { expiresAt })

await page.goto(`${baseUrl}/#/tw-stock-monitor`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.tw-stock-monitor', { timeout: 45000 })
const comparisonPanel = page.getByTestId('readonly-model-strategy-comparison-panel')
await comparisonPanel.waitFor()
const comparisonText = await comparisonPanel.innerText()
assert.ok(comparisonText.includes('6.25%'))
assert.ok(comparisonText.includes('研究候选'))
assert.ok(comparisonText.includes('尚未重新评估'))
assert.ok(comparisonText.includes('所有模型轨道都不能在本页直接应用'))
assert.ok(comparisonText.includes('当前允许列表只有 Model A'))
assert.equal(await page.getByTestId('data-freshness-technical-details').getAttribute('open'), null)
await page.getByTestId('data-freshness-technical-details').locator('summary').click()
assert.ok((await page.getByTestId('b19r2r-shadow-status').innerText()).includes('影子信号阻断'))
assert.ok((await page.getByTestId('b19r2r-shadow-status').innerText()).includes('不阻塞 Model A 日更'))
await page.getByTestId('data-freshness-technical-details').locator('summary').click()
await page.waitForFunction(() => document.querySelector('[data-testid="strategy-workbench-overview-card"]').innerText.includes('2026-06-18'))
const initialContextRequests = allRequests.filter(item => item.url.includes('/api/tw-stock/current-strategy-context'))
assert.equal(initialContextRequests.length, 1, 'initial strategy context should be fetched once')
if (faultIsolation) {
  await page.waitForFunction(() => document.body.innerText.includes('监控配置暂不可读；模型信号、候选名单与历史比较仍独立加载'))
  assert.ok((await page.getByTestId('readonly-strategy-snapshot-panel').innerText()).includes('台积电'))
}
await comparisonPanel.locator('.ant-select').first().click()
await page.getByText('Model A + Model B (B19R2R)（研究候选）', { exact: true }).last().click()
await page.waitForFunction(() => document.body.innerText.includes('Model A + Model B (B19R2R)（研究候选） · Top 50 / exit one worst'))
const advancedToggle = page.getByRole('checkbox', { name: '高级研究与运维' })
assert.equal(await advancedToggle.isChecked(), false)
assert.equal(await page.getByTestId('rank-tech-portfolio-replay-readonly').isVisible(), false)
await advancedToggle.check()
assert.equal(await page.getByTestId('rank-tech-portfolio-replay-readonly').isVisible(), true)
assert.ok((await page.locator('.tw-stock-monitor').innerText()).includes('模拟账户说明'))
await page.getByTestId('qlib-sim-draft').first().click()
await page.waitForFunction(() => document.body.innerText.includes('当前策略工作台为只读模式，不生成模拟交易草稿'))
assert.equal(await page.evaluate(() => window.localStorage.getItem('tw-stock-sim-draft-context')), null)
assert.ok(!page.url().includes('/tw-stock-sim-account'))
await advancedToggle.uncheck()
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
    const required = ['数据链路状态', '查看数据链路详情', 'provider/raw latest 已到 2026-06-21', 'qlib accepted latest 仍为 2026-06-18', '策略总览', '目标交易日：2026-06-19', '已作为历史状态隔离', '模型与策略对比', '6.25%', '研究候选', '尚未重新评估', '所有模型轨道都不能在本页直接应用', '当前允许列表只有 Model A', '怎么理解这次对比', '仍需完成准入审查后才能加入虚拟账户允许列表或调整默认模型', '候选名单', '历史模拟', '模拟账户状态', '解释原因', '策略解释助手', '不构成交易建议', '不连接券商', '不产生真实交易委托']
    const forbiddenMain = ['统一策略上下文', 'YZ Clean E4 产品化', 'clean registry', 'execution_price_mode: next_open', '只展示 Model A / Model B', 'paper_order_intent_artifact_path', 'ReplayWindowPolicy', 'final equity', 'turnover_proxy_by_notional_over_avg_equity', '生成模拟草稿']
    const visibleText = Array.from(document.querySelectorAll('body *')).filter(el => {
      const style = window.getComputedStyle(el)
      const rect = el.getBoundingClientRect()
      return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0
    }).map(el => el.innerText || '').join('\n')
    const openDrawerCount = Array.from(document.querySelectorAll('.ant-drawer.ant-drawer-open')).length
    const openTechPanelCount = Array.from(document.querySelectorAll('.ant-collapse-item-active')).length
    const buttonOverflow = Array.from(document.querySelectorAll('button')).filter(el => el.scrollWidth > el.clientWidth + 2).map(el => el.innerText.trim()).filter(Boolean)
    const cardOverflow = Array.from(document.querySelectorAll('.ant-card, .paper-portfolio-panel, .readonly-strategy-snapshot, .readonly-replay-window, .readonly-comparison, .tw-stock-agent-panel')).filter(el => el.scrollWidth > el.clientWidth + 2).map(el => (el.getAttribute('data-testid') || el.className || '').toString())
    const styleEvidence = selector => {
      const el = document.querySelector(selector)
      if (!el) return null
      const style = window.getComputedStyle(el)
      return {
        display: style.display,
        paddingTop: style.paddingTop,
        borderTopStyle: style.borderTopStyle,
        borderTopWidth: style.borderTopWidth
      }
    }
    return {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      required_missing: required.filter(item => !text.includes(item)),
      forbidden_visible: forbiddenMain.filter(item => visibleText.includes(item)),
      open_drawer_count: openDrawerCount,
      open_tech_panel_count: openTechPanelCount,
      freshness_details_collapsed: !document.querySelector('[data-testid="data-freshness-technical-details"]').open,
      button_overflow: buttonOverflow,
      card_overflow: cardOverflow,
      candidate_row_style: styleEvidence('.readonly-candidate-row'),
      replay_metric_style: styleEvidence('.readonly-replay-window .readonly-snapshot-metric')
    }
  })
  await page.screenshot({ path: path.join(artifactDir, `${name}.png`), fullPage: true })
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(200)
  await page.screenshot({ path: path.join(artifactDir, `${name}-first-screen.png`) })
  for (const [label, selector] of [['comparison', '[data-testid="readonly-model-strategy-comparison-panel"]'], ['candidates', '[data-testid="readonly-strategy-snapshot-panel"]'], ['replay', '[data-testid="readonly-replay-window-panel"]'], ['agent', '#daov-section-agent']]) {
    await page.locator(selector).screenshot({ path: path.join(artifactDir, `${name}-${label}.png`) })
  }
  return metrics
}

const viewportResults = {
  desktop: await viewportAudit('desktop', 1440, 980),
  tablet: await viewportAudit('tablet', 1024, 768),
  mobile: await viewportAudit('mobile', 390, 900)
}

const networkAudit = {
  schema_version: 'tw_ui2d_workbench_network_audit.v1',
  request_count: allRequests.length,
  simple_chat_request_count: simpleChatCount,
  model_strategy_comparison_requests: allRequests.filter(item => item.url.includes('/api/tw-stock/readonly/model-strategy-comparison')),
  forbidden_request_count: forbiddenRequests.length,
  forbidden_requests: forbiddenRequests,
  suspicious_requests: suspiciousRequests,
  monitor_config_write_count: forbiddenRequests.filter(item => item.reason === 'monitor_config_write').length,
  monitor_scan_post_count: forbiddenRequests.filter(item => item.reason === 'monitor_scan_post').length,
  monitor_alerts_write_count: forbiddenRequests.filter(item => item.reason === 'monitor_alerts_write').length,
  ops_dry_run_post_count: forbiddenRequests.filter(item => item.reason === 'provider_publish_refresh_accepted').length,
  frontend_openai_direct_request_count: forbiddenRequests.filter(item => item.reason === 'frontend_openai_direct').length,
  broker_quick_trade_order_request_count: forbiddenRequests.filter(item => item.reason === 'broker_quick_trade' || item.reason === 'order_or_target_position').length,
  failed_response_count: failedResponses.length,
  failed_responses: failedResponses
}
const consoleAudit = {
  schema_version: 'tw_ui2d_workbench_console_audit.v1',
  console_error_count: consoleErrors.length,
  page_error_count: pageErrors.length,
  console_messages: consoleMessages,
  console_errors: consoleErrors,
  page_errors: pageErrors
}
const audit = {
  schema_version: 'tw_ui2d_workbench_acceptance.v1',
  base_url: baseUrl,
  artifact_dir: artifactDir,
  viewport_results: viewportResults,
  required_text_passed: Object.values(viewportResults).every(row => row.required_missing.length === 0),
  forbidden_visible_passed: Object.values(viewportResults).every(row => row.forbidden_visible.length === 0),
  overflow_passed: Object.values(viewportResults).every(row => row.overflowX === false),
  drawer_default_closed_passed: Object.values(viewportResults).every(row => row.open_drawer_count === 0),
  button_overflow_passed: Object.values(viewportResults).every(row => row.button_overflow.length === 0),
  component_styles_passed: Object.values(viewportResults).every(row => row.candidate_row_style && row.candidate_row_style.display === 'grid' && row.candidate_row_style.paddingTop !== '0px' && row.candidate_row_style.borderTopStyle !== 'none' && row.replay_metric_style && row.replay_metric_style.paddingTop !== '0px' && row.replay_metric_style.borderTopStyle !== 'none'),
  card_overflow_diagnostic: Object.fromEntries(Object.entries(viewportResults).map(([key, row]) => [key, row.card_overflow])),
  technical_details_default_collapsed: Object.values(viewportResults).every(row => row.open_tech_panel_count === 0)
}
await writeFile(path.join(artifactDir, 'audit.json'), JSON.stringify(audit, null, 2))
await writeFile(path.join(artifactDir, 'network_audit.json'), JSON.stringify(networkAudit, null, 2))
await writeFile(path.join(artifactDir, 'console_audit.json'), JSON.stringify(consoleAudit, null, 2))

await browser.close()

assert.equal(simpleChatCount, 1)
assert.ok(networkAudit.model_strategy_comparison_requests.length >= 2)
assert.ok(networkAudit.model_strategy_comparison_requests.every(item => item.method === 'GET'))
assert.equal(networkAudit.forbidden_request_count, 0, JSON.stringify(networkAudit.forbidden_requests, null, 2))
assert.equal(networkAudit.monitor_config_write_count, 0)
assert.equal(networkAudit.monitor_scan_post_count, 0)
assert.equal(networkAudit.monitor_alerts_write_count, 0)
assert.equal(networkAudit.ops_dry_run_post_count, 0)
assert.equal(networkAudit.frontend_openai_direct_request_count, 0)
assert.equal(networkAudit.broker_quick_trade_order_request_count, 0)
const unexpectedFailedResponses = networkAudit.failed_responses.filter(item => !faultIsolation || !item.url.match(/\/api\/tw-stock\/(monitor\/config|phase-yz\/productization-status)/))
assert.equal(unexpectedFailedResponses.length, 0, JSON.stringify(unexpectedFailedResponses, null, 2))
assert.equal(consoleAudit.console_error_count, 0, JSON.stringify(consoleAudit.console_errors, null, 2))
assert.equal(consoleAudit.page_error_count, 0, JSON.stringify(consoleAudit.page_errors, null, 2))
assert.equal(audit.required_text_passed, true, JSON.stringify(viewportResults, null, 2))
assert.equal(audit.forbidden_visible_passed, true, JSON.stringify(viewportResults, null, 2))
assert.equal(audit.overflow_passed, true, JSON.stringify(viewportResults, null, 2))
assert.equal(audit.drawer_default_closed_passed, true, JSON.stringify(viewportResults, null, 2))
assert.equal(audit.button_overflow_passed, true, JSON.stringify(viewportResults, null, 2))
assert.equal(audit.component_styles_passed, true, JSON.stringify(viewportResults, null, 2))
assert.equal(audit.technical_details_default_collapsed, true, JSON.stringify(viewportResults, null, 2))
assert.ok(Object.values(viewportResults).every(item => item.freshness_details_collapsed))

console.log(JSON.stringify({ artifactDir, audit, networkAudit, consoleAudit }, null, 2))
