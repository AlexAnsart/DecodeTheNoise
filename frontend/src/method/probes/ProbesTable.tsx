import { ArrowDown, ArrowUp } from 'lucide-react'
import type { ReactElement } from 'react'
import { PROBE_COLUMNS, ProbeLine } from './ProbeLine'
import type { ProbeRow } from './probeRows'
import type { Sort, SortKey } from './probeSort'
import type { ProbeSetting } from './setting'

const COLUMNS: { key: SortKey; label: string; title: string; number: boolean }[] = [
  { key: 'name', label: 'Probe', title: 'The label the probe reads', number: false },
  { key: 'state', label: 'State', title: 'What became of the probe, and the family of its label', number: false },
  { key: 'possible', label: 'Possible', title: 'Precision at the possible level, with its 95% interval', number: true },
  { key: 'probable', label: 'Probable', title: 'Precision at the probable level, with its 95% interval', number: true },
  { key: 'recall', label: 'Recall', title: 'Share of the yes posts flagged, at the level that flags most', number: true },
  { key: 'flagged', label: 'Flagged', title: 'Share of the test split flagged, at the level that flags most', number: true },
  { key: 'lift', label: 'Ranking', title: 'Average precision on random test posts, as a multiple of chance', number: true },
]

interface ProbesTableProps {
  rows: ProbeRow[]
  sort: Sort | null
  /** The probe opened, by its key. */
  open: string | null
  setting: ProbeSetting
  onSort(key: SortKey): void
  onToggle(key: string): void
}

/** Every probe, one line each; a line opens to what the probe measured. */
export function ProbesTable({ rows, sort, open, setting, onSort, onToggle }: ProbesTableProps): ReactElement {
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-ptable">
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              const sorted = sort?.key === column.key
              return (
                <th key={column.key} scope="col" aria-sort={sorted ? (sort.descending ? 'descending' : 'ascending') : 'none'} className={column.number ? 'nm-num' : ''}>
                  <button type="button" className="nm-ptable__sort" title={`${column.title}. Click to sort.`} onClick={() => onSort(column.key)}>
                    {column.label}
                    {sorted ? sort.descending ? <ArrowDown size={11} aria-hidden /> : <ArrowUp size={11} aria-hidden /> : null}
                  </button>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <ProbeLine key={row.key} row={row} open={open === row.key} setting={setting} onToggle={() => onToggle(row.key)} />
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={PROBE_COLUMNS}>No probe matches these filters.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  )
}
