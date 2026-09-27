import {
  getTwStockPaperPortfolioLatestDecision,
  getTwStockPaperPortfolioState,
  getTwStockPaperPortfolioApplyRuns
} from '@/api/tw-stock-readonly'
import {
  applyTwStockPaperPortfolioDecision,
  resetTwStockPaperPortfolio
} from '@/api/tw-stock-action'

/** Simulation-account state and explicitly confirmed paper-only writes. */
export function usePaperPortfolio () {
  const state = { latest: null, account: null, runs: null, error: '', loading: false }
  async function load (params = {}) {
    state.loading = true
    state.error = ''
    try {
      const latest = await getTwStockPaperPortfolioLatestDecision(params)
      const latestData = latest && latest.data && latest.data.data ? latest.data.data : (latest && latest.data ? latest.data : latest)
      const accountParams = latestData && latestData.paper_account_id
        ? { ...params, paper_account_id: latestData.paper_account_id }
        : params
      // A missing clean decision is a valid empty state for a new user. Do
      // not follow it with a guaranteed 404 account-state request; the panel
      // can render the empty state while still showing the audit run list.
      const accountPromise = latestData && latestData.paper_account_id
        ? getTwStockPaperPortfolioState(accountParams)
        : Promise.resolve(null)
      const [account, runs] = await Promise.all([
        accountPromise,
        getTwStockPaperPortfolioApplyRuns({ ...accountParams, limit: 20 })
      ])
      Object.assign(state, { latest, account, runs })
      return { latest, account, runs }
    } catch (error) {
      state.error = error && error.message ? error.message : 'paper portfolio unavailable'
      throw error
    } finally {
      state.loading = false
    }
  }
  async function apply (payload = {}) {
    return applyTwStockPaperPortfolioDecision({ ...payload, paper_only: true })
  }
  async function reset (payload = {}) {
    return resetTwStockPaperPortfolio({ ...payload, paper_only: true })
  }
  return { state, load, apply, reset }
}
