import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"

const root = resolve(new URL("..", import.meta.url).pathname, "..")
const read = path => readFileSync(resolve(root, path), "utf8")

const page = read("src/views/tw-stock-monitor/index.vue")
const smoke = read("tests/unit/tw-stock-monitor-local-smoke.mjs")

for (const testId of [
  "qlib-signal-table",
  "qlib-watch-add",
  "qlib-watch-draft",
  "qlib-watch-fill-config",
  "monitor-config-drawer",
  "monitor-config-symbols"
]) {
  assert.ok(page.includes('data-testid="' + testId + '"'), "missing data-testid " + testId)
}

assert.match(smoke, /getByTestId\("qlib-watch-add"\)|getByTestId\(\x27qlib-watch-add\x27\)/)
assert.match(smoke, /getByTestId\("qlib-watch-fill-config"\)|getByTestId\(\x27qlib-watch-fill-config\x27\)/)
assert.match(smoke, /getByTestId\("monitor-config-drawer"\)|getByTestId\(\x27monitor-config-drawer\x27\)/)
assert.match(smoke, /getByTestId\("monitor-config-symbols"\)|getByTestId\(\x27monitor-config-symbols\x27\)/)
assert.match(smoke, /querySelector\(\x27\[data-testid="monitor-config-symbols"\]\x27\)/)
assert.doesNotMatch(smoke, /querySelectorAll\(\x27textarea\x27\)/)
assert.doesNotMatch(smoke, /locator\(\x27textarea\x27\)/)

const fillDraftMatch = page.match(/fillMonitorConfigFromQlibDraft \(\) \{[\s\S]*?\n    \},\n    qlibTrendAvailable/)
assert.ok(fillDraftMatch, "missing fillMonitorConfigFromQlibDraft method")
const fillDraftBody = fillDraftMatch[0]

for (const required of [
  /this\.config\.symbols/,
  /this\.qlibWatchDraft\.forEach/,
  /symbolsText:\s*symbols\.join\(\x27, \x27\)/,
  /this\.configDrawerVisible = true/
]) {
  assert.match(fillDraftBody, required)
}

for (const forbidden of [
  /saveConfig\(/,
  /saveTwStockMonitorConfig\(/,
  /runScan\(/,
  /scanTwStockMonitor\(/,
  /getTwStockAlerts\(/,
  /updateTwStockAlert\(/,
  /triggerQlibOptionCDryRun\(/,
  /publish/i,
  /refresh-provider/i,
  /quick-trade/i,
  /broker/i,
  /order/i,
  /target_position/i,
  /targetPosition/
]) {
  assert.doesNotMatch(fillDraftBody, forbidden, "fill draft contains forbidden action " + forbidden)
}

console.log("tw-stock watchlist draft checks passed")
