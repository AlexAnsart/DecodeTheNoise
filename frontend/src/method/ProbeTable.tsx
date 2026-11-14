import type { ReactElement } from 'react'
import { useRequest } from '../api/useRequest'
import { fetchMetrics } from '../api/workspace'
import type { LevelMeasure, ProbeInfo } from '../api/workspaceSchema'
import { formatCount } from '../text/format'
import { formatInterval, formatRate } from './figures'

type Level = [name: string, measure: LevelMeasure]

function levelsOf(probe: ProbeInfo): Level[] {
  const levels: Level[] = []
  if (probe.possible) levels.push(['Possible', probe.possible])
  if (probe.probable) levels.push(['Probable', probe.probable])
  return levels
}

function ProbeRows({ probe }: { probe: ProbeInfo }): ReactElement {
  const levels = levelsOf(probe)
  const name = (
    <th scope="rowgroup" rowSpan={Math.max(1, levels.length)} className="nm-table__probe">
      <strong>{probe.label}</strong>
      <span>{probe.description}</span>
      <span className="nm-table__tags">
        <i>{probe.family}</i>
        {probe.state === 'review-only' ? <i title="It only sends posts to the LLM review: it is never shown as a hit">review only</i> : null}
      </span>
    </th>
  )
  if (levels.length === 0) {
    return (
      <tr>
        {name}
        <td colSpan={6}>No level of this probe was measured.</td>
      </tr>
    )
  }
  return (
    <>
      {levels.map(([level, measure], row) => (
        <tr key={level}>
          {row === 0 ? name : null}
          <td>{level}</td>
          <td className="nm-num">
            {formatRate(measure.precision)}
            <span>{formatInterval(measure.precision_low, measure.precision_high)}</span>
          </td>
          <td className="nm-num">{formatRate(measure.false_positive_rate)}</td>
          <td className="nm-num">{formatRate(measure.recall)}</td>
          <td className="nm-num">{formatCount(measure.read)}</td>
          <td className="nm-num">{formatRate(measure.flag_rate)}</td>
        </tr>
      ))}
    </>
  )
}

/** Every probe served, with what each of its levels measured on posts it never saw. */
export function ProbeTable(): ReactElement {
  const metrics = useRequest(fetchMetrics)
  if (metrics.status === 'loading') {
    return (
      <p className="nm-note" role="status">
        Reading the evaluation reports…
      </p>
    )
  }
  if (metrics.status === 'error') {
    return (
      <p className="nm-note nm-note--error" role="alert">
        The evaluation reports could not be read. {metrics.message}
      </p>
    )
  }
  const { probes, reports } = metrics.data
  return (
    <>
      {probes.length === 0 ? (
        <p className="nm-method__empty">No probe has a measured report yet.</p>
      ) : (
        <div className="nm-table-wrap">
          <table className="nm-table">
            <thead>
              <tr>
                <th scope="col">Probe</th>
                <th scope="col">Level</th>
                <th scope="col">Precision, 95% interval</th>
                <th scope="col">False-positive rate</th>
                <th scope="col">Recall</th>
                <th scope="col">Flagged posts read</th>
                <th scope="col">Share flagged</th>
              </tr>
            </thead>
            {probes.map((probe) => (
              <tbody key={probe.key} id={`probe-${probe.key}`}>
                <ProbeRows probe={probe} />
              </tbody>
            ))}
          </table>
        </div>
      )}
      {reports.map((report) => (
        <details key={report.detector} className="nm-method__raw">
          <summary>Report as written by the evaluation: {report.detector}</summary>
          <pre tabIndex={0}>{JSON.stringify(report.metrics, null, 1)}</pre>
        </details>
      ))}
    </>
  )
}
