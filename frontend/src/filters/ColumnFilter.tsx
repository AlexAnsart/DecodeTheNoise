import { ListFilter } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { MapData } from '../map/mapData'
import { Popover } from '../popover/Popover'
import { FilterPanel } from './FilterPanel'

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
  const active = Object.values(values).filter((codes) => codes.length > 0).length

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={`nm-tool${active > 0 ? ' is-active' : ''}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        title="Keep only some values of an attribute"
      >
        <ListFilter size={13} aria-hidden />
        Filters
        {active > 0 ? (
          <span className="nm-filter__badge nm-num" title="Attributes with a filter on">
            {active}
          </span>
        ) : null}
      </button>
      <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} align="start" width={480} label="Filters">
        <FilterPanel columns={data.columns} tab={tab} onTab={setTab} values={values} onValues={onValues} />
      </Popover>
    </>
  )
}
