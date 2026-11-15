import { Search, X } from 'lucide-react'
import type { ReactElement } from 'react'
import { stateWord } from '../words'
import type { ProbeRow } from './probeRows'
import { tally } from './probeSort'
import type { ProbeTable } from './useProbeTable'

interface ChipsProps {
  label: string
  values: [value: string, count: number][]
  chosen: ReadonlySet<string>
  name(value: string): string
  onToggle(value: string): void
}

function Chips({ label, values, chosen, name, onToggle }: ChipsProps): ReactElement {
  return (
    <div className="nm-chips" role="group" aria-label={label}>
      <span className="nm-chips__label">{label}</span>
      {values.map(([value, count]) => (
        <button key={value} type="button" className={`nm-chip-btn${chosen.has(value) ? ' is-on' : ''}`} aria-pressed={chosen.has(value)} onClick={() => onToggle(value)}>
          {name(value)}
          <span className="nm-num">{count}</span>
        </button>
      ))}
    </div>
  )
}

interface ProbeFiltersProps {
  all: ProbeRow[]
  table: ProbeTable
}

/** Narrows the table of probes: by words, by family, by what became of the probe. */
export function ProbeFilters({ all, table }: ProbeFiltersProps): ReactElement {
  const { filter } = table
  const filtered = filter.query !== '' || filter.families.size > 0 || filter.states.size > 0
  return (
    <div className="nm-probe-filters">
      <label className="nm-probe-filters__search">
        <Search size={13} aria-hidden />
        <input className="nm-field" type="search" value={filter.query} onChange={(event) => table.setQuery(event.target.value)} placeholder="Find a probe" aria-label="Find a probe by its name or its question" />
      </label>
      <Chips label="State" values={tally(all, (row) => row.state)} chosen={filter.states} name={(state) => stateWord(state).label} onToggle={table.toggleState} />
      <Chips label="Family" values={tally(all, (row) => row.family)} chosen={filter.families} name={(family) => family} onToggle={table.toggleFamily} />
      <p className="nm-probe-filters__count nm-num" role="status">
        {table.rows.length} of {all.length} probes
        {filtered ? (
          <button type="button" className="nm-chip-btn" onClick={table.clear}>
            <X size={11} aria-hidden />
            Clear the filters
          </button>
        ) : null}
      </p>
    </div>
  )
}
