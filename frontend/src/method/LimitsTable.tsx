import type { ReactElement } from 'react'
import type { Limits } from '../api/workspaceSchema'
import { formatCount } from '../text/format'

const ROWS: { label: string; of(limits: Limits): number }[] = [
  { label: 'Posts stored in a workspace', of: (limits) => limits.items },
  { label: 'Posts in one batch call', of: (limits) => limits.batch_items },
  { label: 'Requests a minute', of: (limits) => limits.requests_per_minute },
  { label: 'LLM reviews a day', of: (limits) => limits.reviews_per_day },
  { label: 'Characters in a post', of: (limits) => limits.text_chars },
]

/** What a workspace may hold and send, as the server states it. */
export function LimitsTable({ limits }: { limits: Limits }): ReactElement {
  return (
    <div className="nm-table-wrap">
      <table className="nm-table">
        <thead>
          <tr>
            <th scope="col">Limit</th>
            <th scope="col">Per workspace</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td className="nm-num">{formatCount(row.of(limits))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
