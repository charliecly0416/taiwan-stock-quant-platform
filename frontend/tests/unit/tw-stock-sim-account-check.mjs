import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const read = file => fs.readFileSync(path.join(root, file), 'utf8')
const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}

const page = read('src/views/tw-stock-sim-account/index.vue')
const monitorPage = read('src/views/tw-stock-monitor/index.vue')
const api = read('src/api/tw-stock.js')
const router = read('src/config/router.config.js')
const zhCN = read('src/locales/lang/zh-CN.js')
const zhTW = read('src/locales/lang/zh-TW.js')
const enUS = read('src/locales/lang/en-US.js')

const boundary = '本页面仅用于台股研究信号的历史与模拟验证，不连接券商，不提交真实订单，不构成投资建议。'

assert(router.includes("path: '/tw-stock-sim-account'"), 'missing /tw-stock-sim-account route')
assert(router.includes("name: 'TWStockSimAccount'"), 'missing TWStockSimAccount route name')
assert(router.includes("component: () => import('@/views/tw-stock-sim-account')"), 'route must import tw-stock-sim-account page')
assert(router.includes("title: 'menu.dashboard.twStockSimAccount'"), 'route must use twStockSimAccount locale key')

assert(zhCN.includes("'menu.dashboard.twStockSimAccount': '台股模拟账户'"), 'missing zh-CN menu text')
assert(zhTW.includes("'menu.dashboard.twStockSimAccount': '台股模擬帳戶'"), 'missing zh-TW menu text')
assert(enUS.includes("'menu.dashboard.twStockSimAccount': 'TW Stock Sim Account'"), 'missing en-US menu text')

assert(page.includes('<h2>台股模拟账户</h2>'), 'page title must be 台股模拟账户')
assert(page.includes(boundary), 'missing fixed safety boundary alert')

const requiredButtons = [
  '创建模拟账户',
  '生成模拟买入草稿',
  '生成模拟卖出草稿',
  '确认模拟成交',
  '取消草稿',
  '刷新模拟账户'
]
for (const text of requiredButtons) {
  assert(page.includes(text), `missing required button text: ${text}`)
}

const pageWithoutAllowedBoundary = page.replace(boundary, '')
const forbiddenTexts = [
  '真实买入',
  '真实卖出',
  '一键买入',
  '一键卖出',
  '自动下单',
  '连接券商',
  '跟随 AI 买入',
  '目标仓位',
  '目标权重',
  '实盘',
  'live trading',
  'paper trading'
]
for (const text of forbiddenTexts) {
  assert(!pageWithoutAllowedBoundary.includes(text), `forbidden visible text found in page: ${text}`)
}

const importedBlock = page.match(/import \{([\s\S]*?)\} from '@\/api\/tw-stock'/)
assert(importedBlock, 'page must import API helpers from @/api/tw-stock')
const importedNames = importedBlock[1].split(',').map(item => item.trim()).filter(Boolean)
const expectedHelpers = [
  'getTwStockSimAccounts',
  'createTwStockSimAccount',
  'getTwStockSimAccount',
  'getTwStockSimPositions',
  'getTwStockSimTrades',
  'getLatestQlibOptionCSignals',
  'getTwStockCrossAnalysisLatest',
  'draftTwStockSimOrder',
  'confirmTwStockSimOrder',
  'cancelTwStockSimOrder'
]
assert(importedNames.length === expectedHelpers.length, `page imports unexpected helper count: ${importedNames.join(', ')}`)
for (const helper of expectedHelpers) {
  assert(importedNames.includes(helper), `page missing API helper import: ${helper}`)
}

const forbiddenImports = [
  'quick',
  'broker',
  'orderApi',
  'agentChat',
  'AgentChat',
  'MonitorConfig',
  'saveTwStockMonitorConfig',
  'runTwStockMonitorScan',
  'updateTwStockAlert',
  'publish',
  'refresh'
]
for (const token of forbiddenImports) {
  assert(!importedBlock[1].includes(token), `forbidden import in sim account page: ${token}`)
}

