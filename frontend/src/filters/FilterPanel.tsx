import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { MapColumn } from '../map/mapData'
import { OptionList } from '../popover/OptionList'
import { columnOptions } from './columnOptions'

interface FilterPanelProps {
  /** The attributes this map carries: a demo and a workspace do not have the same ones. */
  columns: MapColumn[]
  /** Key of the attribute whose values are listed. */
  tab: string
  onTab(key: string): void
  /** Column key to the codes kept; an absent column keeps everything. */
  values: Record<string, number[]>
  onValues(values: Record<string, number[]>): void
}

/** One tab per attribute of the map, and the values of the chosen one to tick. */
export function FilterPanel({ columns, tab, onTab, values, onValues }: FilterPanelProps): ReactElement {
  const column = columns.find((c) => c.key === tab) ?? columns[0]
  // One pass over every point of the map: made when the panel opens or the tab changes.
  const options = useMemo(() => (column ? columnOptions(column) : []), [column])
  if (!column) return <div className="nm-filter__none">This map has no attribute to filter on yet.</div>

  const chosen = new Set(values[column.key] ?? [])
  const keep = (codes: number[]): void => onValues({ ...values, [column.key]: codes })
  const pick = (code: number): void => {
    const next = new Set(chosen)
    if (next.has(code)) next.delete(code)
    else next.add(code)
    keep(Array.from(next))
  }

  return (
    <div className="nm-filter">
      <div className="nm-filter__tabs" role="tablist" aria-label="Attributes">
        {columns.map((c) => {
          const kept = (values[c.key] ?? []).length
          return (
            <button
              key={c.key}
              type="button"
              role="tab"
              aria-selected={c.key === column.key}
              className={`nm-filter__tab${c.key === column.key ? ' is-active' : ''}`}
              onClick={() => onTab(c.key)}
            >
              {c.label}
              {kept > 0 ? <span className="nm-filter__badge nm-num">{kept}</span> : null}
            </button>
          )
        })}
      </div>
      <OptionList key={column.key} options={options} chosen={chosen} onPick={pick} onClear={() => keep([])} label={column.label} />
    </div>
  )
}
