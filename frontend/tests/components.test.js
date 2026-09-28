import test from 'node:test'
import assert from 'node:assert/strict'
import { empty, escape, format, latestRenderer, lineChart, modelOptions, statusPill } from '../src/components.js'

test('missing financial values are not presented as zero', () => {
  for (const value of [null, undefined, '', NaN, Infinity]) {
    for (const name of ['number', 'money', 'percent']) assert.equal(format[name](value), '—')
  }
  assert.equal(format.number(0), '0')
  assert.equal(format.percent(0), '0.00%')
  assert.equal(format.money(0), 'NT$ 0')
})

test('server messages and labels are rendered as text', () => {
  const value = '"><img src=x onerror=alert(1)>'
  for (const result of [empty(value, value), statusPill('BLOCKED', value),
    modelOptions([{ id: value, label: value, role: value }], ''),
    lineChart([{ nav: 1 }], 'nav', { label: value })]) {
    assert.doesNotMatch(result, /<img/)
    assert.ok(result.includes(escape(value)))
  }
})

test('latest response wins even when an earlier request finishes last', async () => {
  const out = { innerHTML: '', isConnected: true }
  const run = latestRenderer(out, error => error.message)
  let resolve
  const first = run(() => new Promise(done => { resolve = done }), String, 'loading old')
  await run(async () => 'current', String, 'loading current')
  resolve('obsolete'); await first
  assert.equal(out.innerHTML, 'current')
  out.isConnected = false
  await run(async () => 'detached result', String, 'detached loading')
  assert.equal(out.innerHTML, 'detached loading')
})

test('an all-missing time series does not draw a zero-valued chart', () => {
  assert.doesNotMatch(lineChart([{ nav: null }, { nav: undefined }], 'nav'), /<polyline/)
  const chart = lineChart([{ nav: 100 }, { nav: null }, { nav: 110 }], 'nav')
  assert.doesNotMatch(chart, /NaN|Infinity/)
  assert.match(chart, /<span>100<\/span>/)
  assert.match(chart, /<span>110<\/span>/)
})


test('maintenance distinguishes serving readiness from daily failure and escapes alerts', async () => {
  const { maintenancePanel } = await import('../src/components.js')
  const result = maintenancePanel({ maintenance: { status: 'CRITICAL', ready: true, created_at: new Date().toISOString(),
    alerts: [{ code: 'SCHEDULED_DAILY_FAILED' }, { code: '<script>unsafe</script>' }] } })
  assert.match(result, /最近计划日更失败/)
  assert.match(result, /role="alert"/)
  assert.doesNotMatch(result, /<script>/)
  assert.match(maintenancePanel({}), /尚未运行/)
})