assert(page.includes('draftTwStockSimOrder'), 'page must create simulated draft')
assert(page.includes('confirmTwStockSimOrder'), 'page must confirm simulated draft')
assert(page.includes('cancelTwStockSimOrder'), 'page must cancel simulated draft')
assert(page.includes("draftOrder.status === 'draft'"), 'confirm button must require draft status')
assert(page.includes("draftOrder.status === 'rejected'"), 'page must handle rejected draft state')
assert(page.includes('simulation_only === true'), 'page must check simulation_only=true')
assert(page.includes('real_orders_enabled === false'), 'page must check real_orders_enabled=false')
assert(page.includes('connects_to_broker === false'), 'page must check connects_to_broker=false')
assert(page.includes('!this.safetyError'), 'confirm flow must be blocked by safetyError')
assert(page.includes('tw-stock-sim-draft-context'), 'sim account page must read signal draft context key')
assert(page.includes('loadPendingSignalDraft'), 'sim account page must load pending signal draft')
assert(page.includes("['qlib_rank', 'cross_analysis'].includes(draft.source_type)"), 'sim account page must only accept qlib_rank/cross_analysis prefill from frontend')
assert(page.includes('source_context: this.tradeForm.source_context'), 'sim account draft call must include source_context')
assert(page.includes('markSignalDraftEdited'), 'sim account page must mark user edits in source_context')
assert(page.includes('绩效复盘'), 'sim account page must include performance review section')
assert(page.includes('历史/模拟结果，不代表未来收益。'), 'performance section must include simulation result disclaimer')
assert(page.includes('持仓浮动盈亏'), 'performance section must include unrealized pnl')
assert(page.includes('已实现盈亏 MVP'), 'performance section must include realized pnl MVP')
assert(page.includes('胜负笔数 MVP'), 'performance section must include win/loss MVP')
assert(page.includes('成交来源'), 'performance section must include source type counts')
assert(page.includes('sourceTypeCounts'), 'page must compute source type counts')
assert(page.includes('performanceSummary'), 'page must compute performance summary')
assert(page.includes('模拟成交标记'), 'sim account page must include simulated trade markers')
assert(page.includes('简化列表替代 K 线标记'), 'page must document simplified marker alternative')
assert(page.includes('filteredTradeMarkers'), 'page must filter simulated trade markers')
assert(page.includes('策略候选（模拟验证）'), 'page must include low-turnover strategy candidate panel')
assert(page.includes('模拟买入候选'), 'strategy panel must include simulated buy candidates')
assert(page.includes('模拟卖出候选'), 'strategy panel must include simulated sell candidates')
assert(page.includes('继续保留观察'), 'strategy panel must include hold/watch candidates')
assert(page.includes('人工复核'), 'strategy panel must include manual review candidates')
assert(page.includes('低换手规则'), 'strategy panel must explain low-turnover rule')
assert(page.includes('prefillStrategyDraft'), 'strategy panel must only prefill simulated draft')
assert(page.includes('getLatestQlibOptionCSignals'), 'strategy panel must read qlib signals')
assert(page.includes('getTwStockCrossAnalysisLatest'), 'strategy panel must read cross-analysis')
assert(page.includes('max-height: 340px'), 'strategy candidate lists must have fixed-height scrolling')
assert(page.includes('overflow-y: auto'), 'strategy candidate lists must scroll inside the panel')

assert(monitorPage.includes('data-testid="qlib-sim-draft"'), 'monitor qlib rows must expose sim draft prefill button')
assert(monitorPage.includes('data-testid="cross-sim-draft"'), 'cross analysis rows must expose sim draft prefill button')
assert(monitorPage.includes('prefillSimDraftFromQlib'), 'monitor page must implement qlib prefill')
assert(monitorPage.includes('prefillSimDraftFromCross'), 'monitor page must implement cross-analysis prefill')
assert(monitorPage.includes('writeSimDraftContext'), 'monitor page must write localStorage prefill context')
assert(monitorPage.includes("this.$router.push('/tw-stock-sim-account')"), 'monitor page must navigate to sim account page')
assert(monitorPage.includes("source_type: 'qlib_rank'"), 'qlib prefill must use qlib_rank source_type')
assert(monitorPage.includes("source_type: 'cross_analysis'"), 'cross prefill must use cross_analysis source_type')
assert(monitorPage.includes("category === 'focus_watch' || alignment === 'aligned'"), 'cross prefill must only allow focus_watch or aligned')
assert(!monitorPage.includes('confirmTwStockSimOrder'), 'monitor page must not confirm simulated trades')
assert(!monitorPage.includes('draftTwStockSimOrder'), 'monitor page must not call draft API directly')

function extractFunction (name) {
  const marker = `export function ${name} `
  const start = api.indexOf(marker)
  assert(start >= 0, `missing API helper: ${name}`)
  const next = api.indexOf('\nexport function ', start + marker.length)
  return api.slice(start, next >= 0 ? next : api.length)
}

const expectedEndpoints = {
  getTwStockSimAccounts: [/\/sim\/accounts/],
  createTwStockSimAccount: [/\/sim\/accounts/],
  getTwStockSimAccount: [/\/sim\/accounts\/\$\{encodeURIComponent\(accountUid\)\}/],
  getTwStockSimPositions: [/\/sim\/accounts\/\$\{encodeURIComponent\(accountUid\)\}\/positions/],
  getTwStockSimTrades: [/\/sim\/accounts\/\$\{encodeURIComponent\(accountUid\)\}\/trades/],
  draftTwStockSimOrder: [/\/sim\/orders\/draft/],
  confirmTwStockSimOrder: [/\/sim\/orders\/\$\{encodeURIComponent\(simOrderUid\)\}\/confirm/],
  cancelTwStockSimOrder: [/\/sim\/orders\/\$\{encodeURIComponent\(simOrderUid\)\}\/cancel/]
}

for (const [helper, patterns] of Object.entries(expectedEndpoints)) {
  const body = extractFunction(helper)
  for (const pattern of patterns) {
    assert(pattern.test(body), `${helper} must match ${pattern}`)
  }
  assert(body.includes('BASE_URL'), `${helper} must use /api/tw-stock base URL`)
  assert(!/quick-trade|broker|\/api\/order\b|\/api\/orders\b|monitor\/scan|monitor\/alerts|quant\/ops|agent\/chat/.test(body), `${helper} contains forbidden endpoint`)
  if (helper === 'draftTwStockSimOrder') {
    assert(body.includes('source_context'), 'draft helper must forward source_context')
    assert(body.includes('source_type'), 'draft helper must forward source_type')
  }
}

console.log('tw-stock-sim-account static checks passed')
