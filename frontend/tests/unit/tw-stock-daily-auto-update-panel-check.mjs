import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = (path) => readFileSync(resolve(root, path), 'utf8')

const page = read('src/views/tw-stock-monitor/index.vue')
const api = read('src/api/tw-stock-readonly.js')

assert.match(api, /export function getTwStockDailyAutoUpdateStatus \(\)/)
assert.match(api, /\/quant\/ops\/daily-auto-update\/status/)
assert.match(api, /method:\s*'get'/)
assert.match(api, /export function getTwStockReadonlyOpsStatus \(\)/)
assert.match(api, /\/quant\/ops\/readonly-status/)

const helperMatch = api.match(/export function getTwStockDailyAutoUpdateStatus \(\) \{[\s\S]*?\n\}/)
assert.ok(helperMatch, 'missing daily auto update status helper')
const helperBody = helperMatch[0]
assert.doesNotMatch(helperBody, /post|put|patch|delete/i)
assert.doesNotMatch(helperBody, /publish|normal-publish|eod|dry-run|broker|quick-trade|place-order|order|refresh-provider/i)

const readonlyOpsHelperMatch = api.match(/export function getTwStockReadonlyOpsStatus \(\) \{[\s\S]*?\n\}/)
assert.ok(readonlyOpsHelperMatch, 'missing readonly ops status helper')
const readonlyOpsHelperBody = readonlyOpsHelperMatch[0]
assert.doesNotMatch(readonlyOpsHelperBody, /post|put|patch|delete/i)
assert.doesNotMatch(readonlyOpsHelperBody, /normal-publish|eod-pipeline|provider-pull|refresh-provider|broker|quick-trade|place-order|target_position|target_weight/i)

assert.match(page, /每日自動更新觀測/)
assert.match(page, /tw-stock-daily-auto-update-panel/)
assert.match(page, /数据链路状态/)
assert.match(page, /tw-stock-data-freshness-overview/)
assert.match(page, /Raw \/ 行情/)
assert.match(page, /qlib accepted latest/)
assert.match(page, /controlled signal latest/)
assert.match(page, /readonly strategy snapshot latest/)
assert.match(page, /Agent DailyAgentPromptArtifact latest/)
assert.match(page, /latest natural cron job/)
assert.match(page, /latest DAPR18 evidence job/)
assert.match(page, /DAPR18 dry-run\/publish flags/)
assert.match(page, /blocker/)
assert.match(page, /next_action_hint/)
assert.match(page, /data-freshness-ops-grid/)
assert.match(page, /freshnessOverviewMessage/)
assert.match(page, /freshnessAcceptedLagging/)
assert.match(page, /refreshFreshnessOverview/)
assert.match(page, /刷新状态/)
assert.match(page, /getTwStockReadonlyOpsStatus/)
assert.match(page, /loadReadonlyOpsStatus/)
assert.match(page, /readonlyOpsStatus/)
assert.match(page, /getTwStockDailyAutoUpdateStatus/)
assert.match(page, /loadDailyAutoUpdateStatus/)
assert.match(page, /dailyAutoUpdateStatus/)
assert.match(page, /qlib accepted latest asof/)
assert.doesNotMatch(page, /latest accepted asof/)
assert.match(page, /pending asof/)
assert.match(page, /FinMind raw/)
assert.match(page, /Yahoo\/Scrapling qlib/)
assert.match(page, /next retry/)
assert.match(page, /fresh_data_wait/)
assert.match(page, /DAPR18 no-publish \/ dry-run observation/)
assert.match(page, /no-publish \/ dry-run observation/)
assert.match(page, /TW_DAPR18_PUBLISH_\*/)
assert.match(page, /same-day data window wait/)
assert.match(page, /只读 dry-run 观察完成，current asof/)
assert.match(page, /不表示 latest pointer 已自动推进/)
assert.doesNotMatch(page, /更新成功，latest_asof/)
assert.doesNotMatch(page, /成功后展示最新只读策略/)
assert.match(page, /FinMind raw 数据已更新，但 Yahoo\/Scrapling qlib 复权数据尚未到目标日期/)
assert.match(page, /系统会继续按定时任务重试 pending asof/)
assert.match(page, /当前 qlib accepted latest 不更新是保护状态，不是失败/)
assert.match(page, /检测到自动更新计划配置或日志，系统会继续按配置重试/)
assert.match(page, /未检测到自动更新计划配置或日志，请检查 cron\/systemd 安装/)
assert.match(page, /orders_enabled=false/)
assert.match(page, /connects_to_broker=false/)
assert.match(page, /research_signal_not_order=true/)

