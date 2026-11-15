/* The review of one selection: asked by a click, slow, and forgotten when the selection changes.
   It is held above the list of the selection, so closing the list neither stops nor loses it. */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { SelectionReview } from '../api/reviewSchema'
import { logger } from '../log/logger'
import { refusalWords } from '../probes/reviewWords'
import { useMapApi } from '../source/mapServices'
import { MAX_REVIEWED, evenly } from './reviewNumbers'

const log = logger('review')

export type SelectionReviewState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: SelectionReview }
  /** The server said no, or did not answer: the sentence says why. */
  | { status: 'error'; message: string }

export interface SelectionReviewRun {
  state: SelectionReviewState
  /** How many of the selected items are sent: fewer than the selection when it is very large. */
  sent: number
  run(): void
}

const IDLE: SelectionReviewState = { status: 'idle' }

/** `indices` is the selection, null when there is none. */
export function useSelectionReview(indices: Uint32Array | null): SelectionReviewRun {
  const api = useMapApi()
  // The state belongs to one selection: another selection starts from idle.
  const [held, setHeld] = useState<{ of: Uint32Array | null; state: SelectionReviewState }>({ of: indices, state: IDLE })
  const pending = useRef<AbortController | null>(null)

  // A request still running when the selection changes, or the map closes, is let go.
  useEffect(() => () => pending.current?.abort(), [indices])

  const run = useCallback((): void => {
    if (!indices) return
    pending.current?.abort()
    const abort = new AbortController()
    pending.current = abort
    setHeld({ of: indices, state: { status: 'loading' } })
    api
      .reviewSelection(evenly(indices, MAX_REVIEWED), abort.signal)
      .then((data) => {
        if (!abort.signal.aborted) setHeld({ of: indices, state: { status: 'ready', data } })
      })
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.warn('the review of a selection could not be made', error)
        setHeld({ of: indices, state: { status: 'error', message: refusalWords(error) } })
      })
  }, [api, indices])

  return { state: held.of === indices ? held.state : IDLE, sent: Math.min(indices?.length ?? 0, MAX_REVIEWED), run }
}
