import { Check, CircleQuestionMark, X } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Finding } from '../api/reviewSchema'
import { ReviewWorth } from './ReviewWorth'
import { READING_WORD } from './reviewWords'

interface FindingRowProps {
  finding: Finding
  /** The name of the label the finding is about. */
  label: string
  /** Number of its quote in the text of the item; null when it has none there. */
  number: number | null
  active: boolean
  onActive(number: number | null): void
}

const READING_ICON: Record<Finding['reading'], typeof Check> = {
  supported: Check,
  'not supported': X,
  unclear: CircleQuestionMark,
}

/** What the review says of one label a probe flagged: confirmed, not confirmed, or left
 *  unclear. Three states, each in its own words, and nothing beyond what was read: a figure
 *  appears only when the API gives one for a confirmed reading. */
export function FindingRow({ finding, label, number, active, onActive }: FindingRowProps): ReactElement {
  const Icon = READING_ICON[finding.reading]
  return (
    <div
      className={`nm-finding nm-finding--${finding.reading.replace(' ', '-')}${active ? ' is-active' : ''}`}
      role="group"
      aria-label={`${label}: ${READING_WORD[finding.reading]}`}
      onPointerEnter={() => onActive(number)}
      onPointerLeave={() => onActive(null)}
    >
      <p className="nm-finding__head">
        <span className="nm-finding__label">{label}</span>
        {number !== null ? (
          <span className="nm-quote-ref nm-quote-ref--row" title="Its words are marked with this number in the text">
            {number}
          </span>
        ) : null}
      </p>
      <p className="nm-finding__reading">
        <Icon size={12} aria-hidden />
        {READING_WORD[finding.reading]}
      </p>
      <p className="nm-technique__says">{finding.explanation}</p>
      {finding.quote && number === null ? <blockquote className="nm-review__quote">“{finding.quote}”</blockquote> : null}
      {finding.reading === 'supported' ? <ReviewWorth measure={finding.reliability} measured={false} /> : null}
    </div>
  )
}
