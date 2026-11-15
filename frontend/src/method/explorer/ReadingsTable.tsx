import type { ReactElement } from 'react'
import type { LabelledPost } from '../../api/methodSchema'
import { Answer } from './Answer'
import { readerShort } from './explorerWords'

interface ReadingsTableProps {
  post: LabelledPost
  /** The labels to list, in order. */
  labels: string[]
  /** A second reading settles nothing: its table has no settled answer. */
  settles: boolean
}

/** Each reading of a post side by side, label by label, with the span each yes quoted, and
 *  the answer that was settled from them. */
export function ReadingsTable({ post, labels, settles }: ReadingsTableProps): ReactElement {
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-readings">
        <thead>
          <tr>
            <th scope="col">Label</th>
            <th scope="col">Each reading</th>
            {settles ? <th scope="col">Settled</th> : null}
            <th scope="col">Span quoted</th>
          </tr>
        </thead>
        <tbody>
          {labels.map((label) => {
            const readings = post.readings.filter((reading) => label in reading.answers)
            const quotes = [...new Set(readings.map((reading) => reading.quotes[label]).filter((quote) => quote))]
            return (
              <tr key={label}>
                <th scope="row">
                  <code>{label}</code>
                </th>
                <td>
                  <span className="nm-readings__answers">
                    {readings.map((reading) => (
                      <Answer key={reading.reader} value={reading.answers[label]} by={readerShort(reading.reader)} title={`Batch ${reading.reader}: one fresh annotator per batch`} />
                    ))}
                    {readings.length === 0 ? '–' : null}
                  </span>
                </td>
                {settles ? <td>{post.answers[label] ? <Answer value={post.answers[label]} /> : '–'}</td> : null}
                <td className="nm-readings__quotes">
                  {quotes.map((quote) => (
                    <q key={quote}>{quote}</q>
                  ))}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
