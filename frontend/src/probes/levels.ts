/* The two levels of a probe and how they are worded. A score is a position against the probe's
   own measured thresholds, the same for every probe: `possible` from 0.5, `probable` from 0.8. */

import type { LevelMeasure, ProbeInfo } from '../api/schema'

export const POSSIBLE_SCORE = 0.5
export const PROBABLE_SCORE = 0.8

export type FlagLevel = 'possible' | 'probable'

export const LEVEL_WORD: Record<FlagLevel, string> = { possible: 'Possible', probable: 'Probable' }

/** The levels a probe was measured at: a level without a measure is never shown as reached. */
export type MeasuredLevels = Pick<ProbeInfo, 'possible' | 'probable'>

/** The level a score reaches among the measured ones. Null under the first one, or when the
 *  probe did not read the point (NaN). Without a probe, both levels count. */
export function levelOf(score: number, probe?: MeasuredLevels): FlagLevel | null {
  if (score >= PROBABLE_SCORE && (!probe || probe.probable)) return 'probable'
  if (score >= POSSIBLE_SCORE && (!probe || probe.possible)) return 'possible'
  return null
}

/** Probes the interface may show. The others only send items to the review. */
export function shownProbes(probes: ProbeInfo[]): ProbeInfo[] {
  return probes.filter((probe) => probe.state === 'shown')
}

export function formatScore(value: number): string {
  return value.toFixed(2)
}

/** What a level measured on held-out posts, in a few words. */
export function measureWords(measure: LevelMeasure): string {
  return `precision ${formatScore(measure.precision)}, ${measure.read} flagged posts read`
}

/** The one-line measure beside a probe's name: its strongest measured level. */
export function probeMeasure(probe: ProbeInfo): string {
  if (probe.probable) return `precision ${formatScore(probe.probable.precision)} at probable (${probe.probable.read} read)`
  if (probe.possible) return `precision ${formatScore(probe.possible.precision)} at possible (${probe.possible.read} read)`
  return 'no level measured'
}

/** `calls` to `Calls`, `rhetorical_techniques` to `Rhetorical techniques`. */
export function familyLabel(family: string): string {
  const words = family.replaceAll('_', ' ').trim()
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : 'Other'
}
