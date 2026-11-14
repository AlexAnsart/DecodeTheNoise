import { Check } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import { formatCount } from '../text/format'
import './optionList.css'

/** From this many options on, a search field heads the list. */
const SEARCH_FROM = 8
/** Rows drawn at most: a long list is narrowed by typing, not by scrolling thousands of rows. */
const MAX_ROWS = 200

export interface Option {
  id: number
  label: string
  count: number
}

interface OptionListProps {
  options: Option[]
  chosen: ReadonlySet<number>
  onPick(id: number): void
  label: string
}

/** A list of values with their counts; type to narrow it. */
export function OptionList({ options, chosen, onPick, label }: OptionListProps): ReactElement {
  const [query, setQuery] = useState('')
  const needle = query.trim().toLowerCase()
  const matching = needle ? options.filter((option) => option.label.toLowerCase().includes(needle)) : options
  const rows = matching.slice(0, MAX_ROWS)
  return (
    <div className="nm-options">
      {options.length >= SEARCH_FROM ? (
        <input
          className="nm-field"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`Search ${label.toLowerCase()}`}
          aria-label={`Search ${label.toLowerCase()}`}
        />
      ) : null}
      <div className="nm-options__rows" role="listbox" aria-label={label} aria-multiselectable>
        {rows.map((option) => (
          <button
            key={option.id}
            type="button"
            role="option"
            aria-selected={chosen.has(option.id)}
            className={`nm-menu-row${chosen.has(option.id) ? ' is-chosen' : ''}`}
            onClick={() => onPick(option.id)}
          >
            <span className="nm-options__check">{chosen.has(option.id) ? <Check size={13} aria-hidden /> : null}</span>
            <span className="nm-menu-row__label">{option.label}</span>
            <span className="nm-menu-row__hint">{formatCount(option.count)}</span>
          </button>
        ))}
        {rows.length === 0 ? <p className="nm-options__empty">Nothing matches.</p> : null}
        {matching.length > rows.length ? (
          <p className="nm-options__empty">{formatCount(matching.length - rows.length)} more: type to narrow the list.</p>
        ) : null}
      </div>
    </div>
  )
}
