import type { ReactElement } from 'react'
import type { Calibration } from '../../api/reportSchema'
import { formatCount } from '../../text/format'
import { formatInterval, formatNumber, formatRate } from '../figures'

/** The level a candidate cut was kept as, when it was. One cut kept for both levels is one
 *  level, probable: the probe has no possible level then. */
function keptAs(threshold: number | undefined, calibration: Calibration): string {
  if (threshold === undefined) return ''
  if (threshold === calibration.probable) return 'probable'
  return threshold === calibration.possible ? 'possible' : ''
}

/** How the thresholds of a probe were placed: every candidate cut, read on the calibration
 *  split, with the precision it measured there; the cuts kept are marked. */
export function CalibrationTable({ calibration }: { calibration: Calibration }): ReactElement | null {
  const edges = calibration.edges ?? []
  if (edges.length === 0) return null
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-calibration nm-num">
        <caption>
          Candidate cuts on the calibration split, highest first. A level takes the deepest cut whose precision meets its target; the test split then
          measures it once.
        </caption>
        <thead>
          <tr>
            <th scope="col">Cut</th>
            <th scope="col">Posts flagged</th>
            <th scope="col">Read</th>
            <th scope="col">Yes</th>
            <th scope="col">Precision, 95% interval</th>
            <th scope="col">Kept as</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((edge, index) => {
            const kept = keptAs(edge.threshold, calibration)
            return (
              <tr key={edge.threshold ?? index} className={kept ? 'is-kept' : ''}>
                <td>{edge.threshold === undefined ? '–' : formatNumber(edge.threshold)}</td>
                <td>{edge.flagged === undefined ? '–' : formatCount(edge.flagged)}</td>
                <td>{edge.read_flagged === undefined ? '–' : formatCount(edge.read_flagged)}</td>
                <td>{edge.positive_flagged === undefined ? '–' : formatCount(edge.positive_flagged)}</td>
                <td>
                  {formatRate(edge.precision?.value ?? null)}
                  {edge.precision ? <span>{formatInterval(edge.precision.low, edge.precision.high)}</span> : null}
                </td>
                <td>{kept}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
