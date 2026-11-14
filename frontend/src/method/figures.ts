/* How a measured rate is written on the method page. Pure. */

const rate = new Intl.NumberFormat('en-US', { style: 'percent', maximumSignificantDigits: 3 })

/** A share between 0 and 1 as a percentage; "not measured" when the report has no value. */
export function formatRate(value: number | null): string {
  return value === null ? 'not measured' : rate.format(value)
}

/** The 95% interval of a rate, low to high. */
export function formatInterval(low: number, high: number): string {
  return `${rate.format(low)} to ${rate.format(high)}`
}
