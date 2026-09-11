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

export function getTwStockReadonlyStrategySnapshot () {
  return request({
    url: `${BASE_URL}/readonly-strategy-snapshot`,
    method: 'get'
  })
}

export function getTwStockPhaseYZProductizationStatus (params = {}) {
  return request({
    url: `${BASE_URL}/phase-yz/productization-status`,
    method: 'get',
    params
  })
}


export function getTwStockCurrentStrategyContext (params = {}) {
  return request({
    url: `${BASE_URL}/current-strategy-context`,
    method: 'get',
    params
  })
}

export function getTwStockReadonlyShadowExposure (params = {}) {
  return request({
    url: `${BASE_URL}/readonly-shadow-exposure`,
    method: 'get',
    params
  })
}

export function getTwStockTradingAgentsReadonlyAnalysisLatest (params = {}) {
  return request({
    url: `${BASE_URL}/tradingagents-readonly-analysis/latest`,
    method: 'get',
    params
  })
}


export function getTwStockReadonlyReplayWindowIndex () {
  return request({
    url: `${BASE_URL}/readonly-replay-window-index`,
    method: 'get'
  })
}

export function getTwStockReadonlyReplayWindow (params = {}) {
  return request({
    url: `${BASE_URL}/readonly-replay-window`,
    method: 'get',
    params
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

export function getTwStockAlerts (params) {
  return request({
    url: `${BASE_URL}/monitor/alerts`,
    method: 'get',
    params
  })
}

export function getTwStockHistory (params) {
  return request({
    url: `${BASE_URL}/monitor/history`,
    method: 'get',
    params
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

export function getTwStockCrossAnalysisReviews (params) {
  return request({
    url: BASE_URL + "/cross-analysis/reviews",
    method: "get",
    params
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

// Readonly explanation exception: backend-only DailyAgentPromptArtifact answer.
export function simpleChatTwStockAgent ({ question, symbol = "", maxItems = 10 } = {}) {
  return request({
    url: BASE_URL + "/agent/simple-chat",
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

export function getTwStockPaperPortfolioLatestDecision (params = {}) {
  return request({
    url: `${BASE_URL}/paper-portfolio/latest-decision`,
    method: 'get',
    params
  })
}

export function getTwStockPaperPortfolioState (params = {}) {
  return request({
    url: `${BASE_URL}/paper-portfolio/state`,
    method: 'get',
    params
  })
}

export function getTwStockPaperPortfolioApplyRuns (params = {}) {
  return request({
    url: `${BASE_URL}/paper-portfolio/apply-runs`,
    method: 'get',
    params
  })
}

export function getTwStockDailyAutoUpdateStatus () {
  return request({
    url: `${BASE_URL}/quant/ops/daily-auto-update/status`,
    method: 'get'
  })
}

export function getTwStockReadonlyOpsStatus () {
  return request({
    url: `${BASE_URL}/quant/ops/readonly-status`,
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
