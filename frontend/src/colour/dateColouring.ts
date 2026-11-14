/* Dates as a gradient placed by quantile: each stretch of colour holds as many points. */

import type { Rgb } from '../theme/theme'
import type { Palette } from './palette'
import { ALPHA_FULL, ALPHA_NO_VALUE, gradientColour } from './palette'

const CUTS = 257

export interface DateBar {
  stops: Rgb[]
  /** Dates at the start, one third, two thirds and the end of the gradient. */
  ticks: number[]
}

export interface DateBase {
  base: Uint8Array
  bar: DateBar | null
  undated: number
}

function shareOf(t: number, cuts: Float64Array): number {
  let low = 0
  let high = cuts.length - 1
  while (low < high) {
    const mid = (low + high) >> 1
    if (cuts[mid] < t) low = mid + 1
    else high = mid
  }
  return low / (cuts.length - 1)
}

export function dateBase(ts: Float64Array, palette: Palette): DateBase {
  const n = ts.length
  const dated = Array.from(ts).filter((t) => t > 0)
  dated.sort((a, b) => a - b)
  const base = new Uint8Array(n * 4)
  const cuts = new Float64Array(CUTS)
  if (dated.length > 0) {
    for (let c = 0; c < CUTS; c += 1) {
      cuts[c] = dated[Math.min(dated.length - 1, Math.round((c / (CUTS - 1)) * (dated.length - 1)))]
    }
  }
  for (let i = 0; i < n; i += 1) {
    const isDated = ts[i] > 0
    const colour = isDated ? gradientColour(palette.dateStops, shareOf(ts[i], cuts)) : palette.others
    base[i * 4] = colour[0]
    base[i * 4 + 1] = colour[1]
    base[i * 4 + 2] = colour[2]
    base[i * 4 + 3] = isDated ? ALPHA_FULL : ALPHA_NO_VALUE
  }
  const at = (share: number): number => cuts[Math.round(share * (CUTS - 1))]
  const bar = dated.length > 0 ? { stops: palette.dateStops, ticks: [at(0), at(1 / 3), at(2 / 3), at(1)] } : null
  return { base, bar, undated: n - dated.length }
}
