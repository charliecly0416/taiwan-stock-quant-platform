## Summary

Describe the Taiwan stock research change and affected backend/frontend/docs areas.

## TWStock Research Safety

- [ ] Ran `python backend/scripts/verify_tw_stock_research_stack.py` or explained why it is not applicable.
- [ ] `AGENT_LIVE_TRADING_ENABLED=false` remains the expected default for research checks.
- [ ] No broker integration is introduced or expanded without explicit review.
- [ ] No IBKR path can submit a paper/live order from the Taiwan stock research workflow.
- [ ] No quick-trade entry is added to TWStock research signals.
- [ ] Any qlib/market-data operation is dry-run/preflight gated unless explicitly reviewed.
- [ ] Research outputs remain recommendations/watchlists, not orders or target positions.
