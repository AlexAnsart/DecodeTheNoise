/* The two cameras of the map and how each shape is framed. */

import { OrbitView, OrthographicView } from '@deck.gl/core'
import type { Bounds, Shape } from './geometry'

export interface ViewState {
  target: [number, number, number]
  zoom: number
  rotationX?: number
  rotationOrbit?: number
  minZoom: number
  maxZoom: number
}

/** What deck.gl hands back after a gesture, read into the shape this app keeps. */
export function readView(raw: {
  target?: number[]
  zoom?: number | [number, number]
  rotationX?: number
  rotationOrbit?: number
}): ViewState {
  const target = raw.target ?? []
  const zoom = Array.isArray(raw.zoom) ? raw.zoom[0] : (raw.zoom ?? 0)
  return {
    target: [target[0] ?? 0, target[1] ?? 0, target[2] ?? 0],
    zoom,
    rotationX: raw.rotationX,
    rotationOrbit: raw.rotationOrbit,
    ...ZOOM_BOUNDS,
  }
}

export interface Size {
  width: number
  height: number
}

const ZOOM_BOUNDS = { minZoom: -6, maxZoom: 16 }
const FLAT_MARGIN = 40
const ANGLED_MARGIN = 70

const OPENING_ANGLES: Record<Exclude<Shape, '2d'>, { rotationX: number; rotationOrbit: number }> = {
  '3d': { rotationX: 30, rotationOrbit: 20 },
  time: { rotationX: 14, rotationOrbit: -16 },
  relief: { rotationX: 36, rotationOrbit: -24 },
}

export function isFlat(shape: Shape): boolean {
  return shape === '2d'
}

/** Two ids on purpose: reusing one id across view types keeps the old controller alive. */
export function viewFor(shape: Shape): OrthographicView | OrbitView {
  return isFlat(shape)
    ? new OrthographicView({ id: 'flat', flipY: true })
    : new OrbitView({ id: 'deep', orbitAxis: 'Z', fovy: 50 })
}

/** The whole map in view, at the opening angle of the shape. */
export function fitView(shape: Shape, bounds: Bounds, size: Size): ViewState {
  if (shape === '2d') {
    const zoom = -Math.log2(
      Math.max(
        (2 * bounds.half[0]) / Math.max(1, size.width - FLAT_MARGIN),
        (2 * bounds.half[1]) / Math.max(1, size.height - FLAT_MARGIN),
      ),
    )
    return { target: [bounds.centre[0], bounds.centre[1], 0], zoom, ...ZOOM_BOUNDS }
  }
  const margin = shape === '3d' ? FLAT_MARGIN : ANGLED_MARGIN
  const room = Math.max(1, Math.min(size.width, size.height) - margin)
  // An angled, stretched shape needs a little more room than its sphere suggests.
  const tighten = shape === '3d' ? 0 : 0.25
  return {
    target: bounds.centre,
    zoom: -Math.log2((2 * bounds.radius) / room) + tighten,
    ...OPENING_ANGLES[shape],
    ...ZOOM_BOUNDS,
  }
}

/** Same place after a change of shape: the anchor stays in the middle, and the zoom shifts so
 *  that about as many neighbours stay on screen. */
export function keepPlace(
  shape: Shape,
  previous: ViewState,
  anchor: [number, number, number],
  gapFrom: number,
  gapTo: number,
): ViewState {
  const zoom = previous.zoom - Math.log2(gapTo / gapFrom)
  if (shape === '2d') return { target: [anchor[0], anchor[1], 0], zoom, ...ZOOM_BOUNDS }
  const angles =
    previous.rotationX === undefined || previous.rotationOrbit === undefined
      ? OPENING_ANGLES[shape]
      : { rotationX: previous.rotationX, rotationOrbit: previous.rotationOrbit }
  return { target: anchor, zoom, ...angles, ...ZOOM_BOUNDS }
}
