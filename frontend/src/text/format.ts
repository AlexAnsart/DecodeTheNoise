/* How numbers and dates are written across the app. */

const count = new Intl.NumberFormat('en-US')
const day = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const month = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' })
const moment = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
})

export function formatCount(value: number): string {
  return count.format(value)
}

export function formatDay(ms: number): string {
  return day.format(ms)
}

export function formatMonth(ms: number): string {
  return month.format(ms)
}

export function formatMoment(ms: number): string {
  return `${moment.format(ms)} UTC`
}

/** `1 point`, `2 points`. */
export function plural(value: number, one: string, many: string): string {
  return `${formatCount(value)} ${value === 1 ? one : many}`
}

/** Value of a `datetime-local` field for a UTC instant, and back. */
export function toFieldValue(ms: number): string {
  return new Date(ms).toISOString().slice(0, 16)
}

export function fromFieldValue(value: string): number | null {
  const ms = Date.parse(`${value}:00Z`)
  return Number.isNaN(ms) ? null : ms
}
