import { api } from './api.js'
import { empty, escape, format } from './components.js'

export function paperView(overview = {}) {
  return '<article class="panel"><h2>持久化模拟账户</h2><p>这是独立的模拟流程。需要管理员签发的短期访问令牌；预览不改变持仓，确认后仅更新模拟账本。模型比较页面始终只读。</p>' +
    '<form id="paper-form" class="control-bar"><label>访问令牌<input name="token" type="password" autocomplete="off" required></label>' +
    '<label>账户编号<input name="account" list="paper-accounts" autocomplete="off"><datalist id="paper-accounts"></datalist></label><label>账户名称<input name="name" value="台股研究模拟账户" maxlength="80"></label>' +
    '<label>初始资金<input name="cash" type="number" min="1" max="1000000000000" value="1000000"></label><label>信号日期<input name="date" type="date" value="' + escape(overview.examples?.paper_date || '') + '"></label>' +
    '<label>操作<select name="operation"><option value="read">读取账户</option><option value="history">查看模拟记录</option><option value="create">创建模拟账户</option><option value="preview">生成模拟预览</option><option value="apply">确认应用预览</option><option value="reset">重置模拟账户</option></select></label>' +
    '<label class="check-label"><input name="confirm" type="checkbox"> 我确认更新或重置此模拟账户</label><button>执行所选模拟操作</button></form>' +
    '<p class="panel-note">令牌仅用于当前页面。预览展示下一交易日历史开盘执行及收盘估值，属于历史模拟；资料不足时明确提示。</p><div id="paper-result"></div></article>'
}

export function paperResult(result) {
  if (result.runs) return '<h3>最近模拟记录</h3>' + (result.runs.length ? '<div class="table-scroll"><table><thead><tr><th>时间</th><th>操作</th><th>结果</th></tr></thead><tbody>' + result.runs.map(run => '<tr><td>' + escape(run.created_at) + '</td><td>' + escape(run.operation) + '</td><td>' + escape(run.result.status) + '</td></tr>').join('') + '</tbody></table></div>' : empty('尚无模拟记录', '此账户没有已确认的操作。'))
  const state = result.state || result.after || result
  const positions = Object.entries(state.positions || {})
  const actions = result.actions || []
  return '<p><strong>' + escape(result.status || 'READY') + '</strong> · simulation-only</p>' +
    (result.status === 'PREVIEW' ? '<p>预览后状态（尚未应用），模拟执行日：' + escape(result.execute_date) + '</p>' : '') +
    '<div class="technical-strip"><span>账户 <strong>' + escape(state.paper_account_id || result.paper_account_id || '') + '</strong></span><span>现金 <strong>' + format.money(state.cash) + '</strong></span><span>epoch <strong>' + escape(state.epoch || result.epoch) + '</strong></span></div>' +
    '<p>净值 ' + format.money(state.nav) + ' · 估值日期 ' + escape(state.mark_asof || '尚未模拟') + '</p>' +
    '<p>当前持仓 ' + positions.length + '；预览动作 ' + actions.length + '</p>' +
    (positions.length ? '<div class="table-scroll"><table><thead><tr><th>持仓</th><th>数量</th><th>总成本</th><th>估值价格</th></tr></thead><tbody>' + positions.map(([symbol, p]) => '<tr><td>' + escape(symbol) + '</td><td>' + format.number(p.quantity) + '</td><td>' + format.money(p.cost_basis) + '</td><td>' + format.money(p.mark_price) + '</td></tr>').join('') + '</tbody></table></div>' : '') +
    (actions.length ? '<div class="table-scroll"><table><thead><tr><th>标的</th><th>模拟动作</th><th>数量</th><th>价格</th></tr></thead><tbody>' + actions.map(a => '<tr><td>' + escape(a.instrument) + '</td><td>' + escape(a.action) + '</td><td>' + format.number(a.quantity) + '</td><td>' + format.money(a.price) + '</td></tr>').join('') + '</tbody></table></div>' : '')
}

export function bindPaper() {
  const form = document.querySelector('#paper-form')
  if (!form) return
  const output = document.querySelector('#paper-result')
  let current = null, preview = null, retry = null
  for (const name of ['token', 'account', 'date']) form.elements[name].addEventListener('input', () => {
    preview = null; retry = null; form.elements.confirm.checked = false
    if (name !== 'date') current = null
  })
  form.addEventListener('submit', async event => {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(form)), button = form.querySelector('button')
    button.disabled = true
    try {
      let result
      if (values.operation === 'read') {
        const accounts = await api.paperAccounts(values.token)
        document.querySelector('#paper-accounts').innerHTML = accounts.accounts.map(account => '<option value="' + escape(account.paper_account_id) + '">' + escape(account.name || account.paper_account_id) + '</option>').join('')
        if (!values.account && accounts.accounts.length) form.elements.account.value = values.account = accounts.accounts[0].paper_account_id
        if (!values.account) { output.innerHTML = empty('尚无模拟账户', '选择创建模拟账户以开始。'); return }
        result = current = await api.paperAccount(values.token, values.account)
        preview = null
      } else if (values.operation === 'history') {
        if (!values.account) throw new Error('请先选择账户。')
        result = await api.paperHistory(values.token, values.account)
      } else if (values.operation === 'preview') {
        if (!values.account || !values.date) throw new Error('请先读取账户并选择信号日期。')
        result = preview = await api.paperPreview(values.token, values.account, values.date)
      } else {
        const signature = JSON.stringify([values.operation, values.account, values.name, values.cash, preview?.decision_id, current?.epoch])
        if (!retry || retry.signature !== signature) retry = { signature, key: crypto.randomUUID() }
        if (values.operation === 'create') result = await api.paperCreate(values.token, { name: values.name, initial_cash: values.cash, key: retry.key })
        else if (values.operation === 'apply') {
          if (!values.confirm || !preview || preview.paper_account_id !== values.account) throw new Error('请先生成此账户的预览并勾选确认。')
          result = await api.paperApply(values.token, { decision_id: preview.decision_id, input_checksum: preview.input_checksum, epoch: preview.epoch, key: retry.key, confirm: true })
        } else if (values.operation === 'reset') {
          if (!values.confirm || !current || current.paper_account_id !== values.account) throw new Error('请先读取此账户并勾选重置确认。')
          result = await api.paperReset(values.token, { paper_account_id: values.account, epoch: current.epoch, key: retry.key, confirm: true })
        }
        if (result.state || result.paper_account_id) current = result.state || result
        preview = null; retry = null
        if (current?.paper_account_id) form.elements.account.value = current.paper_account_id
        form.elements.confirm.checked = false
      }
      output.innerHTML = paperResult(result)
    } catch (error) { output.innerHTML = empty('模拟操作未完成', error.message) }
    finally { button.disabled = false }
  })
}
