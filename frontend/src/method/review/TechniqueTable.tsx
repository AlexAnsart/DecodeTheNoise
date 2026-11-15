import type { ReactElement } from 'react'
import type { ReviewLabel } from '../../api/reviewReportSchema'
import { formatScore } from '../figures'
import { readable } from '../words'
import { counted, known, noRateReason } from './evaluation'
import { RateCell } from './RateCell'

function Line({ name, title, label }: { name: string; title: string; label: ReviewLabel }): ReactElement {
  const reason = noRateReason(label)
  const rates = [label.precision, label.recall, label.fpr]
  return (
    <tr>
      <th scope="row">
        {title}
        <code>{name}</code>
      </th>
      <td>{counted(label.n)}</td>
      <td>{counted(label.positives)}</td>
      <td>{counted(label.marked)}</td>
      <td>{counted(label.tp)}</td>
      <td>{counted(label.fp)}</td>
      <td>{counted(label.fn)}</td>
      {rates.some(Boolean) ? (
        rates.map((rate, index) => <RateCell key={index} rate={rate} none={reason} />)
      ) : (
        <td colSpan={rates.length} className="nm-review-eval__none">
          No rate: {reason}
        </td>
      )}
      <td>{known(label.f1) ? formatScore(label.f1) : '–'}</td>
      <td>{known(label.kappa) ? formatScore(label.kappa) : '–'}</td>
      <td>{known(label.reference_kappa) ? formatScore(label.reference_kappa) : '–'}</td>
    </tr>
  )
}

interface TechniqueTableProps {
  labels: Record<string, ReviewLabel>
  /** The name the review gives a technique, by its key. */
  names: Map<string, string>
}

/** The technique screen against the annotation, technique by technique: the counts always,
 *  the rates when the evaluation gives one, and why when it gives none. */
export function TechniqueTable({ labels, names }: TechniqueTableProps): ReactElement {
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-num nm-review-eval">
        <caption>
          Right: named by the review and a yes in the annotation. Wrong: named, and a no. Missed: a yes that the review did not name. Under each rate,
          its 95% interval. The last column is the agreement of two annotators on the technique: what the review can be asked to reach.
        </caption>
        <thead>
          <tr>
            <th scope="col">Technique</th>
            <th scope="col">Posts</th>
            <th scope="col">Annotated yes</th>
            <th scope="col">Named</th>
            <th scope="col">Right</th>
            <th scope="col">Wrong</th>
            <th scope="col">Missed</th>
            <th scope="col">Precision</th>
            <th scope="col">Recall</th>
            <th scope="col">False-positive rate</th>
            <th scope="col">F1</th>
            <th scope="col">Kappa</th>
            <th scope="col">Annotators' kappa</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(labels).map(([name, label]) => (
            <Line key={name} name={name} title={names.get(name) ?? readable(name)} label={label} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
