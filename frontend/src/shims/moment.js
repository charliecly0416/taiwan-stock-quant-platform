// Vite/esbuild 对 moment 这种 `module.exports = ctor` 的纯 CJS 模块做 ESM
// interop 时，namespace 里只会有 `default`，导致 ant-design-vue 1.x 里
// `import * as moment from 'moment'` 后调 `moment.isMoment` / `moment.utc`
// 等就是 `(void 0) is not a function`。
//
// 这里把 moment 默认导出 + 常用静态方法都重新 named export，再通过 vite alias
// 把 `moment` 指向本文件，三个使用形式（default / named / namespace）都能命中：
//   import moment from 'moment'              -> 默认导出（函数）
//   import { isMoment } from 'moment'        -> named export
//   import * as moment from 'moment'         -> namespace（包含 default 和 named）

import moment from 'moment/moment.js'

export default moment

export const version = moment.version
export const fn = moment.fn

// 工厂 / 构造
export const utc = moment.utc.bind(moment)
export const unix = moment.unix.bind(moment)
export const parseZone = moment.parseZone.bind(moment)
export const invalid = moment.invalid.bind(moment)
export const duration = moment.duration.bind(moment)

// 类型判断
export const isMoment = moment.isMoment
export const isDate = moment.isDate
export const isDuration = moment.isDuration

// 本地化 / 全局配置
export const locale = moment.locale.bind(moment)
export const localeData = moment.localeData.bind(moment)
export const locales = moment.locales.bind(moment)
export const defineLocale = moment.defineLocale.bind(moment)
export const updateLocale = moment.updateLocale.bind(moment)
export const months = moment.months.bind(moment)
export const monthsShort = moment.monthsShort.bind(moment)
export const weekdays = moment.weekdays.bind(moment)
export const weekdaysMin = moment.weekdaysMin.bind(moment)
export const weekdaysShort = moment.weekdaysShort.bind(moment)
export const normalizeUnits = moment.normalizeUnits
export const relativeTimeRounding = moment.relativeTimeRounding
export const relativeTimeThreshold = moment.relativeTimeThreshold
export const calendarFormat = moment.calendarFormat
export const ISO_8601 = moment.ISO_8601
export const RFC_2822 = moment.RFC_2822

// 时区相关（如有 moment-timezone 时会被覆盖，留位）
export const min = moment.min
export const max = moment.max
export const now = moment.now
