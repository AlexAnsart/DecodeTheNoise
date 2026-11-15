/* Why a probe has no such level: a few words for the table, a sentence for the opened probe. Pure. */

import type { Level, ProbeRow } from './probeRows'
import type { LevelStarts } from './setting'

export interface Absence {
  short: string
  long: string
}

/** Null when the level was measured, or when the probe has no level at all: there is then
 *  nothing to say of one level in particular. */
export function absenceOf(row: ProbeRow, level: Level, starts: LevelStarts | null): Absence | null {
  const other = level === 'probable' ? row.possible : row.probable
  if (row[level] || !other) return null
  if (row.report?.withdrawn?.[level]) {
    return {
      short: 'Withdrawn on test',
      long: `This level met its target on calibration, then measured under the bar on the test split: it was withdrawn, and the probe keeps ${level === 'probable' ? 'possible' : 'probable'} alone.`,
    }
  }
  if (level === 'probable') {
    return { short: 'Not reached', long: 'No threshold reached the precision asked of this level: the probe stops at possible.' }
  }
  const between = starts ? `a score between ${starts.possible} and ${starts.probable}` : 'a score under probable'
  return { short: 'Single level', long: `This probe has one level, probable: ${between} has no name for it, and nothing is flagged there.` }
}
