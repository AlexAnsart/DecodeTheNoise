import type { ReactElement } from 'react'
import type { SelectionReview } from '../api/reviewSchema'
import { formatCount } from '../text/format'
import { GroupTechnique } from './GroupTechnique'

interface ReviewReadProps {
  review: SelectionReview
  /** Opens a post on the map. */
  onOpen(index: number): void
}

const NOT_READ: Record<Exclude<SelectionReview['status'], 'done'>, string> = {
  none: 'The LLM had nothing to read in these posts.',
  queued: 'The LLM has not read these posts yet.',
  skipped: 'The LLM did not read these posts.',
  failed: 'The LLM reading did not complete.',
}

/** What the LLM read in a selection: how many posts, what they say, the techniques they use
 *  with the words that show them, what they ask and whom they target. */
export function ReviewRead({ review, onOpen }: ReviewReadProps): ReactElement {
  if (review.status !== 'done') {
    return (
      <section className="nm-sreview__part" aria-label="Read by the LLM">
        <p className="nm-sreview__label">Read by the LLM</p>
        <p className={review.status === 'failed' ? 'nm-sreview__error' : undefined} role={review.status === 'failed' ? 'alert' : undefined}>
          {NOT_READ[review.status]} {review.reason}
        </p>
      </section>
    )
  }
  const sample = review.read.length < review.posts
  return (
    <section className="nm-sreview__part" aria-label="Read by the LLM">
      <p className="nm-sreview__label">Read by the LLM</p>
      <p>
        It read <b className="nm-num">{formatCount(review.read.length)}</b> of the {formatCount(review.posts)} posts{sample ? ': a sample' : ''}.
      </p>
      {review.statement ? <p className="nm-sreview__statement">{review.statement}</p> : null}
      <p className="nm-sreview__sub">Techniques named</p>
      {review.techniques.length === 0 ? <p>The review names no manipulation technique that these posts share.</p> : null}
      {review.techniques.map((technique) => (
        <GroupTechnique key={technique.key} technique={technique} onOpen={onOpen} />
      ))}
      {review.asks ? (
        <p>
          <span className="nm-review__key">What the posts ask</span> {review.asks}
        </p>
      ) : null}
      {review.targets.length > 0 ? (
        <p>
          <span className="nm-review__key">Aimed at</span> {review.targets.map((target) => `“${target}”`).join(', ')}
        </p>
      ) : null}
    </section>
  )
}
