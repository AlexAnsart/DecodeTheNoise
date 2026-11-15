import type { ReactElement } from 'react'
import type { ReviewReport } from '../../api/reviewReportSchema'
import { formatCount } from '../../text/format'
import { formatRate } from '../figures'
import { readable } from '../words'
import { OWN_FIGURE_FROM, known, ownFigures, rateWords } from './evaluation'

const list = new Intl.ListFormat('en-GB', { type: 'conjunction' })

interface ShownFigureProps {
  report: ReviewReport
  /** The name the review gives a technique, by its key. */
  names: Map<string, string>
}

/** Which measured figure the product puts beside a technique the review names: the rule, and
 *  the figures it leads to today. */
export function ShownFigure({ report, names }: ShownFigureProps): ReactElement {
  const { pooled } = report
  const own = ownFigures(report).map(([name, precision]) => `${names.get(name) ?? readable(name)} (${formatRate(precision.value)})`)
  const named = known(pooled?.tp) && known(pooled?.fp) ? `, on ${formatCount(pooled.tp + pooled.fp)} techniques named` : ''
  return (
    <>
      <p className="nm-num">
        Beside a technique it names, the product shows the precision of that technique alone only when the review named it on at least{' '}
        {OWN_FIGURE_FROM} posts of this evaluation: today {own.length > 0 ? list.format(own) : 'no technique does'}. Beside any other technique it
        shows the figure of every measurable technique taken together
        {pooled
          ? `: precision ${rateWords(pooled.precision)}, recall ${rateWords(pooled.recall)}, false-positive rate ${rateWords(pooled.fpr)}${named}.`
          : ', which this report does not hold yet.'}
      </p>
      {pooled?.agreement && pooled.agreement_without_review ? (
        <p className="nm-note nm-num">
          On those techniques the review answers like the annotation on {formatRate(pooled.agreement.value)} of the pairs of a post and a technique.
          Naming nothing at all would agree on {formatRate(pooled.agreement_without_review.value)}, because most posts show no technique: the
          precision and the recall are the figures to read.
        </p>
      ) : null}
    </>
  )
}
