/* What the map does where the browser draws on the CPU (no GPU acceleration). There, drawing
   every point of a large map blocks the page for tens of seconds, and so does asking the canvas
   which point is under the pointer. So a fixed sample of the points is drawn, and picking is
   done here, by projecting the points. The sample is a view: indices stay those of the map,
   and filters, colours and counts are untouched. With a GPU nothing of this applies. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { pickPoint } from './cpuPick'
import { onSample, sampleIndices } from './sample'
import type { Renderer } from './useDeck'

/** Points drawn in software. Measured on the 500,000-point map with SwiftShader: a frame costs
 *  about 25 µs a point, so 100,000 points take about 2.5 s to draw. */
export const SOFTWARE_SAMPLE = 100_000
/** How near the pointer a point must be drawn to be picked, in pixels. */
const PICK_RADIUS_PX = 6

export interface Sampling {
  /** Points of the sample, and points of the map. */
  sample: number
  total: number
  /** `sample`: the sample is drawn. `drawing`: every point is being drawn, the page is about
   *  to stop answering. `all`: every point is drawn. */
  state: 'sample' | 'drawing' | 'all'
  showAll(): void
  showSample(): void
}

export interface SoftwareGuard {
  /** False until the renderer is known: no point is given to the canvas before. */
  ready: boolean
  /** The GPU answers picking. False in software: picking is done on the CPU. */
  gpuPicking: boolean
  /** The points drawn, in ascending order; null when every point is. */
  sample: Uint32Array | null
  /** One value per point: its filter value where it is drawn, 0 where the sample leaves it out. */
  drawn: Float32Array
  /** Set where the sample applies: a large map, drawn in software. */
  notice: Sampling | null
  /** The drawn point under a place of the canvas, found on the CPU. */
  pickAt(x: number, y: number): number | null
  /** Tells the guard a frame was drawn: the wait for the full cloud ends there. */
  frameDrawn(): void
}

interface GuardInput {
  renderer: Renderer
  n: number
  positions: Float32Array
  kept: Float32Array
  selected: number | null
  host: RefObject<HTMLDivElement | null>
  /** Shows or hides the tooltip of a point. */
  onHover(index: number | null, x: number, y: number): void
  pixelMatrix(): number[] | null
}

export function useSoftwareGuard(input: GuardInput): SoftwareGuard {
  const { renderer, n, positions, kept, selected, host, onHover, pixelMatrix } = input
  const software = renderer === 'software'
  // A small map is never sampled: it draws fast enough anywhere.
  const sampled = software && n > SOFTWARE_SAMPLE
  const [all, setAll] = useState(false)
  const [pending, setPending] = useState(false)
  const indices = useMemo(() => (sampled ? sampleIndices(n, SOFTWARE_SAMPLE) : null), [sampled, n])
  const sample = all ? null : indices
  const drawn = useMemo(() => (sample ? onSample(kept, sample) : kept), [kept, sample])
  const latest = useRef({ positions, drawn, sample, selected })

  useEffect(() => {
    latest.current = { positions, drawn, sample, selected }
  })

  const pickAt = useCallback(
    (x: number, y: number): number | null => {
      const matrix = pixelMatrix()
      const now = latest.current
      return matrix ? pickPoint(matrix, now.positions, now.drawn, now.sample, x, y, PICK_RADIUS_PX) : null
    },
    [pixelMatrix],
  )

  // In software the canvas is not asked what is under the pointer: the answer is computed
  // here, once per frame at most, from the last place of the pointer.
  useEffect(() => {
    const node = host.current
    if (!software || !node) return undefined
    let frame = 0
    let at: { x: number; y: number } | null = null
    const answer = (): void => {
      frame = 0
      const hit = at ? pickAt(at.x, at.y) : null
      onHover(hit !== null && hit !== latest.current.selected ? hit : null, at?.x ?? -1, at?.y ?? -1)
    }
    const ask = (): void => {
      if (frame === 0) frame = requestAnimationFrame(answer)
    }
    const onMove = (event: PointerEvent): void => {
      // While a button is held the map is being moved: nothing is hovered.
      if (event.buttons !== 0) return
      const box = node.getBoundingClientRect()
      at = { x: event.clientX - box.left, y: event.clientY - box.top }
      ask()
    }
    const onLeave = (): void => {
      at = null
      ask()
    }
    node.addEventListener('pointermove', onMove)
    node.addEventListener('pointerleave', onLeave)
    return () => {
      cancelAnimationFrame(frame)
      node.removeEventListener('pointermove', onMove)
      node.removeEventListener('pointerleave', onLeave)
    }
  }, [software, host, onHover, pickAt])

  const showAll = useCallback(() => {
    setAll(true)
    setPending(true)
  }, [])
  const showSample = useCallback(() => {
    setAll(false)
    setPending(false)
  }, [])
  const frameDrawn = useCallback(() => setPending(false), [])

  const notice = useMemo<Sampling | null>(
    () => (indices ? { sample: indices.length, total: n, state: !all ? 'sample' : pending ? 'drawing' : 'all', showAll, showSample } : null),
    [indices, n, all, pending, showAll, showSample],
  )

  return { ready: renderer !== 'unknown', gpuPicking: !software, sample, drawn, notice, pickAt, frameDrawn }
}
