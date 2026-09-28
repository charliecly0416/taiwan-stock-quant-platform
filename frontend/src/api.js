async function request(path, body, token) {
  const options = { headers: { Accept: 'application/json' } }
  if (token) options.headers.Authorization = 'Bearer ' + token
  if (body !== undefined) {
    options.method = 'POST'
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }
  const response = await fetch(path, options)
  const payload = await response.json().catch(() => ({ status: 'BLOCKED', message: '服务返回了无法解析的内容。' }))
  if (!response.ok) throw new Error(payload.message || '请求失败')
  return payload
}

const query = values => new URLSearchParams(
  Object.entries(values).filter(([, value]) => value !== '' && value !== null && value !== undefined)
).toString()

export const api = {
  overview: () => request('/api/tw-stock/overview'),
  rankings: (model, date, limit = 50) => request('/api/tw-stock/rankings?' + query({ model, date: date || '', limit })),
  compare: (left, right, date, start = '', end = '') => request('/api/tw-stock/compare?' + query({ left, right, date: date || '', start, end })),
  strategy: (model, date) => request('/api/tw-stock/strategy?' + query({ model, date: date || '' })),
  rankingChanges: (model, date, lookback = 1) => request('/api/tw-stock/ranking-changes?' + query({ model, date: date || '', lookback })),
  crossAnalysis: (model, date, limit = 50) => request('/api/tw-stock/cross-analysis?' + query({ model, date: date || '', limit })),
  replay: (model, start, end) => request('/api/tw-stock/replay?' + query({ model, start, end })),
  market: (symbol, start, end) => request('/api/tw-stock/market/' + encodeURIComponent(symbol) + '?' + query({ start, end })),
  paper: (model, date) => request('/api/tw-stock/paper?' + query({ model, date: date || '' })),
  agentContext: (model, date) => request('/api/tw-stock/agent/context?' + query({ model, date: date || '' })),
  simpleChat: (question, date) => request('/api/tw-stock/agent/simple-chat', { question, date }),
  explain: (symbol, model, date) => request('/api/tw-stock/agent/explain/' + encodeURIComponent(symbol) + '?' + query({ model, date: date || '' })),
  dataStatus: () => request('/api/tw-stock/data-status'),
  operations: () => request('/api/tw-stock/operations/latest'),
  paperAccounts: token => request('/api/tw-stock/sim/accounts', undefined, token),
  paperAccount: (token, account) => request('/api/tw-stock/paper-portfolio/state?' + query({ paper_account_id: account }), undefined, token),
  paperHistory: (token, account) => request('/api/tw-stock/paper-portfolio/apply-runs?' + query({ paper_account_id: account }), undefined, token),
  paperCreate: (token, body) => request('/api/tw-stock/sim/accounts', body, token),
  paperPreview: (token, account, date) => request('/api/tw-stock/paper-portfolio/preview', { paper_account_id: account, date }, token),
  paperApply: (token, body) => request('/api/tw-stock/paper-portfolio/apply-decision', body, token),
  paperReset: (token, body) => request('/api/tw-stock/paper-portfolio/reset', body, token),
}
