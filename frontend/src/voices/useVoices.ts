/* The "one voice, or several?" check of one selection: asked by a click, forgotten when the
   selection changes. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { describeError } from '../api/useRequest'
import type { Voices } from '../api/voicesSchema'
import { logger } from '../log/logger'
import { useMapApi } from '../source/mapServices'

const log = logger('voices')

/** The most points the route reads in one call. */
export const MAX_ITEMS = 5000

export type VoicesState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: Voices }
  | { status: 'error'; message: string }

export interface VoicesCheckState {
  state: VoicesState
  /** How many of the selected items are sent: fewer than the selection when it is very large. */
  sent: number
  check(): void
}

const IDLE: VoicesState = { status: 'idle' }

/** At most `MAX_ITEMS` indices, taken evenly across the selection. */
function evenly(indices: Uint32Array): number[] {
  if (indices.length <= MAX_ITEMS) return Array.from(indices)
  const step = indices.length / MAX_ITEMS
  return Array.from({ length: MAX_ITEMS }, (_, i) => indices[Math.floor(i * step)])
}

export function useVoices(indices: Uint32Array): VoicesCheckState {
  const api = useMapApi()
  // The state belongs to one selection: another selection starts from idle.
  const [held, setHeld] = useState<{ of: Uint32Array; state: VoicesState }>({ of: indices, state: IDLE })
  const pending = useRef<AbortController | null>(null)

  // A request still running when the selection changes, or the block closes, is let go.
  useEffect(() => () => pending.current?.abort(), [indices])

  const check = useCallback((): void => {
    pending.current?.abort()
    const abort = new AbortController()
    pending.current = abort
    setHeld({ of: indices, state: { status: 'loading' } })
    api
      .voices(evenly(indices), abort.signal)
      .then((data) => {
        if (!abort.signal.aborted) setHeld({ of: indices, state: { status: 'ready', data } })
      })
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.error('the voices check failed', error)
        setHeld({ of: indices, state: { status: 'error', message: describeError(error) } })
      })
  }, [api, indices])

  return { state: held.of === indices ? held.state : IDLE, sent: Math.min(indices.length, MAX_ITEMS), check }
}
