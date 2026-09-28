import './style.css'
import { api } from './api.js'
import { bindPaper, paperView } from './paper.js'
import { architecturePanel, maintenancePanel, empty, escape, format, latestRenderer, lineChart, modelOptions, statusPill } from './components.js'

const state = { overview: null, detail: null, view: 'overview', model: 'model_a' }
const app = document.querySelector('#app')
let renderVersion = 0

function shell() {
  app.innerHTML = '<div class="shell">' +
    '<aside><a class="brand" href="#overview"><span class="brand-mark">雙</span><span><strong>台股研究台</strong><small>Model research console</small></span></a>' +
    '<nav>' + [['overview','今日总览'],['rankings','候选榜单'],['compare','模型比较'],['replay','历史回放'],['market','个股行情'],['paper','模拟账户'],['system','系统状态']].map(item => '<a href="#' + item[0] + '" data-view="' + item[0] + '"><span>' + item[1] + '</span></a>').join('') + '</nav>' +
    '<div class="boundary"><strong>只读研究</strong><p>所有结果只用于研究与模拟，不连接券商或真实订单。</p></div></aside>' +
    '<main><header class="topbar"><div><p class="eyebrow">TAIWAN EQUITY · DUAL TRACK</p><h1 id="page-title">今日总览</h1></div><div class="asof" id="asof">资料日期载入中</div></header><section id="view" aria-live="polite"></section></main></div>'
  document.querySelectorAll('[data-view]').forEach(link => link.addEventListener('click', () => { state.view = link.dataset.view; setTimeout(render, 0) }))
}

function loading(message = '正在读取研究产物…') { return '<div class="loading"><span></span><p>' + message + '</p></div>' }
function errorView(error) { return empty('这一页暂时无法读取', error.message + '。请先查看系统状态确认缺少的资料。') }
async function loadDetail() {
  if (state.detail && state.detail.asof === state.overview.asof) return state.detail
  const asof = state.overview.asof || ''
  const model = state.overview.product.default_model || 'model_a'
  const values = await Promise.all([
    api.rankings(model, asof, 50),
    api.strategy(model, asof),
    api.crossAnalysis(model, asof, 8),
    api.paper(model, asof),
  ])
  state.detail = { asof, rankings: values[0], strategy: values[1], cross: values[2], paper: values[3], changes: { entered: [], exited: [] } }
  return state.detail
}

function rankingTable(rows, limit = 10) {
  const visible = (rows || []).slice(0, limit)
  if (!visible.length) return empty('当前没有可用榜单', '模型产物缺失或被资料门禁挡住。')
  return '<div class="table-scroll"><table><thead><tr><th>排名</th><th>标的</th><th>研究分数</th><th>研究动作</th></tr></thead><tbody>' + visible.map(row => '<tr><td>#' + row.rank + '</td><td><strong>' + escape(format.symbol(row.instrument)) + '</strong></td><td>' + format.number(row.score) + '</td><td><span class="research-label">观察优先级</span></td></tr>').join('') + '</tbody></table></div>'
}

function intentList(intents) {
  if (!intents || !intents.length) return empty('没有新的模拟意图', '当前策略没有产生候选调入或调出复核。')
  return '<div class="intent-list">' + intents.map(item => '<article><strong>' + escape(format.symbol(item.instrument)) + '</strong><span>' + (item.action === 'buy' ? '模拟调入' : '模拟调出复核') + '</span><small>' + escape(item.reason || '策略规则') + '</small></article>').join('') + '</div>'
}

