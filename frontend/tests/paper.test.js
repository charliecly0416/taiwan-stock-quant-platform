import test from 'node:test'
import assert from 'node:assert/strict'
import { paperResult } from '../src/paper.js'

test('preview displays projected holdings and labels them as unapplied', () => {
  const html = paperResult({ status: 'PREVIEW', execute_date: '2026-09-24',
    after: { cash: '80.00', nav: '890.00', positions: { TW2330: { quantity: 90, cost_basis: '920', mark_price: '9' } } } })
  assert.match(html, /尚未应用/)
  assert.match(html, /TW2330/)
  assert.match(html, /NT\$ 890/)
})

test('paper history escapes server labels', () => {
  const html = paperResult({ runs: [{ operation: '<script>', created_at: 'today', result: { status: 'READY' } }] })
  assert.equal(html.includes('<script>'), false)
  assert.match(html, /&lt;script&gt;/)
})
