/* Every filter ends as one byte per point; the legend's hidden entries are subtracted after. */

import type { Shape, TimeRange } from '../map/geometry'
import type { MapData } from '../map/mapData'

export interface Filters {
  period: TimeRange | null
  /** Column key to the codes kept. A column that is absent keeps everything. */
  values: Record<string, number[]>
  /** Points kept by a search, with the words that were searched. */
  search: { query: string; hits: Uint8Array } | null
  /** Points kept from a selection the user chose to filter on. */
  kept: { label: string; mask: Uint8Array } | null
}

export const NO_FILTERS: Filters = { period: null, values: {}, search: null, kept: null }

export function hasFilters(filters: Filters): boolean {
  return (
    filters.period !== null ||
    filters.search !== null ||
    filters.kept !== null ||
    Object.values(filters.values).some((codes) => codes.length > 0)
  )
}

export function filterMask(data: MapData, filters: Filters, shape: Shape): Uint8Array {
  const mask = new Uint8Array(data.n).fill(1)
  const { period, search, kept } = filters
  if (period || shape === 'time') {
    for (let i = 0; i < data.n; i += 1) {
      const t = data.ts[i]
      // The time shape has no place for an undated point.
      if (!(t > 0) || (period && (t < period.from || t > period.to))) mask[i] = 0
    }
  }
  for (const [key, codes] of Object.entries(filters.values)) {
    const column = data.columns.find((c) => c.key === key)
    if (!column || codes.length === 0) continue
    const allowed = new Set(codes)
    for (let i = 0; i < data.n; i += 1) if (!allowed.has(column.codes[i])) mask[i] = 0
  }
  for (const part of [search?.hits, kept?.mask]) {
    if (!part) continue
    for (let i = 0; i < data.n; i += 1) if (part[i] !== 1) mask[i] = 0
  }
  return mask
}

export interface Kept {
  /** 1 for a point drawn, 0 for a hidden one: the value the GPU filter reads. */
  values: Float32Array
  shown: number
  /** Points shown per legend entry, under the filters (hidden entries included). */
  perEntry: Uint32Array
}

export function keptPoints(mask: Uint8Array, entryOf: Uint16Array, entries: number, hidden: ReadonlySet<number>): Kept {
  const values = new Float32Array(mask.length)
  const perEntry = new Uint32Array(entries)
  let shown = 0
  for (let i = 0; i < mask.length; i += 1) {
    if (mask[i] !== 1) continue
    perEntry[entryOf[i]] += 1
    if (hidden.has(entryOf[i])) continue
    values[i] = 1
    shown += 1
  }
  return { values, shown, perEntry }
}
