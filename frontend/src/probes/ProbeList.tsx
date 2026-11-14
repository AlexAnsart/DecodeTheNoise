import { Check } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import type { ProbeInfo } from '../api/schema'
import { familyLabel, probeMeasure, shownProbes } from './levels'
import './probes.css'

/** From this many probes on, a search field heads the list. */
const SEARCH_FROM = 8

interface ProbeListProps {
  /** Every probe of the map: the list keeps the ones the interface may show. */
  probes: ProbeInfo[]
  /** Key of the probe in use, when one is. */
  current: string | null
  disabled?: boolean
  onPick(probe: ProbeInfo): void
}

function byFamily(probes: ProbeInfo[]): Array<[string, ProbeInfo[]]> {
  const families = new Map<string, ProbeInfo[]>()
  for (const probe of probes) families.set(probe.family, [...(families.get(probe.family) ?? []), probe])
  return Array.from(families)
}

/** The probes of a map, by family. Each row says what was measured, never a bare name. */
export function ProbeList({ probes, current, disabled = false, onPick }: ProbeListProps): ReactElement {
  const [query, setQuery] = useState('')
  const shown = useMemo(() => shownProbes(probes), [probes])
  if (shown.length === 0) return <p className="nm-probes__none">No probe has a measured report yet.</p>

  const needle = query.trim().toLowerCase()
  const matching = needle
    ? shown.filter((probe) => `${probe.label} ${probe.family} ${probe.description}`.toLowerCase().includes(needle))
    : shown
  const families = byFamily(matching)

  return (
    <div className="nm-probes">
      {shown.length > SEARCH_FROM ? (
        <input
          className="nm-field"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search the probes"
          aria-label="Search the probes"
        />
      ) : null}
      <div className="nm-probes__rows" role="listbox" aria-label="Probes">
        {families.map(([family, members]) => (
          <div key={family} role="group" aria-label={familyLabel(family)}>
            {families.length > 1 ? <p className="nm-probes__family">{familyLabel(family)}</p> : null}
            {members.map((probe) => (
              <button
                key={probe.key}
                type="button"
                role="option"
                aria-selected={probe.key === current}
                className={`nm-probe-row${probe.key === current ? ' is-chosen' : ''}`}
                disabled={disabled}
                title={probe.description}
                onClick={() => onPick(probe)}
              >
                <span className="nm-probe-row__label">{probe.label}</span>
                <span className="nm-probe-row__measure">{probeMeasure(probe)}</span>
                {probe.key === current ? <Check size={13} className="nm-probe-row__check" aria-hidden /> : null}
              </button>
            ))}
          </div>
        ))}
        {matching.length === 0 ? <p className="nm-probes__none">No probe matches.</p> : null}
      </div>
    </div>
  )
}
