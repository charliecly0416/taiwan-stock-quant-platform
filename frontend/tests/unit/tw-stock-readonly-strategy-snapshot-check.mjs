import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const frontendRoot = path.join(root, 'frontend')
const vuePath = path.join(frontendRoot, 'src/views/tw-stock-monitor/index.vue')
const apiPath = path.join(frontendRoot, 'src/api/tw-stock-readonly.js')
const componentPath = path.join(frontendRoot, 'src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue')
const auditPath = path.join(frontendRoot, 'src/views/tw-stock-monitor/components/ReplayAuditDetail.vue')
const vue = fs.readFileSync(vuePath, 'utf8')
const api = fs.readFileSync(apiPath, 'utf8')
const component = fs.readFileSync(componentPath, 'utf8')
const audit = fs.readFileSync(auditPath, 'utf8')

function assert (condition, message) {
  if (!condition) {
    console.error(`[readonly-strategy-snapshot-check] ${message}`)
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

const apiFn = sliceBetween(api, 'export function getTwStockReadonlyStrategySnapshot', 'export function getTwStockReadonlyReplayWindowIndex')
const loader = sliceBetween(vue, 'async loadReadonlyStrategySnapshot ()', 'async loadReadonlyReplayWindow ()')
const mountedBlock = sliceBetween(vue, 'mounted ()', 'beforeDestroy ()')
const refreshAllBlock = sliceBetween(vue, 'async refreshAll ()', 'async loadConfig ()')
const acceptancePath = `${mountedBlock}
${refreshAllBlock}
${loader}`

assert(vue.includes('ReadonlyStrategySnapshotPanel'), 'component import/registration missing')
assert(vue.includes('<readonly-strategy-snapshot-panel'), 'component usage missing')
assert(component.includes('data-testid="readonly-strategy-snapshot-panel"'), 'panel test id missing')
assert(component.includes('候选名单'), 'panel title missing')
assert(component.includes('只读研究'), 'readonly label missing')
assert(component.includes('研究排名'), 'research ranking label missing')
assert(component.includes('候选调入'), 'entry candidate label missing')
assert(component.includes('调出复核'), 'exit observation label missing')
assert(component.includes('signal date'), 'data date label missing')
assert(component.includes('model'), 'model label missing')
assert(component.includes('strategy'), 'strategy label missing')
assert(component.includes('覆盖状态'), 'coverage label missing')
assert(component.includes('审计状态'), 'audit status label missing')
assert(component.includes('ReplayAuditDetail'), 'audit detail component missing')
assert(audit.includes('data-testid="readonly-audit-detail"'), 'audit detail test id missing')
assert(apiFn.includes('/readonly-strategy-snapshot'), 'readonly endpoint missing')
assert(/method:\s*['"]get['"]/.test(apiFn), 'readonly API wrapper must use GET')
assert(loader.includes('getTwStockReadonlyStrategySnapshot()'), 'loader must call readonly API wrapper')
assert(!/method:\s*['"](?:post|put|patch|delete)['"]/i.test(apiFn), 'API wrapper contains forbidden write method')
assert(!/saveTwStockMonitorConfig|scanTwStockMonitor|scanAllTwStockMonitors|triggerQlibOptionCDryRun|runTwStockPortfolioReplay|runTwStockReadonlyBacktest|saveTwStockCrossAnalysisReview|chatTwStockAgent/.test(loader), 'loader calls a non-snapshot action')
assert(!/loadRankTechPortfolioPanel|loadPortfolioReplay|runTwStockPortfolioReplay|runTwStockReadonlyBacktest|runReadonlyBacktest/.test(acceptancePath), 'M4 acceptance path calls replay/strategy write action')

const forbiddenText = ['下单', '买入指令', '卖出指令', '目标仓位', '自动交易', '一键交易', '券商同步', '保证收益', '胜率承诺']
for (const word of forbiddenText) {
  assert(!component.includes(word), `component contains forbidden text: ${word}`)
}

const forbiddenNetworkHints = [
  '/monitor/scan',
  '/monitor/config',
  '/monitor/alerts',
  '/quant/signals/dry-run',
  'accepted_latest',
  'provider_publish',
  '--enable-legacy-provider-publish',
  'TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH'
]
for (const hint of forbiddenNetworkHints) {
  assert(!component.includes(hint) && !loader.includes(hint), `readonly component/loader contains forbidden network hint: ${hint}`)
}

console.log('[readonly-strategy-snapshot-check] ok')
