import type { MapColumn } from '../map/mapData'
import { NO_VALUE } from '../map/mapData'
import type { Option } from '../popover/OptionList'

/** The values of a column that at least one point carries, most frequent first. */
export function columnOptions(column: MapColumn): Option[] {
  const counts = new Uint32Array(column.names.length)
  for (let i = 0; i < column.codes.length; i += 1) {
    const code = column.codes[i]
    if (code !== NO_VALUE) counts[code] += 1
  }
  return Array.from(counts.keys())
    .filter((code) => counts[code] > 0)
    .sort((a, b) => counts[b] - counts[a] || column.names[a].localeCompare(column.names[b]))
    .map((code) => ({ id: code, label: column.names[code], count: counts[code] }))
}
