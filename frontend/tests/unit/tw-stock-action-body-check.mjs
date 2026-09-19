import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const sourcePath = path.resolve(process.cwd(), 'frontend/src/api/tw-stock-action.js')
const source = fs.readFileSync(sourcePath, 'utf8')

// Execute the helpers with a recorder so this test covers serialized request
// bodies, including caller attempts to override safety flags.
const executable = source
  .replace(/^import request from ['"]@\/utils\/request['"]\s*$/m, '')
  .replace(/export function /g, 'function ')
  .concat('\nreturn { runTwStockReadonlyBacktest, runTwStockPortfolioReplay, applyTwStockPaperPortfolioDecision, resetTwStockPaperPortfolio };')

const calls = []
const request = config => {
  calls.push(config)
  return config
}
const helpers = new Function('request', executable)(request)

const backtest = helpers.runTwStockReadonlyBacktest({
  persist: true,
  market: 'Crypto',
  timeframe: '5m',
  enableMtf: true
})
assert.equal(backtest.data.persist, false)
assert.equal(backtest.data.market, 'TWStock')
assert.equal(backtest.data.timeframe, '1D')
assert.equal(backtest.data.enableMtf, false)

const replay = helpers.runTwStockPortfolioReplay({ persist: true })
assert.equal(replay.data.persist, false)

const apply = helpers.applyTwStockPaperPortfolioDecision({ paper_only: false, paper_account_id: 'paper-1' })
assert.equal(apply.data.paper_only, true)
const reset = helpers.resetTwStockPaperPortfolio({ paper_only: false, paper_account_id: 'paper-1' })
assert.equal(reset.data.paper_only, true)

assert.equal(calls.length, 4)
console.log('TW stock action helper body safety checks passed')
