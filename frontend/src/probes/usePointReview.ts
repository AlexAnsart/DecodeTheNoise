import { useCallback, useSyncExternalStore } from 'react'
import type { Review } from '../api/reviewSchema'
import { useReviewStore } from '../source/mapServices'
import type { ReviewAsk } from './reviewStore'

export interface PointReview {
  /** The review to show, when there is one: the one asked from this page, else the one the
   *  map stores with the item. */
  review: Review | null
  /** What became of the review asked from this page: running, refused, or not asked. */
  ask: ReviewAsk
  /** Has the LLM review the point now. */
  run(): void
}

/** The LLM review of one point. `stored` is the review that came with its reading, if any. */
export function usePointReview(index: number, stored: Review | null): PointReview {
  const store = useReviewStore()
  const ask = useSyncExternalStore(store.subscribe, () => store.state(index))
  const run = useCallback(() => store.ask(index), [store, index])
  const kept = stored && stored.status !== 'none' ? stored : null
  return { review: ask.status === 'done' ? ask.review : kept, ask, run }
}