async function overviewView() {
  const detail = await loadDetail()
  const models = state.overview.models
  const requiredData = state.overview.data.filter(item => item.mainline_required !== false)
  const dataReady = requiredData.filter(item => item.status === 'READY').length
  const operation = state.overview.operations
  return (state.overview.status !== 'READY' ? empty('当前研究产物未通过验证', state.overview.reason || '请查看系统状态；未验证结果不会作为正常榜单展示。') : '') + '<div class="hero-grid"><article class="hero-card"><p class="eyebrow">LATEST RESEARCH DAY</p><strong class="hero-date">' + (state.overview.asof || '尚无资料') + '</strong><p>每日从全市场筛出 150 支流动性候选，由冻结 Model A 排名；Top50 进入只读策略与历史模拟。</p></article>' +
    '<article class="metric-card"><span>模型轨道</span><strong>' + models.length + '</strong><small>由配置注册，不写模型分支</small></article>' +
    '<article class="metric-card"><span>主线数据集</span><strong>' + dataReady + '/' + requiredData.length + '</strong><small>影子研究资料单独标记，不阻断 Model A</small></article>' +
    '<article class="metric-card"><span>最近日更</span><strong>' + (operation.latest?.asof || '尚未运行') + '</strong><small>' + (operation.latest?.dry_run ? '最近记录为 dry-run' : '正式 artifact') + '</small></article></div>' +
    '<div class="workbench-grid"><article class="panel candidate-panel"><div class="panel-head"><div><p class="eyebrow">MODEL A · TOP50</p><h3>今日候选</h3></div><span>' + statusPill(detail.rankings.status, detail.rankings.status) + '</span></div><p class="panel-note">研究分数只用于相对排序；候选调入需要人工复核。</p>' + (detail.rankings.status === 'READY' ? rankingTable(detail.rankings.rows, 10) : empty('候选暂不可用', detail.rankings.reason || '缺少有效模型产物。')) + '<div class="panel-foot"><span>榜首 ' + (detail.rankings.rows[0] ? escape(format.symbol(detail.rankings.rows[0].instrument)) : '—') + '</span><a href="#rankings" data-jump="rankings">查看完整榜单与变化 →</a></div></article><article class="panel strategy-panel"><div class="panel-head"><div><p class="eyebrow">STRATEGY RULE</p><h3>策略意图</h3></div><span>' + statusPill(detail.strategy.status, detail.strategy.status) + '</span></div><p class="panel-note">' + escape(state.overview.strategy) + ' · ' + escape(state.overview.execution) + '</p>' + (detail.strategy.status === 'READY' ? intentList(detail.strategy.intents) : empty('策略暂不可用', detail.strategy.reason || '缺少有效模型产物。')) + '<div class="panel-foot"><span>模拟初始资金 ' + format.money(detail.paper.nav) + '</span><a href="#replay" data-jump="replay">查看历史回放 →</a></div></article></div>' +
    '<div class="section-head"><div><p class="eyebrow">MODEL LANES</p><h2>同一规范，两条模型轨道</h2></div><a href="#compare" data-jump="compare">打开模型比较 →</a></div>' +
    '<div class="model-rails">' + models.map(model => '<article class="rail ' + escape(model.role) + '"><div class="rail-line"></div><div><div class="rail-top"><span>' + escape(model.role) + '</span>' + statusPill(model.status, model.status) + '</div><h3>' + escape(model.label) + '</h3><p>' + escape(model.description) + '</p><dl><div><dt>产物日期</dt><dd>' + (model.asof || '尚无') + '</dd></div><div><dt>排名数量</dt><dd>' + (model.rows || 0) + '</dd></div><div><dt>产品权限</dt><dd>' + (model.production_allowed ? '默认模拟轨道' : '只读影子轨道') + '</dd></div></dl>' + (model.reason ? '<div class="notice">' + escape(model.reason) + '</div>' : '') + '</div></article>').join('') + '</div>' +
    '<article class="panel cross-panel"><div class="panel-head"><div><p class="eyebrow">RANK + TECHNICAL CONTEXT</p><h3>候选的行情背景</h3></div><span class="pill muted">只读复核</span></div><p class="panel-note">技术指标帮助人工复核候选背景，不改变模型排序，也不生成交易建议。</p>' + (detail.cross.status !== 'READY' ? empty('行情背景暂不可用', detail.cross.reason || '缺少同日验证资料。') : '<div class="table-scroll"><table><thead><tr><th>标的</th><th>排名</th><th>收盘</th><th>MA20</th><th>RSI14</th><th>背景</th></tr></thead><tbody>' + (detail.cross.rows || []).map(row => '<tr><td><strong>' + escape(format.symbol(row.instrument)) + '</strong></td><td>#' + row.rank + '</td><td>' + format.number(row.close) + '</td><td>' + format.number(row.ma20) + '</td><td>' + format.number(row.rsi14) + '</td><td>' + escape(row.research_state || '人工复核') + '</td></tr>').join('') + '</tbody></table></div>') + '</article>' +
    '<article class="panel explanation-panel"><div class="panel-head"><div><p class="eyebrow">RESEARCH EXPLANATION</p><h3>研究解释助手</h3></div><span class="pill muted">本地、只读</span></div><p class="panel-note">基于当前 ModelSignalArtifact 生成口径解释，不调用远端模型、不暴露密钥。</p><form id="explain-form" class="inline-form"><input name="symbol" value="' + (detail.rankings.rows[0] ? format.symbol(detail.rankings.rows[0].instrument) : '2330') + '" inputmode="numeric" aria-label="股票代码"><button>解释当前排序</button></form><div id="explain-result">' + empty('选择标的后查看', '解释只描述研究排序与证据，不输出交易指令。') + '</div></article>' +
    '<article class="panel agent-panel"><div class="panel-head"><h3>每日研究问答</h3><span class="pill muted">每日产物 · 本地解释</span></div><p class="panel-note">支持排名、日期和策略口径提问；每日上下文与模型来源必须通过验证。</p><form id="agent-form" class="inline-form"><textarea name="question" maxlength="1000" required aria-label="研究问题">排名第一是谁？</textarea><button>查询研究证据</button></form><div id="agent-result"></div></article>' +
    '<div class="section-head"><div><p class="eyebrow">TODAY’S RULE</p><h2>唯一策略，next_open 执行</h2></div></div><article class="rule-card"><span class="rule-index">01</span><div><strong>保留 Top50</strong><p>若持仓跌出 Top50，每次只复核一支最弱持仓，再查看当前排名最高且尚未持有的候选。</p></div><span class="arrow">→</span><div><strong>下一交易日开盘</strong><p>信号日只产生研究意图，历史模拟统一使用下一交易日开盘价与费用参数。</p></div></article>'
}

