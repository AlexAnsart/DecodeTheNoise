/* The reviews asked from this page, one map at a time. A review takes seconds and is limited:
   it goes on when its card closes, and its answer is there when the card opens again. */

import type { MapApi } from '../api/client'
import type { Review } from '../api/reviewSchema'
import { logger } from '../log/logger'
import { refusalWords } from './reviewWords'

const log = logger('review')
const KEPT = 200

/** What became of the review asked for one point. */
export type ReviewAsk =
  | { status: 'idle' }
  | { status: 'running' }
  | { status: 'done'; review: Review }
  /** The server said no, or did not answer: the sentence says why. */
  | { status: 'refused'; message: string }

const IDLE: ReviewAsk = { status: 'idle' }
const RUNNING: ReviewAsk = { status: 'running' }

export interface ReviewStore {
  state(index: number): ReviewAsk
  /** Has the LLM review the point now. A point already being reviewed is not asked twice. */
  ask(index: number): void
  /** Calls `listener` when the state of a point changes. Returns the way to stop. */
  subscribe(listener: () => void): () => void
}

export function createReviewStore(api: MapApi): ReviewStore {
  const asked = new Map<number, ReviewAsk>()
  const listeners = new Set<() => void>()

  const set = (index: number, state: ReviewAsk): void => {
    asked.delete(index)
    asked.set(index, state)
    if (asked.size > KEPT) {
      // The oldest answer goes; a review still running is never dropped.
      for (const [old, kept] of asked) {
        if (kept.status === 'running') continue
        asked.delete(old)
        break
      }
    }
    listeners.forEach((notify) => notify())
  }

  return {
    state: (index) => asked.get(index) ?? IDLE,
    ask(index) {
      if (asked.get(index)?.status === 'running') return
      set(index, RUNNING)
      api
        .review(index)
        .then((review) => set(index, { status: 'done', review }))
        .catch((error: unknown) => {
          log.warn('a review could not be made', error)
          set(index, { status: 'refused', message: refusalWords(error) })
        })
    },
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
