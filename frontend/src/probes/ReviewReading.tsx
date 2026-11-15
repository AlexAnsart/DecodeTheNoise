import type { ReactElement } from 'react'
import type { Review } from '../api/reviewSchema'
import type { ProbeInfo } from '../api/schema'
import type { PlacedQuotes } from '../items/quotes'
import { FindingRow } from './FindingRow'
import { VOICE_LINE, overallWords, pinnedWords } from './reviewWords'
import { TechniqueRow } from './TechniqueRow'

interface ReviewReadingProps {
  /** A review that completed. */
  review: Review
  /** The probes of the map, to name the one a finding is about. */
  probes: ProbeInfo[]
  /** Where the quotes of the review sit in the text of the item: each row carries its number. */
  marks: PlacedQuotes | null
  active: number | null
  onActive(number: number | null): void
}

/** What the review read in one post: the techniques it names, what it says of the other labels
 *  a probe flagged, whose voice the post is in, what it asks and whom it targets. Then what
 *  the reading is worth, and what made it. */
export function ReviewReading({ review, probes, marks, active, onActive }: ReviewReadingProps): ReactElement {
  const voice = review.voice ? VOICE_LINE[review.voice] : null
  const pinned = pinnedWords(review.model, review.prompt_version)
  const row = (quote: string | null): { number: number | null; active: boolean; onActive(number: number | null): void } => {
    const number = quote && marks ? marks.numberOf(quote) : null
    return { number, active: number !== null && number === active, onActive }
  }
  // A technique a probe had flagged and the review confirmed is said once, in its technique
  // row: its finding is not shown a second time.
  const named = new Set(review.techniques.map((technique) => technique.key))
  const confirmed = new Set(review.findings.filter((finding) => finding.reading === 'supported').map((finding) => finding.probe))
  const findings = review.findings.filter((finding) => !(finding.reading === 'supported' && named.has(finding.probe)))

  return (
    <>
      <p className="nm-review__label">Techniques named</p>
      {review.techniques.length === 0 ? <p className="nm-verdicts__note">The review names no manipulation technique in this post.</p> : null}
      {review.techniques.map((technique) => (
        <TechniqueRow
          key={`${technique.key}:${technique.quote}`}
          technique={technique}
          flagged={confirmed.has(technique.key)}
          measured={review.measured}
          {...row(technique.quote)}
        />
      ))}
      {review.measured && review.overall ? (
        <p className="nm-review__measure">
          {overallWords(review.overall)}{' '}
          <a className="nm-link" href="/method#review">
            How it is measured
          </a>
        </p>
      ) : null}
      {findings.length > 0 ? <p className="nm-review__label">Flagged by a probe</p> : null}
      {findings.map((finding) => (
        <FindingRow
          key={finding.probe}
          finding={finding}
          label={finding.label || (probes.find((probe) => probe.key === finding.probe)?.label ?? finding.probe)}
          {...row(finding.quote)}
        />
      ))}
      {voice ? (
        <p className="nm-review__line">
          <span className="nm-review__key">{voice.word}</span> {voice.says}
        </p>
      ) : null}
      {review.asks ? (
        <p className="nm-review__line">
          <span className="nm-review__key">Asks the reader</span> “{review.asks}”
        </p>
      ) : null}
      {review.target ? (
        <p className="nm-review__line">
          <span className="nm-review__key">Aimed at</span> “{review.target}”
        </p>
      ) : null}
      {review.measured ? null : <p className="nm-review__limit">LLM reading, not measured yet.</p>}
      {pinned ? <p className="nm-review__pinned">{pinned}</p> : null}
    </>
  )
}
