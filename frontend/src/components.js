const isNumeric = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))

export const format = {
  number: value => isNumeric(value) ? Number(value).toLocaleString('zh-TW', { maximumFractionDigits: 2 }) : '—',
  percent: value => isNumeric(value) ? (Number(value) * 100).toFixed(2) + '%' : '—',
  money: value => isNumeric(value) ? 'NT$ ' + Number(value).toLocaleString('zh-TW', { maximumFractionDigits: 0 }) : '—',
  symbol: value => String(value || '').replace(/^TW/, ''),
}

export function escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]))
}

export function statusPill(status, label = status) {
  const tone = status === 'READY' || status === 'ready' ? 'ok' : status === 'BLOCKED' ? 'warn' : 'muted'
  return '<span class="pill ' + tone + '">' + escape(label || '未知') + '</span>'
}

export function empty(title, detail) {
  return '<div class="empty"><strong>' + escape(title) + '</strong><p>' + escape(detail) + '</p></div>'
}

// Each output owns one sequence: a slower old request cannot replace the latest.
export function latestRenderer(output, renderError) {
  let version = 0
  return async (task, render, pending) => {
    const current = ++version
    output.innerHTML = pending
    try {
      const data = await task()
      if (current === version && output.isConnected) output.innerHTML = render(data)
    } catch (error) {
      if (current === version && output.isConnected) output.innerHTML = renderError(error)
    }
  }
}

export function lineChart(rows, key, options = {}) {
  const value = options.value || (v => v)
  if (!rows || !rows.length) return empty('没有可绘制的数据', '请调整日期范围后再试。')
  const values = rows.filter(row => isNumeric(row[key])).map(row => Number(row[key]))
  if (!values.length) return empty('数值为空', '返回结果没有可用数值。')
  const width = 760, height = 230, pad = 20, min = Math.min(...values), max = Math.max(...values), span = max - min || 1
  const points = rows.flatMap((row, index) => isNumeric(row[key]) ? [(pad + index * (width - pad * 2) / Math.max(1, rows.length - 1)) + ',' + (height - pad - (Number(row[key]) - min) * (height - pad * 2) / span)] : []).join(' ')
  return '<div class="chart-wrap"><svg class="line-chart" viewBox="0 0 ' + width + ' ' + height + '" role="img" aria-label="' + escape(options.label || '') + '"><line x1="' + pad + '" y1="' + (height - pad) + '" x2="' + (width - pad) + '" y2="' + (height - pad) + '"/><polyline points="' + points + '"/></svg><div class="chart-scale"><span>' + escape(value(min)) + '</span><span>' + escape(value(max)) + '</span></div></div>'
}

export function modelOptions(models, selected) {
  return (models || []).map(model => '<option value="' + escape(model.id) + '" ' + (model.id === selected ? 'selected' : '') + '>' + escape(model.label) + ' · ' + escape(model.role) + '</option>').join('')
}

export function architecturePanel(overview) {
  const operation = overview.operations || {}, release = operation.active_release
  const baseline = (overview.models || []).find(model => model.role === 'baseline')
  const stages = [
    ['行情与候选池', 'provider_refresh.py / data.py', '增量行情 → 标准化 → 流动性筛选'],
    ['Model A 排名', 'models.py', '当日 150 支候选 → 冻结 Alpha158 / LightGBM → 排名'],
    ['策略与回放', 'strategy.py / replay.py', 'Top50 → 每次退出一支最弱持仓 → next_open 模拟'],
    ['完整批次发布', 'orchestrator.py / validation.py', '校验信号与每日上下文；成功才整体切换'],
    ['研究服务', 'service.py / agent.py', 'Flask 查询 → 已验证信号、行情指标、带引用问答'],
    ['前端与模拟账户', 'frontend/src / paper.py', '七个研究视图；模拟账本独立预览与确认'],
  ]
  return '<article class="panel architecture-panel"><div class="panel-head"><div><p class="eyebrow">CLEAN PRODUCT · MODULE FLOW</p><h3>一条数据链路，独立模块协作</h3></div>' + statusPill(overview.status) + '</div>' +
    '<p class="panel-note">Model A 是当前主线，B19R2R 仅作历史研究对照。全市场行情用于筛选，模型只对当日候选评分。</p>' +
    '<ol class="pipeline">' + stages.map(([name, code, description], index) => '<li><span class="pipeline-step">' + (index + 1) + '</span><div><strong>' + name + '</strong><p>' + description + '</p><code>' + code + '</code></div></li>').join('') + '</ol>' +
    '<div class="technical-strip"><span>资料日期<strong>' + escape(overview.asof || '待验证') + '</strong></span><span>基线信号<strong>' + escape(baseline?.rows ?? '—') + '</strong></span><span>服务入口<strong>Flask + Gunicorn</strong></span><span>运行管理<strong>systemd</strong></span><span>发布方式<strong>完整批次切换</strong></span></div>' +
    '<details><summary>展开运维与来源</summary><dl><dt>当前批次</dt><dd>' + escape(release?.run_id || '尚未激活完整批次') + '</dd><dt>最近手工运行</dt><dd>' + escape(operation.latest_manual?.created_at || '尚无') + '</dd><dt>最近计划运行</dt><dd>' + escape(operation.latest_scheduled?.created_at || operation.scheduler?.created_at || '尚未触发，不能以手工运行替代') + '</dd><dt>日更策略</dt><dd>台北时间工作日 18:30、19:30、20:30；检查实际市场交易日，失败保留上一批次。</dd><dt>持久化边界</dt><dd>研究产物按运行保存；模拟账户使用独立 SQLite 账本，研究页面不写账户。</dd></dl></details></article>'
}

export function maintenancePanel(operations = {}) {
  const report = operations.maintenance
  if (!report) return empty('运维检查尚未运行', '健康检查每十分钟执行，分别检查服务、日更、备份和磁盘。')
  const labels = { WEB_NOT_READY: '研究服务未就绪', LATEST_DAILY_FAILED: '最近日更失败',
    SCHEDULED_DAILY_FAILED: '最近计划日更失败', DAILY_TIMEOUT: '日更超过预期时间',
    SCHEDULED_ATTEMPT_MISSING: '未发现应有的计划运行', PUBLISHED_DATA_BEHIND_CHECKED_SESSION: '发布批次落后于已检查的市场交易日',
    DISK_SPACE_LOW: '磁盘剩余空间不足', BACKUP_MISSING_OR_OLD: '备份缺失、失败或超过 36 小时' }
  const stale = !report.created_at || Date.now() - Date.parse(report.created_at) > 25 * 60 * 1000
  const alerts = [...(report.alerts || []), ...(stale ? [{code: '健康检查状态已超过 25 分钟未更新'}] : [])]
  return '<article class="panel maintenance-panel"><div class="panel-head"><h3>持续运维检查</h3>' +
    statusPill(report.status === 'OK' && !stale ? 'READY' : 'BLOCKED', stale ? '状态待刷新' : report.status) + '</div>' +
    '<p>服务可用性与日更成功状态独立检查。告警记录在系统日志和本页。</p>' +
    '<dl><dt>最后检查</dt><dd>' + escape(report.created_at) + '</dd><dt>最近备份</dt><dd>' + escape(report.backup?.created_at || '尚无') +
    '</dd><dt>剩余空间</dt><dd>' + format.number(report.free_bytes / 1024 ** 3) + ' GB</dd></dl>' +
    (alerts.length ? '<ul role="alert">' + alerts.map(a => '<li>' + escape(labels[a.code] || a.code) + '</li>').join('') + '</ul>' : '<p>当前检查没有异常。</p>') + '</article>'
}
