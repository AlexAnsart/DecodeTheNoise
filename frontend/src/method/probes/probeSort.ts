/* Ordering and narrowing the table of probes. Pure. */

import type { ProbeRow } from './probeRows'
import { widestLevel } from './probeRows'

export type SortKey = 'name' | 'state' | 'possible' | 'probable' | 'recall' | 'flagged' | 'lift'

export interface Sort {
  key: SortKey
  descending: boolean
}

export interface ProbeFilter {
  /** Words of the name, the key or the question. */
  query: string
  /** Empty: every family, every state. */
  families: ReadonlySet<string>
  states: ReadonlySet<string>
}

export const NO_FILTER: ProbeFilter = { query: '', families: new Set(), states: new Set() }

/** As the report lists them: shown first. */
const STATE_ORDER = ['shown', 'review-only', 'dropped']

function valueOf(row: ProbeRow, key: SortKey): number | string | null {
  switch (key) {
    case 'name':
      return row.name.toLowerCase()
    case 'state': {
      const at = STATE_ORDER.indexOf(row.state ?? '')
      return at === -1 ? STATE_ORDER.length : at
    }
    case 'possible':
      return row.possible?.precision?.value ?? null
    case 'probable':
      return row.probable?.precision?.value ?? null
    case 'recall':
      return widestLevel(row)?.recall?.value ?? null
    case 'flagged':
      return widestLevel(row)?.flagRate ?? null
    case 'lift':
      return row.lift
  }
}

/** Rows without a value for the column go last, whichever way it is sorted. */
export function sortRows(rows: ProbeRow[], sort: Sort | null): ProbeRow[] {
  if (!sort) return rows
  const way = sort.descending ? -1 : 1
  return [...rows].sort((a, b) => {
    const left = valueOf(a, sort.key)
    const right = valueOf(b, sort.key)
    if (left === null || right === null) return left === right ? 0 : left === null ? 1 : -1
    if (typeof left === 'string' || typeof right === 'string') return way * String(left).localeCompare(String(right))
    return way * (left - right)
  })
}

export function matches(row: ProbeRow, filter: ProbeFilter): boolean {
  if (filter.families.size > 0 && !filter.families.has(row.family ?? '')) return false
  if (filter.states.size > 0 && !filter.states.has(row.state ?? '')) return false
  const needle = filter.query.trim().toLowerCase()
  if (!needle) return true
  return [row.key, row.name, row.question ?? ''].some((text) => text.toLowerCase().includes(needle))
}

/** The values of a column, in order of first appearance, with how many rows hold each. */
export function tally(rows: ProbeRow[], of: (row: ProbeRow) => string | null): [value: string, count: number][] {
  const counts = new Map<string, number>()
  for (const row of rows) {
    const value = of(row)
    if (value !== null) counts.set(value, (counts.get(value) ?? 0) + 1)
  }
  return [...counts.entries()]
}
