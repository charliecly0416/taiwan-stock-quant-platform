import request from '@/utils/request'

const BASE_URL = '/api/tw-stock'

export function getTwStockTrends (params) {
  return request({
    url: `${BASE_URL}/trends`,
    method: 'get',
    params
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
