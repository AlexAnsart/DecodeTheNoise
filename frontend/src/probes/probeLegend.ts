/* A probe as a colouring: each point takes the colour of the level its score reaches. */

import type { Legend, LegendEntry } from '../colour/legend'
import { paintEntries } from '../colour/legend'
import type { Palette } from '../colour/palette'
import { ALPHA_FULL, ALPHA_NO_VALUE, ALPHA_REST } from '../colour/palette'
import type { MapData } from '../map/mapData'
import { levelOf, measureWords, probeMeasure } from './levels'
import type { ProbeScores } from './useProbeScores'

const PROBABLE = 0
const POSSIBLE = 1
const NOT_FLAGGED = 2
const NOT_READ = 3

/** Legend and colours of the probe `key`. Until its scores are read, every point is unread and
 *  the legend says why. */
export function probeLegend(data: MapData, key: string, probe: ProbeScores, palette: Palette): Legend {
  const info = data.probes.find((candidate) => candidate.key === key)
  const { scores } = probe
  const entries: LegendEntry[] = [
    // A level the probe was not measured at never holds a point, so its row is never shown.
    { id: PROBABLE, label: 'Probable', colour: palette.probable, alpha: ALPHA_FULL, total: 0, hint: info?.probable ? `At this level: ${measureWords(info.probable)}` : undefined },
    { id: POSSIBLE, label: 'Possible', colour: palette.possible, alpha: ALPHA_FULL, total: 0, hint: info?.possible ? `At this level: ${measureWords(info.possible)}` : undefined },
    { id: NOT_FLAGGED, label: 'Not flagged', colour: palette.rest, alpha: ALPHA_REST, total: 0 },
    { id: NOT_READ, label: scores ? 'Not read' : 'Not read yet', colour: palette.others, alpha: ALPHA_NO_VALUE, total: 0 },
  ]
  const entryOf = new Uint16Array(data.n)
  for (let i = 0; i < data.n; i += 1) {
    // A point added since the scores were read has none yet.
    const score = scores && i < scores.length ? scores[i] : Number.NaN
    const level = info ? levelOf(score, info) : null
    const entry = Number.isNaN(score) ? NOT_READ : level === 'probable' ? PROBABLE : level === 'possible' ? POSSIBLE : NOT_FLAGGED
    entryOf[i] = entry
    entries[entry].total += 1
  }
  return {
    title: info ? `Probe: ${info.label}` : 'Probe',
    entries,
    entryOf,
    base: paintEntries(data.n, entries, entryOf),
    dateBar: null,
    note: probe.note ?? (info ? `Measured: ${probeMeasure(info)}.` : null),
  }
}
