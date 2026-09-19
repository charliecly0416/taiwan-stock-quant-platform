import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const frontendRoot = path.basename(root) === 'frontend' ? root : path.join(root, 'frontend')
const apiPath = path.join(frontendRoot, 'src/api/tw-stock-readonly.js')
const pagePath = path.join(frontendRoot, 'src/views/tw-stock-monitor/index.vue')
const componentPath = path.join(frontendRoot, 'src/views/tw-stock-monitor/components/ReadonlyModelStrategyComparisonPanel.vue')
const api = fs.readFileSync(apiPath, 'utf8')
const page = fs.readFileSync(pagePath, 'utf8')
const component = fs.readFileSync(componentPath, 'utf8')

function sliceBetween (source, start, end) {
  const startIndex = source.indexOf(start)
  assert.ok(startIndex >= 0, `missing start marker: ${start}`)
  const endIndex = source.indexOf(end, startIndex + start.length)
  assert.ok(endIndex > startIndex, `missing end marker: ${end}`)
  return source.slice(startIndex, endIndex)
}

const fixture = {
  ok: true,
  schema_version: 'tw_stock.readonly_model_strategy_comparison.v1',
  readonly_only: true,
  no_apply: true,
  catalog: {
    models: [
      { model_id: 'model_a', display_name: 'Model A · 当前 baseline', role: 'active_baseline', comparison_selectable: true },
      { model_id: 'model_a_plus_b_b19r2r', display_name: 'Model A+B · research challenger', role: 'research_challenger', comparison_selectable: true }
    ],
    strategies: [
      { strategy_id: 'top50_exit_one_worst_sell', display_name: '跌出 Top50 后最多替换一支', comparison_selectable: true },
      { strategy_id: 'legacy_phase1c', compatibility: 'legacy_lineage_only', comparison_selectable: false, compatible_model_ids: [] }
    ],
    windows: [{ window_id: 'historical_30d_20260722_20260901', display_name: '历史回放 30 日', selectable: true }],
    combinations: [
      { combination_id: 'model_a_30d', model_id: 'model_a', strategy_id: 'top50_exit_one_worst_sell', window_id: 'historical_30d_20260722_20260901', comparison_selectable: true },
      { combination_id: 'model_a_plus_b_30d', model_id: 'model_a_plus_b_b19r2r', strategy_id: 'top50_exit_one_worst_sell', window_id: 'historical_30d_20260722_20260901', comparison_selectable: true }
    ]
  },
  selected: {
    model_id: 'model_a',
    strategy_id: 'top50_exit_one_worst_sell',
    window_id: 'historical_30d_20260722_20260901',
    combination_id: 'model_a_30d'
  },
  comparison: {
    results: [
      { model_id: 'model_a', model_role: 'active_baseline', metrics: { net_return: 0.009951, max_drawdown: -0.02, turnover: 0.4, fee_tax: 1200, top5_abs_contribution_share: 0.52 }, gate_status: 'BASELINE' },
      { model_id: 'model_a_plus_b_b19r2r', model_role: 'research_challenger', metrics: { net_return: 0.080797, max_drawdown: -0.03, turnover: 0.5, fee_tax: 1400, top5_abs_contribution_share: 0.63 }, gate_status: 'FAIL' }
    ],
    delta: { net_return_b_minus_a: 0.070846 },
    diagnostics: {
      bootstrap_95pct_lower_bound: { measured_value: -0.0056, threshold: 0, status: 'FAIL' },
      negative_twii20_regime_return_delta: { measured_value: -0.0481, threshold: -0.02, status: 'FAIL' },
      concentration: { top5_abs_contribution_share: { measured_value: 0.5075, threshold: 0.45, status: 'FAIL' } }
    }
  },
  safety: { runtime_effect: 'none' }
}

const apiFn = sliceBetween(api, 'export function getTwStockReadonlyModelStrategyComparison', 'export function getTwStockLTROptionalSimStrategies')
const loader = sliceBetween(page, 'async loadReadonlyModelStrategyComparison', 'async loadReadonlyReplayWindowIndex')

assert.match(apiFn, /\/readonly\/model-strategy-comparison/)
assert.match(apiFn, /method:\s*'get'/)
assert.doesNotMatch(apiFn, /method:\s*'(post|put|patch|delete)'/i)
assert.match(loader, /getTwStockReadonlyModelStrategyComparison\(query\)/)
assert.match(page, /<readonly-model-strategy-comparison-panel/)
assert.match(page, /this\.loadReadonlyModelStrategyComparison\(\)/)

for (const text of ['模型与策略对比', 'Model A 与 Model A+B', '都不能在本页直接应用', '当前基线', '研究候选，联合门槛未通过', '不会写入模拟账户', '净收益', '最大回撤', '费用 / 换手', '收益集中度', '弱市表现', 'Bootstrap 稳定性下界', 'A+B Top5 收益集中度', 'no_apply']) {
  assert.ok(component.includes(text), `missing comparison UI text: ${text}`)
}

assert.doesNotMatch(component, /\$emit\(['"]apply['"]/)
assert.doesNotMatch(component, /<a-button[^>]*>[^<]*(应用|下单|交易)/)
assert.doesNotMatch(component, /provider.publish|accepted.latest|\/broker\/|quick-trade/i)

assert.equal(fixture.readonly_only, true)
assert.equal(fixture.no_apply, true)
assert.equal(fixture.safety.runtime_effect, 'none')
assert.deepEqual(fixture.catalog.models.map(item => item.role), ['active_baseline', 'research_challenger'])
assert.equal(fixture.catalog.combinations.filter(item => item.comparison_selectable).length, 2)
const legacyStrategy = fixture.catalog.strategies.find(item => item.compatibility === 'legacy_lineage_only')
assert.equal(legacyStrategy.comparison_selectable, false)
assert.deepEqual(legacyStrategy.compatible_model_ids, [])
for (const combination of fixture.catalog.combinations) {
  assert.ok(fixture.catalog.models.some(item => item.model_id === combination.model_id))
  assert.ok(fixture.catalog.strategies.some(item => item.strategy_id === combination.strategy_id && item.comparison_selectable === true))
  assert.ok(fixture.catalog.windows.some(item => item.window_id === combination.window_id))
}

console.log('[readonly-model-strategy-comparison-check] ok')
