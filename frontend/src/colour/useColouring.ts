/* What colours the map: a column or the date, or groups composed by the user on top of it. */

import { useCallback, useMemo, useState } from 'react'
import type { MapData } from '../map/mapData'
import type { Colouring, Legend, PaintGroup } from './legend'
import { buildLegend, defaultColouring } from './legend'
import type { Palette } from './palette'

const STORAGE_KEY = 'noisemap.colouring'

export interface ColouringState {
  /** The attribute chosen in the colour menu. */
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

function storedChoice(data: MapData): Colouring {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'date') return { kind: 'date' }
    if (value && data.columns.some((column) => column.key === value)) return { kind: 'column', key: value }
  } catch {
    // No storage: the default colouring applies.
  }
  return defaultColouring(data)
}

function remember(colouring: Colouring): void {
  try {
    if (colouring.kind === 'date') localStorage.setItem(STORAGE_KEY, 'date')
    else if (colouring.kind === 'column') localStorage.setItem(STORAGE_KEY, colouring.key)
  } catch {
    // Not remembered.
  }
}

export function useColouring(data: MapData, palette: Palette): ColouringState {
  const [choice, setChoice] = useState<Colouring>(() => storedChoice(data))
  const [composed, setComposed] = useState<PaintGroup[] | null>(null)
  const [hidden, setHidden] = useState<ReadonlySet<number>>(new Set())
  const [peek, setPeek] = useState<number | null>(null)

  const legend = useMemo(
    () => buildLegend(data, composed ? { kind: 'groups', groups: composed } : choice, palette),
    [data, choice, composed, palette],
  )

  const reset = useCallback(() => {
    setHidden(new Set())
    setPeek(null)
  }, [])

  const choose = useCallback(
    (colouring: Colouring) => {
      setChoice(colouring)
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

  const toggle = useCallback((entry: number) => {
    setHidden((previous) => {
      const next = new Set(previous)
      if (next.has(entry)) next.delete(entry)
      else next.add(entry)
      return next
    })
  }, [])

  const solo = useCallback(
    (entry: number) => {
      setHidden((previous) => {
        const others = legend.entries.filter((e) => e.id !== entry).map((e) => e.id)
        const alreadyAlone = !previous.has(entry) && others.every((id) => previous.has(id))
        return new Set(alreadyAlone ? [] : others)
      })
    },
    [legend],
  )

  const hideAll = useCallback(
    (hide: boolean) => setHidden(new Set(hide ? legend.entries.map((e) => e.id) : [])),
    [legend],
  )

  return { choice, composed, legend, hidden, peek, choose, compose, toggle, solo, hideAll, setPeek }
}
