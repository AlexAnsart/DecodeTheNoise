import type { ReactElement } from 'react'
import { useRequest } from '../api/useRequest'
import { voicesReportSchema } from '../api/voicesSchema'
import type { VoicesReport } from '../api/voicesSchema'
import { fetchMetrics } from '../api/workspace'
import type { Metrics } from '../api/workspaceSchema'
import { VoicesSizeTable } from './VoicesSizeTable'

/** The evaluation report of the check, when one was written and reads as expected. */
function reportOf(metrics: Metrics): VoicesReport | null {
  const entry = metrics.reports.find((report) => report.detector === 'voices')
  const parsed = entry ? voicesReportSchema.safeParse(entry.metrics) : null
  return parsed?.success ? parsed.data : null
}

function Measured(): ReactElement {
  const metrics = useRequest(fetchMetrics)
  if (metrics.status === 'loading') {
    return (
      <p className="nm-note" role="status">
        Reading the evaluation report…
      </p>
    )
  }
  if (metrics.status === 'error') {
    return (
      <p className="nm-note nm-note--error" role="alert">
        The evaluation report could not be read. {metrics.message}
      </p>
    )
  }
  const report = reportOf(metrics.data)
  if (!report || report.sizes.length === 0) return <p className="nm-method__empty">Not measured yet: the check stays off.</p>
  return (
    <>
      <p>
        Each line is a group size the check runs at. The threshold was set on one half of the real groups; every figure is counted on the other half
        and on groups written from one brief, which the threshold never saw.{report.evaluated ? ` Evaluated on ${report.evaluated}.` : ''}
      </p>
      <VoicesSizeTable sizes={report.sizes} />
      {report.limits.length > 0 ? (
        <>
          <h3>Limits</h3>
          <ul>
            {report.limits.map((limit) => (
              <li key={limit}>{limit}</li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  )
}

/** The method page's section on the check: what it compares, how to read it, what it does not
 *  say, and what it measured. */
export function VoicesMethod(): ReactElement {
  return (
    <>
      <p>
        Select posts on the map with the lasso and open their list: the check is at the top. It asks one question of the actors in the selection: does
        each of them have a voice of its own, or could any post have come from any of them?
      </p>
      <h3>What it compares</h3>
      <p>
        Two kinds of pairs: two posts by the same actor, and two posts by different actors. People who write on their own have their subjects and their
        manner, so their own posts resemble each other more. To know what chance alone gives, the check shuffles who wrote what, many times, and
        compares again. The score is how far the real authorship stands above the shuffles: 0 when shuffling changes nothing.
      </p>
      <h3>How to read it</h3>
      <p>
        A low score means the actors are interchangeable. That is what several names fed by one source of text look like: one brief given to a model,
        one script, one feed of headlines. A high score means each actor has a voice of its own. The answer has three states: <b>Possible: one voice</b>,{' '}
        <b>Separate voices</b>, and <b>Not enough evidence</b> when too few actors have enough posts in the selection.
      </p>
      <h3>What it does not say</h3>
      <p>
        It never says who is behind the actors, nor that a model wrote the posts. A fan campaign, a news feed or a posting tool can score low too. A
        flag is a reason to read the posts, not a conclusion.
      </p>
      <h3>What it measured</h3>
      <Measured />
    </>
  )
}
