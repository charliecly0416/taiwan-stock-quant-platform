import test from 'node:test'
import assert from 'node:assert/strict'
import { api } from '../src/api.js'

test('comparison omits unused date bounds so strict API validation succeeds', async t => {
  let url
  t.mock.method(globalThis, 'fetch', async path => {
    url = new URL(path, 'http://localhost')
    return { ok: true, json: async () => ({ status: 'READY' }) }
  })
  await api.compare('model_a', 'model_a_plus_b', '2026-05-07')
  assert.equal(url.searchParams.get('date'), '2026-05-07')
  assert.equal(url.searchParams.has('start'), false)
  assert.equal(url.searchParams.has('end'), false)
})

test('comparison preserves an explicitly selected replay window', async t => {
  let url
  t.mock.method(globalThis, 'fetch', async path => {
    url = new URL(path, 'http://localhost')
    return { ok: true, json: async () => ({ status: 'READY' }) }
  })
  await api.compare('model_a', 'model_a_plus_b', '2026-05-07', '2026-04-30', '2026-05-07')
  assert.equal(url.searchParams.get('start'), '2026-04-30')
  assert.equal(url.searchParams.get('end'), '2026-05-07')
})

test('default date is omitted without silently removing invalid numeric zero', async t => {
  let url
  t.mock.method(globalThis, 'fetch', async path => {
    url = new URL(path, 'http://localhost')
    return { ok: false, json: async () => ({ status: 'BLOCKED', message: 'limit must be positive' }) }
  })
  await assert.rejects(api.rankings('model_a', undefined, 0), /limit must be positive/)
  assert.equal(url.searchParams.has('date'), false)
  assert.equal(url.searchParams.get('limit'), '0')
})

test('research questions send only the local readonly payload', async t => {
  let sent
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    sent = { path, ...options }
    return { ok: true, json: async () => ({ status: 'READY', readonly: true }) }
  })
  await api.simpleChat('排名第一是谁？', '2026-09-24')
  assert.equal(sent.path, '/api/tw-stock/agent/simple-chat')
  assert.equal(sent.method, 'POST')
  assert.deepEqual(JSON.parse(sent.body), { question: '排名第一是谁？', date: '2026-09-24' })
})

test('paper authorization stays in headers and does not enter URLs or research requests', async t => {
  const sent = []
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    sent.push({ path, ...options })
    return { ok: true, json: async () => ({ status: 'READY' }) }
  })
  await api.paperAccount('fixture-token', 'account with spaces')
  assert.equal(sent[0].headers.Authorization, 'Bearer fixture-token')
  assert.equal(sent[0].path.includes('fixture-token'), false)
  await api.simpleChat('排名', '2026-09-24')
  assert.equal(sent[1].headers.Authorization, undefined)
})
