import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const hooks = new URL('../../src/views/tw-stock-monitor/composables/', import.meta.url)
function loadHook (file, name, dependencies) {
  const source = readFileSync(fileURLToPath(new URL(file, hooks)), 'utf8')
    .replace(/import[\s\S]*?from '@\/api\/tw-stock-readonly'\s*/, '')
    .replace(`export function ${name}`, `function ${name}`)
  return vm.runInNewContext(`${source}\n${name}()`, dependencies)
}

let dailyCalls = 0
let readonlyCalls = 0
let failReadonly = true
const unavailable = new Error('readonly ops unavailable')
const ops = loadHook('useDailyOpsStatus.js', 'useDailyOpsStatus', {
  getTwStockDailyAutoUpdateStatus: async () => { dailyCalls += 1; return { status: 'accepted' } },
  getTwStockReadonlyOpsStatus: async () => {
    readonlyCalls += 1
    if (failReadonly) throw unavailable
    return { status: 'ready' }
  }
})
const first = ops.load()
assert.equal(ops.load(), first, 'concurrent callers must share the same request')
const partial = await first
assert.equal(partial.daily.status, 'accepted')
assert.equal(partial.readonly, null)
assert.equal(partial.errors.readonly, unavailable)
assert.equal(partial.errors.daily, null)
assert.equal(dailyCalls, 1)
assert.equal(readonlyCalls, 1)
assert.equal(ops.state.loading, false)
failReadonly = false
const recovered = await ops.load()
assert.equal(recovered.readonly.status, 'ready')
assert.equal(recovered.errors.readonly, null)
assert.equal(dailyCalls, 2, 'refresh must fetch new state instead of stale cached state')

const signal = loadHook('useSignalContext.js', 'useSignalContext', {
  getTwStockCurrentStrategyContext: async () => ({ signal_asof: '2026-09-18' })
})
assert.equal((await signal.load()).context.signal_asof, '2026-09-18')
assert.equal(signal.state.loading, false)
console.log('readonly load isolation behavior checks passed')
