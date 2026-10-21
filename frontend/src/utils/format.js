/** Shared formatting helpers used across the whole UI. */

const CURRENCY_SYMBOLS = {
  INR: '₹',
  USD: '$',
  EUR: '€',
  GBP: '£',
  AED: 'AED',
  SGD: 'S$',
  AUD: 'A$',
  CAD: 'C$',
}

/** 'INR' -> '₹'. Unknown codes fall back to the code itself. */
export function currencySymbol(code) {
  return CURRENCY_SYMBOLS[code] || `${code} `
}

/**
 * Format money for display.
 *
 * The backend already returns a Decimal-backed string (for example
 * "1250.00"), so we only add grouping separators and the symbol here. Grouping
 * is done manually rather than with Intl, to keep the output identical in every
 * browser and avoid locale surprises during a demo.
 */
export function formatCurrency(amount, code = 'INR', options = {}) {
  const { decimals = 2, showSymbol = true } = options
  const numeric = Number(amount ?? 0)
  const safe = Number.isFinite(numeric) ? numeric : 0

  const fixed = Math.abs(safe).toFixed(decimals)
  const [whole, fraction] = fixed.split('.')

  // Indian numbering (1,25,000) vs international (125,000).
  let grouped
  if (code === 'INR') {
    const last3 = whole.slice(-3)
    const rest = whole.slice(0, -3)
    grouped = rest ? `${rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${last3}` : last3
  } else {
    grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }

  const sign = safe < 0 ? '-' : ''
  const body = fraction ? `${grouped}.${fraction}` : grouped

  return showSymbol ? `${sign}${currencySymbol(code)}${body}` : `${sign}${body}`
}

/** Compact money for tight spaces: 12500 -> '₹12.5K'. */
export function formatCurrencyCompact(amount, code = 'INR') {
  const numeric = Number(amount ?? 0)
  if (!Number.isFinite(numeric)) return currencySymbol(code) + '0'
  const abs = Math.abs(numeric)
  const sign = numeric < 0 ? '-' : ''

  if (abs >= 1_000_000) return `${sign}${currencySymbol(code)}${(abs / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `${sign}${currencySymbol(code)}${(abs / 1_000).toFixed(1)}K`
  return formatCurrency(numeric, code)
}

/** '2026-11-05' -> '5 Nov 2026'. */
export function formatDate(value, options = {}) {
  if (!value) return '—'
  const date = value instanceof Date ? value : new Date(`${String(value).slice(0, 10)}T00:00:00`)
  if (Number.isNaN(date.getTime())) return '—'

  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...options,
  })
}

/** '2026-11-05' -> '5 Nov'. Used where the year is already obvious. */
export function formatDateShort(value) {
  return formatDate(value, { year: undefined })
}

/** ISO timestamp -> '5 Nov 2026, 14:30'. */
export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return `${formatDate(date)}, ${date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })}`
}

/** ISO timestamp -> '2 minutes ago' / 'in 3 days'. */
export function formatRelative(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  const diffMs = date.getTime() - Date.now()
  const diffMin = Math.round(diffMs / 60000)
  const absMin = Math.abs(diffMin)

  const units = [
    { limit: 60, div: 1, unit: 'minute', past: 'ago', future: 'from now' },
    { limit: 1440, div: 60, unit: 'hour', past: 'ago', future: 'from now' },
    { limit: 10080, div: 1440, unit: 'day', past: 'ago', future: 'from now' },
    { limit: 43200, div: 10080, unit: 'week', past: 'ago', future: 'from now' },
  ]

  for (const { limit, div, unit, past, future } of units) {
    if (absMin < limit) {
      const value_ = Math.round(absMin / div) || 1
      const label = `${value_} ${unit}${value_ > 1 ? 's' : ''}`
      return diffMs < 0 ? `${label} ${past}` : `in ${label}`
    }
  }
  return formatDate(date)
}

/** Human wording for a number of days: -3 -> '3 days overdue', 0 -> 'Today'. */
export function formatDaysRemaining(days) {
  const value = Number(days ?? 0)
  if (value < 0) {
    const n = Math.abs(value)
    return `${n} day${n === 1 ? '' : 's'} overdue`
  }
  if (value === 0) return 'Today'
  if (value === 1) return 'Tomorrow'
  return `${value} days left`
}

/** Today, in the browser's own timezone, as 'YYYY-MM-DD'. */
export function todayISO() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10)
}

/** Shift a 'YYYY-MM-DD' string by N days. */
export function shiftDate(isoDate, days) {
  const date = new Date(`${isoDate}T00:00:00`)
  date.setDate(date.getDate() + days)
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 10)
}

/** Whole days from today to an ISO date. */
export function daysUntil(isoDate) {
  const target = new Date(`${String(isoDate).slice(0, 10)}T00:00:00`)
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return Math.round((target.getTime() - now.getTime()) / 86400000)
}

/** '08:00:00' -> '8:00 AM' */
export function formatTime(value) {
  if (!value) return '—'
  const parts = String(value).split(':')
  const hour = Number(parts[0])
  const minute = Number(parts[1] || 0)
  if (Number.isNaN(hour) || Number.isNaN(minute)) return String(value)
  const suffix = hour < 12 ? 'AM' : 'PM'
  const display = hour % 12 || 12
  return `${display}:${String(minute).padStart(2, '0')} ${suffix}`
}

/** '2026-11-05' -> 'Thu, 5 Nov 2026' */
export function formatLongToday(date = new Date()) {
  return date.toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

/** '250' -> '250 ml' */
export function formatMl(amount) {
  return `${Number(amount ?? 0).toLocaleString('en-IN')} ml`
}

/** Time-of-day greeting used by the dashboard header. */
export function greeting(date = new Date()) {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning!'
  if (hour < 17) return 'Good afternoon!'
  return 'Good evening!'
}

/** Turn 'bill_overdue' into 'Bill overdue'. */
export function humanise(value) {
  if (!value) return ''
  const text = String(value).replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}