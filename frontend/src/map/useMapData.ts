import { useEffect, useState } from 'react'
import { ApiError, fetchBuffers, fetchManifest } from '../api/client'
import { logger } from '../log/logger'
import type { MapData } from './mapData'
import { decodeMap } from './mapData'

const log = logger('map')

export type MapLoad =
  | { status: 'loading' }
  | { status: 'ready'; data: MapData }
  | { status: 'error'; message: string }

function explain(error: unknown): string {
  if (error instanceof ApiError && error.status === 503) return error.message
  if (error instanceof ApiError) return `The server answered ${error.status}: ${error.message}`
  return 'The map could not be read from the server.'
}

/** Reads the manifest, then the one binary file of typed arrays. */
export function useMapData(): MapLoad {
  const [load, setLoad] = useState<MapLoad>({ status: 'loading' })

  useEffect(() => {
    let current = true
    fetchManifest()
      .then(async (manifest) => decodeMap(manifest, await fetchBuffers(manifest.build)))
      .then((data) => {
        if (current) setLoad({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        log.error('the map could not be loaded', error)
        if (current) setLoad({ status: 'error', message: explain(error) })
      })
    return () => {
      current = false
    }
  }, [])

  return load
}
