import { Check, Search, X } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import { formatCount, plural } from '../text/format'
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
  onClear(): void
  label: string
}

/** A list of values to tick, each with its count and a bar of its share; type to narrow it. */
export function OptionList({ options, chosen, onPick, onClear, label }: OptionListProps): ReactElement {
  const [query, setQuery] = useState('')
  const needle = query.trim().toLowerCase()
  const matching = needle ? options.filter((option) => option.label.toLowerCase().includes(needle)) : options
  const rows = matching.slice(0, MAX_ROWS)
  // Each bar is drawn against the most frequent value.
  const peak = options.reduce((most, option) => Math.max(most, option.count), 1)
  const what = label.toLowerCase()
  const values = plural(options.length, 'value', 'values')
  const state = needle
    ? `${formatCount(matching.length)} of ${values} match`
    : chosen.size > 0
      ? `${formatCount(chosen.size)} of ${values} kept`
      : `${values} · tick the ones to keep`

  return (
    <div className="nm-options">
      {options.length >= SEARCH_FROM ? (
        <label className="nm-options__search">
          <Search size={13} aria-hidden />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Search ${what}`} aria-label={`Search ${what}`} />
          {query ? (
            <button type="button" onClick={() => setQuery('')} title="Clear the search" aria-label="Clear the search">
              <X size={12} aria-hidden />
            </button>
          ) : null}
        </label>
      ) : null}
      <div className="nm-options__meta">
        <span className="nm-num">{state}</span>
        {chosen.size > 0 ? (
          <button type="button" className="nm-text-btn" onClick={onClear} title={`Keep every value of ${what} again`}>
            Clear
          </button>
        ) : null}
      </div>
      <div className={`nm-options__rows${chosen.size > 0 ? ' has-chosen' : ''}`} role="listbox" aria-label={label} aria-multiselectable>
        {rows.map((option) => (
          <button
            key={option.id}
            type="button"
            role="option"
            aria-selected={chosen.has(option.id)}
            className={`nm-option${chosen.has(option.id) ? ' is-chosen' : ''}`}
            title={option.label}
            onClick={() => onPick(option.id)}
          >
            <span className="nm-option__box" aria-hidden>
              {chosen.has(option.id) ? <Check size={10} strokeWidth={3.5} /> : null}
            </span>
            <span className="nm-option__label">{option.label}</span>
            <span className="nm-option__bar" aria-hidden>
              <i style={{ width: `${(option.count / peak) * 100}%` }} />
            </span>
            <span className="nm-option__count nm-num">{formatCount(option.count)}</span>
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
