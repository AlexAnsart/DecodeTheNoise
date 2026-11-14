/* The pasted text as a point of the map: where it sits in the current shape, and whether it is
   open like a clicked point (label, lines, list of its neighbours). */

import { useCallback, useMemo, useState } from 'react'
import type { Analysis } from '../api/schema'
import type { Shape } from '../map/geometry'
import type { Pasted } from '../map/useMapStage'
import type { PasteState } from './usePaste'

export interface PastedPoint {
  /** The analysis of a text that found its place, null otherwise. */
  analysis: Analysis | null
  /** Where it sits. Null when nothing is placed, or when the shape has no place for it. */
  point: Pasted | null
  setOpen(open: boolean): void
}

export function usePastedPoint(state: PasteState, shape: Shape, selected: number | null): PastedPoint {
  const analysis = state.status === 'done' && state.analysis.outcome === 'placed' ? state.analysis : null
  // Open from the moment it is placed: what is remembered is the placement that was closed.
  const [closed, setClosed] = useState<Analysis | null>(null)
  // One point is open at a time: a selected point of the map takes the place.
  const open = analysis !== null && closed !== analysis && selected === null

  const point = useMemo<Pasted | null>(() => {
    // The date view has no place for a text without a date.
    if (!analysis?.position3 || !analysis.position2 || shape === 'time') return null
    const [x, y] = analysis.position2
    const position: Pasted['position'] = shape === '3d' ? analysis.position3 : shape === '2d' ? [x, y, 0] : [x, -y, 0]
    return { position, neighbours: analysis.neighbours.map((neighbour) => neighbour.index), highlighted: open }
  }, [analysis, shape, open])

  const setOpen = useCallback((next: boolean) => setClosed(next ? null : analysis), [analysis])

  return { analysis, point, setOpen }
}
