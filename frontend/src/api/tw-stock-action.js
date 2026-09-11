import request from '@/utils/request'

const BASE_URL = '/api/tw-stock'

export function saveTwStockMonitorConfig (data) {
  return request({
    url: `${BASE_URL}/monitor/config`,
    method: 'post',
    data
  })
}

export function updateTwStockAlert (id, data) {
  return request({
    url: `${BASE_URL}/monitor/alerts/${id}`,
    method: 'put',
    data
  })
}

export function scanTwStockMonitor (data) {
  return request({
    url: `${BASE_URL}/monitor/scan`,
    method: 'post',
    data
  })
}

export function scanAllTwStockMonitors (data) {
  return request({
    url: `${BASE_URL}/monitor/scan-all`,
    method: 'post',
    data
  })
}

// Explicit readonly simulation POST: classified as action surface, not pure GET readonly.
export function runTwStockPortfolioReplay (data = {}) {
  return request({
    url: `${BASE_URL}/rank-tech-cross/portfolio-replay`,
    method: 'post',
    data: {
      ...data,
      persist: false
    }
  })
}

export function saveTwStockCrossAnalysisReview (data) {
  return request({
    url: BASE_URL + "/cross-analysis/reviews",
    method: "put",
    data: {
      asof: data && data.asof,
      run_id: data && (data.run_id || data.runId),
      symbol: data && data.symbol,
      cross_category: data && (data.cross_category || data.crossCategory),
      decision_status: data && (data.decision_status || data.decisionStatus),
      user_note: data && (data.user_note || data.userNote)
    }
  })
}

export function chatTwStockAgent ({ question, symbol = "", maxItems = 10 } = {}) {
  return request({
    url: BASE_URL + "/agent/chat",
    method: "post",
    data: {
      question: String(question || "").slice(0, 500),
      symbol: String(symbol || "").trim(),
      maxItems: Math.max(1, Math.min(Number(maxItems || 10), 20))
    }
  })
}

export function triggerQlibOptionCDryRun (asof) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/dry-run`,
    method: 'post',
    data: { asof }
  })
}

export function triggerQlibOptionCSchedulerTick (data = {}) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/scheduler/tick`,
    method: 'post',
    data
  })
}

export function triggerQlibOptionCAcceptedLatestSchedulerTick (data = {}) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/accepted-latest-scheduler/tick`,
    method: 'post',
    data
  })
}

export function triggerQlibOptionCEodPipelineTick (data = {}) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/eod-pipeline/tick`,
    method: 'post',
    data
  })
}

export function triggerQlibOptionCEodAutomationTick (data = {}) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/eod-automation/tick`,
    method: 'post',
    data
  })
}

export function triggerQlibOptionCNormalPublish (data = {}) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/normal-publish`,
    method: 'post',
    data
  })
}

export function createTwStockSimAccount (data) {
  return request({
    url: `${BASE_URL}/sim/accounts`,
    method: 'post',
    data: {
      name: data && data.name,
      initial_cash: data && (data.initial_cash || data.initialCash)
    }
  })
}

export function applyTwStockPaperPortfolioDecision (data = {}) {
  return request({
    url: `${BASE_URL}/paper-portfolio/apply-decision`,
    method: 'post',
    data: {
      paper_account_id: data.paper_account_id || data.paperAccountId,
      paper_account_epoch: data.paper_account_epoch || data.paperAccountEpoch,
      decision_id: data.decision_id || data.decisionId,
      paper_order_intent_artifact_path: data.paper_order_intent_artifact_path || data.paperOrderIntentArtifactPath,
      decision_artifact_id: data.decision_artifact_id || data.decisionArtifactId,
      input_checksum: data.input_checksum || data.inputChecksum,
      idempotency_key: data.idempotency_key || data.idempotencyKey,
      confirmed_by_user: data.confirmed_by_user === true,
      confirm_text: data.confirm_text || data.confirmText || '确认应用到模拟账户'
    }
  })
}

export function resetTwStockPaperPortfolio (data = {}) {
  return request({
    url: `${BASE_URL}/paper-portfolio/reset`,
    method: 'post',
    data: {
      paper_account_id: data.paper_account_id || data.paperAccountId,
      current_epoch: data.current_epoch || data.currentEpoch,
      idempotency_key: data.idempotency_key || data.idempotencyKey,
      input_checksum: data.input_checksum || data.inputChecksum,
      confirmed_by_user: data.confirmed_by_user === true,
      confirm_text: data.confirm_text || data.confirmText || '确认重置模拟账户',
      reset_initial_cash: data.reset_initial_cash || data.resetInitialCash
    }
  })
}

export function draftTwStockSimOrder (data) {
  return request({
    url: `${BASE_URL}/sim/orders/draft`,
    method: 'post',
    data: {
      account_uid: data && (data.account_uid || data.accountUid),
      symbol: data && data.symbol,
      side: data && data.side,
      quantity: data && data.quantity,
      source_type: data && data.source_type ? data.source_type : 'manual',
      source_context: data && data.source_context ? data.source_context : undefined
    }
  })
}

export function confirmTwStockSimOrder (simOrderUid) {
  return request({
    url: `${BASE_URL}/sim/orders/${encodeURIComponent(simOrderUid)}/confirm`,
    method: 'post'
  })
}

export function cancelTwStockSimOrder (simOrderUid) {
  return request({
    url: `${BASE_URL}/sim/orders/${encodeURIComponent(simOrderUid)}/cancel`,
    method: 'post'
  })
}

// Explicit readonly simulation POST: classified as action surface, not pure GET readonly.
export function runTwStockReadonlyBacktest (data) {
  return request({
    url: '/api/indicator/backtest',
    method: 'post',
    data: {
      market: 'TWStock',
      timeframe: '1D',
      persist: false,
      enableMtf: false,
      ...data
    }
  })
}
