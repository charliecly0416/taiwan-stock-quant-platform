import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = (path) => readFileSync(resolve(root, path), 'utf8')

const page = read('src/views/tw-stock-monitor/index.vue')
const api = read('src/api/tw-stock.js')

assert.match(api, /export function getTwStockDailyAutoUpdateStatus \(\)/)
assert.match(api, /\/quant\/ops\/daily-auto-update\/status/)
assert.match(api, /method:\s*'get'/)

const helperMatch = api.match(/export function getTwStockDailyAutoUpdateStatus \(\) \{[\s\S]*?\n\}/)
assert.ok(helperMatch, 'missing daily auto update status helper')
const helperBody = helperMatch[0]
assert.doesNotMatch(helperBody, /post|put|patch|delete/i)
assert.doesNotMatch(helperBody, /publish|normal-publish|eod|dry-run|broker|quick-trade|place-order|order|refresh-provider/i)

assert.match(page, /每日自動更新狀態/)
assert.match(page, /tw-stock-daily-auto-update-panel/)
assert.match(page, /getTwStockDailyAutoUpdateStatus/)
assert.match(page, /loadDailyAutoUpdateStatus/)
assert.match(page, /dailyAutoUpdateStatus/)
assert.match(page, /latest accepted asof/)
assert.match(page, /pending asof/)
assert.match(page, /FinMind raw/)
assert.match(page, /Yahoo\/Scrapling qlib/)
assert.match(page, /next retry/)
assert.match(page, /fresh_data_wait/)
assert.match(page, /FinMind raw 数据已更新，但 Yahoo\/Scrapling qlib 复权数据尚未到目标日期/)
assert.match(page, /系统会继续按定时任务重试 pending asof/)
assert.match(page, /当前 latest 不更新是正确的保护行为/)
assert.match(page, /检测到自动更新计划配置或日志，系统会继续按配置重试/)
assert.match(page, /未检测到自动更新计划配置或日志，请检查 cron\/systemd 安装/)
assert.match(page, /orders_enabled=false/)
assert.match(page, /connects_to_broker=false/)
assert.match(page, /research_signal_not_order=true/)

const panelMatch = page.match(/<div class="daily-auto-update-panel"[\s\S]*?<div class="qlib-run-browser">/)
assert.ok(panelMatch, 'missing daily auto update panel block')
const panel = panelMatch[0]
for (const forbidden of [
  'publish',
  'normal-publish',
  'eod-pipeline',
  'refresh-provider',
  'scan-all',
  'quick-trade',
  'place-order',
  'broker connect',
  '下單',
  '提交订单',
  '提交訂單',
  '買入',
  '卖出',
  '自動交易',
  '自动交易'
]) {
  assert.ok(!panel.toLowerCase().includes(forbidden.toLowerCase()), `panel contains forbidden text: ${forbidden}`)
}

const methodMatch = page.match(/async loadDailyAutoUpdateStatus \(\) \{[\s\S]*?\n    \},\n    async loadQlibSignals/)
assert.ok(methodMatch, 'missing loadDailyAutoUpdateStatus method')
const methodBody = methodMatch[0]
assert.match(methodBody, /getTwStockDailyAutoUpdateStatus\(\)/)
assert.doesNotMatch(methodBody, /save|post|put|patch|delete|trigger|scanTwStockMonitor|triggerQlibOptionCDryRun|saveTwStockMonitorConfig/i)

console.log('tw-stock daily auto update panel checks passed')
