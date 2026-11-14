/* The swarm layer is optional: a map packed without it, or a detector without its evaluation
   report, simply has none. */

import { useEffect, useState } from 'react'
import { fetchSwarm, fetchSwarmLayer } from '../api/client'
import type { Swarm, SwarmLayer } from '../api/schema'
import { logger } from '../log/logger'

const log = logger('swarms')

export function useSwarmLayer(): SwarmLayer | null {
  const [layer, setLayer] = useState<SwarmLayer | null>(null)

  useEffect(() => {
    let current = true
    fetchSwarmLayer()
      .then((found) => {
        if (current) setLayer(found)
      })
      .catch((error: unknown) => log.error('the swarm layer could not be read', error))
    return () => {
      current = false
    }
  }, [])

  return layer
}

export type SwarmLoad = { status: 'loading' } | { status: 'ready'; swarm: Swarm } | { status: 'error' }

/** One swarm with its evidence, read when its panel opens. */
export function useSwarm(id: number): SwarmLoad {
  const [load, setLoad] = useState<{ id: number; state: SwarmLoad }>({ id, state: { status: 'loading' } })

  useEffect(() => {
    const abort = new AbortController()
    fetchSwarm(id, abort.signal)
      .then((swarm) => setLoad({ id, state: { status: 'ready', swarm } }))
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.error('the swarm could not be read', error)
        setLoad({ id, state: { status: 'error' } })
      })
    return () => abort.abort()
  }, [id])

  // What was read for another swarm is not shown for this one.
  return load.id === id ? load.state : { status: 'loading' }
}