const panelMatch = page.match(/<div class="daily-auto-update-panel"[\s\S]*?<div class="qlib-run-browser">/)
assert.ok(panelMatch, 'missing daily auto update panel block')
const panel = panelMatch[0]
const overviewMatch = page.match(/<div class="data-freshness-overview"[\s\S]*?<a-alert\s+v-if="degradedNotice"/)
assert.ok(overviewMatch, 'missing first-screen data freshness overview block')
const overview = overviewMatch[0]
for (const forbidden of [
  'normal-publish',
  'eod-pipeline',
  'refresh-provider',
  'accepted latest switch',
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
  assert.ok(!overview.toLowerCase().includes(forbidden.toLowerCase()), `overview contains forbidden text: ${forbidden}`)
}

const methodMatch = page.match(/async loadDailyAutoUpdateStatus \(\) \{[\s\S]*?\n    \},\n    async loadReadonlyOpsStatus/)
assert.ok(methodMatch, 'missing loadDailyAutoUpdateStatus method')
const methodBody = methodMatch[0]
assert.match(methodBody, /getTwStockDailyAutoUpdateStatus\(\)/)
assert.doesNotMatch(methodBody, /save|post|put|patch|delete|trigger|scanTwStockMonitor|triggerQlibOptionCDryRun|saveTwStockMonitorConfig/i)

const readonlyOpsMethodMatch = page.match(/async loadReadonlyOpsStatus \(\) \{[\s\S]*?\n    \},\n    refreshFreshnessOverview/)
assert.ok(readonlyOpsMethodMatch, 'missing loadReadonlyOpsStatus method')
const readonlyOpsMethodBody = readonlyOpsMethodMatch[0]
assert.match(readonlyOpsMethodBody, /getTwStockReadonlyOpsStatus\(\)/)
assert.doesNotMatch(readonlyOpsMethodBody, /save|post|put|patch|delete|trigger|scanTwStockMonitor|triggerQlibOptionCDryRun|saveTwStockMonitorConfig|publish|switch|openai|broker|order/i)

const freshnessMethodMatch = page.match(/refreshFreshnessOverview \(\) \{[\s\S]*?\n    \},\n    async loadQlibSignals/)
assert.ok(freshnessMethodMatch, 'missing refreshFreshnessOverview method')
const freshnessMethodBody = freshnessMethodMatch[0]
assert.match(freshnessMethodBody, /loadReadonlyOpsStatus\(\)/)
assert.match(freshnessMethodBody, /loadDailyAutoUpdateStatus\(\)/)
assert.match(freshnessMethodBody, /loadQlibHealth\(\)/)
assert.match(freshnessMethodBody, /loadCurrentStrategyContext\(\)/)
assert.match(freshnessMethodBody, /loadReadonlyStrategySnapshot\(\)/)
assert.match(freshnessMethodBody, /loadTwStockAgentContext\(\)/)
assert.doesNotMatch(freshnessMethodBody, /save|post|put|patch|delete|trigger|scanTwStockMonitor|triggerQlibOptionCDryRun|saveTwStockMonitorConfig|publish|switch/i)

console.log('tw-stock daily auto update panel checks passed')
