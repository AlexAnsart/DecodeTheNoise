import { ArrowDown, ArrowUp } from 'lucide-react'
import type { ReactElement } from 'react'
import { LEVEL_CELLS, PROBE_COLUMNS, ProbeLine } from './ProbeLine'
import type { ProbeRow } from './probeRows'
import { LEVEL_NAMES, LEVELS } from './probeRows'
import type { Measure, Sort, SortKey } from './probeSort'
import type { ProbeSetting } from './setting'

/** What the table gives for each level, in the order of its columns. */
const LEVEL_COLUMNS: { measure: Measure; label: string; title: string }[] = [
  { measure: 'precision', label: 'Precision', title: 'flagged posts that are a yes, with the 95% interval' },
  { measure: 'recall', label: 'Recall', title: 'yes posts that are flagged' },
  { measure: 'flagged', label: 'Flagged', title: 'share of the test split that is flagged' },
]

interface SortHeaderProps {
  column: SortKey
  label: string
  title: string
  sort: Sort | null
  className?: string
  /** Over the two rows of the header: a column that belongs to no level. */
  tall?: boolean
  onSort(key: SortKey): void
}

function SortHeader({ column, label, title, sort, className, tall = false, onSort }: SortHeaderProps): ReactElement {
  const sorted = sort?.key === column
  return (
    <th scope="col" rowSpan={tall ? 2 : undefined} aria-sort={sorted ? (sort.descending ? 'descending' : 'ascending') : 'none'} className={className}>
      <button type="button" className="nm-ptable__sort" title={`${title}. Click to sort.`} onClick={() => onSort(column)}>
        {label}
        {sorted ? sort.descending ? <ArrowDown size={11} aria-hidden /> : <ArrowUp size={11} aria-hidden /> : null}
      </button>
    </th>
  )
}

interface ProbesTableProps {
  rows: ProbeRow[]
  sort: Sort | null
  /** The probe opened, by its key. */
  open: string | null
  setting: ProbeSetting
  onSort(key: SortKey): void
  onToggle(key: string): void
}

/** Every probe, one line each, with the same figures for its two levels, probable first; a
 *  line opens to what the probe measured. */
export function ProbesTable({ rows, sort, open, setting, onSort, onToggle }: ProbesTableProps): ReactElement {
  const { starts } = setting
  return (
    <div className="nm-table-wrap nm-ptable-wrap">
      <table className="nm-table nm-ptable">
        <thead>
          <tr>
            <SortHeader column="name" label="Probe" title="The label the probe reads" sort={sort} tall onSort={onSort} />
            <SortHeader column="state" label="State" title="What became of the probe, and the family of its label" sort={sort} tall onSort={onSort} />
            {LEVELS.map((level) => (
              <th key={level} scope="colgroup" colSpan={LEVEL_CELLS} className={`nm-ptable__group nm-ptable__level nm-ptable__level--${level}`}>
                {LEVEL_NAMES[level]}
                {starts ? <span>from a score of {starts[level]}</span> : null}
              </th>
            ))}
            <SortHeader column="lift" label="Ranking" title="Average precision on random test posts, as a multiple of chance" sort={sort} className="nm-num nm-ptable__group" tall onSort={onSort} />
          </tr>
          <tr>
            {LEVELS.flatMap((level) =>
              LEVEL_COLUMNS.map((column, at) => {
                const key: SortKey = `${level}.${column.measure}`
                return (
                  <SortHeader
                    key={key}
                    column={key}
                    label={column.label}
                    title={`At the ${level} level: ${column.title}`}
                    sort={sort}
                    className={at === 0 ? 'nm-num nm-ptable__group' : 'nm-num'}
                    onSort={onSort}
                  />
                )
              }),
            )}
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
