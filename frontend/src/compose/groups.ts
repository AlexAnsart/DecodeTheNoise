/* Composed colours: the user defines a few groups of points, and each group takes a colour. */

import { maskOfIndices, maskOfPeriod } from '../colour/emphasis'
import type { PaintGroup } from '../colour/legend'
import { columnOptions } from '../filters/columnOptions'
import type { MapData } from '../map/mapData'
import { formatDay } from '../text/format'

export const MIN_GROUPS = 2
export const MAX_GROUPS = 6

/** `column:<key>` for one value of an attribute, or one of the three other kinds. */
export type GroupKind = `column:${string}` | 'period' | 'selection' | 'filters'

export interface Draft {
  kind: GroupKind
  /** Code of the chosen value, for a column. */
  value: number | null
  from: number | null
  to: number | null
}

export interface DraftSources {
  data: MapData
  /** Points chosen with the lasso, when there are some. */
  selection: Uint32Array | null
  /** Points the filters on screen keep, when a filter is on. */
  filtered: Uint8Array | null
}

export interface KindOption {
  kind: GroupKind
  label: string
  /** Why the kind has nothing to pick, when it has not. */
  disabled: string | null
}

export function kindOptions(sources: DraftSources): KindOption[] {
  const hasDates = sources.data.ts.some((t) => t > 0)
  return [
    ...sources.data.columns.map((column) => ({ kind: `column:${column.key}` as const, label: column.label, disabled: null })),
    { kind: 'period', label: 'A period', disabled: hasDates ? null : 'No item of this map is dated.' },
    { kind: 'selection', label: 'The selection', disabled: sources.selection ? null : 'Select points with the lasso first.' },
    { kind: 'filters', label: 'The filters on screen', disabled: sources.filtered ? null : 'No filter is on.' },
  ]
}

export function emptyDraft(kind: GroupKind): Draft {
  return { kind, value: null, from: null, to: null }
}

/** Two groups to start from: the two most frequent values of the first plain attribute. */
export function openingDrafts(data: MapData): Draft[] {
  const column = data.columns.find((c) => c.key !== 'zone' && c.key !== 'actor') ?? data.columns[0]
  if (!column) return [emptyDraft('period'), emptyDraft('period')]
  const [first, second] = columnOptions(column)
  const kind: GroupKind = `column:${column.key}`
  return [
    { ...emptyDraft(kind), value: first?.id ?? null },
    { ...emptyDraft(kind), value: second?.id ?? null },
  ]
}

/** The group a draft describes, or null while it is incomplete. */
export function draftGroup(draft: Draft, sources: DraftSources): PaintGroup | null {
  const { data } = sources
  if (draft.kind === 'period') {
    if (draft.from === null || draft.to === null || draft.to < draft.from) return null
    return { label: `${formatDay(draft.from)} – ${formatDay(draft.to)}`, mask: maskOfPeriod(data.ts, draft.from, draft.to) }
  }
  if (draft.kind === 'selection') {
    return sources.selection ? { label: 'The selection', mask: maskOfIndices(data.n, sources.selection) } : null
  }
  if (draft.kind === 'filters') {
    return sources.filtered ? { label: 'The filters on screen', mask: sources.filtered } : null
  }
  const column = data.columns.find((c) => `column:${c.key}` === draft.kind)
  if (!column || draft.value === null) return null
  const mask = new Uint8Array(data.n)
  for (let i = 0; i < data.n; i += 1) if (column.codes[i] === draft.value) mask[i] = 1
  return { label: column.names[draft.value], mask }
}

/** Groups that hold at least one point. Fewer than two means there is nothing to compare. */
export function paintedGroups(drafts: Draft[], sources: DraftSources): PaintGroup[] {
  return drafts
    .map((draft) => draftGroup(draft, sources))
    .filter((group): group is PaintGroup => group !== null && group.mask.includes(1))
}
