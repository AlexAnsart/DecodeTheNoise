/* The camera lives in a ref and is pushed to deck.gl: first view, change of shape, centring. */

import { useCallback, useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import type { Shape } from './geometry'
import { frameBounds, nearestPoint, pointAt } from './geometry'
import type { Vec3 } from './layers'
import type { MapDeck } from './useDeck'
import type { Size, ViewState } from './views'
import { fitView, isFlat, keepPlace, viewFor } from './views'

/** Within this zoom distance of the whole-map view, a change of shape shows the whole map. */
const NEAR_FIT = 0.5

export interface CameraInput {
  deck: RefObject<MapDeck | null>
  size: Size | null
  shape: Shape
  positions: Float32Array
  gap: number
  kept: Float32Array
  selected: number | null
  /** Places that must stay in view besides the points: the ends of the axes. */
  frame: Vec3[]
}

export interface Camera {
  view: RefObject<ViewState | null>
  onView(view: ViewState): void
  fit(): void
  /** Puts a point in the middle of the free part of the canvas, zoom and angle kept. */
  centreOn(index: number, coveredRight: number): void
}

interface Previous {
  shape: Shape
  positions: Float32Array
  gap: number
}

export function useCamera(input: CameraInput): Camera {
  const { deck, size, shape, positions, gap } = input
  const view = useRef<ViewState | null>(null)
  const previous = useRef<Previous | null>(null)
  const latest = useRef(input)

  useEffect(() => {
    latest.current = input
  })

  const push = useCallback(
    (next: ViewState) => {
      view.current = next
      deck.current?.setProps({ viewState: next })
    },
    [deck],
  )

  const fit = useCallback(() => {
    const now = latest.current
    if (!now.size) return
    push(fitView(now.shape, frameBounds(now.positions, now.kept), now.size, now.frame))
  }, [push])

  const ready = size !== null
  useEffect(() => {
    const now = latest.current
    if (!now.size || !deck.current) return
    const before = previous.current
    previous.current = { shape, positions, gap }
    deck.current.setProps({ views: viewFor(shape) })
    const whole = fitView(shape, frameBounds(positions, now.kept), now.size, now.frame)
    if (!before || !view.current || before.shape === shape) {
      if (!view.current) push(whole)
      return
    }
    const wholeBefore = fitView(before.shape, frameBounds(before.positions, now.kept), now.size)
    const anchor = now.selected ?? nearestPoint(before.positions, view.current.target, now.kept)
    const nearWhole = now.selected === null && Math.abs(view.current.zoom - wholeBefore.zoom) < NEAR_FIT
    if (anchor === null || nearWhole) {
      push(whole)
      return
    }
    const kept = keepPlace(shape, view.current, pointAt(positions, anchor), before.gap, gap)
    // Coming from the flat map there is no angle to keep: the shape opens at its own.
    push(isFlat(before.shape) ? { ...kept, rotationX: whole.rotationX, rotationOrbit: whole.rotationOrbit } : kept)
  }, [deck, shape, positions, gap, ready, push])

  const centreOn = useCallback(
    (index: number, coveredRight: number) => {
      const now = latest.current
      if (!view.current || !now.size) return
      const centred: ViewState = { ...view.current, target: pointAt(now.positions, index) }
      if (coveredRight <= 0) {
        push(centred)
        return
      }
      // Aim at the place that sits half the covered width to the right of the point.
      const viewport = viewFor(now.shape).makeViewport({ ...now.size, viewState: centred })
      if (!viewport) {
        push(centred)
        return
      }
      const [x, y, depth] = viewport.project(centred.target)
      const aim = viewport.unproject([x + coveredRight / 2, y, depth])
      push({ ...centred, target: [aim[0], aim[1], isFlat(now.shape) ? 0 : (aim[2] ?? 0)] })
    },
    [push],
  )

  const onView = useCallback((next: ViewState) => push(next), [push])

  return { view, onView, fit, centreOn }
}
