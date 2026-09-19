import {
  getTwStockReadonlyReplayWindowIndex,
  getTwStockReadonlyReplayWindow,
  getTwStockObservationReplay
} from '@/api/tw-stock-readonly'
import { runTwStockPortfolioReplay } from '@/api/tw-stock-action'

/** Replay query surface; POST is explicitly simulation-only and persist=false. */
export function useReadonlyReplay () {
  const state = { index: null, window: null, observation: null, result: null, error: '', loading: false }
  async function loadIndex () {
    state.index = await getTwStockReadonlyReplayWindowIndex()
    return state.index
  }
  async function loadWindow (params = {}) {
    state.window = await getTwStockReadonlyReplayWindow(params)
    return state.window
  }
  async function loadObservation (params = {}) {
    state.observation = await getTwStockObservationReplay(params)
    return state.observation
  }
  async function simulate (payload = {}) {
    state.loading = true
    state.error = ''
    try {
      state.result = await runTwStockPortfolioReplay({ ...payload, persist: false })
      return state.result
    } catch (error) {
      state.error = error && error.message ? error.message : 'readonly replay unavailable'
      throw error
    } finally {
      state.loading = false
    }
  }
  return { state, loadIndex, loadWindow, loadObservation, simulate }
}