async function compareView() {
  const models = state.overview.models
  const comparisonStart = state.overview.examples?.comparison_start || ''
  const comparisonEnd = state.overview.examples?.comparison_end || ''
  const commonDate = state.overview.examples?.comparison_date || models.map(model => model.asof).filter(Boolean).sort()[0] || state.overview.asof || ''
  return '<form class="control-bar" id="compare-form"><label>比较日期<input type="date" name="date" value="' + commonDate + '"></label><label>左轨<select name="left">' + modelOptions(models, 'model_a') + '</select></label><label>右轨<select name="right">' + modelOptions(models, 'model_a_plus_b') + '</select></label><label class="check-label"><input type="checkbox" name="includeReplay"> 读取历史回放指标</label><label>回放开始<input type="date" name="start" value="' + comparisonStart + '"></label><label>回放结束<input type="date" name="end" value="' + comparisonEnd + '"></label><button>比较研究轨道</button></form><p class="form-note">默认显示有完整证据的历史比较日期；勾选历史回放后，会按同一窗口返回收益、回撤、交易数和账户结果。资料不足的轨道会明确 BLOCKED。</p><div id="compare-result">' + empty('选择一个共同日期', 'Model A 与 Model A+B 会分别执行，再按股票代码对齐排名。') + '</div>'
}

async function rankingsView() {
  const models = state.overview.models
  const date = state.overview.asof || ''
  return '<form class="control-bar" id="rankings-form"><label>模型<select name="model">' + modelOptions(models, state.model) + '</select></label><label>资料日期<input type="date" name="date" value="' + date + '"></label><label>榜单范围<select name="limit"><option value="30">Top30</option><option value="50" selected>Top50</option></select></label><button type="submit">读取榜单</button><button type="button" data-load-changes>读取进入/离开</button></form><p class="form-note">榜单是研究排序；分数不代表收益率、胜率、上涨概率或仓位大小。</p><div id="rankings-result">' + empty('等待榜单', '选择模型与资料日期后读取只读 ModelSignalArtifact。') + '</div><div id="ranking-changes-result"></div>'
}

function rankingsResult(data) {
  if (data.status !== 'READY') return empty('榜单被资料门禁挡住', data.reason || '当前日期没有可验证的模型产物。')
  return '<article class="panel"><div class="panel-head"><div><p class="eyebrow">' + escape(data.label || data.model) + '</p><h3>' + data.asof + ' · ' + data.row_count + ' 支候选</h3></div>' + statusPill(data.status, data.status) + '</div>' + rankingTable(data.rows, data.rows.length) + '<p class="panel-note">artifact：' + escape(data.artifact?.run_id || 'runtime read') + '；当前页面只用于人工复核。</p></article>'
}

