import { Check } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Technique } from '../api/reviewSchema'
import { ReviewWorth } from './ReviewWorth'

interface TechniqueRowProps {
  technique: Technique
  /** Number of its quote in the text of the item; null when the text does not hold the quote. */
  number: number | null
  /** Its quote is the one brought out in the text. */
  active: boolean
  /** A probe flagged the item for this same technique, and the review confirmed the flag. */
  flagged: boolean
  /** The review has its evaluation: a technique without a figure of its own says so. */
  measured: boolean
  /** Brings a quote out in the text, or none. */
  onActive(number: number | null): void
}

/** A technique the review names: what it is called, how the post uses it, and the number of
 *  the words it leans on, marked in the text above. When a probe had flagged it too, the row
 *  says so once, in place of a second row about the probe. */
export function TechniqueRow({ technique, number, active, flagged, measured, onActive }: TechniqueRowProps): ReactElement {
  return (
    <div
      className={`nm-technique${active ? ' is-active' : ''}`}
      role="group"
      aria-label={`Technique: ${technique.name}`}
      onPointerEnter={() => onActive(number)}
      onPointerLeave={() => onActive(null)}
    >
      <p className="nm-technique__head">
        {number !== null ? (
          <span className="nm-quote-ref nm-quote-ref--row" title="Its words are marked with this number in the text">
            {number}
          </span>
        ) : null}
        <span className="nm-technique__name">{technique.name}</span>
      </p>
      {flagged ? (
        <p className="nm-technique__flagged">
          <Check size={11} aria-hidden />
          Flagged by the probe, confirmed by the review
        </p>
      ) : null}
      <p className="nm-technique__says">{technique.explanation}</p>
      {number === null ? <blockquote className="nm-review__quote">“{technique.quote}”</blockquote> : null}
      <ReviewWorth measure={technique.reliability} measured={measured} />
    </div>
  )
}
