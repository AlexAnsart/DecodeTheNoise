/* How a measured number is written on the method page. Pure. */

const rate = new Intl.NumberFormat('en-US', { style: 'percent', maximumSignificantDigits: 3 })
const short = new Intl.NumberFormat('en-US', { style: 'percent', maximumSignificantDigits: 2 })
const plain = new Intl.NumberFormat('en-US', { maximumSignificantDigits: 3 })

/** Under one post in two million, the low end of an interval is rounding noise: it reads 0%. */
const NOISE = 5e-7

const share = (value: number): string => rate.format(Math.abs(value) < NOISE ? 0 : value)

/** A share between 0 and 1 as a percentage; "not measured" when the report has no value. */
export function formatRate(value: number | null): string {
  return value === null ? 'not measured' : share(value)
}

/** The same share where room is short: two digits, and a dash for no value. */
export function formatShare(value: number | null): string {
  return value === null ? '–' : short.format(value)
}

/** The 95% interval of a rate, low to high. */
export function formatInterval(low: number, high: number): string {
  return `${share(low)} to ${share(high)}`
}

/** How many times above chance a ranking is: "×12". */
export function formatLift(lift: number | null): string {
  return lift === null ? '–' : `×${plain.format(lift)}`
}

/** A number that is not a share: a threshold, an average precision. */
export function formatNumber(value: number): string {
  return plain.format(value)
}

/** A score that is not a share of posts (a kappa, an F1): two decimals, as the reports print it. */
export function formatScore(value: number): string {
  const fixed = value.toFixed(2)
  return fixed === '-0.00' ? '0.00' : fixed
}
