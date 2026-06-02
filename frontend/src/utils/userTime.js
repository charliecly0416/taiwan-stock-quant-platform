import storage from 'store'
import { USER_INFO } from '@/store/mutation-types'

export function getUserTimezoneFromStorage () {
  try {
    const u = storage.get(USER_INFO) || {}
    const tz = u.timezone
    return (tz && String(tz).trim()) || ''
  } catch (e) {
    return ''
  }
}

export function parseToDate (input) {
  if (input == null || input === '') return null
  if (input instanceof Date) {
    return isNaN(input.getTime()) ? null : input
  }
  if (typeof input === 'number') {
    const ms = input < 1e12 ? input * 1000 : input
    const d = new Date(ms)
    return isNaN(d.getTime()) ? null : d
  }
  if (typeof input === 'string') {
    const s = input.trim()
    if (/^\d+$/.test(s)) {
      const n = parseInt(s, 10)
      const ms = n < 1e12 ? n * 1000 : n
      const d = new Date(ms)
      return isNaN(d.getTime()) ? null : d
    }
    const d = new Date(s)
    return isNaN(d.getTime()) ? null : d
  }
  return null
}

/**
 * Format instant for display using profile timezone when set; otherwise browser default.
 */
export function formatUserDateTime (input, opts = {}) {
  const d = parseToDate(input)
  if (!d) return opts.fallback != null ? opts.fallback : '-'
  const locale = opts.locale || (typeof navigator !== 'undefined' && navigator.language) || 'zh-CN'
  const tz = getUserTimezoneFromStorage()
  const intlOpts = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }
  if (tz) {
    intlOpts.timeZone = tz
  }
  try {
    return d.toLocaleString(locale, intlOpts)
  } catch (e) {
    try {
      const { timeZone, ...rest } = intlOpts
      return d.toLocaleString(locale, rest)
    } catch (e2) {
      return d.toLocaleString()
    }
  }
}

/**
 * Format a backtest trade timestamp.
 *
 * Backend writes trade times via `timestamp.strftime('%Y-%m-%d %H:%M')` on
 * naive UTC-indexed pandas DataFrames (see backend/app/services/backtest.py).
 * That string carries no tz info, but its value IS UTC. `new Date(s)` would
 * interpret it as browser-local, producing a wrong wall clock for any user
 * outside UTC (e.g. CN users see "8 hours late").
 *
 * This helper:
 *   1. detects bare `YYYY-MM-DD HH:mm[:ss]` strings and parses them as UTC,
 *   2. falls back to `parseToDate` for tz-aware/ISO/number/Date inputs,
 *   3. renders using the user's profile timezone if set, else browser local.
 */
export function formatBacktestTime (input, opts = {}) {
  if (input == null || input === '') {
    return opts.fallback != null ? opts.fallback : '-'
  }
  let d = null
  if (typeof input === 'string') {
    const s = input.trim()
    if (!s) return opts.fallback != null ? opts.fallback : '-'
    const isNaive = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$/.test(s) &&
      !/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)
    if (isNaive) {
      let iso = s.replace(' ', 'T')
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(iso)) iso += ':00'
      d = new Date(iso + 'Z')
    } else {
      d = parseToDate(s)
    }
  } else {
    d = parseToDate(input)
  }
  if (!d || isNaN(d.getTime())) {
    return opts.fallback != null ? opts.fallback : '-'
  }
  const locale = opts.locale || (typeof navigator !== 'undefined' && navigator.language) || 'zh-CN'
  const tz = getUserTimezoneFromStorage()
  const intlOpts = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }
  if (opts.withSeconds) intlOpts.second = '2-digit'
  if (tz) intlOpts.timeZone = tz
  try {
    return d.toLocaleString(locale, intlOpts)
  } catch (e) {
    try {
      const { timeZone, ...rest } = intlOpts
      return d.toLocaleString(locale, rest)
    } catch (e2) {
      return d.toLocaleString()
    }
  }
}

/**
 * Format instant in the browser's local timezone (ignores profile timezone override).
 * Use for audit-style timestamps (e.g. trade history) so wall clock matches the user's machine.
 */
/**
 * Strategy / bot runtime logs: backend emits UTC ISO (Z) via ``to_utc_iso``; naive
 * strings without a tz suffix are treated as UTC wall clock before applying the
 * user's profile timezone (or browser local).
 */
export function formatStrategyLogTime (input, opts = {}) {
  return formatBacktestTime(input, { withSeconds: true, ...opts })
}

export function formatBrowserLocalDateTime (input, opts = {}) {
  const d = parseToDate(input)
  if (!d) return opts.fallback != null ? opts.fallback : '-'
  const locale = opts.locale || (typeof navigator !== 'undefined' && navigator.language) || 'zh-CN'
  const intlOpts = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }
  try {
    return d.toLocaleString(locale, intlOpts)
  } catch (e) {
    return d.toLocaleString()
  }
}
