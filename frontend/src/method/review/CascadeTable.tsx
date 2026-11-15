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

interface CascadeTableProps {
  cascade: ReviewCascade
  /** The name the review gives a technique, by its key. */
  names: Map<string, string>
}

/** A probe, then the review on what it flagged: the precision after the probe alone, and the
 *  precision of what the review keeps. */
export function CascadeTable({ cascade, names }: CascadeTableProps): ReactElement {
  const lines = Object.entries(cascade.probes)
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-num nm-review-eval">
        <caption>{setting(cascade)}</caption>
        <thead>
          <tr>
            <th scope="col">Probe</th>
            <th scope="col">Flagged by the probe</th>
            <th scope="col">Of them, a yes</th>
            <th scope="col">Precision after the probe alone</th>
            <th scope="col">Read by the review</th>
            <th scope="col">Kept</th>
            <th scope="col">Of them, a yes</th>
            <th scope="col">Precision after the review</th>
          </tr>
        </thead>
        <tbody>
          {lines.map(([name, probe]) => (
            <tr key={name}>
              <th scope="row">
                {names.get(name) ?? readable(name)}
                <code>{name}</code>
              </th>
              <td>{counted(probe.flagged)}</td>
              <td>{counted(probe.flagged_yes)}</td>
              <RateCell rate={probe.after_probe} />
              <td>{counted(probe.read)}</td>
              <td>{counted(probe.kept)}</td>
              <td>{counted(probe.kept_yes)}</td>
              <RateCell rate={probe.after_review} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
