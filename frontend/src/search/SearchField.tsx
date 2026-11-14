import { CornerDownLeft, ListFilter, LoaderCircle, Mountain, Search, X } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { MapData } from '../map/mapData'
import { Popover } from '../popover/Popover'
import { plural } from '../text/format'
import { useSearch } from './useSearch'
import './search.css'

interface SearchFieldProps {
  data: MapData
  /** Words the map is filtered on, when it is. */
  filteredOn: string | null
  onPick(index: number): void
  onFilter(query: string, hits: Uint8Array): void
  /** Raises the map by how much each item resembles the text. */
  onLift(query: string): void
  onClear(): void
}

/** Finds items by their words. A result centres the map on its point; the last rows turn the
 *  search into a filter, or into a relief by meaning. */
export function SearchField({ data, filteredOn, onPick, onFilter, onLift, onClear }: SearchFieldProps): ReactElement {
  const wrap = useRef<HTMLDivElement>(null)
  const [text, setText] = useState(filteredOn ?? '')
  const [open, setOpen] = useState(false)
  const search = useSearch(data, text)
  const ready = search.settled.length >= 2 && search.settled === text.trim()

  const pick = (index: number): void => {
    setOpen(false)
    onPick(index)
  }
  const clear = (): void => {
    setText('')
    setOpen(false)
    onClear()
  }

  return (
    <div ref={wrap} className="nm-search">
      {search.loading ? <LoaderCircle size={13} className="nm-search__icon nm-spin" aria-hidden /> : <Search size={13} className="nm-search__icon" aria-hidden />}
      <input
        type="search"
        value={text}
        placeholder="Search the items"
        aria-label="Search the items"
        onChange={(event) => {
          setText(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && ready && search.hits.length > 0) pick(search.hits[0].index)
        }}
      />
      {text ? (
        <button type="button" className="nm-search__clear" onClick={clear} title="Clear the search" aria-label="Clear the search">
          <X size={12} aria-hidden />
        </button>
      ) : null}
      <Popover anchor={wrap} open={open && text.trim().length >= 2} onClose={() => setOpen(false)} align="start" variant="menu" width={360} label="Search results">
        {search.error ? <p className="nm-search__state nm-search__state--error">{search.error}</p> : null}
        {!search.error && !ready ? <p className="nm-search__state">Searching…</p> : null}
        {ready && search.hits.length === 0 && !search.error ? <p className="nm-search__state">No item holds these words.</p> : null}
        {ready
          ? search.hits.map((hit, position) => (
              <button key={hit.id} type="button" className="nm-search__row" onClick={() => pick(hit.index)}>
                <span className="nm-search__label">{hit.label}</span>
                <span className="nm-search__hint">{hit.hint}</span>
                {position === 0 ? <CornerDownLeft size={12} aria-hidden /> : null}
              </button>
            ))
          : null}
        {ready && search.mask && search.total > 0 ? (
          <button
            type="button"
            className="nm-search__row nm-search__row--action"
            onClick={() => {
              if (search.mask) onFilter(search.settled, search.mask)
              setOpen(false)
            }}
          >
            <ListFilter size={13} aria-hidden />
            <span className="nm-search__label">Filter by this search</span>
            <span className="nm-search__hint">{plural(search.total, 'item', 'items')}</span>
          </button>
        ) : null}
        {ready ? (
          <button
            type="button"
            className="nm-search__row nm-search__row--action"
            onClick={() => {
              onLift(search.settled)
              setOpen(false)
            }}
            title="Raises each item by how much its meaning resembles these words, whatever words it uses"
          >
            <Mountain size={13} aria-hidden />
            <span className="nm-search__label">Raise what resembles “{search.settled}” by meaning</span>
          </button>
        ) : null}
      </Popover>
    </div>
  )
}