function compareResult(data) {
  if (data.status !== 'READY') return '<div class="split-blocked"><article><h3>' + escape(data.left?.model) + '</h3>' + statusPill(data.left?.status || 'BLOCKED') + '<p>' + escape(data.left?.reason || data.reason || '没有可用产物') + '</p></article><article><h3>' + escape(data.right?.model) + '</h3>' + statusPill(data.right?.status || 'BLOCKED') + '<p>' + escape(data.right?.reason || data.reason || '没有可用产物') + '</p></article></div>'
  const window = data.window
  const replayMetric = (model, label, side, key, formatter) => '<article><span>' + escape(model) + ' · ' + label + '</span><strong>' + (side.status === 'READY' ? formatter(side[key]) : 'BLOCKED') + '</strong></article>'
  const metrics = window ? '<div class="comparison-summary four">' + replayMetric(data.left, '累计收益', window.left, 'cumulative_return', format.percent) + replayMetric(data.left, '最大回撤', window.left, 'max_drawdown', format.percent) + replayMetric(data.left, '费用', window.left, 'total_fees', format.money) + replayMetric(data.left, '换手', window.left, 'turnover', format.percent) + replayMetric(data.right, '累计收益', window.right, 'cumulative_return', format.percent) + replayMetric(data.right, '最大回撤', window.right, 'max_drawdown', format.percent) + replayMetric(data.right, '费用', window.right, 'total_fees', format.money) + replayMetric(data.right, '换手', window.right, 'turnover', format.percent) + '</div><p class="form-note">回放窗口：' + data.window.start + ' — ' + data.window.end + '；指标来自 simulation-only 历史模拟，不代表未来收益。</p>' : ''
  return '<div class="comparison-summary"><article><span>共同 Top50</span><strong>' + data.overlap_top50 + '</strong></article><article><span>比较日期</span><strong>' + data.asof + '</strong></article><article><span>结论</span><strong>' + (data.overlap_top50 >= 40 ? '选股接近，排序不同' : '候选差异明显') + '</strong></article></div>' + metrics + '<div class="table-scroll"><table><thead><tr><th>股票</th><th>' + escape(data.left) + '</th><th>' + escape(data.right) + '</th><th>名次变化</th></tr></thead><tbody>' + data.rows.map(row => '<tr><td><strong>' + escape(format.symbol(row.instrument)) + '</strong></td><td>' + (row.left_rank || '—') + '</td><td>' + (row.right_rank || '—') + '</td><td class="delta ' + (row.rank_change > 0 ? 'up' : row.rank_change < 0 ? 'down' : '') + '">' + (row.rank_change > 0 ? '+' : '') + (row.rank_change ?? '—') + '</td></tr>').join('') + '</tbody></table></div>'
}

async function replayView() {
  const models = state.overview.models
  return '<form class="control-bar" id="replay-form"><label>模型<select name="model">' + modelOptions(models, state.model) + '</select></label><label>开始日期<input type="date" name="start" value="2025-06-23" required></label><label>结束日期<input type="date" name="end" value="2025-06-30" required></label><button>运行模拟回放</button></form><p class="form-note">回放会按每个交易日实际调用所选模型、生成策略意图，并在下一交易日开盘模拟成交。</p><div id="replay-result">' + empty('等待参数', '建议先用较短日期范围确认结果，再扩大回放窗口。') + '</div>'
}

function replayResult(data) {
  if (data.status !== 'READY') return empty('回放被资料门禁挡住', (data.blocked_on ? data.blocked_on + '：' : '') + (data.reason || '缺少所需资料'))
  return '<div class="comparison-summary four"><article><span>累计收益</span><strong>' + format.percent(data.cumulative_return) + '</strong></article><article><span>最大回撤</span><strong>' + format.percent(data.max_drawdown) + '</strong></article><article><span>期末净值</span><strong>' + format.money(data.final_nav) + '</strong></article><article><span>模拟交易</span><strong>' + data.trade_count + '</strong></article></div><article class="panel account-panel"><div class="panel-head"><div><p class="eyebrow">SIMULATION ACCOUNT</p><h3>模拟账户状态</h3></div><span class="pill muted">只读 · 不持久化</span></div><div class="technical-strip"><span>现金 <strong>' + format.money(data.account?.cash) + '</strong></span><span>市值 <strong>' + format.money(data.account?.market_value) + '</strong></span><span>持仓数 <strong>' + (data.account?.positions?.length || 0) + '</strong></span><span>执行口径 <strong>next_open</strong></span></div><p class="panel-note">回放结果只用于历史复盘，clean 不连接券商、不写入账户。</p></article><article class="panel"><div class="panel-head"><h3>NAV 曲线</h3><span>' + data.start + ' — ' + data.end + '</span></div>' + lineChart(data.nav, 'nav', { value: format.money, label: '模拟账户 NAV' }) + '</article><article class="panel"><div class="panel-head"><h3>最近交易</h3><span>模拟成交</span></div><div class="table-scroll"><table><thead><tr><th>执行日</th><th>股票</th><th>动作</th><th>数量</th><th>价格</th></tr></thead><tbody>' + data.trades.slice(-20).reverse().map(row => '<tr><td>' + row.execute_date + '</td><td><strong>' + escape(format.symbol(row.instrument)) + '</strong></td><td>' + (row.action === 'buy' ? '调入' : '调出复核') + '</td><td>' + format.number(row.quantity) + '</td><td>' + format.number(row.price) + '</td></tr>').join('') + '</tbody></table></div></article>'
}

