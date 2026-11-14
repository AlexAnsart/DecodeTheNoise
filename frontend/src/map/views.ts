/* The two cameras of the map and how each shape is framed. */

import { OrbitView, OrthographicView } from '@deck.gl/core'
import type { Bounds, Shape } from './geometry'
import type { Vec3 } from './layers'

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
/** The fit in depth searches the zoom this far around a first guess, in this many passes. */
const FIT_SEARCH_OUT = 3
const FIT_SEARCH_IN = 2
const FIT_PASSES = 16

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

function corners(bounds: Bounds): Vec3[] {
  const out: Vec3[] = []
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      for (const sz of [-1, 1]) {
        out.push([
          bounds.centre[0] + sx * bounds.half[0],
          bounds.centre[1] + sy * bounds.half[1],
          bounds.centre[2] + sz * bounds.half[2],
        ])
      }
    }
  }
  return out
}

/** How far the places that must stay in view spill out of the stage, the camera aimed at the
 *  centre: 1 touches the margin, more than 1 is cut. */
function spill(shape: Shape, state: ViewState, points: Vec3[], size: Size, margin: number): number {
  const viewport = viewFor(shape).makeViewport({ ...size, viewState: state })
  if (!viewport) return Infinity
  const roomX = Math.max(1, (size.width - margin) / 2)
  const roomY = Math.max(1, (size.height - margin) / 2)
  let worst = 0
  for (const point of points) {
    const [x, y] = viewport.project(point)
    worst = Math.max(worst, Math.abs(x - size.width / 2) / roomX, Math.abs(y - size.height / 2) / roomY)
  }
  return worst
}

/** The whole map in view, at the opening angle of the shape. `frame` lists places that must
 *  stay in view besides the points: the ends of the axes and their words. */
export function fitView(shape: Shape, bounds: Bounds, size: Size, frame: Vec3[] = []): ViewState {
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
  const state: ViewState = {
    target: bounds.centre,
    zoom: -Math.log2((2 * bounds.radius) / room),
    ...OPENING_ANGLES[shape],
    ...ZOOM_BOUNDS,
  }
  // With perspective the size on screen is not linear in the zoom: search the closest zoom at
  // which nothing is cut. The size grows with the zoom, so a bisection finds it.
  const points = [...corners(bounds), ...frame]
  let low = state.zoom - FIT_SEARCH_OUT
  let high = state.zoom + FIT_SEARCH_IN
  for (let pass = 0; pass < FIT_PASSES; pass += 1) {
    const middle = (low + high) / 2
    if (spill(shape, { ...state, zoom: middle }, points, size, margin) > 1) high = middle
    else low = middle
  }
  return { ...state, zoom: low }
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
