// Vue 2.7 Composition API 包装：暴露响应式 ready / loading / failed 状态。
// 在 KlineChart 这类只用一次的页面里用更顺手，且自动在组件卸载时取消订阅。

import { ref, onBeforeUnmount } from 'vue'
import pyodideService from './pyodideService'

export function usePyodide ({ autoPrewarm = false } = {}) {
  const ready = ref(false)
  const loading = ref(false)
  const failed = ref(false)
  const error = ref(null)

  const unsubscribe = pyodideService.onStateChange((s) => {
    ready.value = s.ready
    loading.value = s.loading
    failed.value = s.failed
    error.value = s.error
  })

  onBeforeUnmount(() => {
    unsubscribe()
  })

  if (autoPrewarm) {
    pyodideService.prewarm()
  }

  return {
    ready,
    loading,
    failed,
    error,
    prewarm: pyodideService.prewarm,
    ensureReady: pyodideService.ensureReady,
    runStrategy: pyodideService.runStrategy,
    runPython: pyodideService.runPython,
    loadPackages: pyodideService.loadPackages
  }
}
