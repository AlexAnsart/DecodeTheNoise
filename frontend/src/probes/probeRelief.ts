/* A probe as an axis: the height of a point is its score, with no rescaling, so the two levels
   sit at the same height for every probe. */

import type { ProbeInfo } from '../api/schema'
import type { Relief, ReliefTick } from '../axes/relief'
import { POSSIBLE_SCORE, PROBABLE_SCORE, levelOf } from './levels'

/** The scale of the height axis: the levels the probe was measured at, where they start. */
function ticksOf(probe: ProbeInfo): ReliefTick[] {
  const ticks: ReliefTick[] = [{ at: 0, text: '0' }]
  if (probe.possible) ticks.push({ at: POSSIBLE_SCORE, text: 'possible' })
  if (probe.probable) ticks.push({ at: PROBABLE_SCORE, text: 'probable' })
  return [...ticks, { at: 1, text: '1' }]
}

/** `scores` holds one value per point, NaN where the probe does not read the point: such a
 *  point stays on the floor, faint. */
export function probeRelief(probe: ProbeInfo, scores: Float32Array): Relief {
  const heights = new Float32Array(scores.length)
  const unread = new Uint8Array(scores.length)
  let flagged = 0
  let missing = 0
  for (let i = 0; i < scores.length; i += 1) {
    const score = scores[i]
    if (Number.isNaN(score)) {
      heights[i] = Number.NaN
      unread[i] = 1
      missing += 1
      continue
    }
    heights[i] = Math.min(1, Math.max(0, score))
    if (levelOf(score, probe) !== null) flagged += 1
  }
  return {
    label: probe.label,
    heights,
    unread: missing > 0 ? unread : null,
    note: flagged === 0 ? 'No item of this map reaches a level of this probe.' : null,
    source: { kind: 'probe', key: probe.key },
    ticks: ticksOf(probe),
  }
}
