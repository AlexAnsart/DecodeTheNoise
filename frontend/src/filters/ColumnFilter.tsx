import { ListFilter } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { MapData } from '../map/mapData'
import { OptionList } from '../popover/OptionList'
import { Popover } from '../popover/Popover'
import { columnOptions } from './columnOptions'

interface ColumnFilterProps {
  data: MapData
  /** Column key to the codes kept; an absent column keeps everything. */
  values: Record<string, number[]>
  onValues(values: Record<string, number[]>): void
}

/** Keeps only the points whose attribute is among the chosen values, one tab per attribute. */
export function ColumnFilter({ data, values, onValues }: ColumnFilterProps): ReactElement {
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState(data.columns[0]?.key ?? '')
  const column = data.columns.find((c) => c.key === tab) ?? data.columns[0]
  const options = useMemo(() => (column ? columnOptions(column) : []), [column])
  const active = Object.values(values).filter((codes) => codes.length > 0).length
  const chosen = new Set(column ? (values[column.key] ?? []) : [])

  const pick = (code: number): void => {
    if (!column) return
    const next = new Set(chosen)
    if (next.has(code)) next.delete(code)
    else next.add(code)
    onValues({ ...values, [column.key]: Array.from(next) })
  }

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={`nm-tool${active > 0 ? ' is-active nm-tool--marked' : ''}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        title="Keep only some values of an attribute"
      >
        <ListFilter size={13} aria-hidden />
        Filters{active > 0 ? ` (${active})` : ''}
      </button>
      <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} align="start" width={320} label="Filters">
        <div className="nm-filter-tabs" role="tablist">
          {data.columns.map((c) => (
            <button
              key={c.key}
              type="button"
              role="tab"
              aria-selected={c.key === column?.key}
              className={`nm-filter-tab${c.key === column?.key ? ' is-active' : ''}${(values[c.key] ?? []).length > 0 ? ' is-set' : ''}`}
              onClick={() => setTab(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
        {column ? <OptionList key={column.key} options={options} chosen={chosen} onPick={pick} label={column.label} /> : null}
        <div className="nm-filter-foot">
          <button
            type="button"
            className="nm-btn-secondary nm-btn-small"
            disabled={!column || chosen.size === 0}
            onClick={() => column && onValues({ ...values, [column.key]: [] })}
          >
            Clear this attribute
          </button>
        </div>
      </Popover>
    </>
  )
}
