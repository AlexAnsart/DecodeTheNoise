import { X } from 'lucide-react'
import type { ReactElement, ReactNode } from 'react'
import type { TimeRange } from '../map/geometry'
import type { MapData } from '../map/mapData'
import { SearchField } from '../search/SearchField'
import { ColumnFilter } from './ColumnFilter'
import type { Filters } from './mask'
import { NO_FILTERS, hasFilters } from './mask'
import { PeriodFilter } from './PeriodFilter'
import './filters.css'

interface FilterBarProps {
  data: MapData
  range: TimeRange | null
  filters: Filters
  onFilters(filters: Filters): void
  onPick(index: number): void
  onLift(query: string): void
  /** Drawn right after the search field. */
  beside: ReactNode
  /** The tools of the map, drawn at the right end of the bar. */
  tools: ReactNode
}

/** Filters and search on the left, the tools of the map on the right. */
export function FilterBar({ data, range, filters, onFilters, onPick, onLift, beside, tools }: FilterBarProps): ReactElement {
  return (
    <div className="nm-bar">
      <ColumnFilter data={data} values={filters.values} onValues={(values) => onFilters({ ...filters, values })} />
      <PeriodFilter ts={data.ts} range={range} period={filters.period} onPeriod={(period) => onFilters({ ...filters, period })} />
      {filters.kept ? (
        <span className="nm-bar__chip" title="The map shows only the items of this selection">
          {filters.kept.label}
          <button type="button" onClick={() => onFilters({ ...filters, kept: null })} title="Stop filtering on this selection" aria-label="Stop filtering on this selection">
            <X size={12} aria-hidden />
          </button>
        </span>
      ) : null}
      {hasFilters(filters) ? (
        <button type="button" className="nm-tool nm-tool--icon" onClick={() => onFilters(NO_FILTERS)} title="Clear every filter" aria-label="Clear every filter">
          <X size={13} aria-hidden />
        </button>
      ) : null}
      <SearchField
        // The field restarts when the filter it wrote is cleared from elsewhere.
        key={filters.search?.query ?? 'free'}
        data={data}
        filteredOn={filters.search?.query ?? null}
        onPick={onPick}
        onFilter={(query, hits) => onFilters({ ...filters, search: { query, hits } })}
        onLift={onLift}
        onClear={() => filters.search && onFilters({ ...filters, search: null })}
      />
      {beside}
      {tools}
    </div>
  )
}
