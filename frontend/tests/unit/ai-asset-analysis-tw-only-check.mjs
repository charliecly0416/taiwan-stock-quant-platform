import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const read = file => fs.readFileSync(path.join(root, file), 'utf8')
const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}

const page = read('src/views/ai-analysis/index.vue')
const assetPage = read('src/views/ai-asset-analysis/index.vue')
const zhCN = read('src/locales/lang/zh-CN.js')
const zhTW = read('src/locales/lang/zh-TW.js')
const enUS = read('src/locales/lang/en-US.js')

assert(assetPage.includes(':embedded="true"'), 'AI asset page must embed ai-analysis in scoped mode')
assert(page.includes('v-if="!embedded" class="top-index-bar"'), 'embedded AI asset page must hide global index bar')
assert(page.includes('v-if="!embedded" class="left-panel"'), 'embedded AI asset page must hide unrelated heatmap/calendar panel')
assert(page.includes("const TW_MARKET_VALUES = new Set(['TWStock', 'tws'])"), 'must support both TWStock and tws market values')
assert(page.includes("if (TW_MARKET_VALUES.has(market)) return '台股'"), 'TW market label must render 台股, not raw i18n key')
assert(page.includes("'TWStock': '#08979c'"), 'TWStock tag must use a visible custom color')
assert(page.includes("'tws': '#08979c'"), 'tws tag must use a visible custom color')
assert(page.includes('rows.filter(item => TW_MARKET_VALUES.has(item.value))'), 'embedded market tabs must filter to TW markets')
assert(page.includes('res.data.filter(item => TW_MARKET_VALUES.has(item.market))'), 'embedded watchlist must filter to TW markets')
assert(page.includes('AI资产分析页面当前仅保留台股标的。'), 'embedded add flow must reject non-TW markets')

for (const locale of [zhCN, zhTW]) {
  assert(locale.includes("'dashboard.analysis.market.TWStock': '台股'"), 'missing TWStock zh locale')
  assert(locale.includes("'dashboard.analysis.market.tws': '台股'"), 'missing tws zh locale')
}
assert(enUS.includes("'dashboard.analysis.market.TWStock': 'Taiwan Stock'"), 'missing TWStock en locale')
assert(enUS.includes("'dashboard.analysis.market.tws': 'Taiwan Stock'"), 'missing tws en locale')

console.log('ai-asset-analysis tw-only checks passed')
