import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { ReviewDoc } from '../../api/methodSchema'
import type { ReviewReport } from '../../api/reviewReportSchema'
import { formatCount } from '../../text/format'
import { reportPath } from '../reports'
import { SourceLink } from '../SourceLink'
import { CascadeTable } from './CascadeTable'
import { known, setting } from './evaluation'
import { RunsAgreement } from './RunsAgreement'
import { ShownFigure } from './ShownFigure'
import { TechniqueTable } from './TechniqueTable'

/** What the answers of the review were, before any of them is compared. */
function Answers({ report }: { report: ReviewReport }): ReactElement | null {
  const { failed, rejected_quotes: rejected } = report
  if (!known(failed) && !known(rejected)) return null
  const asked = known(report.asked) ? ` of ${formatCount(report.asked)}` : ''
  return (
    <ul className="nm-label-facts nm-num">
      {known(failed) ? (
        <li>
          <strong>Answers that could not be read.</strong> {formatCount(failed)}
          {asked}. An answer that cannot be read is a failed review, never a guess.
        </li>
      ) : null}
      {known(rejected) ? (
        <li>
          <strong>Quotes that were not in the post.</strong>{' '}
          {rejected === 0 ? 'None: every quote the review gave was found in the post, character for character.' : `${formatCount(rejected)}: each was thrown away, and the reading it backed with it.`}
        </li>
      ) : null}
    </ul>
  )
}

interface ReviewEvaluationProps {
  report: ReviewReport | null
  /** The techniques the review screens for, as the server names them. */
  techniques: ReviewDoc['techniques']
}

/** How the review was measured against the annotation: where, technique by technique, which
 *  figure the product shows from it, how stable an answer is, and what was not measured. */
export function ReviewEvaluation({ report, techniques }: ReviewEvaluationProps): ReactElement {
  const names = useMemo(() => new Map(techniques.map((technique) => [technique.key, technique.name])), [techniques])
  if (!report) {
    return (
      <p className="nm-method__empty">
        Not measured yet. Until the review has its own evaluation report, every reading it gives is marked "not measured" in the interface.
      </p>
    )
  }
  const cascaded = report.cascade && Object.keys(report.cascade.probes).length > 0 ? report.cascade : null
  const banded = report.cascade_bands && Object.keys(report.cascade_bands.probes).length > 0 ? report.cascade_bands : null
  return (
    <>
      <p className="nm-num">{setting(report)}</p>
      {report.reference ? (
        <p className="nm-note">
          <strong>What it is compared with.</strong> {report.reference}
        </p>
      ) : null}
      <p className="nm-note nm-num">
        Read from <SourceLink path={reportPath('review')} />
        {report.model ? `: model ${report.model}` : ''}
        {report.prompt_version ? `, prompt ${report.prompt_version}` : ''}
        {known(report.temperature) ? `, temperature ${report.temperature}` : ''}. These figures hold for that model and that prompt only.
      </p>
      <Answers report={report} />
      <TechniqueTable labels={report.labels} names={names} />
      <h3>The figure shown beside a reading</h3>
      <ShownFigure report={report} names={names} />
      {report.runs_agreement ? (
        <>
          <h3>The same posts, asked twice</h3>
          <RunsAgreement runs={report.runs_agreement} temperature={report.temperature} />
        </>
      ) : null}
      {banded ? (
        <>
          <h3>A probe, then the review</h3>
          <CascadeTable cascade={banded} names={names} />
          {cascaded ? (
            <p className="nm-note">
              A first measure used only the flagged posts of the random test sample ({known(cascaded.posts_read) ? formatCount(cascaded.posts_read) : 'fewer'} posts read): the same thing on far fewer posts, with wider intervals. It is kept in the
              report beside this one, under <code>cascade</code>.
            </p>
          ) : null}
        </>
      ) : cascaded ? (
        <>
          <h3>A probe, then the review</h3>
          <CascadeTable cascade={cascaded} names={names} />
        </>
      ) : null}
      <h3>What was not measured</h3>
      <ul>
        <li>The review of a selection of posts: what it says of a group has no measured figure.</li>
        <li>
          What the review answers about a probe that is not a technique (attacks, calls, claims)
          {cascaded || banded ? ', beyond the probes of the table above' : ''}.
        </li>
        <li>Any other model or prompt version: a review made with another one is marked "not measured" in the interface.</li>
      </ul>
    </>
  )
}
