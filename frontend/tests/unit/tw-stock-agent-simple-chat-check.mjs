import fs from 'node:fs'
import assert from 'node:assert/strict'

const api = fs.readFileSync('frontend/src/api/tw-stock-readonly.js', 'utf8')
const page = fs.readFileSync('frontend/src/views/tw-stock-monitor/index.vue', 'utf8')

assert.match(api, /export function simpleChatTwStockAgent/)
assert.match(api, /\/agent\/simple-chat/)
assert.match(page, /simpleChatTwStockAgent/)
assert.match(page, /signal_asof/)
assert.match(page, /target_date/)
assert.match(page, /checksum/)
assert.match(page, /agentCitations/)
assert.match(page, /agentWarnings/)
assert.match(page, /agentResearchDisclaimer/)
assert.match(page, /今天策略是什么？/)
assert.match(page, /排名第一是谁？/)
assert.match(page, /今天有哪些候选调入？/)
assert.match(page, /今天有哪些调出复核？/)
assert.match(page, /2330 当前状态如何？/)
assert.match(page, /为什么模拟账户不能应用？/)
assert.match(page, /数据新鲜度如何？/)

const simpleApiBlock = api.slice(api.indexOf('export function simpleChatTwStockAgent'), api.indexOf('export function getQlibOptionCHealth'))
assert.doesNotMatch(simpleApiBlock, /OPENAI_API_KEY|api\.openai\.com|chat\/completions|@openai|quick-trade|broker|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts/i)
assert.match(simpleApiBlock, /BASE_URL \+ "\/agent\/simple-chat"/)

const panelStart = page.indexOf('<div class="tw-stock-agent-panel">')
const panelEnd = page.indexOf('<div v-if="crossAnalysisAccepted"', panelStart)
const panel = page.slice(panelStart, panelEnd)
assert.doesNotMatch(panel, /quick-trade|broker|order submit|target-position|target_position|target_weight|provider publish|accepted latest|qlib refresh|monitor config|monitor scan|monitor alerts/i)
assert.doesNotMatch(panel, /OPENAI_API_KEY|api\.openai\.com|chat\/completions|@openai/i)

const questionsStart = page.indexOf('this.agentSuggestedQuestions = [')
const questionsEnd = page.indexOf('].slice(0, 7)', questionsStart)
const questions = page.slice(questionsStart, questionsEnd)
assert.doesNotMatch(questions, /下单|仓位|收益保证|自动交易|目标仓位|quick-trade|broker/i)

console.log('tw-stock-agent-simple-chat-check passed')
