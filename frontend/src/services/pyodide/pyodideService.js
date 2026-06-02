// Pyodide 主线程单例服务。
// - 懒创建 Worker，避免在无关页面也启动一个 ~20MB 的 Python 运行时。
// - 全局只有一个 Worker 实例；多页面 / 多组件复用。
// - 通过 Comlink 包装 Worker，主线程像调本地方法一样调用。
//
// 用法：
//   import pyodideService from '@/services/pyodide/pyodideService'
//   pyodideService.prewarm()         // 进入相关路由时调用（fire-and-forget）
//   const json = await pyodideService.runStrategy({ userCode, rawData, params })

import { wrap } from 'comlink'

let workerInstance = null
let api = null
let readyPromise = null
let state = {
  ready: false,
  loading: false,
  failed: false,
  error: null
}
const listeners = new Set()

function notify () {
  for (const cb of listeners) {
    try { cb({ ...state }) } catch (_) {}
  }
}

function _setState (patch) {
  state = { ...state, ...patch }
  notify()
}

function _readEnv () {
  // 读取构建期注入的 env（vite.config.js 已映射 VUE_APP_* → import.meta.env.VITE_*）
  // 这里同时兼容 process.env（define 兜底）和 import.meta.env
  const env = (typeof import.meta !== 'undefined' && import.meta.env) || {}
  const preferCdnRaw = env.VITE_PYODIDE_PREFER_CDN
  const preferCdn = preferCdnRaw === undefined || preferCdnRaw === ''
    ? import.meta.env.PROD
    : (preferCdnRaw === 'true' || preferCdnRaw === '1' || preferCdnRaw === 'yes')
  return {
    cdnBase: env.VITE_PYODIDE_CDN_BASE || '',
    localBase: env.VITE_PYODIDE_LOCAL_BASE || '',
    preferCdn,
    version: env.VITE_PYODIDE_VERSION || '0.25.0'
  }
}

function _createWorker () {
  if (workerInstance) return
  // Vite ES 模块 Worker：自动打包 comlink 依赖；pyodide.mjs 由 worker 内 import() 远程取。
  workerInstance = new Worker(new URL('./pyodide.worker.js', import.meta.url), {
    type: 'module',
    name: 'pyodide'
  })
  api = wrap(workerInstance)
}

async function ensureReady () {
  if (state.ready) return
  if (readyPromise) return readyPromise

  _createWorker()
  _setState({ loading: true, failed: false, error: null })

  readyPromise = (async () => {
    try {
      await api.init(_readEnv())
      _setState({ ready: true, loading: false, failed: false, error: null })
    } catch (err) {
      _setState({ ready: false, loading: false, failed: true, error: err && err.message ? err.message : String(err) })
      throw err
    }
  })()

  return readyPromise
}

function prewarm () {
  // fire-and-forget；调用方不关心结果，失败状态会通过 onStateChange 通知。
  ensureReady().catch(() => {})
}

async function runStrategy (payload) {
  await ensureReady()
  return api.runStrategy(payload)
}

async function runPython (code, globalsObj) {
  await ensureReady()
  return api.runPython(code, globalsObj)
}

async function loadPackages (pkgs) {
  await ensureReady()
  return api.loadPackages(pkgs)
}

function onStateChange (cb) {
  listeners.add(cb)
  // 立即推送当前状态，便于初始同步
  try { cb({ ...state }) } catch (_) {}
  return () => listeners.delete(cb)
}

function getState () {
  return { ...state }
}

export default {
  prewarm,
  ensureReady,
  runStrategy,
  runPython,
  loadPackages,
  onStateChange,
  getState
}
