import { useEffect, useMemo, useState } from 'react'
import { logger } from '../log/logger'
import type { MapData } from '../map/mapData'
import { useScoreStore } from '../source/mapServices'

const log = logger('probes')

export interface ProbeScores {
  /** One score per point, NaN where the probe does not read it. On a map that has just grown,
   *  the array is shorter than the map until the scores are read again. Null until first read. */
  scores: Float32Array | null
  /** What to say while the scores are missing: being read, or not readable. */
  note: string | null
}

const NONE: ProbeScores = { scores: null, note: null }

/** The scores of one probe over the map, read again each time the map changes. */
export function useProbeScores(data: MapData, probeKey: string | null): ProbeScores {
  const store = useScoreStore()
  const [read, setRead] = useState<{ key: string; scores: Float32Array } | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const { version } = data

  useEffect(() => {
    if (probeKey === null) return undefined
    let current = true
    setFailed(null)
    store
      .read(probeKey, version)
      .then((scores) => {
        if (current) setRead({ key: probeKey, scores })
      })
      .catch((error: unknown) => {
        if (!current) return
        log.error('the scores of a probe could not be read', error)
        setFailed(probeKey)
      })
    return () => {
      current = false
    }
  }, [store, probeKey, version])

  return useMemo(() => {
    if (probeKey === null) return NONE
    const scores = read && read.key === probeKey ? read.scores : null
    if (failed === probeKey) return { scores, note: 'The scores of this probe could not be read.' }
    return { scores, note: scores ? null : 'Reading the scores…' }
  }, [probeKey, read, failed])
}
