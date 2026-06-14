import request from '@/utils/request'

const BASE_URL = '/api/tw-stock'

export function getTwStockTrends (params) {
  return request({
    url: `${BASE_URL}/trends`,
    method: 'get',
    params
  })
}


export function getTwStockLTRReadonlyExplanation () {
  return request({
    url: `${BASE_URL}/ltr-readonly-explanation`,
    method: 'get'
  })
}

export function getTwStockLTROptionalSimStrategies () {
  return request({
    url: `${BASE_URL}/ltr-optional-sim-strategies`,
    method: 'get'
  })
}

export function getTwStockMonitorConfig (params) {
  return request({
    url: `${BASE_URL}/monitor/config`,
    method: 'get',
    params
  })
}

export function saveTwStockMonitorConfig (data) {
  return request({
    url: `${BASE_URL}/monitor/config`,
    method: 'post',
    data
  })
}

export function getTwStockAlerts (params) {
  return request({
    url: `${BASE_URL}/monitor/alerts`,
    method: 'get',
    params
  })
}

export function updateTwStockAlert (id, data) {
  return request({
    url: `${BASE_URL}/monitor/alerts/${id}`,
    method: 'put',
    data
  })
}

export function getTwStockHistory (params) {
  return request({
    url: `${BASE_URL}/monitor/history`,
    method: 'get',
    params
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

export function getTwStockScanLogs (params) {
  return request({
    url: `${BASE_URL}/monitor/scan-logs`,
    method: 'get',
    params
  })
}



export function getLatestQlibOptionCSignals ({ bucket, enrichTrend = true, trendLimit = 120 } = {}) {
  const normalizedBucket = bucket === 'top50' ? 'top50' : 'top30'
  return request({
    url: `${BASE_URL}/quant/signals/latest`,
    method: 'get',
    params: {
      bucket: normalizedBucket,
      enrichTrend: Boolean(enrichTrend),
      trendLimit: Math.max(20, Math.min(Number(trendLimit || 120), 500))
    }
  })
}



export function getQlibOptionCRankChanges ({ bucket = "top30", lookback = 10 } = {}) {
  const normalizedBucket = bucket === "top50" ? "top50" : "top30"
  return request({
    url: `${BASE_URL}/quant/signals/rank-changes`,
    method: "get",
    params: {
      bucket: normalizedBucket,
      lookback: Math.max(2, Math.min(Number(lookback || 10), 60))
    }
  })
}



export function getTwStockCrossAnalysisLatest ({ bucket = "top30", limit = 120, maxItems, includeRawTrend = false } = {}) {
  const normalizedBucket = ["top30", "top50", "all"].includes(bucket) ? bucket : "top30"
  const defaultMaxItems = normalizedBucket === "top30" ? 30 : 50
  return request({
    url: BASE_URL + "/cross-analysis/latest",
    method: "get",
    params: {
      bucket: normalizedBucket,
      limit: Math.max(20, Math.min(Number(limit || 120), 500)),
      maxItems: Math.max(1, Math.min(Number(maxItems || defaultMaxItems), 50)),
      includeRawTrend: Boolean(includeRawTrend)
    }
  })
}

export function getTwStockCrossAnalysisSymbol (symbol, { limit = 120, includeRawTrend = true } = {}) {
  return request({
    url: BASE_URL + "/cross-analysis/symbol/" + encodeURIComponent(symbol),
    method: "get",
    params: {
      limit: Math.max(20, Math.min(Number(limit || 120), 500)),
      includeRawTrend: Boolean(includeRawTrend)
    }
  })
}

export function getTwStockRankTechCrossLatest ({ bucket = 'top30', limit = 120, maxItems, includeTechnicalStrategies = true, technicalStrategies = ['ma', 'rsi', 'macd', 'bollinger'] } = {}) {
  const normalizedBucket = ['top30', 'top50', 'all'].includes(bucket) ? bucket : 'top30'
  const defaultMaxItems = normalizedBucket === 'top50' ? 50 : 30
  return request({
    url: `${BASE_URL}/rank-tech-cross/latest`,
    method: 'get',
    params: {
      bucket: normalizedBucket,
      limit: Math.max(20, Math.min(Number(limit || 120), 500)),
      maxItems: Math.max(1, Math.min(Number(maxItems || defaultMaxItems), 50)),
      includeTechnicalStrategies: Boolean(includeTechnicalStrategies),
      technicalStrategies: Array.isArray(technicalStrategies) ? technicalStrategies.join(',') : technicalStrategies
    }
  })
}

export function getTwStockObservationReplay (params = {}) {
  return request({
    url: `${BASE_URL}/rank-tech-cross/observation-replay`,
    method: 'get',
    params
  })
}

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

export function getTwStockCrossAnalysisReviews (params) {
  return request({
    url: BASE_URL + "/cross-analysis/reviews",
    method: "get",
    params
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

export function getTwStockAgentContext ({ maxItems = 10 } = {}) {
  return request({
    url: BASE_URL + "/agent/context",
    method: "get",
    params: {
      maxItems: Math.max(1, Math.min(Number(maxItems || 10), 20))
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

export function getQlibOptionCHealth () {
  return request({
    url: `${BASE_URL}/quant/signals/health`,
    method: 'get'
  })
}

export function getQlibOptionCRuns ({ limit = 20, status = 'all' } = {}) {
  return request({
    url: `${BASE_URL}/quant/signals/runs`,
    method: 'get',
    params: {
      limit: Math.max(1, Math.min(Number(limit || 20), 100)),
      status
    }
  })
}

export function getQlibOptionCRunDetail (runId, { bucket, enrichTrend = false, trendLimit = 120 } = {}) {
  const normalizedBucket = bucket === 'top50' || bucket === 'all' ? bucket : 'top30'
  return request({
    url: `${BASE_URL}/quant/signals/runs/${encodeURIComponent(runId)}`,
    method: 'get',
    params: {
      bucket: normalizedBucket,
      enrichTrend: Boolean(enrichTrend),
      trendLimit: Math.max(20, Math.min(Number(trendLimit || 120), 500))
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

export function getQlibOptionCJob (jobId) {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/jobs/${encodeURIComponent(jobId)}`,
    method: 'get'
  })
}

export function getQlibOptionCJobLog (jobId, stream = 'stdout') {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/jobs/${encodeURIComponent(jobId)}/logs`,
    method: 'get',
    params: {
      stream: stream === 'stderr' ? 'stderr' : 'stdout'
    }
  })
}

export function getQlibOptionCLatestJob () {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/latest`,
    method: 'get'
  })
}



export function getTwStockSimAccounts () {
  return request({
    url: `${BASE_URL}/sim/accounts`,
    method: 'get'
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

export function getTwStockSimAccount (accountUid) {
  return request({
    url: `${BASE_URL}/sim/accounts/${encodeURIComponent(accountUid)}`,
    method: 'get'
  })
}

export function getTwStockSimPositions (accountUid) {
  return request({
    url: `${BASE_URL}/sim/accounts/${encodeURIComponent(accountUid)}/positions`,
    method: 'get'
  })
}

export function getTwStockSimTrades (accountUid, { limit = 100 } = {}) {
  return request({
    url: `${BASE_URL}/sim/accounts/${encodeURIComponent(accountUid)}/trades`,
    method: 'get',
    params: {
      limit: Math.max(1, Math.min(Number(limit || 100), 500))
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

export function getTwStockDailyAutoUpdateStatus () {
  return request({
    url: `${BASE_URL}/quant/ops/daily-auto-update/status`,
    method: 'get'
  })
}

export function getQlibOptionCScheduler () {
  return request({
    url: `${BASE_URL}/quant/ops/option-c/scheduler`,
    method: 'get'
  })
}

export function getTwStockKline (params) {
  return request({
    url: '/api/indicator/kline',
    method: 'get',
    params: {
      market: 'TWStock',
      timeframe: '1D',
      ...params
    }
  })
}


export function getTwStockBacktestTemplates () {
  return request({
    url: '/api/indicator/backtest/tw-stock/templates',
    method: 'get'
  })
}

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
