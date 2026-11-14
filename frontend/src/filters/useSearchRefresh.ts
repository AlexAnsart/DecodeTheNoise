import { useEffect, useRef } from 'react'
import { logger } from '../log/logger'
import type { MapData } from '../map/mapData'
import { useMapApi } from '../source/mapServices'
import type { Filters } from './mask'

const log = logger('filters')

/** A search filter on a map that grows: its hits cover the points it knew. Each time the map is
 *  read again, the search is asked again so the new points are judged too. */
export function useSearchRefresh(data: MapData, filters: Filters, setFilters: (update: (current: Filters) => Filters) => void): void {
  const api = useMapApi()
  const latest = useRef(filters)

  useEffect(() => {
    latest.current = filters
  })

  useEffect(() => {
    const query = latest.current.search?.query
    if (!data.live || query === undefined) return undefined
    const abort = new AbortController()
    api
      .searchText(query, abort.signal)
      .then((answer) => {
        // The server may already hold more points than the map on screen: indices are stable,
        // so the answer is cut to the points shown.
        if (answer.length < data.n) return
        const hits = answer.length === data.n ? answer : answer.slice(0, data.n)
        setFilters((current) => (current.search?.query === query ? { ...current, search: { query, hits } } : current))
      })
      .catch((error: unknown) => {
        if (!abort.signal.aborted) log.warn('the search filter could not be refreshed', error)
      })
    return () => abort.abort()
  }, [api, data, setFilters])
}
