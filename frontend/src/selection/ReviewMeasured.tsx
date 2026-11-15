import { useState } from 'react'
import type { ReactElement } from 'react'
import type { SelectionReview } from '../api/reviewSchema'
import { formatCount, plural } from '../text/format'
import { THIN_COUNT, percent, ratioWords, standingOut } from './reviewNumbers'

/** Rows shown before the rest goes behind "more". */
const FIRST_ROWS = 5

interface ReviewMeasuredProps {
  review: SelectionReview
  /** Items of the selection, and how many of them were sent to the review. */
  selected: number
  sent: number
}

/** What is measured on a selection, with no LLM: its posts, its actors, and the probes that
 *  flag it more often than the rest of the map, strongest first. */
export function ReviewMeasured({ review, selected, sent }: ReviewMeasuredProps): ReactElement {
  const [all, setAll] = useState(false)
  const rows = standingOut(review.rates)
  const shown = all ? rows : rows.slice(0, FIRST_ROWS)

  return (
    <section className="nm-sreview__part" aria-label="Measured by the probes">
      <p className="nm-sreview__label">Measured by the probes</p>
      <p>
        <b className="nm-num">{formatCount(review.posts)}</b> {review.posts === 1 ? 'post' : 'posts'} by{' '}
        <b className="nm-num">{formatCount(review.actors)}</b> {review.actors === 1 ? 'actor' : 'actors'}.
      </p>
      {sent < selected ? (
        <p className="nm-sreview__fine">
          The review took {formatCount(sent)} of the {formatCount(selected)} selected items, evenly.
        </p>
      ) : null}
      {rows.length === 0 ? (
        <p>{review.rates.length === 0 ? 'No probe is read on this map.' : 'No probe flags these posts more often than the rest of the map.'}</p>
      ) : (
        <table className="nm-rates">
          <thead>
            <tr>
              <th scope="col">Flagged more here</th>
              <th scope="col">Here</th>
              <th scope="col">Elsewhere</th>
              <th scope="col">Ratio</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((rate) => (
              <tr key={rate.key}>
                <th scope="row">
                  {rate.label}
                  <span className="nm-rates__count">{plural(rate.flagged, 'post', 'posts')}</span>
                </th>
                <td className="nm-num">{percent(rate.rate)}</td>
                <td className="nm-num">{percent(rate.elsewhere)}</td>
                <td className="nm-num nm-rates__ratio">{ratioWords(rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {rows.length > FIRST_ROWS ? (
        <button type="button" className="nm-sreview__more" onClick={() => setAll((value) => !value)} aria-expanded={all}>
          {all ? 'Show fewer' : `Show ${rows.length - FIRST_ROWS} more`}
        </button>
      ) : null}
      {rows.length > 0 ? (
        <p className="nm-sreview__fine">
          Share of the posts each probe flags, here and in the rest of the map. Counted by the probes: no LLM is involved.
          {rows.some((rate) => rate.flagged < THIN_COUNT) ? ' A ratio counted on one or two posts says little: those rows come last.' : ''}
        </p>
      ) : null}
    </section>
  )
}
