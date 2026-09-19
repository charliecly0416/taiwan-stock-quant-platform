import { getTwStockCurrentStrategyContext } from '@/api/tw-stock-readonly'

/** Unified descriptor/context reads; never reads experiment files in the browser. */
export function useSignalContext () {
  const state = { context: null, productization: null, error: '', loading: false }
  async function load (params = {}) {
    state.loading = true
    state.error = ''
    try {
      const context = await getTwStockCurrentStrategyContext(params)
      state.context = context
      return { context }
    } catch (error) {
      state.error = error && error.message ? error.message : 'signal context unavailable'
      throw error
    } finally {
      state.loading = false
    }
  }
  return { state, load }
}
