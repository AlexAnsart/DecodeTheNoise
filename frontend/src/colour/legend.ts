/* A colouring turns one attribute of the points into a legend and a base colour per point. */

import type { MapColumn, MapData } from '../map/mapData'
import { NO_VALUE } from '../map/mapData'
import type { Rgb } from '../theme/theme'
import type { Palette } from './palette'
import { ALPHA_FULL, ALPHA_NO_VALUE, ALPHA_OTHERS, ALPHA_REST, PALETTE_SIZE, cycledColour } from './palette'
import { dateBase } from './dateColouring'
import type { DateBar } from './dateColouring'

export interface PaintGroup {
  label: string
  /** One byte per point, 1 when the point belongs to the group. */
  mask: Uint8Array
}

/** A colouring read from the map itself. */
export type PlainColouring =
  | { kind: 'column'; key: string }
  | { kind: 'date' }
  | { kind: 'groups'; groups: PaintGroup[] }

/** A probe colouring also needs the scores of the probe: see probes/probeLegend.ts. */
export type Colouring = PlainColouring | { kind: 'probe'; key: string }

export interface LegendEntry {
  id: number
  label: string
  colour: Rgb
  alpha: number
  /** Points of the whole map in this entry. */
  total: number
  hint?: string
  /** Code in the column, when the entry is one value of a column. */
  code?: number
}

export interface Legend {
  title: string
  entries: LegendEntry[]
  /** Per point, the id of its entry. */
  entryOf: Uint16Array
  /** RGBA per point at full strength. */
  base: Uint8Array
  dateBar: DateBar | null
  /** A sentence under the title: what the colours were measured to be worth, or what is missing. */
  note: string | null
}

/** Columns whose every value keeps its own colour instead of falling into "Others". */
const DISTINCT_COLUMNS = new Set(['zone'])

function fill(base: Uint8Array, i: number, colour: Rgb, alpha: number): void {
  base[i * 4] = colour[0]
  base[i * 4 + 1] = colour[1]
  base[i * 4 + 2] = colour[2]
  base[i * 4 + 3] = alpha
}

export function paintEntries(n: number, entries: LegendEntry[], entryOf: Uint16Array): Uint8Array {
  const base = new Uint8Array(n * 4)
  for (let i = 0; i < n; i += 1) {
    const entry = entries[entryOf[i]]
    fill(base, i, entry.colour, entry.alpha)
  }
  return base
}

function columnLegend(data: MapData, column: MapColumn, palette: Palette): Legend {
  const counts = new Uint32Array(column.names.length)
  let none = 0
  for (let i = 0; i < data.n; i += 1) {
    const code = column.codes[i]
    if (code === NO_VALUE) none += 1
    else counts[code] += 1
  }
  // Ranked on the whole map, so a filter never repaints a category.
  const ranked = Array.from(counts.keys())
    .filter((code) => counts[code] > 0)
    .sort((a, b) => counts[b] - counts[a] || column.names[a].localeCompare(column.names[b]))
  const distinct = DISTINCT_COLUMNS.has(column.key)
  const own = distinct ? ranked : ranked.slice(0, PALETTE_SIZE)
  const entries: LegendEntry[] = own.map((code, k) => ({
    id: k,
    label: column.names[code],
    colour: cycledColour(palette, k),
    alpha: ALPHA_FULL,
    total: counts[code],
    code,
    hint: column.key === 'zone' ? data.zones[code]?.words.join(' · ') : undefined,
  }))
  const entryOfCode = new Int32Array(column.names.length).fill(-1)
  own.forEach((code, k) => {
    entryOfCode[code] = k
  })
  let othersId = -1
  if (ranked.length > own.length) {
    othersId = entries.length
    const total = ranked.slice(own.length).reduce((sum, code) => sum + counts[code], 0)
    entries.push({ id: othersId, label: 'Others', colour: palette.others, alpha: ALPHA_OTHERS, total })
  }
  let noneId = -1
  if (none > 0) {
    noneId = entries.length
    entries.push({ id: noneId, label: 'No value', colour: palette.others, alpha: ALPHA_NO_VALUE, total: none })
  }
  const entryOf = new Uint16Array(data.n)
  for (let i = 0; i < data.n; i += 1) {
    const code = column.codes[i]
    entryOf[i] = code === NO_VALUE ? noneId : entryOfCode[code] >= 0 ? entryOfCode[code] : othersId
  }
  return { title: column.label, entries, entryOf, base: paintEntries(data.n, entries, entryOf), dateBar: null, note: null }
}

function groupsLegend(data: MapData, groups: PaintGroup[], palette: Palette): Legend {
  const entries: LegendEntry[] = groups.map((group, k) => ({
    id: k,
    label: group.label,
    colour: palette.categories[k % PALETTE_SIZE],
    alpha: ALPHA_FULL,
    total: 0,
  }))
  const restId = entries.length
  entries.push({ id: restId, label: 'The rest', colour: palette.rest, alpha: ALPHA_REST, total: 0 })
  const entryOf = new Uint16Array(data.n)
  for (let i = 0; i < data.n; i += 1) {
    // A point in several groups takes the first.
    const k = groups.findIndex((group) => group.mask[i] === 1)
    entryOf[i] = k >= 0 ? k : restId
    entries[entryOf[i]].total += 1
  }
  return { title: 'Composed colours', entries, entryOf, base: paintEntries(data.n, entries, entryOf), dateBar: null, note: null }
}

function dateLegend(data: MapData, palette: Palette): Legend {
  const { base, bar, undated } = dateBase(data.ts, palette)
  const entries: LegendEntry[] = [
    { id: 0, label: 'Dated', colour: palette.dateStops[2], alpha: ALPHA_FULL, total: data.n - undated },
  ]
  const entryOf = new Uint16Array(data.n)
  if (undated > 0) {
    entries.push({ id: 1, label: 'No date', colour: palette.others, alpha: ALPHA_NO_VALUE, total: undated })
    for (let i = 0; i < data.n; i += 1) if (!(data.ts[i] > 0)) entryOf[i] = 1
  }
  return { title: 'Date', entries, entryOf, base, dateBar: bar, note: null }
}

export function buildLegend(data: MapData, colouring: PlainColouring, palette: Palette): Legend {
  if (colouring.kind === 'date') return dateLegend(data, palette)
  if (colouring.kind === 'groups') return groupsLegend(data, colouring.groups, palette)
  const column = data.columns.find((c) => c.key === colouring.key) ?? data.columns[0]
  // A map can have no column at all (a workspace before its first items are described).
  return column ? columnLegend(data, column, palette) : dateLegend(data, palette)
}

/** The colouring a map opens with: zones when it has some, else its first column, else dates. */
export function defaultColouring(data: MapData): PlainColouring {
  if (data.columns.some((column) => column.key === 'zone')) return { kind: 'column', key: 'zone' }
  if (data.columns.length > 0) return { kind: 'column', key: data.columns[0].key }
  return { kind: 'date' }
}
