import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(new URL('..', import.meta.url).pathname, '..')
const read = (path) => readFileSync(resolve(root, path), 'utf8')

const page = read('src/views/tw-stock-monitor/index.vue')
const readonlyApi = read('src/api/tw-stock-readonly.js')
const actionApi = read('src/api/tw-stock-action.js')
const compatApi = read('src/api/tw-stock.js')
const paperPanel = read('src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue')
const api = `${readonlyApi}\n${actionApi}\n${compatApi}`
const routes = read('src/config/router.config.js')
const permission = read('src/permission.js')
const aiAssetPage = read('src/views/ai-asset-analysis/index.vue')

assert.match(routes, /redirect:\s*'\/tw-stock-monitor'/)
assert.match(permission, /defaultRoutePath\s*=\s*'\/tw-stock-monitor'/)
assert.match(routes, /path:\s*'\/tw-stock-monitor'/)
assert.match(routes, /menu\.dashboard\.twStockMonitor/)
assert.match(readonlyApi, /const BASE_URL = '\/api\/tw-stock'/)
assert.match(readonlyApi, /export function getTwStockReadonlyOpsStatus \(\)/)
assert.match(readonlyApi, /\/quant\/ops\/readonly-status/)
assert.match(readonlyApi, /getTwStockReadonlyOpsStatus \(\) \{[\s\S]*method:\s*'get'/)
assert.match(compatApi, /export \* from '\.\/tw-stock-readonly'/)
assert.match(compatApi, /export \* from '\.\/tw-stock-action'/)
assert.match(readonlyApi, /getTwStockLTRReadonlyExplanation/)
assert.match(readonlyApi, /\/ltr-readonly-explanation/)
assert.match(page, /data-testid="ltr-readonly-explanation-panel"/)
assert.match(page, /为什么现在不动/)
assert.match(page, /item\.why_no_action/)
assert.match(page, /item\.tradeoff_summary/)
assert.match(page, /item\.readonly_disclaimer/)
assert.match(page, /查看历史回放明细/)
assert.match(page, /detail\.net_return_summary/)
assert.match(page, /detail\.drawdown_summary/)
assert.match(page, /detail\.action_count_summary/)
assert.match(page, /detail\.turnover_summary/)
assert.match(page, /loadLtrReadonlyExplanation/)
assert.match(page, /getTwStockLTRReadonlyExplanation\(\)/)
assert.match(readonlyApi, /getTwStockLTROptionalSimStrategies/)
assert.match(readonlyApi, /\/ltr-optional-sim-strategies/)
assert.match(readonlyApi, /getTwStockLTROptionalSimStrategies \(\) \{[\s\S]*method: 'get'/)
assert.match(page, /data-testid="ltr-optional-sim-strategy-panel"/)
assert.match(page, /可选模拟策略/)
assert.match(page, /默认主策略/)
assert.match(page, /ltrOptionalSimSelected: 'phase1c_ltr_simple_daily'/)
assert.match(page, /换手 proxy/)
assert.match(page, /首屏主指标使用独立测试区间/)
assert.match(page, /样本内\/验证\/样本外混合结果/)
assert.match(page, /item\.display_name/)
assert.match(page, /ltrOptionalSimSelectedStrategy\.status_label/)
assert.match(page, /费用后历史模拟/)
assert.match(page, /independent_test 切片/)
assert.match(page, /ltrOptionalSimSelectedStrategy\.display_name/)
assert.match(page, /仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。/)
assert.match(page, /loadLtrOptionalSimStrategies/)
assert.match(page, /getTwStockLTROptionalSimStrategies\(\)/)
assert.doesNotMatch(page, /source_trace/)
assert.doesNotMatch(page, /summary_notes/)

assert.doesNotMatch(readonlyApi, /manual-review\/explanation/)
assert.doesNotMatch(readonlyApi, /getTwStockManualReviewExplanation/)
assert.doesNotMatch(page, /manualReviewReadonlyTestMode/)
assert.doesNotMatch(page, /manual-review-readonly-test/)
assert.doesNotMatch(page, /manual-review-explanation-panel/)

assert.doesNotMatch(aiAssetPage, /getTradingOpportunities/)
assert.doesNotMatch(aiAssetPage, /QuickTradePanel/)
assert.doesNotMatch(aiAssetPage, /quick-trade|qt-floating-btn|radar-section/)

assert.match(page, /from '@\/api\/tw-stock-readonly'/)
assert.match(page, /from '@\/api\/tw-stock-action'/)
assert.doesNotMatch(page, /from '@\/api\/tw-stock'/)
assert.match(page, /getTwStockReadonlyOpsStatus/)
assert.match(page, /loadReadonlyOpsStatus/)
assert.match(page, /readonlyOpsStatus/)
assert.doesNotMatch(page, /chatTwStockAgent/)
assert.doesNotMatch(page, /saveTwStockMonitorConfig|scanTwStockMonitor|scanAllTwStockMonitors|updateTwStockAlert|triggerQlibOptionCDryRun|createTwStockSimAccount|draftTwStockSimOrder|confirmTwStockSimOrder|cancelTwStockSimOrder|applyTwStockPaperPortfolioDecision|resetTwStockPaperPortfolio/)
const actionImportMatch = page.match(/import \{[\s\S]*?\} from '@\/api\/tw-stock-action'/)
assert.ok(actionImportMatch, 'monitor page must explicitly import readonly simulation POST helpers from action client')
assert.match(actionImportMatch[0], /runTwStockReadonlyBacktest/)
assert.match(actionImportMatch[0], /runTwStockPortfolioReplay/)
assert.doesNotMatch(actionImportMatch[0], /chatTwStockAgent|saveTwStockMonitorConfig|scanTwStockMonitor|scanAllTwStockMonitors|updateTwStockAlert|triggerQlibOptionCDryRun|createTwStockSimAccount|draftTwStockSimOrder|confirmTwStockSimOrder|cancelTwStockSimOrder|applyTwStockPaperPortfolioDecision|resetTwStockPaperPortfolio/)

assert.match(paperPanel, /from '@\/api\/tw-stock-readonly'/)
assert.match(paperPanel, /from '@\/api\/tw-stock-action'/)
assert.doesNotMatch(paperPanel, /from '@\/api\/tw-stock'/)
assert.match(paperPanel, /getTwStockPaperPortfolioState/)
assert.match(paperPanel, /applyTwStockPaperPortfolioDecision/)
assert.match(paperPanel, /resetTwStockPaperPortfolio/)

const readonlyPostMatches = readonlyApi.match(/method:\s*['"]post['"]/g) || []
assert.equal(readonlyPostMatches.length, 1, 'readonly client must contain only the simple-chat explanation POST exception')
assert.match(readonlyApi, /simpleChatTwStockAgent[\s\S]*\/agent\/simple-chat/)
assert.doesNotMatch(readonlyApi, /method:\s*['"](put|delete|patch)['"]/i)
for (const [name, pattern] of [
  ['/monitor/scan write', /\/monitor\/scan[`'"]/],
  ['/monitor/scan-all write', /\/monitor\/scan-all[`'"]/],
  ['/quant/ops/option-c/dry-run', /\/quant\/ops\/option-c\/dry-run/],
  ['/quant/ops/option-c/scheduler/tick', /\/quant\/ops\/option-c\/scheduler\/tick/],
  ['/quant/ops/option-c/accepted-latest-scheduler', /\/quant\/ops\/option-c\/accepted-latest-scheduler/],
  ['/quant/ops/option-c/eod-pipeline/tick', /\/quant\/ops\/option-c\/eod-pipeline\/tick/],
  ['/quant/ops/option-c/eod-automation/tick', /\/quant\/ops\/option-c\/eod-automation\/tick/],
  ['/quant/ops/option-c/normal-publish', /\/quant\/ops\/option-c\/normal-publish/],
  ['/paper-portfolio/apply-decision', /\/paper-portfolio\/apply-decision/],
  ['/paper-portfolio/reset', /\/paper-portfolio\/reset/],
  ['/sim/orders/draft', /\/sim\/orders\/draft/],
  ['/agent/chat', /\/agent\/chat[`'"]/],
  ['/api/indicator/backtest POST', /url:\s*['"]\/api\/indicator\/backtest['"]/]
]) {
  assert.doesNotMatch(readonlyApi, pattern, `readonly client contains forbidden endpoint: ${name}`)
}
assert.doesNotMatch(readonlyApi, /broker|quick-trade|orders\/|target_position|targetPosition|target_weight|targetWeight|provider_uri|providerPath|provider_path|refresh-provider|publish-job/i)
const simpleChatBlock = readonlyApi.slice(readonlyApi.indexOf('export function simpleChatTwStockAgent'), readonlyApi.indexOf('export function getQlibOptionCHealth'))
assert.match(simpleChatBlock, /question/)
assert.match(simpleChatBlock, /symbol/)
assert.match(simpleChatBlock, /maxItems/)
assert.doesNotMatch(simpleChatBlock, /\b(order|target|broker|provider|monitor|publish|OPENAI_API_KEY|openai|baseURL|base_url)\s*:/i)

for (const source of [page, paperPanel, readonlyApi, actionApi, compatApi]) {
  assert.doesNotMatch(source, /https:\/\/api\.openai\.com|OPENAI_API_KEY|openai_api_key|OpenAI base URL|Authorization:\s*['"]Bearer|new OpenAI|createOpenAI|\/v1\/chat\/completions/i)
}

assert.match(actionApi, /saveTwStockMonitorConfig[\s\S]*\/monitor\/config[\s\S]*method:\s*'post'/)
assert.match(actionApi, /updateTwStockAlert[\s\S]*\/monitor\/alerts\/\$\{id\}[\s\S]*method:\s*'put'/)
assert.match(actionApi, /scanTwStockMonitor[\s\S]*\/monitor\/scan[\s\S]*method:\s*'post'/)
assert.match(actionApi, /triggerQlibOptionCDryRun[\s\S]*\/quant\/ops\/option-c\/dry-run[\s\S]*method:\s*'post'/)
assert.match(actionApi, /applyTwStockPaperPortfolioDecision[\s\S]*\/paper-portfolio\/apply-decision[\s\S]*method:\s*'post'/)
assert.match(actionApi, /resetTwStockPaperPortfolio[\s\S]*\/paper-portfolio\/reset[\s\S]*method:\s*'post'/)
assert.match(actionApi, /chatTwStockAgent[\s\S]*\/agent\/chat[\s\S]*method:\s*"post"/)
assert.match(actionApi, /runTwStockPortfolioReplay[\s\S]*\/rank-tech-cross\/portfolio-replay[\s\S]*persist:\s*false/)
assert.match(actionApi, /runTwStockReadonlyBacktest[\s\S]*\/api\/indicator\/backtest[\s\S]*persist:\s*false/)

for (const endpoint of [
  '/monitor/config',
  '/monitor/alerts',
  '/monitor/history',
  '/monitor/scan',
  '/monitor/scan-all',
  '/monitor/scan-logs'
]) {
  assert.ok(api.includes(endpoint), `missing endpoint ${endpoint}`)
}

assert.match(page, /orders_enabled=false/)
assert.match(page, /<h2>台股研究<\/h2>/)
assert.match(page, /本页面仅用于台股研究信号的人工复盘与历史验证，不连接券商，不产生真实交易委托，不构成投资建议。/)
assert.match(page, /data-testid="strategy-workbench-selection-controls"/)
assert.match(page, /handleWorkbenchModelSelect/)
assert.match(page, /handleWorkbenchStrategySelect/)
assert.match(page, /readonlyWorkbenchMode \(\) \{[\s\S]*?return true/)
assert.match(page, /查看配置/)
assert.doesNotMatch(page, /<a-icon type="scan" \/> 手動研究掃描/)
assert.match(page, /degradedNotice/)
assert.match(page, /刷新监控状态/)
assert.match(page, /refreshMonitorReadonly/)
assert.match(page, /provider\/raw latest/)
assert.match(page, /qlib accepted latest/)
assert.match(page, /controlled signal latest/)
assert.match(page, /readonly strategy snapshot latest/)
assert.match(page, /Agent DailyAgentPromptArtifact latest/)
assert.match(page, /latest natural cron job/)
assert.match(page, /latest DAPR18 evidence job/)
assert.match(page, /DAPR18 dry-run\/publish flags/)
assert.match(page, /blocker/)
assert.match(page, /next_action_hint/)
assert.match(page, /data-freshness-ops-grid/)
assert.match(page, /readonlyOpsProviderRawLatest/)
assert.match(page, /readonlyOpsQlibAcceptedLatest/)
assert.match(page, /readonlyOpsControlledSignalLatest/)
assert.match(page, /readonlyOpsSnapshotLatest/)
assert.match(page, /readonlyOpsAgentPromptLatest/)
assert.match(page, /readonlyOpsNaturalCronJob/)
assert.match(page, /readonlyOpsDapr18EvidenceJob/)
assert.match(page, /readonlyOpsDapr18Controls/)
assert.match(page, /unknown provider\/raw latest/)
assert.match(page, /unknown qlib accepted latest/)
assert.match(page, /unknown controlled signal latest/)
assert.match(page, /unknown readonly snapshot latest/)
assert.match(page, /unknown Agent prompt latest/)
assert.match(page, /this\.loadReadonlyOpsStatus\(\)/)
assert.match(page, /derived\/fallback from current-strategy-context/)
assert.match(page, /derived\/fallback from cross-analysis/)
assert.match(page, /首屏使用 readonly snapshot latest/)
assert.match(page, /qlib accepted latest .*Agent prompt latest .*分开展示/)
assert.match(page, /DAPR18 no-publish \/ dry-run observation/)
assert.match(page, /same-day data window wait/)
assert.match(page, /当前 qlib accepted latest 不更新是保护状态，不是失败/)
assert.match(page, /只读 dry-run 观察完成，current asof/)
assert.match(page, /不表示 latest pointer 已自动推进/)
assert.doesNotMatch(page, /更新成功，latest_asof/)
assert.doesNotMatch(page, /成功后展示最新只读策略/)
assert.doesNotMatch(page, /latest accepted asof/)
assert.doesNotMatch(page, /当前首屏使用 .*accepted.*只读策略口径/)
assert.match(page, /当前策略工作台为只读模式，不在前端保存监控配置。/)
assert.match(page, /当前策略工作台为只读模式，不在前端写入提醒状态。/)
assert.match(page, /当前策略工作台为只读模式，不在前端手动运行 qlib ops。/)
assert.match(page, /当前策略工作台为只读模式，不在前端保存复盘状态。/)
assert.match(page, /日線 K 線 \/ 走勢/)
assert.match(page, /ref="priceChart"/)
assert.match(page, /ref="scoreChart"/)
assert.match(page, /getTwStockHistory/)
assert.match(page, /getTwStockKline/)
assert.match(page, /refreshIntervalMs/)
assert.match(page, /window\.setInterval/)
assert.match(page, /showMovingAverages/)
assert.match(page, /showVolume/)
assert.match(page, /movingAveragePoints/)
assert.match(page, /trendCustomRow/)
assert.match(page, /selected-symbol-panel/)
assert.match(page, /MA5/)
assert.match(page, /MA20/)
assert.match(page, /MA60/)
assert.match(page, /量能/)
assert.match(page, /Vol Ratio/)
assert.match(page, /60D/)
assert.match(page, /Bars/)
assert.match(page, /chart-tooltip/)
assert.match(page, /handleChartMouseMove/)
assert.match(page, /clearChartHover/)
assert.match(page, /chartLayouts/)
assert.match(page, /priceDataStatusText/)
assert.match(page, /priceDataStale/)
assert.match(page, /chartEmptyText/)
assert.match(page, /route\.query\.symbol/)
assert.match(page, /日線資料可能過舊/)
assert.match(page, /chartRangeBars/)
assert.match(page, /displayedPriceCandles/)
assert.match(page, /displayedHistoryItems/)
assert.match(page, /handleChartRangeChange/)
assert.match(page, /sliceByChartRange/)
assert.match(page, /chartWindowText/)
assert.match(page, /30D/)
assert.match(page, /120D/)
assert.match(page, /窗口/)
assert.match(api, /getTwStockKline/)
assert.match(api, /\/api\/indicator\/kline/)
assert.match(api, /market:\s*'TWStock'/)
assert.match(api, /getTwStockBacktestTemplates/)
assert.match(api, /runTwStockReadonlyBacktest/)
assert.match(api, /\/api\/indicator\/backtest\/tw-stock\/templates/)
assert.match(api, /\/api\/indicator\/backtest/)
assert.match(api, /persist:\s*false/)
assert.match(api, /enableMtf:\s*false/)
assert.match(api, /timeframe:\s*'1D'/)

assert.match(api, /getQlibOptionCHealth/)
assert.match(api, /\/quant\/signals\/health/)
assert.match(page, /qlib Option C 数据状态/)
assert.match(page, /getQlibOptionCHealth\(\)/)
assert.match(page, /loadQlibHealth/)
assert.match(page, /TWStock local daily bars/)
assert.match(page, /qd_tw_stock_daily_bars/)
assert.match(page, /accepted/)
assert.match(page, /stale/)
assert.match(page, /wait-state/)
assert.match(page, /missing/)
assert.match(page, /qlibHealthWarnings/)
assert.match(api, /getLatestQlibOptionCSignals/)
assert.match(api, /\/quant\/signals\/latest/)
assert.match(api, /getQlibOptionCRuns/)
assert.match(api, /getQlibOptionCRunDetail/)
assert.match(api, /\/quant\/signals\/runs/)
assert.match(api, /encodeURIComponent\(runId\)/)
assert.match(api, /normalizedBucket = bucket === 'top50' \? 'top50' : 'top30'/)
assert.match(api, /enrichTrend:\s*Boolean\(enrichTrend\)/)
assert.match(api, /trendLimit:\s*Math\.max\(20,\s*Math\.min\(Number\(trendLimit \|\| 120\),\s*500\)\)/)
assert.doesNotMatch(api, /enrich_trend\s*:\s*true/)


assert.match(api, /triggerQlibOptionCDryRun/)
assert.match(api, /getQlibOptionCJob/)
assert.match(api, /getQlibOptionCJobLog/)
assert.match(api, /getQlibOptionCLatestJob/)
assert.match(api, /\/quant\/ops\/option-c\/dry-run/)
assert.match(api, /\/quant\/ops\/option-c\/jobs/)
assert.match(api, /\/quant\/ops\/option-c\/latest/)
assert.match(api, /data:\s*\{ asof \}/)
assert.doesNotMatch(api, /provider_uri|providerPath|provider_path|max_workers|maxWorkers|publish-job|refresh-provider/)
assert.match(page, /qlib Option C Ops Dry-run/)
assert.match(page, /Dry-run only/)
assert.match(page, /Research ops/)
assert.match(page, /No latest update/)
assert.match(page, /No accepted artifact/)
assert.match(page, /No trading/)
assert.match(page, /triggerQlibOpsDryRun/)
assert.match(page, /loadQlibOpsLatest/)
assert.match(page, /refreshQlibOpsJob/)
assert.match(page, /loadQlibOpsLog/)
assert.match(page, /latest_signal_updated=/)
assert.match(page, /normal_signal_run=/)
assert.match(page, /accepted_artifact_generated=/)
assert.match(page, /orders_enabled=/)
assert.match(page, /writes_orders=/)
assert.match(page, /writes_positions=/)
assert.match(page, /stdout/)
assert.match(page, /stderr/)
assert.doesNotMatch(page, /刷新 qlib provider|正式发布|生成 latest|生成 accepted/)

assert.match(page, /当前 asof 研究排名/)
assert.match(page, /qlib Option C 歷史研究 run/)
assert.match(page, /qlibRunStatusFilter/)
assert.match(page, /loadQlibRuns/)
assert.match(page, /loadQlibRunDetail/)
assert.match(page, /getQlibOptionCRuns\(\{ limit: 20, status: this\.qlibRunStatusFilter \}\)/)
assert.match(page, /getQlibOptionCRunDetail\(run\.run_id/)
assert.match(page, /回到 latest/)
assert.match(page, /blocked\/wait-state run 不展示可用 signals/)
assert.match(page, /研究觀察草稿/)
assert.match(page, /加入觀察/)
assert.match(page, /查看配置草稿/)
assert.match(page, /觀察草稿僅供人工復盤/)
assert.match(page, /不會自動啟用掃描/)
assert.match(page, /不會自動建立提醒/)
assert.match(page, /不會產生訂單或持倉/)
assert.match(page, /qlibWatchDraft/)
assert.match(page, /addQlibWatchDraft/)
assert.match(page, /fillMonitorConfigFromQlibDraft/)
assert.match(page, /tw-stock-monitor-qlib-watch-draft/)
assert.match(page, /研究排序/)
assert.match(page, /非交易建议/)
assert.match(page, /高级只读诊断/)
assert.match(page, /低频维护信息/)
assert.match(page, /不触发补数、发布或 latest 切换/)
assert.match(page, /copyReadonlyStatusSummary/)
assert.match(page, /buildReadonlyStatusSummaryPayload/)
assert.match(page, /只读展示；不拉取数据、不发布 provider、不切换 latest、不连接券商、不产生订单。/)
assert.match(page, /Top 30/)
assert.match(page, /Top 50/)
assert.match(page, /asof/)
assert.match(page, /run_id/)
assert.match(page, /ranking-meta-grid/)
assert.match(page, /模型日期/)
assert.match(page, /行情日期/)
assert.match(page, /qlib_score/)
assert.doesNotMatch(page, /diagnostic_only=\{\{/)
assert.match(page, /research_signal_not_order/)
assert.match(page, /qlibWarnings/)
assert.match(page, /qlibSignalsAccepted/)
assert.match(page, /qlibEmptyText/)
assert.match(page, /getLatestQlibOptionCSignals\(\{ bucket: this\.qlibBucket, enrichTrend: true, trendLimit: 120 \}\)/)
assert.match(page, /selectTrendSymbol\(record\.symbol\)/)
assert.match(page, /enrichTrend:\s*true/)
assert.match(page, /trendLimit:\s*120/)
assert.doesNotMatch(page, /enrich_trend\s*:\s*true/)
assert.doesNotMatch(page, /qlib_score[^\n]{0,80}(收益|勝率|胜率|漲幅|涨幅|概率|機率|仓位|倉位)/)
assert.doesNotMatch(page, /(收益|勝率|胜率|漲幅|涨幅|概率|機率|仓位|倉位)[^\n]{0,80}qlib_score/)

assert.match(page, /trend_label/)
assert.match(page, /trend_score/)
assert.match(page, /price-date-cell/)
assert.match(page, /quality_warnings/)
assert.match(page, /trend unavailable|趋势不可用/)
assert.match(page, /qlibTrendAvailable/)
assert.doesNotMatch(page, /combined_score/)
assert.doesNotMatch(api, /combined_score/)
assert.doesNotMatch(page, /buy_score/)
assert.doesNotMatch(api, /buy_score/)
assert.doesNotMatch(page, /target_weight/)
assert.doesNotMatch(api, /target_weight/)
const pageWithoutReadonlySafetyFlags = page.replace(/not_target_position/g, '')
const apiWithoutReadonlySafetyFlags = api.replace(/not_target_position/g, '')
assert.doesNotMatch(pageWithoutReadonlySafetyFlags, /target_position/)
assert.doesNotMatch(apiWithoutReadonlySafetyFlags, /target_position/)

assert.match(page, /回測驗證/)
assert.match(page, /台股只讀回測驗證/)
assert.match(page, /歷史模擬/)
assert.match(page, /historical simulation/)
assert.match(page, /connects_to_broker=false/)
assert.match(page, /getTwStockBacktestTemplates/)
assert.match(page, /runTwStockReadonlyBacktest/)
assert.match(page, /strategyId/)
assert.match(page, /ma_cross_builtin/)
assert.match(page, /backtestEquityChart/)
assert.match(page, /backtestDataQuality/)
assert.match(page, /backtestAssumptions/)
assert.match(page, /backtestTrades/)
assert.match(page, /需要先更新本地日線歸檔/)

assert.match(page, /title: '操作'/)
assert.match(page, /加入觀察/)
assert.match(page, /回測驗證/)
assert.match(page, /@click\.stop="addQlibWatchDraft\(row\)"/)
assert.match(page, /openQlibReadonlyBacktest/)
assert.match(page, /@click\.stop="openQlibReadonlyBacktest\(row\)"/)
assert.match(page, /readonlyBacktestPanel/)
assert.match(page, /this\.backtestPanelVisible = true/)
assert.match(page, /await this\.selectTrendSymbol\(row\.symbol\)/)
assert.match(page, /scrollIntoView\(\{ behavior: 'smooth', block: 'start' \}\)/)
assert.match(page, /回測結果不是 qlib score 的驗證結論/)
assert.match(page, /不是未來收益承諾/)


const draftActionMatch = page.match(/addQlibWatchDraft \(row\) \{[\s\S]*?\n    \},\n    removeQlibWatchDraft/)
assert.ok(draftActionMatch, 'missing addQlibWatchDraft method')
const draftActionBody = draftActionMatch[0]
assert.match(page, /persistQlibWatchDraft \(\) \{[\s\S]*localStorage\.setItem/)
assert.match(draftActionBody, /persistQlibWatchDraft\(\)/)
assert.doesNotMatch(draftActionBody, /saveConfig\(/)
assert.doesNotMatch(draftActionBody, /saveTwStockMonitorConfig\(/)
assert.doesNotMatch(draftActionBody, /runScan\(/)
assert.doesNotMatch(draftActionBody, /scanTwStockMonitor\(/)
assert.doesNotMatch(draftActionBody, /runReadonlyBacktest\(/)
assert.doesNotMatch(draftActionBody, /runTwStockReadonlyBacktest\(/)
assert.doesNotMatch(draftActionBody, /quick-trade|broker|order|target_position|targetPosition/i)

const fillDraftMatch = page.match(/fillMonitorConfigFromQlibDraft \(\) \{[\s\S]*?\n    \},\n    qlibTrendAvailable/)
assert.ok(fillDraftMatch, 'missing fillMonitorConfigFromQlibDraft method')
const fillDraftBody = fillDraftMatch[0]
assert.match(fillDraftBody, /symbolsText/)
assert.match(fillDraftBody, /configDrawerVisible = true/)
assert.doesNotMatch(fillDraftBody, /saveConfig\(/)
assert.doesNotMatch(fillDraftBody, /saveTwStockMonitorConfig\(/)
assert.doesNotMatch(fillDraftBody, /runScan\(/)
assert.doesNotMatch(fillDraftBody, /scanTwStockMonitor\(/)
assert.doesNotMatch(fillDraftBody, /getTwStockAlerts\(/)
assert.doesNotMatch(fillDraftBody, /enabled\s*:\s*true/)
assert.doesNotMatch(fillDraftBody, /\.enabled\s*=\s*true/)

const actionMatch = page.match(/async openQlibReadonlyBacktest \(row\) \{[\s\S]*?\n    \},\n    qlibCustomRow/)
assert.ok(actionMatch, 'missing openQlibReadonlyBacktest method')
const actionBody = actionMatch[0]
assert.match(actionBody, /selectTrendSymbol\(row\.symbol\)/)
assert.match(actionBody, /backtestPanelVisible = true/)
assert.match(actionBody, /loadBacktestTemplates\(\)/)
assert.doesNotMatch(actionBody, /saveConfig\(/)
assert.doesNotMatch(actionBody, /runScan\(/)
assert.doesNotMatch(actionBody, /scanTwStockMonitor\(/)
assert.doesNotMatch(actionBody, /runReadonlyBacktest\(\)/)
assert.doesNotMatch(actionBody, /runTwStockReadonlyBacktest\(/)

function scrubReadonlyHistoricalSimulationText (source) {
  const requiredContext = [
    '只读历史模拟',
    '历史模拟，不代表未来收益',
    '不连接券商',
    '不生成订单',
    '模拟成交标记'
  ]
  for (const phrase of requiredContext) {
    assert.ok(source.includes(phrase), `missing readonly simulation context: ${phrase}`)
  }
  const allowedReadonlyPhrases = new Map([
    ['仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。', 1],
    ['不新增模拟买入', 1],
    ['模拟买入候选', 2],
    ['才卖出排名最低的一支', 1],
    ['卖出排名最低的一支', 1],
    ['再从 Top10 最高排名补一支', 2],
    ['模拟买入', 1],
    ['模拟卖出', 1]
  ])
  let scrubbed = source
  for (const [phrase, expectedCount] of allowedReadonlyPhrases.entries()) {
    const count = scrubbed.split(phrase).length - 1
    assert.equal(count, expectedCount, `unexpected readonly simulation phrase count: ${phrase}`)
    scrubbed = scrubbed.split(phrase).join('')
  }
  return scrubbed
}

const pageForForbiddenText = scrubReadonlyHistoricalSimulationText(page)

for (const forbidden of [

  '刷新 qlib provider',
  '重新生成 qlib 信号',
  '重新生成 qlib 信號',
  '自动补数据',
  '自動補數據',
  '开始交易',
  '開始交易',
  '重新运行 qlib',
  '重新運行 qlib',
  '刷新数据源',
  '刷新資料源',
  'provider refresh',
  '重训模型',
  '重訓模型',
  '导入交易计划',
  '導入交易計劃',
  'quick-trade',
  'broker-accounts',
  'ibkr',
  'paper order',
  'live order',
  'submit order',
  'auto buy',
  'auto sell',
  '下單',
  '买入',
  '買入',
  '卖出',
  '賣出',
  '提交订单',
  '提交訂單',
  'automatic trading',
  'target position',
  'target weight',
  'quick trade',
  'quick_trade',
  'broker connect',
  '自動交易',
  '自动交易',
  '目標倉位',
  '目标仓位',
  '建議倉位',
  '建议仓位',
  '推薦買入',
  '推荐买入',
  '交易信號',
  '交易信号',
  '買入概率',
  '买入概率',
  '預測收益',
  '预测收益',
  '預期漲幅',
  '预期涨幅'
]) {
  assert.ok(!pageForForbiddenText.toLowerCase().includes(forbidden), `page contains forbidden text: ${forbidden}`)
  assert.ok(!api.toLowerCase().includes(forbidden), `api contains forbidden text: ${forbidden}`)
}


assert.ok(page.includes('getTwStockSimAccounts'), 'monitor page should import sim accounts for readonly trade markers')
assert.ok(page.includes('getTwStockSimTrades'), 'monitor page should import sim trades for readonly trade markers')
assert.ok(page.includes('chartSimTradeMarkers'), 'monitor page should compute chart sim trade markers')
assert.ok(page.includes('loadSimTradeMarkers'), 'monitor page should load sim trade markers')
assert.ok(page.includes('模拟成交标记'), 'monitor chart should show simulated trade marker count')
assert.ok(page.includes('模拟买入') && page.includes('模拟卖出'), 'monitor chart should draw simulated buy/sell marker labels')
assert.ok(!page.includes('confirmTwStockSimOrder'), 'monitor marker feature must not confirm simulated trades')
assert.ok(!page.includes('draftTwStockSimOrder'), 'monitor marker feature must not draft simulated trades')

console.log('tw-stock-monitor static checks passed')
