/* The scores of a probe over a whole map: one download per probe and per version of the map,
   shared by the axis and the colouring that read it. */

import type { MapApi } from '../api/client'

const KEPT = 6

export interface ScoreStore {
  /** One float per point, NaN where the probe does not read the point. */
  read(probeKey: string, version: number): Promise<Float32Array>
}

export function createScoreStore(api: MapApi): ScoreStore {
  const kept = new Map<string, Promise<Float32Array>>()
  return {
    read(probeKey, version) {
      const id = `${version}:${probeKey}`
      const known = kept.get(id)
      if (known) return known
      const asked = api.scores(probeKey)
      kept.set(id, asked)
      // A failed download is not kept: the next reader asks again.
      asked.catch(() => kept.delete(id))
      if (kept.size > KEPT) {
        const oldest = kept.keys().next().value
        if (oldest !== undefined) kept.delete(oldest)
      }
      return asked
    },
  }
}
