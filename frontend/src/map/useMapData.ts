import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import type { MapApi } from '../api/client'
import { logger } from '../log/logger'
import type { MapData } from './mapData'
import { decodeMap, emptyMap } from './mapData'
import { painted } from './painted'

const log = logger('map')
/** A live map is read again at most this often, however fast its version moves. */
const MIN_SPACING_MS = 700
/** After a failed read of a map already on screen, the wait before trying again, and how often. */
const RETRY_MS = 4000
const MAX_RETRIES = 3

/** How far the first read of a map is. */
export interface MapProgress {
  /** Points of the map being read. */
  points: number
  /** Share of its bytes received, 0 to 1. Null where the browser gives nothing to count. */
  share: number | null
}

export type MapLoad =
  /** `progress` is null until the manifest has said what the map holds. */
  | { status: 'loading'; progress: MapProgress | null }
  /** `stale` says why the map on screen could not be read again, when it could not. */
  | { status: 'ready'; data: MapData; stale: string | null }
  | { status: 'error'; message: string }

const LOADING: MapLoad = { status: 'loading', progress: null }
/** The bar moves by hundredths: the page is not rendered again for every chunk received. */
const PROGRESS_STEP = 0.01

function explain(error: unknown): string {
  if (error instanceof ApiError && error.status === 503) return error.message
  if (error instanceof ApiError && error.status === 401) return 'This workspace key is not known to the server any more.'
  if (error instanceof ApiError) return `The server answered ${error.status}: ${error.message}`
  return 'The map could not be read from the server.'
}

/** `report` is given for the first read of a map only: a map already on screen stays there
 *  while it is read again, with nothing to show of the wait. */
async function readMap(api: MapApi, report: ((progress: MapProgress) => void) | null): Promise<MapData> {
  const manifest = await api.manifest()
  if (manifest.n === 0) return emptyMap(manifest)
  if (!report) return decodeMap(manifest, await api.buffers(manifest))
  const points = manifest.n
  report({ points, share: null })
  let reported = -1
  const buffers = await api.buffers(manifest, undefined, (received, total) => {
    const share = total > 0 ? received / total : 1
    if (share < 1 && share - reported < PROGRESS_STEP) return
    reported = share
    report({ points, share })
  })
  return decodeMap(manifest, buffers)
}

/** Reads the manifest, then the one binary file of typed arrays. `version` is the version a
 *  live map is known to have reached: when it moves, the map is read again, one read at a
 *  time, and the map on screen stays until the next one has arrived. */
export function useMapData(api: MapApi, version?: number): MapLoad {
  // What was read belongs to one source: after a change of source, nothing of the previous map
  // is shown, not even for one render.
  const [held, setHeld] = useState<{ api: MapApi; load: MapLoad }>({ api, load: LOADING })
  const reach = useRef<(version: number) => void>(() => undefined)

  useEffect(() => {
    let current = true
    let running = false
    let timer: ReturnType<typeof setTimeout> | null = null
    let startedAt = 0
    let failures = 0
    let shown: number | null = null
    let wanted: number | null = null

    const plan = (wait: number): void => {
      if (running || timer !== null || !current) return
      timer = setTimeout(() => {
        timer = null
        void read()
      }, wait)
    }
    const read = async (): Promise<void> => {
      running = true
      startedAt = performance.now()
      const asked = wanted
      try {
        const report = (progress: MapProgress): void => {
          if (current) setHeld({ api, load: { status: 'loading', progress } })
        }
        const first = shown === null
        const data = await readMap(api, first ? report : null)
        // A large map takes a moment to draw: the page shows that all of it has arrived first.
        if (first) await painted()
        if (!current) return
        shown = data.version
        failures = 0
        setHeld({ api, load: { status: 'ready', data, stale: null } })
      } catch (error) {
        if (!current) return
        log.error('the map could not be loaded', error)
        failures += 1
        setHeld((previous) => ({
          api,
          load:
            previous.api === api && previous.load.status === 'ready'
              ? { ...previous.load, stale: `The map could not be refreshed. ${explain(error)}` }
              : { status: 'error', message: explain(error) },
        }))
      } finally {
        running = false
      }
      // The version moved while this read was running, or the read failed: read again.
      if (failures > 0 && failures <= MAX_RETRIES && shown !== null) plan(RETRY_MS)
      else if (failures === 0 && wanted !== null && wanted !== asked && wanted !== shown) plan(MIN_SPACING_MS)
    }

    reach.current = (next) => {
      wanted = next
      if (next !== shown) plan(Math.max(0, MIN_SPACING_MS - (performance.now() - startedAt)))
    }
    void read()
    return () => {
      current = false
      if (timer !== null) clearTimeout(timer)
      reach.current = () => undefined
    }
  }, [api])

  useEffect(() => {
    if (version !== undefined) reach.current(version)
  }, [version, api])

  return held.api === api ? held.load : LOADING
}
