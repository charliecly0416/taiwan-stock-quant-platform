import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const api = read('src/api/tw-stock.js')
const page = read('src/views/tw-stock-monitor/index.vue')

for (const required of [
  'getTwStockAgentContext',
  'chatTwStockAgent',
  '/agent/context',
  '/agent/chat'
]) {
  assert.ok(api.includes(required), `api missing ${required}`)
}

for (const required of [
  '台股研究助手',
  'agentSuggestedQuestions',
  '今天 top30 是哪些？',
  '今天模型和趋势都支持的股票有哪些？',
  '今天建议回避或人工复盘的股票有哪些？',
  '2330 的指标是多少？',
  '当前数据新鲜度和口径是什么？',
  'agentQuestion',
  'askTwStockAgent',
  'chatTwStockAgent',
  'getTwStockAgentContext',
  '当前使用后端 deterministic fallback / 未启用 OpenAI。',
  '该问题已被研究边界阻断；本面板只展示研究解释。',
  '引用来源',
  'agentCitations',
  'agentQlibAsof',
  'agentQlibRunId',
  'agentFreshnessStatus',
  'agentResearchDisclaimer',
  '仅供研究观察，不构成交易建议',
  'qlib score 是横截面排序分数',
  'agentWarnings',
  'agentItems',
  'quality_warnings',
  'cross_category',
  'human_action'
]) {
  assert.ok(page.includes(required), `page missing ${required}`)
}

const contextMatch = api.match(/function getTwStockAgentContext[\s\S]*?\n\}/)
assert.ok(contextMatch, 'missing getTwStockAgentContext body')
assert.match(contextMatch[0], /method:\s*"get"/)
assert.match(contextMatch[0], /maxItems:\s*Math\.max\(1,\s*Math\.min\(Number\(maxItems \|\| 10\),\s*20\)\)/)

const chatMatch = api.match(/function chatTwStockAgent[\s\S]*?\n\}/)
assert.ok(chatMatch, 'missing chatTwStockAgent body')
assert.match(chatMatch[0], /method:\s*"post"/)
assert.match(chatMatch[0], /slice\(0, 500\)/)
assert.doesNotMatch(chatMatch[0], /OPENAI_API_KEY|openai|sdk/i)

const agentTemplateMatch = page.match(/<div class="tw-stock-agent-panel">[\s\S]*?<div v-if="crossAnalysisAccepted" class="qlib-meta-grid">/)
assert.ok(agentTemplateMatch, 'missing agent panel template')
const agentTemplate = agentTemplateMatch[0]

for (const required of [
  'answer',
  'citations',
  'warnings',
  'qlib asof',
  'run_id',
  'freshness',
  'research-only',
  'deterministic fallback',
  'blocked',
  'qlib score',
  'trend',
  'category'
]) {
  assert.ok(agentTemplate.includes(required), `agent template missing ${required}`)
}

for (const forbidden of [
  'OPENAI_API_KEY',
  'OpenAI SDK',
  '@openai',
  'openai.chat',
  '/quant/ops/option-c',
  '/cross-analysis/history/import-latest',
  '/cross-analysis/reviews',
  '/api/indicator/backtest',
  '/api/quick-trade',
  'quick-trade',
  'broker',
  'target_position',
  'targetPosition',
  'target_weight',
  'targetWeight',
  '下单',
  '下單',
  '立即买入',
  '立即賣出',
  '目标仓位',
  '目標倉位'
]) {
  assert.ok(!agentTemplate.toLowerCase().includes(forbidden.toLowerCase()), `agent panel contains forbidden text: ${forbidden}`)
}

const loadContextMatch = page.match(/async loadTwStockAgentContext \(\) \{[\s\S]*?\n    \},\n    handleAgentEnter/)
assert.ok(loadContextMatch, 'missing loadTwStockAgentContext method')
assert.match(loadContextMatch[0], /getTwStockAgentContext\(\{ maxItems: 10 \}\)/)
assert.doesNotMatch(loadContextMatch[0], /OpenAI|OPENAI_API_KEY|ops|DryRun|backtest|quick-trade|broker/i)

const askMatch = page.match(/async askTwStockAgent \(question\) \{[\s\S]*?\n    \},\n    async loadCrossAnalysis/)
assert.ok(askMatch, 'missing askTwStockAgent method')
assert.match(askMatch[0], /chatTwStockAgent/)
assert.match(askMatch[0], /slice\(0, 500\)/)
assert.doesNotMatch(askMatch[0], /OpenAI|OPENAI_API_KEY|ops|DryRun|runTwStockReadonlyBacktest|quick-trade|broker/i)

assert.doesNotMatch(api, /OPENAI_API_KEY|@openai|openai\/resources|openai\.chat/i)
assert.doesNotMatch(page, /OPENAI_API_KEY|@openai|openai\/resources|openai\.chat/i)

console.log('tw-stock agent panel checks passed')
