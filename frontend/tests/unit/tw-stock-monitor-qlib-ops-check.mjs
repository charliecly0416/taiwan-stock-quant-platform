import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const api = read('src/api/tw-stock.js')
const page = read('src/views/tw-stock-monitor/index.vue')

for (const required of [
  'triggerQlibOptionCDryRun',
  'getQlibOptionCJob',
  'getQlibOptionCJobLog',
  'getQlibOptionCLatestJob',
  'getQlibOptionCScheduler',
  '/quant/ops/option-c/dry-run',
  '/quant/ops/option-c/jobs',
  '/quant/ops/option-c/latest',
  '/quant/ops/option-c/scheduler'
]) {
  assert.ok(api.includes(required), `api missing ${required}`)
}

const triggerMatch = api.match(/function triggerQlibOptionCDryRun \(asof\) \{[\s\S]*?\n\}/)
assert.ok(triggerMatch, 'missing triggerQlibOptionCDryRun body')
assert.match(triggerMatch[0], /data:\s*\{ asof \}/)
for (const forbidden of ['provider', 'cwd', 'maxWorkers', 'max_workers', 'latest', 'accepted', 'publish', 'refresh']) {
  if (forbidden === 'latest') continue
  assert.ok(!triggerMatch[0].includes(forbidden), `trigger body contains forbidden ${forbidden}`)
}

for (const required of [
  'qlib Option C Ops Dry-run',
  'Dry-run only',
  'Research ops',
  'No latest update',
  'No accepted artifact',
  'No trading',
  'latest_signal_updated=',
  'normal_signal_run=',
  'accepted_artifact_generated=',
  'orders_enabled=',
  'writes_orders=',
  'writes_positions=',
  'triggerQlibOpsDryRun',
  'loadQlibOpsLatest',
  'refreshQlibOpsJob',
  'loadQlibOpsLog',
  'loadQlibScheduler',
  'Scheduler {{ qlibSchedulerEnabledText }}',
  'Manual tick dry-run only',
  'auto_loop_started'
]) {
  assert.ok(page.includes(required), `page missing ${required}`)
}

const opsMethodMatch = page.match(/triggerQlibOpsDryRun \(\) \{[\s\S]*?\n    \},\n    async refreshQlibOpsJob/)
assert.ok(opsMethodMatch, 'missing triggerQlibOpsDryRun method')
assert.match(opsMethodMatch[0], /triggerQlibOptionCDryRun\(asof\)/)
for (const forbidden of [
  'scanTwStockMonitor',
  'runTwStockReadonlyBacktest',
  'saveTwStockMonitorConfig',
  'publish',
  'refresh provider',
  'provider_uri',
  'target_position',
  'targetPosition'
]) {
  assert.ok(!opsMethodMatch[0].includes(forbidden), `ops trigger method contains forbidden ${forbidden}`)
}


for (const required of [
  'qlibOpsCanTrigger',
  'Admin ops required',
  'tw_stock_qlib_ops',
  'tw_stock_ops',
  'readLocalJson',
  'Option C ops admin or tw_stock_qlib_ops permission required'
]) {
  assert.ok(page.includes(required), `page missing auth guard UI text ${required}`)
}

assert.match(page, /<a-button v-if="qlibOpsCanTrigger"[\s\S]*?triggerQlibOpsDryRun/)

assert.ok(page.includes('qlibSchedulerEnabledText'), 'missing scheduler enabled computed')
assert.ok(page.includes('qlibSchedulerStatusColor'), 'missing scheduler status color computed')
assert.ok(!page.includes('scheduler/tick'), 'frontend must not expose scheduler tick endpoint')
for (const forbiddenSchedulerText of [
  '啟用自動調度',
  '启用自动调度',
  'Enable scheduler',
  'Start scheduler',
  'normal signal',
  'formal publish',
  'provider rebuild'
]) {
  assert.ok(!page.includes(forbiddenSchedulerText), `page contains forbidden scheduler text ${forbiddenSchedulerText}`)
}
for (const forbiddenText of [
  '買入',
  '买入',
  '賣出',
  '卖出',
  '下單',
  '提交订单',
  '提交訂單',
  '正式发布',
  '生成 latest',
  '生成 accepted',
  '刷新 provider',
  '刷新 qlib provider',
  'target position',
  'target weight'
]) {
  assert.ok(!page.toLowerCase().includes(forbiddenText.toLowerCase()), `page contains forbidden text ${forbiddenText}`)
}

console.log('tw-stock-monitor qlib ops checks passed')
