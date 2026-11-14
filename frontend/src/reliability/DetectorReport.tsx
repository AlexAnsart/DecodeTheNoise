import { ExternalLink } from 'lucide-react'
import type { ReactElement } from 'react'
import type { DetectorMetrics } from '../api/schema'
import { SOURCE_URL } from '../app/source'
import { formatCount, formatRate } from '../text/format'

function interval(low: number | null, high: number | null): string {
  return low !== null && high !== null ? `${formatRate(low)} to ${formatRate(high)}` : 'not computed'
}

/** What one detector measured to be: every rate with its interval, its sample and the data
 *  behind it, then what the audit of its mistakes found and what was not tested. */
export function DetectorReport({ metrics }: { metrics: DetectorMetrics }): ReactElement {
  return (
    <article className="nm-report">
      <header>
        <h3>{metrics.title}</h3>
        <a href={`${SOURCE_URL}/blob/main/${metrics.report}`} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={11} aria-hidden />
          Full report of {metrics.date}
        </a>
      </header>
      <p className="nm-report__decides">
        Decided per {metrics.unit}: {metrics.decides}
      </p>
      <table className="nm-report__table nm-num">
        <thead>
          <tr>
            <th scope="col">Measure</th>
            <th scope="col">Value</th>
            <th scope="col">95% interval</th>
            <th scope="col">n</th>
            <th scope="col">Measured on</th>
          </tr>
        </thead>
        <tbody>
          {metrics.results.map((measure) => (
            <tr key={`${measure.name}:${measure.set}`}>
              <th scope="row">{measure.name}</th>
              <td>{formatRate(measure.value)}</td>
              <td>{interval(measure.low, measure.high)}</td>
              <td>{formatCount(measure.n)}</td>
              <td className="nm-report__set">{measure.set}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {metrics.precision_at_base_rates.length > 0 ? (
        <>
          <h4>What a flag is worth, by how common the behaviour is</h4>
          <p className="nm-report__hint">
            The same detector is right less often where what it looks for is rarer. Among the {metrics.unit}s it flags,
            the share that is right:
          </p>
          <ul className="nm-report__rates nm-num">
            {metrics.precision_at_base_rates.map((row) => (
              <li key={row.prevalence}>
                <strong>{formatRate(row.precision)}</strong> when {formatRate(row.prevalence)} of all {metrics.unit}s do
                what it looks for
                {row.low !== null && row.high !== null ? ` (${interval(row.low, row.high)})` : ''}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {metrics.false_positive_modes.length > 0 ? (
        <>
          <h4>When it is wrong</h4>
          <ul className="nm-report__modes">
            {metrics.false_positive_modes.map((mode) => (
              <li key={mode.mode}>
                <strong>{mode.mode}.</strong> {mode.example} <span>What the product does: {mode.response}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {metrics.untested.length > 0 ? (
        <>
          <h4>Not tested</h4>
          <ul className="nm-report__untested">
            {metrics.untested.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      ) : null}
    </article>
  )
}
