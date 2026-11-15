import type { ReactElement } from 'react'
import type { ReviewCascade } from '../../api/reviewReportSchema'
import { formatCount } from '../../text/format'
import { readable } from '../words'
import { counted, known } from './evaluation'
import { RateCell } from './RateCell'

/** What the report says of the posts the cascade was measured on. */
function setting(cascade: ReviewCascade): string {
  const flagged = known(cascade.posts_flagged) ? formatCount(cascade.posts_flagged) : 'Some'
  const posts = known(cascade.posts) ? ` of the ${formatCount(cascade.posts)} posts` : ' of the posts'
  const read = known(cascade.posts_read) ? `The review read ${formatCount(cascade.posts_read)} of them, drawn at random` : 'The review read a random draw of them'
  const pack = cascade.pack_run ? ` (probes of run ${cascade.pack_run})` : ''
  return `${flagged}${posts} are flagged by at least one technique probe at its lowest level${pack}. ${read}, as the product sends them: the probes that flagged the post are listed, and the review answers each. "Kept" means it answered "supported" for that probe.`
}

/** The same, for the cascade measured on every test post read by score band. */
function bandSetting(cascade: ReviewCascade): string {
  const read = known(cascade.posts_read) ? formatCount(cascade.posts_read) : 'The'
  const pack = cascade.pack_run ? ` (probes of run ${cascade.pack_run})` : ''
  return `${read} test posts that a technique probe flags at its lowest level${pack}, each with a settled answer: those of the random sample, and those the probe campaign drew inside each band of the probe's scores. Each band counts for the test posts it holds, so the rates are those of every test post counted in the second column, not only of the posts read. A probe marked "highest scores only" has no level and was read at the top of its scores alone: its figures are those of that top, since the posts under it were hardly read. The review read them as the product sends them: the probes that flagged the post are listed, and the review answers each. "Kept" means it answered "supported" for that probe.`
}

interface CascadeTableProps {
  cascade: ReviewCascade
  /** The name the review gives a technique, by its key. */
  names: Map<string, string>
}

/** A probe, then the review on what it flagged: the precision after the probe alone, and the
 *  precision of what the review keeps. */
export function CascadeTable({ cascade, names }: CascadeTableProps): ReactElement {
  const lines = Object.entries(cascade.probes)
  const banded = cascade.design === 'bands'
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-num nm-review-eval">
        <caption>{banded ? bandSetting(cascade) : setting(cascade)}</caption>
        <thead>
          <tr>
            <th scope="col">Probe</th>
            <th scope="col">{banded ? 'Test posts measured' : 'Flagged by the probe'}</th>
            <th scope="col">{banded ? 'Of them, read' : 'Of them, a yes'}</th>
            <th scope="col">Precision after the probe alone</th>
            {banded ? null : <th scope="col">Read by the review</th>}
            <th scope="col">Kept</th>
            <th scope="col">Of them, a yes</th>
            <th scope="col">Precision after the review</th>
            {banded ? <th scope="col">True positives kept</th> : null}
          </tr>
        </thead>
        <tbody>
          {lines.map(([name, probe]) => (
            <tr key={name}>
              <th scope="row">
                {names.get(name) ?? readable(name)}
                <code>{name}</code>
                {probe.scope === 'head' ? <span className="nm-note">highest scores only</span> : null}
              </th>
              <td>{counted(banded ? probe.flagged_in_split : probe.flagged)}</td>
              <td>{counted(banded ? probe.read : probe.flagged_yes)}</td>
              <RateCell rate={probe.after_probe} none={banded ? 'a band was not read' : undefined} />
              {banded ? null : <td>{counted(probe.read)}</td>}
              <td>{counted(probe.kept)}</td>
              <td>{counted(probe.kept_yes)}</td>
              <RateCell rate={probe.after_review} none={banded ? 'a band was not read' : undefined} />
              {banded ? <RateCell rate={probe.true_positives_kept} none="a band was not read" /> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
