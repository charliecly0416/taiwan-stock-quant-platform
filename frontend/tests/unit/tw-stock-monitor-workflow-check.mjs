import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = (path) => readFileSync(resolve(root, path), 'utf8')

const workflow = read('../.github/workflows/frontend-tw-stock-monitor.yml')
const acceptance = read('docs/TW_STOCK_MONITOR_FRONTEND_ACCEPTANCE_CN.md')
const smoke = read('docs/TW_STOCK_MONITOR_LOCAL_SMOKE_CN.md')

assert.match(workflow, /name:\s*Frontend TWStock Monitor/)
assert.match(workflow, /working-directory:\s*\.\/frontend/)
assert.match(workflow, /tests\/unit\/tw-stock-monitor-static-check\.mjs/)
assert.match(workflow, /tests\/unit\/tw-stock-monitor-qlib-ops-check\.mjs/)
assert.match(workflow, /node tests\/unit\/tw-stock-monitor-static-check\.mjs/)
assert.match(workflow, /node tests\/unit\/tw-stock-monitor-workflow-check\.mjs/)
assert.match(workflow, /pnpm install --frozen-lockfile/)
assert.match(workflow, /pnpm build/)

for (const forbidden of [
  'verify_tw_stock_research_stack',
  'backend_api_python',
  'quick-trade',
  'broker-accounts',
  'ibkr',
  'paper order',
  'live order',
  'submit order',
  'auto buy',
  'auto sell',
  '下單',
  '买入',
  '買入',
  '卖出',
  '賣出',
  '提交订单',
  '提交訂單',
  '刷新 qlib provider',
]) {
  assert.ok(!workflow.toLowerCase().includes(forbidden), `workflow contains forbidden text: ${forbidden}`)
}

for (const required of [
  '/#/tw-stock-monitor',
  'orders_enabled=false',
  'Human Review',
  '/api/tw-stock',
  'node tests/unit/tw-stock-monitor-static-check.mjs',
  'node tests/unit/tw-stock-monitor-workflow-check.mjs',
  'corepack pnpm build',
  'node tests/unit/tw-stock-monitor-local-smoke.mjs',
  '不连接 broker',
  '不启用 live',
  'qlib 研究观察草稿',
  '观察草稿是人工复盘用途',
  '保存监控配置必须由用户手动点击',
  '不自动扫描、不自动提醒、不自动交易',
  'qlib Option C 数据状态',
]) {
  assert.ok(acceptance.includes(required), `acceptance doc missing required text: ${required}`)
}

for (const required of [
  'http://127.0.0.1:8000/#/tw-stock-monitor',
  'VITE_DEV_PROXY_TARGET=http://localhost:5000',
  'ENABLE_TW_STOCK_MONITOR_WORKER=false',
  'AGENT_LIVE_TRADING_ENABLED=false',
  '/api/tw-stock/monitor/scan',
  '/api/tw-stock/monitor/config',
  '不进入后端台股研究 workflow',
  '不连接 broker',
  '不启用 live',
  '不提交订单',
  'qlib 研究观察草稿',
  '观察草稿是人工复盘用途',
  '保存监控配置必须由用户手动点击',
  '不自动扫描、不自动提醒、不自动交易',
  'qlib Option C 数据状态',
]) {
  assert.ok(smoke.includes(required), `local smoke doc missing required text: ${required}`)
}


for (const required of [
  'qlib Option C Ops Dry-run',
  'Dry-run only',
  'Research ops',
  'No latest update',
  'No accepted artifact',
  'No trading',
  '/api/tw-stock/quant/ops/option-c/dry-run',
  '/api/tw-stock/quant/ops/option-c/latest',
]) {
  assert.ok(workflow.includes(required) || acceptance.includes(required) || smoke.includes(required), `ops workflow docs missing required text: ${required}`)
}

console.log('tw-stock-monitor workflow checks passed')
