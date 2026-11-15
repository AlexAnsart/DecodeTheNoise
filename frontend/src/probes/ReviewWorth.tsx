import type { ReactElement } from 'react'
import type { ReviewMeasure } from '../api/reviewSchema'
import { figureWords } from './reviewWords'

interface ReviewWorthProps {
  /** How the review agreed with the annotation for this technique, when the API gives it. */
  measure: ReviewMeasure | null
  /** The review has its evaluation: a technique without a figure of its own then says so.
   *  Without an evaluation, one line under the review says it for every reading. */
  measured: boolean
}

/** What one technique named by the review is worth: its measured agreement with the
 *  annotation, with its interval, or the plain fact that it has no figure of its own. */
export function ReviewWorth({ measure, measured }: ReviewWorthProps): ReactElement | null {
  if (measure) return <p className="nm-review__measure">{figureWords(measure)}</p>
  return measured ? <p className="nm-review__measure">No figure of its own yet.</p> : null
}
