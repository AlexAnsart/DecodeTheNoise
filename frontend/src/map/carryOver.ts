/* What survives when a live map is read again. Points keep their index and new ones are added
   after them, but every per-point array has a new length, and a column's values are coded again
   (they are ranked by frequency). State that names points or codes is translated here. */

import type { Filters } from '../filters/mask'
import type { MapData } from './mapData'

/** A mask on a map of `n` points. The points added since it was made are outside it. */
export function fitMask(mask: Uint8Array, n: number): Uint8Array {
  if (mask.length === n) return mask
  const out = new Uint8Array(n)
  out.set(mask.subarray(0, Math.min(n, mask.length)))
  return out
}

/** Codes of a column of the previous map, as the codes the same values have now. A value that
 *  is gone (a zone renamed, a category emptied) is dropped. */
export function carryCodes(previous: MapData, next: MapData, key: string, codes: number[]): number[] {
  const before = previous.columns.find((column) => column.key === key)
  const after = next.columns.find((column) => column.key === key)
  if (!before || !after) return []
  if (before.names === after.names) return codes
  const codeOf = new Map(after.names.map((name, code) => [name, code]))
  return codes.flatMap((code) => {
    const now = codeOf.get(before.names[code])
    return now === undefined ? [] : [now]
  })
}

/** The same filters on the next map. A search keeps its hits on the points it knew: the search
 *  is run again by its owner to cover the new ones. */
export function carryFilters(filters: Filters, previous: MapData, next: MapData): Filters {
  const values: Record<string, number[]> = {}
  for (const [key, codes] of Object.entries(filters.values)) {
    const carried = carryCodes(previous, next, key, codes)
    if (carried.length > 0) values[key] = carried
  }
  return {
    period: filters.period,
    values,
    search: filters.search ? { query: filters.search.query, hits: fitMask(filters.search.hits, next.n) } : null,
    kept: filters.kept ? { label: filters.kept.label, mask: fitMask(filters.kept.mask, next.n) } : null,
  }
}
