/* Ordering and narrowing the table of probes. Pure. */

import type { Level, LevelView, ProbeRow } from './probeRows'

/** What the table gives for each level. */
export type Measure = 'precision' | 'recall' | 'flagged'

export type SortKey = 'name' | 'state' | 'lift' | `${Level}.${Measure}`

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

const MEASURES: Record<Measure, (view: LevelView) => number | null> = {
  precision: (view) => view.precision?.value ?? null,
  recall: (view) => view.recall?.value ?? null,
  flagged: (view) => view.flagRate,
}

function measured(level: Level, measure: Measure): (row: ProbeRow) => number | null {
  return (row) => {
    const view = row[level]
    return view ? MEASURES[measure](view) : null
  }
}

const VALUES: Record<SortKey, (row: ProbeRow) => number | string | null> = {
  name: (row) => row.name.toLowerCase(),
  state: (row) => {
    const at = STATE_ORDER.indexOf(row.state ?? '')
    return at === -1 ? STATE_ORDER.length : at
  },
  lift: (row) => row.lift,
  'probable.precision': measured('probable', 'precision'),
  'probable.recall': measured('probable', 'recall'),
  'probable.flagged': measured('probable', 'flagged'),
  'possible.precision': measured('possible', 'precision'),
  'possible.recall': measured('possible', 'recall'),
  'possible.flagged': measured('possible', 'flagged'),
}

/** Rows without a value for the column go last, whichever way it is sorted. */
export function sortRows(rows: ProbeRow[], sort: Sort | null): ProbeRow[] {
  if (!sort) return rows
  const way = sort.descending ? -1 : 1
  const valueOf = VALUES[sort.key]
  return [...rows].sort((a, b) => {
    const left = valueOf(a)
    const right = valueOf(b)
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
