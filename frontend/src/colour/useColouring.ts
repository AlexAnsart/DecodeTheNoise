/* What colours the map: a column, the date or a probe, or groups composed by the user. */

import { useCallback, useMemo, useState } from 'react'
import { fitMask } from '../map/carryOver'
import type { MapData } from '../map/mapData'
import { probeLegend } from '../probes/probeLegend'
import { useProbeScores } from '../probes/useProbeScores'
import type { Colouring, Legend, PaintGroup } from './legend'
import { buildLegend, defaultColouring } from './legend'
import type { Palette } from './palette'

const STORAGE_KEY = 'noisemap.colouring'
const PROBE_PREFIX = 'probe:'

export interface ColouringState {
  /** The attribute that colours the map: the one chosen in the menu when this map has it. */
  choice: Colouring
  composed: PaintGroup[] | null
  legend: Legend
  hidden: ReadonlySet<number>
  /** Legend entry under the pointer: only its points stay lit while it is hovered. */
  peek: number | null
  choose(colouring: Colouring): void
  compose(groups: PaintGroup[] | null): void
  toggle(entry: number): void
  solo(entry: number): void
  hideAll(hide: boolean): void
  setPeek(entry: number | null): void
}

function storedChoice(): Colouring | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'date') return { kind: 'date' }
    if (value?.startsWith(PROBE_PREFIX)) return { kind: 'probe', key: value.slice(PROBE_PREFIX.length) }
    if (value) return { kind: 'column', key: value }
  } catch {
    // No storage: the default colouring applies.
  }
  return null
}

function remember(colouring: Colouring): void {
  try {
    if (colouring.kind === 'date') localStorage.setItem(STORAGE_KEY, 'date')
    else if (colouring.kind === 'column') localStorage.setItem(STORAGE_KEY, colouring.key)
    else if (colouring.kind === 'probe') localStorage.setItem(STORAGE_KEY, `${PROBE_PREFIX}${colouring.key}`)
  } catch {
    // Not remembered.
  }
}

/** Whether this map has what the colouring reads. A growing map gains columns and probes. */
function applies(colouring: Colouring, data: MapData): boolean {
  if (colouring.kind === 'column') return data.columns.some((column) => column.key === colouring.key)
  if (colouring.kind === 'probe') return data.probes.some((probe) => probe.key === colouring.key && probe.state === 'shown')
  return true
}

export function useColouring(data: MapData, palette: Palette): ColouringState {
  const [chosen, setChosen] = useState<Colouring | null>(storedChoice)
  const [composed, setComposed] = useState<PaintGroup[] | null>(null)
  // Hidden entries are kept by label: a map that grows ranks its entries again.
  const [hiddenLabels, setHiddenLabels] = useState<ReadonlySet<string>>(new Set())
  const [peek, setPeek] = useState<number | null>(null)
  const [seen, setSeen] = useState(data)
  if (seen !== data) {
    // The map was read again: the composed groups keep their points, on the new size.
    setSeen(data)
    if (composed) setComposed(composed.map((group) => ({ label: group.label, mask: fitMask(group.mask, data.n) })))
  }

  const choice = useMemo(() => (chosen && applies(chosen, data) ? chosen : defaultColouring(data)), [chosen, data])
  const probe = useProbeScores(data, !composed && choice.kind === 'probe' ? choice.key : null)

  const legend = useMemo(() => {
    if (composed) return buildLegend(data, { kind: 'groups', groups: composed }, palette)
    if (choice.kind === 'probe') return probeLegend(data, choice.key, probe, palette)
    return buildLegend(data, choice, palette)
  }, [data, choice, composed, palette, probe])

  const hidden = useMemo(() => {
    const ids = new Set<number>()
    for (const entry of legend.entries) if (hiddenLabels.has(entry.label)) ids.add(entry.id)
    return ids
  }, [legend, hiddenLabels])

  const reset = useCallback(() => {
    setHiddenLabels(new Set())
    setPeek(null)
  }, [])

  const choose = useCallback(
    (colouring: Colouring) => {
      setChosen(colouring)
      setComposed(null)
      remember(colouring)
      reset()
    },
    [reset],
  )

  const compose = useCallback(
    (groups: PaintGroup[] | null) => {
      setComposed(groups)
      reset()
    },
    [reset],
  )

  const toggle = useCallback(
    (entry: number) => {
      const label = legend.entries.find((candidate) => candidate.id === entry)?.label
      if (label === undefined) return
      setHiddenLabels((previous) => {
        const next = new Set(previous)
        if (next.has(label)) next.delete(label)
        else next.add(label)
        return next
      })
    },
    [legend],
  )

  const solo = useCallback(
    (entry: number) => {
      const label = legend.entries.find((candidate) => candidate.id === entry)?.label
      if (label === undefined) return
      setHiddenLabels((previous) => {
        const others = legend.entries.filter((candidate) => candidate.id !== entry).map((candidate) => candidate.label)
        const alreadyAlone = !previous.has(label) && others.every((other) => previous.has(other))
        return new Set(alreadyAlone ? [] : others)
      })
    },
    [legend],
  )

  const hideAll = useCallback(
    (hide: boolean) => setHiddenLabels(new Set(hide ? legend.entries.map((entry) => entry.label) : [])),
    [legend],
  )

  return { choice, composed, legend, hidden, peek, choose, compose, toggle, solo, hideAll, setPeek }
}
