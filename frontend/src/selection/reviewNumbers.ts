/* The numbers of a selection review: which points are sent, which probes stand out, and how a
   share and a ratio are written. Pure. */

import type { ProbeRate } from '../api/reviewSchema'

/** The most points the review route takes in one call. */
export const MAX_REVIEWED = 5000

/** At most `most` indices, taken evenly across the selection. */
export function evenly(indices: Uint32Array, most: number): number[] {
  if (indices.length <= most) return Array.from(indices)
  const step = indices.length / most
  return Array.from({ length: most }, (_, i) => indices[Math.floor(i * step)])
}

/** A share as a percentage: whole above 10%, one decimal under, and never a false zero. */
export function percent(share: number): string {
  const value = share * 100
  if (value === 0) return '0%'
  if (value < 0.1) return '<0.1%'
  return value < 10 ? `${value.toFixed(1)}%` : `${Math.round(value)}%`
}

/** How many times more often a probe flags the selection than the rest of the map. */
export function ratioWords(rate: ProbeRate): string {
  if (rate.lift === null) return 'only here'
  return `×${rate.lift >= 10 ? Math.round(rate.lift) : rate.lift.toFixed(1)}`
}

/** Under this many flagged posts, a ratio rests on too little to lead the list. */
export const THIN_COUNT = 3

/** The probes that flag the selection more often than the rest of the map, strongest first.
 *  A ratio counted on one or two posts comes after the others, however high: it says little.
 *  A probe that flags nothing elsewhere has no ratio and leads its group. */
export function standingOut(rates: ProbeRate[]): ProbeRate[] {
  const ratio = (rate: ProbeRate): number => rate.lift ?? Number.POSITIVE_INFINITY
  return rates
    .filter((rate) => rate.flagged > 0 && (rate.lift === null || rate.lift > 1))
    .sort((a, b) => {
      const thin = Number(a.flagged < THIN_COUNT) - Number(b.flagged < THIN_COUNT)
      if (thin !== 0) return thin
      return ratio(a) === ratio(b) ? b.flagged - a.flagged : ratio(b) - ratio(a)
    })
}
