import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.join(process.cwd(), 'frontend')
const read = file => fs.readFileSync(path.join(root, file), 'utf8')
const hooks = [
  ['useDailyOpsStatus.js', ['getTwStockDailyAutoUpdateStatus', 'getTwStockReadonlyOpsStatus']],
  ['useSignalContext.js', ['getTwStockCurrentStrategyContext']],
  ['useReadonlyReplay.js', ['getTwStockReadonlyReplayWindowIndex', 'getTwStockReadonlyReplayWindow', 'runTwStockPortfolioReplay', 'persist: false']],
  ['usePaperPortfolio.js', ['getTwStockPaperPortfolioState', 'applyTwStockPaperPortfolioDecision', 'resetTwStockPaperPortfolio', 'paper_only: true']],
  ['useAgentContext.js', ['getTwStockAgentContext', 'simpleChatTwStockAgent']]
]

for (const [file, required] of hooks) {
  const source = read(`src/views/tw-stock-monitor/composables/${file}`)
  for (const token of required) assert.ok(source.includes(token), `${file} missing ${token}`)
  assert.doesNotMatch(source, /\.csv|provider_uri|private.?model|OPENAI_API_KEY|quick.?trade|broker|target.?position/i)
}

const readonlyApi = read('src/api/tw-stock-readonly.js')
const actionApi = read('src/api/tw-stock-action.js')
assert.equal((readonlyApi.match(/method:\s*['"]post['"]/g) || []).length, 1)
assert.match(actionApi, /runTwStockPortfolioReplay[\s\S]*persist:\s*false/)
assert.match(actionApi, /runTwStockReadonlyBacktest[\s\S]*persist:\s*false/)
assert.doesNotMatch(readonlyApi, /\/paper-portfolio\/(apply-decision|reset)|\/sim\/orders\//)

const backtestBody = actionApi.slice(actionApi.indexOf('export function runTwStockReadonlyBacktest'), actionApi.length)
assert.ok(backtestBody.indexOf('...data') < backtestBody.indexOf('persist: false'), 'readonly backtest must place persist=false after caller data')
for (const functionName of ['applyTwStockPaperPortfolioDecision', 'resetTwStockPaperPortfolio']) {
  const start = actionApi.indexOf(`export function ${functionName}`)
  const end = actionApi.indexOf('\nexport function ', start + 1)
  const body = actionApi.slice(start, end < 0 ? actionApi.length : end)
  assert.match(body, /paper_only:\s*true/)
}
console.log('ARCH-3 frontend boundary checks passed')
