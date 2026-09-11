import fs from 'node:fs'
import assert from 'node:assert/strict'

const api = [
  fs.readFileSync('frontend/src/api/tw-stock.js', 'utf8'),
  fs.readFileSync('frontend/src/api/tw-stock-readonly.js', 'utf8')
].join('\n')
const page = fs.readFileSync('frontend/src/views/tw-stock-monitor/index.vue', 'utf8')
const panel = fs.readFileSync('frontend/src/views/tw-stock-monitor/components/TradingAgentsReadonlyPanel.vue', 'utf8')

assert.match(api, /export function getTwStockTradingAgentsReadonlyAnalysisLatest/)
assert.match(api, /\/tradingagents-readonly-analysis\/latest/)
assert.match(page, /TradingAgentsReadonlyPanel/)
assert.match(page, /loadTradingAgentsReadonlyAnalysis/)
assert.match(panel, /data-testid="tradingagents-readonly-panel"/)
assert.match(panel, /validated sanitized artifact/)
assert.match(panel, /外部研究摘要暂不可用/)
assert.match(panel, /raw_files_included === false/)

const helperMatch = api.match(/export function getTwStockTradingAgentsReadonlyAnalysisLatest[\s\S]*?\n\}/)
assert.ok(helperMatch, 'missing TradingAgents readonly API helper')
assert.match(helperMatch[0], /method:\s*'get'/)
assert.doesNotMatch(helperMatch[0], /post|put|patch|delete|artifactRoot|run_tradingagents|TradingAgentsGraph|OPENAI_API_KEY|chat\/completions/i)

const methodMatch = page.match(/async loadTradingAgentsReadonlyAnalysis \(\) \{[\s\S]*?\n    \},\n    handleAgentEnter/)
assert.ok(methodMatch, 'missing loadTradingAgentsReadonlyAnalysis method')
assert.match(methodMatch[0], /getTwStockTradingAgentsReadonlyAnalysisLatest\(\)/)
assert.doesNotMatch(methodMatch[0], /post|put|patch|delete|artifactRoot|OpenAI|OPENAI_API_KEY|runTradingAgents|TradingAgentsGraph|monitor\/scan|provider|accepted latest|quick-trade|broker/i)

for (const forbidden of [
  'raw_tradingagents_state',
  'raw_complete_report',
  'Buy',
  'Sell',
  'Hold',
  'Overweight',
  'Underweight',
  'price target',
  'target price',
  'stop loss',
  'entry price',
  'position sizing',
  'target_weight',
  'target_position',
  'quick-trade',
  'place order',
  'submit order',
  'OPENAI_API_KEY',
  'chat/completions'
]) {
  assert.ok(!panel.includes(forbidden), `panel contains forbidden text: ${forbidden}`)
}

console.log('tw-stock-tradingagents-readonly-panel-check passed')
