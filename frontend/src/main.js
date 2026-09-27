import './style.css'

const app = document.querySelector('#app')
app.innerHTML = `
  <main>
    <header><p class="eyebrow">READ-ONLY RESEARCH</p><h1>台股模型研究台</h1><p>同一份数据、同一条流水线，比较 baseline 与 shadow。</p></header>
    <section class="card"><h2>模型与策略</h2><div id="config">载入中…</div></section>
    <section class="card"><h2>动态回放</h2><form id="replay"><label>模型<select name="model"></select></label><label>开始<input name="start" type="date" required></label><label>结束<input name="end" type="date" required></label><button>执行只读回放</button></form><pre id="result">请选择参数。</pre></section>
  </main>`
const configBox = document.querySelector('#config')
const select = document.querySelector('select[name=model]')
fetch('/api/tw-stock/config').then(r => r.json()).then(data => {
  const models = Object.entries(data.models || {})
  configBox.innerHTML = `<div class="grid">${models.map(([id, m]) => `<article><strong>${id}</strong><span>${m.role}</span><small>${m.stages.join(' → ')}</small></article>`).join('')}<article><strong>${data.strategy}</strong><span>唯一策略</span><small>${data.execution}</small></article></div>`
  select.innerHTML = models.map(([id, m]) => `<option value="${id}">${id} · ${m.role}</option>`).join('')
}).catch(e => { configBox.textContent = e.message })
document.querySelector('#replay').addEventListener('submit', async event => {
  event.preventDefault(); const p = new URLSearchParams(new FormData(event.currentTarget)); const out = document.querySelector('#result'); out.textContent = '运行中…'
  try { const r = await fetch(`/api/tw-stock/replay?${p}`); out.textContent = JSON.stringify(await r.json(), null, 2) } catch (e) { out.textContent = e.message }
})