async function marketView() {
  return '<form class="control-bar" id="market-form"><label>股票代码<input name="symbol" value="2330" inputmode="numeric" required></label><label>开始日期<input type="date" name="start" value="2026-01-02" required></label><label>结束日期<input type="date" name="end" value="' + (state.overview.asof || '') + '" required></label><button>查看日线</button></form><div id="market-result">' + empty('输入股票代码', '行情只从后端治理后的本地资料读取，浏览器不会直接连接数据供应商。') + '</div>'
}

function marketResult(data) {
  if (data.status !== 'READY') return empty('行情暂不可用', data.reason || '所选标的或窗口没有可验证的价格。')
  const latest = data.summary || {}
  return '<article class="panel"><div class="panel-head"><div><p class="eyebrow">TW' + data.symbol + '</p><h3>日收盘走势</h3></div><span>' + data.rows.length + ' 个交易日</span></div><div class="technical-strip"><span>收盘 <strong>' + format.number(latest.close) + '</strong></span><span>MA20 <strong>' + format.number(latest.ma20) + '</strong></span><span>RSI14 <strong>' + format.number(latest.rsi14) + '</strong></span><span>20D <strong>' + format.percent(latest.ret20) + '</strong></span><span>量比 <strong>' + format.number(latest.volume_ratio20) + '</strong></span></div>' + lineChart(data.rows, 'close', { value: format.number, label: data.symbol + ' 收盘价' }) + '</article><div class="table-scroll"><table><thead><tr><th>日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>MA20</th><th>RSI14</th><th>成交量</th></tr></thead><tbody>' + data.rows.slice(-30).reverse().map(row => '<tr><td>' + row.date + '</td><td>' + format.number(row.open) + '</td><td>' + format.number(row.high) + '</td><td>' + format.number(row.low) + '</td><td><strong>' + format.number(row.close) + '</strong></td><td>' + format.number(row.ma20) + '</td><td>' + format.number(row.rsi14) + '</td><td>' + format.number(row.volume) + '</td></tr>').join('') + '</tbody></table></div>'
}

async function systemView() {
  const data = state.overview.data, operations = state.overview.operations
  return maintenancePanel(operations) + architecturePanel(state.overview) + '<div class="section-head"><div><p class="eyebrow">DATA GOVERNANCE</p><h2>数据集状态</h2></div></div><div class="status-list">' + data.map(item => '<article><div><strong>' + escape(item.dataset) + '</strong><small>' + escape(item.source) + '</small></div>' + statusPill(item.status) + '<dl><div><dt>最新日期</dt><dd>' + (item.latest_asof || '尚无') + '</dd></div><div><dt>行数</dt><dd>' + format.number(item.rows) + '</dd></div></dl></article>').join('') + '</div><div class="section-head"><div><p class="eyebrow">OPERATIONS</p><h2>日更运行状态</h2></div></div><article class="panel ops"><div>' + statusPill(operations.status) + '<h3>' + (operations.latest?.asof || '尚未产生正式日更记录') + '</h3><p>baseline 失败才阻断主线；shadow 被挡住会保留原因，但不会污染 Model A 的状态。</p></div><dl><div><dt>Artifact root</dt><dd>' + escape(operations.artifact_root) + '</dd></div><div><dt>产品边界</dt><dd>readonly · simulation-only</dd></div></dl></article>'
}

function bindRequest(formId, outputId, request, renderer, message, trigger) {
  const form = document.querySelector(formId)
  if (!form) return
  const output = document.querySelector(outputId)
  const run = latestRenderer(output, errorView)
  const control = trigger ? form.querySelector(trigger) : form
  control.addEventListener(trigger ? 'click' : 'submit', event => {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(form))
    run(() => request(values), renderer, loading(message))
  })
}

