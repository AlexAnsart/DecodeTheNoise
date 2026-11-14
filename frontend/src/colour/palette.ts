/* Colours of the points, read from the design tokens so the canvas follows the theme. */

import type { Rgb } from '../theme/theme'
import { tokenRgb } from '../theme/theme'

export const PALETTE_SIZE = 12
/** Alpha of a point at full strength, of a point left in the shade, of the "others" bucket,
 *  of a point without a value. */
export const ALPHA_FULL = 215
export const ALPHA_DIM = 28
export const ALPHA_OTHERS = 210
export const ALPHA_NO_VALUE = 110
export const ALPHA_REST = 90

export interface Palette {
  categories: Rgb[]
  dateStops: Rgb[]
  others: Rgb
  rest: Rgb
  accent: Rgb
  muted: Rgb
  highlight: Rgb
  danger: Rgb
  /** The two levels of a probe, as an intensity. */
  possible: Rgb
  probable: Rgb
}

export function readPalette(): Palette {
  return {
    categories: Array.from({ length: PALETTE_SIZE }, (_, i) => tokenRgb(`--nm-cat-${i + 1}`)),
    dateStops: [1, 2, 3, 4].map((i) => tokenRgb(`--nm-date-${i}`)),
    others: tokenRgb('--nm-text-muted'),
    rest: tokenRgb('--nm-rest'),
    accent: tokenRgb('--nm-accent'),
    muted: tokenRgb('--nm-text-muted'),
    highlight: tokenRgb('--nm-point-highlight'),
    danger: tokenRgb('--nm-danger'),
    possible: tokenRgb('--nm-level-possible'),
    probable: tokenRgb('--nm-level-probable'),
  }
}

function shade(colour: Rgb, amount: number): Rgb {
  const toward = amount > 0 ? 255 : 0
  const share = Math.abs(amount)
  return [
    Math.round(colour[0] + (toward - colour[0]) * share),
    Math.round(colour[1] + (toward - colour[1]) * share),
    Math.round(colour[2] + (toward - colour[2]) * share),
  ]
}

/** Colour of the k-th category when every category must stay distinct (zones): the palette,
 *  then the same hues lighter, then darker. */
export function cycledColour(palette: Palette, k: number): Rgb {
  const base = palette.categories[k % PALETTE_SIZE]
  const round = Math.floor(k / PALETTE_SIZE)
  if (round === 0) return base
  const step = 0.22 * Math.ceil(round / 2)
  return shade(base, round % 2 === 1 ? Math.min(0.6, step) : -Math.min(0.6, step))
}

/** Position on the date gradient for a share in [0, 1]. */
export function gradientColour(stops: Rgb[], share: number): Rgb {
  const scaled = Math.min(1, Math.max(0, share)) * (stops.length - 1)
  const low = Math.min(stops.length - 2, Math.floor(scaled))
  const t = scaled - low
  const a = stops[low]
  const b = stops[low + 1]
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ]
}

export function cssColour(colour: Rgb): string {
  return `rgb(${colour[0]}, ${colour[1]}, ${colour[2]})`
}
