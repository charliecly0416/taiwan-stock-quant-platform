import {
  getTwStockDailyAutoUpdateStatus,
  getTwStockReadonlyOpsStatus
} from '@/api/tw-stock-readonly'

function createState () {
  return { data: null, error: '', loading: false }
}
/** Read-only operations/freshness state for the monitor workbench. */
export function useDailyOpsStatus () {
  const state = createState()
  let inflight = null
  function load () {
    if (inflight) return inflight
    inflight = read().finally(() => { inflight = null })
    return inflight
  }
  async function read () {
    state.loading = true
    state.error = ''
    try {
      const [daily, readonly] = await Promise.allSettled([
        getTwStockDailyAutoUpdateStatus(),
        getTwStockReadonlyOpsStatus()
      ])
      state.data = {
        daily: daily.status === 'fulfilled' ? daily.value : null,
        readonly: readonly.status === 'fulfilled' ? readonly.value : null,
        errors: {
          daily: daily.status === 'rejected' ? daily.reason : null,
          readonly: readonly.status === 'rejected' ? readonly.reason : null
        }
      }
      return state.data
    } catch (error) {
      state.error = error && error.message ? error.message : 'daily ops status unavailable'
      throw error
    } finally {
      state.loading = false
    }
  }
  return { state, load }
}
