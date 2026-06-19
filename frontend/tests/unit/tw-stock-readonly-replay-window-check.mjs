import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const vuePath = path.join(root, 'src/views/tw-stock-monitor/index.vue')
const apiPath = path.join(root, 'src/api/tw-stock.js')
const componentPath = path.join(root, 'src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue')
const auditPath = path.join(root, 'src/views/tw-stock-monitor/components/ReplayAuditDetail.vue')
const vue = fs.readFileSync(vuePath, 'utf8')
const api = fs.readFileSync(apiPath, 'utf8')
const component = fs.readFileSync(componentPath, 'utf8')
const audit = fs.readFileSync(auditPath, 'utf8')

function assert (condition, message) {
  if (!condition) {
    console.error(`[readonly-replay-window-check] ${message}`)
    process.exit(1)
  }
}

function sliceBetween (source, start, end) {
  const s = source.indexOf(start)
  assert(s >= 0, `missing start marker ${start}`)
  const e = source.indexOf(end, s + start.length)
  assert(e > s, `missing end marker ${end}`)
  return source.slice(s, e)
}

const apiFn = sliceBetween(api, 'export function getTwStockReadonlyReplayWindowIndex', 'export function getTwStockLTROptionalSimStrategies')
const loader = sliceBetween(vue, 'async loadReadonlyReplayWindowIndex ()', 'ltrOptionalSimMetricText')
const mountedBlock = sliceBetween(vue, 'mounted ()', 'beforeDestroy ()')
const refreshAllBlock = sliceBetween(vue, 'async refreshAll ()', 'async loadConfig ()')
const acceptancePath = `${mountedBlock}
${refreshAllBlock}
${loader}`

assert(vue.includes('ReadonlyReplayWindowPanel'), 'component import/registration missing')
assert(vue.includes('<readonly-replay-window-panel'), 'component usage missing')
assert(component.includes('data-testid="readonly-replay-window-panel"'), 'panel test id missing')
assert(component.includes('只读回放窗口'), 'panel title missing')
assert(component.includes('后端校验'), 'backend validation label missing')
assert(component.includes('标准产物'), 'standard artifact label missing')
assert(component.includes('模型'), 'model label missing')
assert(component.includes('策略'), 'strategy label missing')
assert(component.includes('合法窗口'), 'legal window label missing')
assert(component.includes('净收益'), 'net return label missing')
assert(component.includes('最大回撤'), 'drawdown label missing')
assert(component.includes('交易次数'), 'action count label missing')
assert(component.includes('手续费/税费'), 'fee/tax label missing')
assert(component.includes('覆盖状态'), 'coverage label missing')
assert(component.includes('审计状态'), 'audit status label missing')
assert(component.includes('ReplayAuditDetail'), 'audit detail component missing')
assert(audit.includes('data-testid="readonly-audit-detail"'), 'audit detail test id missing')
assert(apiFn.includes('/readonly-replay-window-index'), 'readonly replay index endpoint missing')
assert(apiFn.includes('/readonly-replay-window'), 'readonly replay endpoint missing')
assert(/method:\s*['"]get['"]/.test(apiFn), 'readonly replay API wrapper must use GET')
assert(loader.includes('getTwStockReadonlyReplayWindowIndex'), 'loader must call readonly replay index API wrapper')
assert(loader.includes('getTwStockReadonlyReplayWindow'), 'loader must call readonly replay API wrapper')
assert(!/method:\s*['"](?:post|put|patch|delete)['"]/i.test(apiFn), 'API wrapper contains forbidden write method')
assert(!/saveTwStockMonitorConfig|scanTwStockMonitor|scanAllTwStockMonitors|triggerQlibOptionCDryRun|runTwStockPortfolioReplay|runTwStockReadonlyBacktest|saveTwStockCrossAnalysisReview|chatTwStockAgent/.test(loader), 'loader calls non-readonly action')
assert(!/loadRankTechPortfolioPanel|loadPortfolioReplay|runTwStockPortfolioReplay|runTwStockReadonlyBacktest|runReadonlyBacktest/.test(acceptancePath), 'M4 acceptance path calls replay/strategy write action')

const primaryIndex = component.indexOf('净收益')
const auditIndex = component.indexOf('source manifest')
assert(primaryIndex >= 0 && auditIndex > primaryIndex, 'audit fields must appear after primary metrics')

const forbiddenText = ['下单', '买入指令', '卖出指令', '目标仓位', '自动交易', '一键交易', '券商同步', '保证收益', '胜率承诺']
for (const word of forbiddenText) {
  assert(!component.includes(word), `component contains forbidden text: ${word}`)
}

const forbiddenNetworkHints = ['provider_publish', 'accepted_latest', '--enable-legacy-provider-publish', 'TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH', '/broker/', 'quick-trade']
for (const hint of forbiddenNetworkHints) {
  assert(!component.includes(hint) && !loader.includes(hint), `readonly component/loader contains forbidden network hint: ${hint}`)
}

console.log('[readonly-replay-window-check] ok')
