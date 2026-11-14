/* The paste box on the map: the panel, the pasted text as a point, the list of its nearest
   items, and the camera coming onto it once it is placed. */

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Analysis } from '../api/schema'
import { pointAt } from '../map/geometry'
import type { MapModel } from '../map/useMapModel'
import type { Pasted, Stage } from '../map/useMapStage'
import type { Paste } from './usePaste'
import { usePaste } from './usePaste'
import { usePastedPoint } from './usePastedPoint'

/** Width the paste panel covers on the right of the stage, margins included. */
const PASTE_PANEL_WIDTH = 396

export interface PasteFlow {
  paste: Paste
  /** The analysis of a text that found its place, null otherwise. */
  analysis: Analysis | null
  /** Where the pasted text sits in the current shape, when it has a place. */
  pasted: Pasted | null
  /** While it is open: its nearest items the filters still show. */
  neighbours: number[] | null
  /** The panel is open. */
  pasting: boolean
  setPasting(open: boolean): void
  /** Opens the pasted point like a clicked one, or closes it. */
  setOpen(open: boolean): void
  /** Asks the camera to come onto the pasted text. */
  locate(): void
  /** How many times the camera was asked: a new count is a new ask. */
  locateAsked: number
}

export function usePasteFlow(model: MapModel, lasso: boolean): PasteFlow {
  const { shape, selected, kept, setSelected } = model
  const [pasting, setPasting] = useState(false)
  const [locateAsked, setLocateAsked] = useState(0)
  const paste = usePaste()
  const { analysis, point: pasted, setOpen } = usePastedPoint(paste.state, shape, selected)
  const neighbours = useMemo(
    () => (pasted?.highlighted && !lasso ? pasted.neighbours.filter((other) => kept.values[other] >= 0.5) : null),
    [pasted, lasso, kept],
  )
  const locate = useCallback(() => setLocateAsked((count) => count + 1), [])

  useEffect(() => {
    // A text that has just been placed opens like a clicked point: the panel gives way to the
    // list of its neighbours, and the camera is asked to go to it.
    if (!analysis) return
    setSelected(null)
    setPasting(false)
    locate()
    // Only a new placement does this, not a change of what surrounds it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis])

  return { paste, analysis, pasted, neighbours, pasting, setPasting, setOpen, locate, locateAsked }
}

/** Brings the camera onto the pasted text each time it is asked, close enough to read the
 *  items it is tied to. Runs after the render that opened the list, so the width the list
 *  covers is known. */
export function usePasteLocate(flow: PasteFlow, model: MapModel, stage: Stage, coveredRight: () => number): void {
  const { pasted, pasting, locateAsked } = flow
  const { positions } = model
  const { centreAt } = stage.camera

  useEffect(() => {
    if (locateAsked === 0 || !pasted) return
    // The typical distance to its nearest items: one far neighbour must not keep the camera away.
    const distances = pasted.neighbours
      .map((other) => {
        const at = pointAt(positions, other)
        return Math.hypot(at[0] - pasted.position[0], at[1] - pasted.position[1], at[2] - pasted.position[2])
      })
      .sort((a, b) => a - b)
    const reach = distances[Math.floor(distances.length / 2)] ?? 0
    centreAt(pasted.position, coveredRight() + (pasting ? PASTE_PANEL_WIDTH : 0), reach)
    // Only an ask moves the camera, not a change of what surrounds the pasted text.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locateAsked])
}
