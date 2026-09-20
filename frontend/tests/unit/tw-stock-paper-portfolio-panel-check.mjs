import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'

const root = process.cwd()
const frontendRoot = path.basename(root) === 'frontend' ? root : path.join(root, 'frontend')
const read = file => fs.readFileSync(path.join(frontendRoot, file), 'utf8')
const readonlyApi = read('src/api/tw-stock-readonly.js')
const actionApi = read('src/api/tw-stock-action.js')
const api = `${readonlyApi}\n${actionApi}`
const monitor = read('src/views/tw-stock-monitor/index.vue')
const panel = read('src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue')

assert.ok(monitor.includes("import PaperPortfolioPanel from './components/PaperPortfolioPanel.vue'"), 'monitor must import PaperPortfolioPanel')
assert.ok(monitor.includes('<paper-portfolio-panel'), 'monitor must render PaperPortfolioPanel')
assert.ok(monitor.includes(':phase-yz-status="phaseYZProductizationPayload"'), 'monitor must pass YZ3 status into PaperPortfolioPanel')
assert.ok(monitor.includes(':active-signal-as-of="currentContextSignalAsOf"'), 'monitor must pass current signal date into PaperPortfolioPanel')
assert.ok(panel.includes('data-testid="paper-portfolio-panel"'), 'panel test id missing')
assert.ok(panel.includes('应用到模拟账户'), 'apply text must include 模拟')
assert.ok(panel.includes('重置模拟账户'), 'reset text must include 模拟账户')
assert.ok(panel.includes('此操作只会写入模拟账户，不会产生真实交易委托。'), 'apply confirmation safety text missing')
assert.ok(panel.includes('旧状态会归档'), 'reset archive text missing')
assert.ok(panel.includes('paper_order_intent_artifact_path'), 'apply payload must use artifact path')
assert.ok(panel.includes('decisionDateMismatch'), 'decision date mismatch guard missing')
assert.ok(panel.includes('phaseYZDateMismatch'), 'phase YZ date mismatch guard missing')
assert.ok(panel.includes('dateContextMismatch'), 'combined date mismatch guard missing')
assert.ok(panel.includes('已作为历史状态隔离，不能应用'), 'historical state explanation missing')
assert.ok(!panel.includes('paper_order_intent:'), 'frontend must not submit raw paper_order_intent payload')

const helpers = [
  'getTwStockPaperPortfolioLatestDecision',
  'getTwStockPaperPortfolioState',
  'getTwStockPaperPortfolioApplyRuns',
  'applyTwStockPaperPortfolioDecision',
  'resetTwStockPaperPortfolio'
]
for (const helper of helpers) assert.ok(api.includes(`export function ${helper}`), `missing API helper ${helper}`)

const allowedPostBodies = [
  extractFunction('applyTwStockPaperPortfolioDecision'),
  extractFunction('resetTwStockPaperPortfolio')
].join('\n')
assert.ok(allowedPostBodies.includes('/paper-portfolio/apply-decision'), 'apply helper endpoint mismatch')
assert.ok(allowedPostBodies.includes('/paper-portfolio/reset'), 'reset helper endpoint mismatch')
assert.ok(!allowedPostBodies.includes('/quick-trade'), 'paper helpers must not call quick-trade')
assert.ok(!allowedPostBodies.includes('/broker'), 'paper helpers must not call broker')
assert.ok(!allowedPostBodies.includes('/monitor/scan'), 'paper helpers must not call monitor scan')
assert.ok(!allowedPostBodies.includes('/monitor/alerts'), 'paper helpers must not write alerts')
assert.ok(!allowedPostBodies.includes('/quant/ops'), 'paper helpers must not call quant ops')

const forbiddenVisible = ['实盘下单', '真实买入', '真实卖出', '自动交易', '连接券商', '保证收益', '上涨概率', '目标仓位']
for (const text of forbiddenVisible) assert.ok(!panel.includes(text), `forbidden visible text: ${text}`)

function extractFunction (name) {
  const marker = `export function ${name} `
  const start = api.indexOf(marker)
  assert.ok(start >= 0, `missing function ${name}`)
  const next = api.indexOf('\nexport function ', start + marker.length)
  return api.slice(start, next >= 0 ? next : api.length)
}

console.log('tw-stock-paper-portfolio-panel static checks passed')
