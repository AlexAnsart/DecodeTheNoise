import { useEffect, useState } from 'react'
import type { PointReading } from '../api/schema'
import { logger } from '../log/logger'
import type { MapData } from '../map/mapData'
import { useMapApi } from '../source/mapServices'

const log = logger('probes')

export type ReadingState =
  /** The map has no probe: there is nothing to read. */
  | { status: 'none' }
  | { status: 'loading' }
  | { status: 'ready'; reading: PointReading }
  | { status: 'error' }

/** What the probes and the review say of one point. Read again when a live map changes: a
 *  review arrives after the item, and the reading on screen stays until the next one is in. */
export function usePointReading(data: MapData, index: number): ReadingState {
  const api = useMapApi()
  const [read, setRead] = useState<PointReading | null>(null)
  const [failed, setFailed] = useState<number | null>(null)
  const wanted = data.probes.length > 0
  const { version } = data

  useEffect(() => {
    if (!wanted) return undefined
    const abort = new AbortController()
    setFailed(null)
    api
      .reading(index, abort.signal)
      .then(setRead)
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.error('the reading of a point could not be fetched', error)
        setFailed(index)
      })
    return () => abort.abort()
  }, [api, index, version, wanted])

  if (!wanted) return { status: 'none' }
  if (read && read.index === index) return { status: 'ready', reading: read }
  return failed === index ? { status: 'error' } : { status: 'loading' }
}
