import type { ReactElement } from 'react'
import type { Finding, ProbeInfo, Review } from '../api/schema'

const READING_WORD: Record<Finding['reading'], string> = {
  supported: 'Supported',
  'not supported': 'Not supported',
  unclear: 'Unclear',
}

interface ReviewBlockProps {
  /** A review that exists: queued, done, skipped or failed. */
  review: Review
  /** The probes of the map, to name the one a finding is about. */
  probes: ProbeInfo[]
}

function labelOf(probes: ProbeInfo[], key: string): string {
  return probes.find((probe) => probe.key === key)?.label ?? key
}

/** The LLM review of a flagged item: it read the item again with its context, and says for
 *  each probe whether the text supports the flag, with the words it leans on. */
export function ReviewBlock({ review, probes }: ReviewBlockProps): ReactElement {
  const pinned = review.model ? `${review.model}${review.prompt_version ? `, prompt ${review.prompt_version}` : ''}` : undefined
  return (
    <div className="nm-review">
      <p className="nm-review__head" title={pinned}>
        LLM review
      </p>
      {review.status === 'queued' ? <p className="nm-verdicts__note">Waiting: the item will be read again with its context.</p> : null}
      {review.status === 'skipped' ? <p className="nm-verdicts__note">Skipped. {review.reason}</p> : null}
      {review.status === 'failed' ? <p className="nm-verdicts__note nm-verdicts__note--error">It did not complete. {review.reason}</p> : null}
      {review.status === 'done' && review.findings.length === 0 ? <p className="nm-verdicts__note">The review returned no finding.</p> : null}
      {review.status === 'done'
        ? review.findings.map((finding) => (
            <div key={finding.probe}>
              <p className="nm-review__finding">
                <span className={`nm-review__reading nm-review__reading--${finding.reading.replace(' ', '-')}`}>{READING_WORD[finding.reading]}</span>
                {' · '}
                {labelOf(probes, finding.probe)}. {finding.explanation}
              </p>
              {finding.quote ? <blockquote className="nm-review__quote">“{finding.quote}”</blockquote> : null}
            </div>
          ))
        : null}
      {review.status === 'done' && !review.measured ? <p className="nm-review__limit">LLM reading, not measured yet.</p> : null}
    </div>
  )
}
