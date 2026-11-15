/* The filters and the order of the table of probes. */

import { useCallback, useMemo, useState } from 'react'
import type { ProbeRow } from './probeRows'
import type { ProbeFilter, Sort, SortKey } from './probeSort'
import { NO_FILTER, matches, sortRows } from './probeSort'

export interface ProbeTable {
  filter: ProbeFilter
  sort: Sort | null
  /** The rows to draw: filtered, ordered, and always holding the probe that is open. */
  rows: ProbeRow[]
  setQuery(query: string): void
  toggleFamily(family: string): void
  toggleState(state: string): void
  sortBy(key: SortKey): void
  clear(): void
}

function toggled(values: ReadonlySet<string>, value: string): Set<string> {
  const next = new Set(values)
  if (!next.delete(value)) next.add(value)
  return next
}

/** A column sorts with its best first: names from A, numbers from the highest. A second click
 *  turns it round, a third returns to the order of the report. */
function nextSort(current: Sort | null, key: SortKey): Sort | null {
  const first = key !== 'name' && key !== 'state'
  if (current?.key !== key) return { key, descending: first }
  return current.descending === first ? { key, descending: !first } : null
}

export function useProbeTable(all: ProbeRow[], open: string | null): ProbeTable {
  const [filter, setFilter] = useState<ProbeFilter>(NO_FILTER)
  const [sort, setSort] = useState<Sort | null>(null)

  const rows = useMemo(
    // A probe opened from a link stays in the table whatever the filters say.
    () => sortRows(all.filter((row) => row.key === open || matches(row, filter)), sort),
    [all, filter, sort, open],
  )

  return {
    filter,
    sort,
    rows,
    setQuery: useCallback((query: string) => setFilter((current) => ({ ...current, query })), []),
    toggleFamily: useCallback((family: string) => setFilter((current) => ({ ...current, families: toggled(current.families, family) })), []),
    toggleState: useCallback((state: string) => setFilter((current) => ({ ...current, states: toggled(current.states, state) })), []),
    sortBy: useCallback((key: SortKey) => setSort((current) => nextSort(current, key)), []),
    clear: useCallback(() => setFilter(NO_FILTER), []),
  }
}