function changesResult(data) {
  if (data.status !== 'READY') return empty('榜单变化暂不可用', data.reason || '资料门禁挡住了当前请求。')
  return '<article class="panel"><div class="panel-head"><h3>榜单变化</h3><span>' + escape(data.previous_asof) + ' → ' + escape(data.asof) + '</span></div><div class="technical-strip"><span>进入 <strong>' + data.entered.length + '</strong></span><span>离开 <strong>' + data.exited.length + '</strong></span><span>留在榜内 <strong>' + data.stayed.length + '</strong></span></div></article>'
}

function explanationResult(data) {
  if (data.status !== 'READY') return empty('解释暂不可用', data.reason || '资料门禁挡住了当前请求。')
  return '<div class="explanation-result"><p>' + escape(data.answer) + '</p><small>' + (data.evidence || []).map(item => '排名 #' + escape(item.rank) + ' · score ' + format.number(item.score)).join('；') + '</small></div>'
}

function chatResult(data) {
  return '<div class="explanation-result"><p>' + escape(data.answer || data.reason) + '</p><small>' + escape(data.mode || '') + ' · ' + escape(data.context_digest?.signal_asof || '上下文未验证') + '</small><p>' + escape(data.research_only_disclaimer || '') + '</p><small>' + (data.citations || []).map(escape).join('<br>') + '</small>' + (data.reason ? '<p>' + escape(data.reason) + '</p>' : '') + '</div>'
}

function bindView() {
  bindPaper()
  bindRequest('#compare-form', '#compare-result', form => api.compare(form.left, form.right, form.date, form.includeReplay ? form.start : '', form.includeReplay ? form.end : ''), compareResult, '两条模型轨道正在独立计算…')
  bindRequest('#replay-form', '#replay-result', form => api.replay(form.model, form.start, form.end), replayResult, '逐日运行模型、策略与 next_open 模拟…')
  bindRequest('#market-form', '#market-result', form => api.market(form.symbol, form.start, form.end), marketResult, '读取治理后的本地行情…')
  bindRequest('#rankings-form', '#rankings-result', form => api.rankings(form.model, form.date, form.limit), rankingsResult, '读取模型排名…')
  bindRequest('#rankings-form', '#ranking-changes-result', form => api.rankingChanges(form.model, form.date, 1), changesResult, '读取榜单变化…', '[data-load-changes]')
  bindRequest('#explain-form', '#explain-result', form => api.explain(form.symbol, state.overview.product.default_model || 'model_a', state.overview.asof), explanationResult, '读取模型产物解释…')
  bindRequest('#agent-form', '#agent-result', form => api.simpleChat(form.question, state.overview.asof), chatResult, '验证每日上下文及来源…')
  document.querySelectorAll('[data-jump]').forEach(link => link.addEventListener('click', () => { state.view = link.dataset.jump; setTimeout(render, 0) }))
}

async function render() {
  const version = ++renderVersion
  const names = { overview: '今日总览', rankings: '候选榜单', compare: '模型比较', replay: '历史回放', market: '个股行情', paper: '模拟账户', system: '系统状态' }
  document.querySelector('#page-title').textContent = names[state.view]
  document.querySelectorAll('[data-view]').forEach(link => link.classList.toggle('active', link.dataset.view === state.view))
  const view = document.querySelector('#view'); view.innerHTML = loading()
  try {
    const renderer = { overview: overviewView, rankings: rankingsView, compare: compareView, replay: replayView, market: marketView, paper: () => paperView(state.overview), system: systemView }[state.view]
    const content = await renderer()
    if (version !== renderVersion) return
    view.innerHTML = content; await bindView()
  } catch (error) { if (version === renderVersion) view.innerHTML = errorView(error) }
}

async function boot() {
  shell(); document.querySelector('#view').innerHTML = loading('正在确认模型、资料与日更状态…')
  window.addEventListener('hashchange', () => {
    const next = location.hash.slice(1) || 'overview'
    if (['overview','rankings','compare','replay','market','paper','system'].includes(next) && next !== state.view) {
      state.view = next
      if (state.overview) render()
    }
  })
  try {
    state.overview = await api.overview(); document.querySelector('#asof').textContent = '资料截至 ' + (state.overview.asof || '未知')
    const hash = location.hash.replace('#', ''); if (['overview','rankings','compare','replay','market','paper','system'].includes(hash)) state.view = hash
    await render()
  } catch (error) { document.querySelector('#view').innerHTML = errorView(error) }
}

boot()
