/* The state of the map view and the typed arrays derived from it. */

import { useEffect, useMemo, useState } from 'react'
import type { Relief } from '../axes/relief'
import { litPoints, maskOfEntry, maskOfIndices, maskOfPeriod, paintPoints } from '../colour/emphasis'
import type { Palette } from '../colour/palette'
import type { ColouringState } from '../colour/useColouring'
import { useColouring } from '../colour/useColouring'
import type { Filters, Kept } from '../filters/mask'
import { NO_FILTERS, filterMask, keptPoints } from '../filters/mask'
import type { Scrubber } from '../scrubber/useScrubber'
import { useScrubber } from '../scrubber/useScrubber'
import type { Shape, TimeRange } from './geometry'
import { busyRange, neighbourGap, positionsFor } from './geometry'
import type { MapData } from './mapData'

const SHAPE_KEY = 'noisemap.shape'

export interface MapModel {
  shape: Shape
  setShape(shape: Shape): void
  relief: Relief | null
  setRelief(relief: Relief | null): void
  colouring: ColouringState
  filters: Filters
  setFilters(filters: Filters): void
  selected: number | null
  setSelected(index: number | null): void
  /** Points chosen with the lasso. */
  picked: Uint32Array | null
  setPicked(indices: Uint32Array | null): void
  scrubber: Scrubber
  range: TimeRange | null
  positions: Float32Array
  gap: number
  kept: Kept
  colours: Uint8Array
}

function storedShape(): Shape {
  try {
    const value = localStorage.getItem(SHAPE_KEY)
    if (value === '2d' || value === '3d') return value
  } catch {
    // No storage: the map opens in depth.
  }
  return '3d'
}

export function useMapModel(data: MapData, palette: Palette): MapModel {
  const [shape, setShapeState] = useState<Shape>(storedShape)
  const [relief, setReliefState] = useState<Relief | null>(null)
  const [filters, setFilters] = useState<Filters>(NO_FILTERS)
  const [selected, setSelected] = useState<number | null>(null)
  const [picked, setPicked] = useState<Uint32Array | null>(null)
  const colouring = useColouring(data, palette)
  const range = useMemo(() => busyRange(data.ts), [data])
  const scrubber = useScrubber(range)

  const setShape = (next: Shape): void => {
    setShapeState(next)
    if (next !== 'relief') setReliefState(null)
    try {
      if (next === '2d' || next === '3d') localStorage.setItem(SHAPE_KEY, next)
    } catch {
      // Not remembered.
    }
  }
  const setRelief = (next: Relief | null): void => {
    setReliefState(next)
    setShapeState((current) => (next ? 'relief' : current === 'relief' ? '3d' : current))
  }

  const positions = useMemo(
    () => positionsFor(shape, data, range, relief?.heights ?? null),
    [shape, data, range, relief],
  )
  const gaps = useMemo(
    () => ({ deep: neighbourGap(data, data.pos3), flat: neighbourGap(data, positionsFor('2d', data, null, null)) }),
    [data],
  )
  const { legend, hidden, peek } = colouring
  const mask = useMemo(() => filterMask(data, filters, shape), [data, filters, shape])
  const kept = useMemo(
    () => keptPoints(mask, legend.entryOf, legend.entries.length, hidden),
    [mask, legend, hidden],
  )

  const window = scrubber.on ? scrubber.window : null
  const lit = useMemo(() => {
    // A legend row under the pointer overrides every other light.
    if (peek !== null) return maskOfEntry(legend.entryOf, peek)
    return litPoints(data.n, [
      picked ? maskOfIndices(data.n, picked) : null,
      window ? maskOfPeriod(data.ts, window.from, window.to) : null,
    ])
  }, [data, legend, peek, picked, window])
  const colours = useMemo(
    () => paintPoints(legend.base, lit, shape === 'relief' ? (relief?.unread ?? null) : null),
    [legend, lit, relief, shape],
  )

  useEffect(() => {
    // A point the filter hides cannot stay selected: its card would point at nothing.
    if (selected !== null && kept.values[selected] < 0.5) setSelected(null)
  }, [selected, kept])

  return {
    shape,
    setShape,
    relief,
    setRelief,
    colouring,
    filters,
    setFilters,
    selected,
    setSelected,
    picked,
    setPicked,
    scrubber,
    range,
    positions,
    gap: shape === '3d' ? gaps.deep : gaps.flat,
    kept,
    colours,
  }
}
