import { useEffect, useRef } from 'react'
import { logger } from '../log/logger'
import type { MapData } from '../map/mapData'
import { probeRelief } from '../probes/probeRelief'
import { useMapApi, useScoreStore } from '../source/mapServices'
import type { Relief } from './relief'
import { MAX_LIKENESS_ITEMS, likenessRelief } from './relief'

const log = logger('axes')

interface ReliefState {
  relief: Relief | null
  /** Points chosen with the lasso: what a relief by selection resembles. */
  picked: Uint32Array | null
  setRelief(relief: Relief): void
}

/** On a live map, reads the heights of the relief again each time the map is read again, so
 *  the points added since rise like the others. */
export function useReliefRefresh(data: MapData, state: ReliefState): void {
  const api = useMapApi()
  const scores = useScoreStore()
  const latest = useRef(state)

  useEffect(() => {
    latest.current = state
  })

  useEffect(() => {
    const { relief, picked } = latest.current
    if (!data.live || !relief) return undefined
    const { source, label } = relief
    let asked: Promise<Relief> | null = null
    if (source.kind === 'probe') {
      const probe = data.probes.find((candidate) => candidate.key === source.key)
      if (probe) asked = scores.read(probe.key, data.version).then((values) => probeRelief(probe, values))
    } else if (source.kind === 'concept') {
      asked = api.similarityToText(source.text).then((values) => likenessRelief(label, values, source))
    } else if (picked) {
      const sample = Array.from(picked.slice(0, MAX_LIKENESS_ITEMS))
      asked = api.similarityToItems(sample).then((values) => likenessRelief(label, values, source, picked))
    }
    if (!asked) return undefined
    let current = true
    asked
      .then((next) => {
        // Only when the relief on screen is still the one that was read again.
        if (current && latest.current.relief?.source === source) latest.current.setRelief(next)
      })
      .catch((error: unknown) => {
        if (current) log.warn('the relief could not be read again', error)
      })
    return () => {
      current = false
    }
  }, [api, scores, data])
}
