import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const router = fs.readFileSync(path.join(root, 'src/config/router.config.js'), 'utf8')
const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}

const hiddenDashboardRoutes = [
  'TradingBot',
  'BrokerAccounts'
]

function routeBlockByName (name) {
  const marker = `name: '${name}'`
  const pos = router.indexOf(marker)
  assert(pos >= 0, `${name} route is missing`)
  const start = router.lastIndexOf('{', pos)
  const end = router.indexOf('      },', pos)
  assert(start >= 0 && end > pos, `${name} route block could not be parsed`)
  return router.slice(start, end + 8)
}

for (const name of hiddenDashboardRoutes) {
  const block = routeBlockByName(name)
  assert(block.includes('hidden: true'), `${name} must stay hidden from the sidebar until the page is adapted`)
}


const visibleDashboardRoutes = [
  'AIAssetAnalysis',
  'IndicatorCommunity',
  'IndicatorIDE',
  'StrategyLive',
  'TWStockMonitor',
  'TWStockSimAccount'
]

for (const name of visibleDashboardRoutes) {
  const block = routeBlockByName(name)
  assert(!block.includes('hidden: true'), `${name} must remain visible in the sidebar`)
}


console.log('tw-stock menu scope checks passed')
