import { LoaderCircle, Sparkles } from 'lucide-react'
import type { ReactElement } from 'react'
import type { ProbeInfo } from '../api/schema'
import type { PlacedQuotes } from '../items/quotes'
import { ReviewReading } from './ReviewReading'
import type { PointReview } from './usePointReview'
import './review.css'

interface ReviewBlockProps {
  point: PointReview
  probes: ProbeInfo[]
  /** Where the quotes of the review sit in the text of the item. */
  marks: PlacedQuotes | null
  active: number | null
  onActive(number: number | null): void
}

/** `reading`: a review that completed. `fresh`: none was ever made for this post. */
type Shown = 'running' | 'reading' | 'refused' | 'queued' | 'skipped' | 'failed' | 'empty' | 'fresh'

function shownOf({ review, ask }: PointReview): Shown {
  if (ask.status === 'running') return 'running'
  if (ask.status === 'refused') return 'refused'
  if (!review) return 'fresh'
  if (review.status === 'done') return 'reading'
  return review.status === 'none' ? 'empty' : review.status
}

/** The LLM review of one item, in its card. A quiet button asks for it; while it runs, it says
 *  so; a refusal is a sentence. Then the reading, with its uncertainty left visible. */
export function ReviewBlock({ point, probes, marks, active, onActive }: ReviewBlockProps): ReactElement {
  const { review, ask, run } = point
  const shown = shownOf(point)
  const canAsk = shown !== 'running' && shown !== 'reading' && shown !== 'queued'

  return (
    <section className="nm-review" aria-label="LLM review">
      <p className="nm-verdicts__title">LLM review</p>
      {shown === 'running' ? (
        <p className="nm-review__busy" role="status">
          <LoaderCircle size={13} className="nm-spin" aria-hidden />
          Reading the post again with its neighbours. A few seconds…
        </p>
      ) : null}
      {shown === 'reading' && review ? <ReviewReading review={review} probes={probes} marks={marks} active={active} onActive={onActive} /> : null}
      {shown === 'queued' ? <p className="nm-verdicts__note">Waiting: this post will be read again with its context.</p> : null}
      {shown === 'skipped' ? <p className="nm-verdicts__note">The review was skipped. {review?.reason}</p> : null}
      {shown === 'failed' ? (
        <p className="nm-verdicts__note nm-verdicts__note--error" role="alert">
          The review did not complete. {review?.reason}
        </p>
      ) : null}
      {shown === 'empty' ? <p className="nm-verdicts__note">The review had nothing to read in this post.</p> : null}
      {shown === 'refused' && ask.status === 'refused' ? (
        <p className="nm-verdicts__note nm-verdicts__note--error" role="alert">
          {ask.message}
        </p>
      ) : null}
      {shown === 'fresh' ? (
        <p className="nm-verdicts__note">Reads the post again with its neighbours, names the techniques it uses and quotes them.</p>
      ) : null}
      {canAsk ? (
        <button type="button" className="nm-btn-secondary nm-btn-small nm-review__ask" onClick={run}>
          <Sparkles size={12} aria-hidden />
          {shown === 'fresh' ? 'Review with the LLM' : 'Try again'}
        </button>
      ) : null}
    </section>
  )
}
