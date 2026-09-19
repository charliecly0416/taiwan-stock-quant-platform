import {
  getTwStockAgentContext,
  simpleChatTwStockAgent
} from '@/api/tw-stock-readonly'

/** Agent explanation context; backend owns prompt/artifact loading and safety gates. */
export function useAgentContext () {
  const state = { context: null, answer: null, error: '', loading: false }
  async function load (params = {}) {
    state.loading = true
    state.error = ''
    try {
      state.context = await getTwStockAgentContext(params)
      return state.context
    } catch (error) {
      state.error = error && error.message ? error.message : 'agent context unavailable'
      throw error
    } finally {
      state.loading = false
    }
  }
  async function ask (payload = {}) {
    state.loading = true
    state.error = ''
    try {
      state.answer = await simpleChatTwStockAgent(payload)
      return state.answer
    } catch (error) {
      state.error = error && error.message ? error.message : 'agent explanation unavailable'
      throw error
    } finally {
      state.loading = false
    }
  }
  return { state, load, ask }
}
