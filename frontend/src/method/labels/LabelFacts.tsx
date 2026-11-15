import type { ReactElement } from 'react'
import type { Agreement, Prevalence } from '../../api/reportSchema'
import { formatCount } from '../../text/format'
import { formatInterval, formatRate, formatScore } from '../figures'
import { disagreed } from '../probeFiles'

interface LabelFactsProps {
  agreement: Agreement | null
  prevalence: Prevalence | null
}

const known = (value: number | null | undefined): value is number => value !== null && value !== undefined

function AgreementLine({ agreement }: { agreement: Agreement }): ReactElement {
  const posts = known(agreement.n) ? `${formatCount(agreement.n)} posts read twice` : 'Posts read twice'
  const yes =
    known(agreement.yes_a) && known(agreement.yes_b)
      ? `${formatCount(agreement.yes_a)} and ${formatCount(agreement.yes_b)} yes answers${known(agreement.both_yes) ? `, ${formatCount(agreement.both_yes)} in common` : ''}`
      : null
  if (!known(agreement.kappa)) {
    return (
      <li>
        <strong>Agreement between two annotators.</strong> {posts}
        {yes ? ` (${yes})` : ''}: no kappa can be computed without a yes on each side.
      </li>
    )
  }
  return (
    <li>
      <strong>Agreement between two annotators.</strong> {posts}: kappa {formatScore(agreement.kappa)}
      {yes ? ` (${yes})` : ''}.
      {disagreed(agreement) ? ' The annotators themselves disagree on this label, so no reliability is shown for it.' : ''}
    </li>
  )
}

/** What the campaign measured about a label before any probe: how far two annotators agree on
 *  it, and how frequent it is. */
export function LabelFacts({ agreement, prevalence }: LabelFactsProps): ReactElement | null {
  if (!agreement && !prevalence) return null
  return (
    <ul className="nm-label-facts nm-num">
      {agreement ? <AgreementLine agreement={agreement} /> : null}
      {prevalence && known(prevalence.share) ? (
        <li>
          <strong>How frequent it is.</strong> {formatRate(prevalence.share)} of the posts drawn at random are a yes
          {known(prevalence.yes) && known(prevalence.decided) ? ` (${formatCount(prevalence.yes)} of ${formatCount(prevalence.decided)} decided)` : ''}
          {known(prevalence.low) && known(prevalence.high) ? `, 95% interval ${formatInterval(prevalence.low, prevalence.high)}` : ''}. Only posts drawn at
          random are a sample of the corpus: no other rate of this page says how frequent a label is.
        </li>
      ) : null}
    </ul>
  )
}
