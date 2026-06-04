import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const twPage = read('src/views/tw-stock-monitor/index.vue')
const agentTokensPage = read('src/views/agent-tokens/index.vue')
const profilePage = read('src/views/profile/index.vue')

assert.match(twPage, /import moment from 'moment'/)
assert.match(twPage, /asof:\s*moment\('2026-06-01',\s*'YYYY-MM-DD'\)/)
assert.doesNotMatch(twPage, /qlibOpsForm:\s*\{[\s\S]*?asof:\s*'2026-06-01'[\s\S]*?\}/)
assert.doesNotMatch(twPage, /<a-date-picker[^>]*:value="\s*''\s*"/)
assert.doesNotMatch(twPage, /<a-date-picker[^>]*v-model="[^"]*"[^>]*value="\s*"/)

assert.match(agentTokensPage, /<a-input :value="revealed\.token" read-only class="reveal-token-input" \/>/)
assert.doesNotMatch(agentTokensPage, /<a-input[^>]*\sreadOnly\b/)
assert.match(profilePage, /<a-input[\s\S]*:value="referralLink"[\s\S]*read-only[\s\S]*size="small"/)

const consoleAllowlist = [
  '[antd-pro] NOTICE: Antd use lazy-load.'
]
assert.deepEqual(consoleAllowlist, ['[antd-pro] NOTICE: Antd use lazy-load.'])

for (const forbidden of [
  'console.warn =',
  'console.error =',
  'window.console.warn',
  'window.console.error',
  'ignoreHTTPSErrors',
  "page.on(\'console\', () => {})"
]) {
  assert.ok(!twPage.includes(forbidden), `tw-stock page contains console suppression: ${forbidden}`)
}

console.log('tw-stock console clean static checks passed')
