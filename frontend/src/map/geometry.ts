/* Where each point sits in each shape of the map, and the measures the camera needs. */

import type { MapData } from './mapData'
import { NO_NEIGHBOUR } from './mapData'

/** `2d`: the flat map. `3d`: the meaning layout in depth. `time`: the date on an axis in front
 *  of the upright flat map. `relief`: a score as height above the flat map. */
export type Shape = '2d' | '3d' | 'time' | 'relief'

export interface TimeRange {
  from: number
  to: number
}

export interface Bounds {
  centre: [number, number, number]
  /** Half sizes along x, y, z. */
  half: [number, number, number]
  radius: number
}

const GAP_SAMPLE = 4000
const GAP_NEIGHBOURS = 3
export const TIME_STRETCH = 1.6
export const RELIEF_TOP = 1.2

/** The span holding 99% of the dated points: a few stray dates must not flatten the axis. */
export function busyRange(ts: Float64Array): TimeRange | null {
  const dated = Array.from(ts).filter((t) => t > 0)
  if (dated.length === 0) return null
  dated.sort((a, b) => a - b)
  const at = (share: number): number => dated[Math.min(dated.length - 1, Math.floor(share * dated.length))]
  const from = at(0.005)
  const to = at(0.995)
  return to > from ? { from, to } : { from, to: from + 1 }
}

/** Half side of the flat map, the unit the other shapes are sized by. */
export function flatSpan(data: MapData): number {
  let span = 0
  for (let i = 0; i < data.pos2.length; i += 1) span = Math.max(span, Math.abs(data.pos2[i]))
  return span || 1
}

/** Position of a date on the time axis, in [-1, 1]. */
export function timePlace(t: number, range: TimeRange): number {
  const share = (t - range.from) / (range.to - range.from)
  return Math.min(1, Math.max(0, share)) * 2 - 1
}

export function positionsFor(
  shape: Shape,
  data: MapData,
  range: TimeRange | null,
  heights: Float32Array | null,
): Float32Array {
  if (shape === '3d') return data.pos3
  const { n, pos2, ts } = data
  const out = new Float32Array(n * 3)
  const span = flatSpan(data)
  for (let i = 0; i < n; i += 1) {
    const x = pos2[i * 2]
    const y = pos2[i * 2 + 1]
    if (shape === '2d') {
      out[i * 3] = x
      out[i * 3 + 1] = y
    } else if (shape === 'time') {
      // The flat map stands upright behind the date axis.
      out[i * 3] = range && ts[i] > 0 ? timePlace(ts[i], range) * span * TIME_STRETCH : 0
      out[i * 3 + 1] = x
      out[i * 3 + 2] = -y
    } else {
      const h = heights ? heights[i] : Number.NaN
      out[i * 3] = x
      out[i * 3 + 1] = -y
      out[i * 3 + 2] = Number.isNaN(h) ? 0 : h * span * RELIEF_TOP
    }
  }
  return out
}

/** Typical distance between a point and its nearest stored neighbours, in the given layout.
 *  The point radius and the zoom kept across shapes both derive from it. */
export function neighbourGap(data: MapData, positions: Float32Array): number {
  const { n, k, neighbours } = data
  if (k === 0) return 1
  const step = Math.max(1, Math.floor(n / GAP_SAMPLE))
  const gaps: number[] = []
  for (let i = 0; i < n; i += step) {
    let best = Infinity
    for (let j = 0; j < Math.min(GAP_NEIGHBOURS, k); j += 1) {
      const other = neighbours[i * k + j]
      if (other === NO_NEIGHBOUR) continue
      const dx = positions[i * 3] - positions[other * 3]
      const dy = positions[i * 3 + 1] - positions[other * 3 + 1]
      const dz = positions[i * 3 + 2] - positions[other * 3 + 2]
      best = Math.min(best, Math.hypot(dx, dy, dz))
    }
    if (Number.isFinite(best) && best > 0) gaps.push(best)
  }
  if (gaps.length === 0) return 1
  gaps.sort((a, b) => a - b)
  return gaps[Math.floor(gaps.length / 2)]
}

export function boundsOf(positions: Float32Array, kept?: Float32Array): Bounds {
  const min = [Infinity, Infinity, Infinity]
  const max = [-Infinity, -Infinity, -Infinity]
  const n = positions.length / 3
  for (let i = 0; i < n; i += 1) {
    if (kept && kept[i] < 0.5) continue
    for (let a = 0; a < 3; a += 1) {
      const v = positions[i * 3 + a]
      if (v < min[a]) min[a] = v
      if (v > max[a]) max[a] = v
    }
  }
  if (!Number.isFinite(min[0])) return { centre: [0, 0, 0], half: [1, 1, 1], radius: 1 }
  const centre: [number, number, number] = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2]
  const half: [number, number, number] = [(max[0] - min[0]) / 2, (max[1] - min[1]) / 2, (max[2] - min[2]) / 2]
  // The sphere around the centre that holds every shown point: tighter than the box diagonal.
  let reach = 0
  for (let i = 0; i < n; i += 1) {
    if (kept && kept[i] < 0.5) continue
    const d = (positions[i * 3] - centre[0]) ** 2 + (positions[i * 3 + 1] - centre[1]) ** 2 + (positions[i * 3 + 2] - centre[2]) ** 2
    if (d > reach) reach = d
  }
  return { centre, half, radius: Math.sqrt(reach) || 1 }
}

const FRAME_SAMPLE = 20000
const FRAME_TRIM = 0.005
const FRAME_PAD = 1.08

/** The box the camera frames: the bulk of the shown points. A handful of strays at the far
 *  ends would otherwise shrink the whole map to a corner of the stage. */
export function frameBounds(positions: Float32Array, kept?: Float32Array): Bounds {
  const n = positions.length / 3
  const shown: number[] = []
  for (let i = 0; i < n; i += 1) if (!kept || kept[i] >= 0.5) shown.push(i)
  if (shown.length === 0) return boundsOf(positions, kept)
  const step = Math.max(1, Math.floor(shown.length / FRAME_SAMPLE))
  const centre: [number, number, number] = [0, 0, 0]
  const half: [number, number, number] = [1, 1, 1]
  for (let axis = 0; axis < 3; axis += 1) {
    const values: number[] = []
    for (let j = 0; j < shown.length; j += step) values.push(positions[shown[j] * 3 + axis])
    values.sort((a, b) => a - b)
    const low = values[Math.floor(FRAME_TRIM * (values.length - 1))]
    const high = values[Math.ceil((1 - FRAME_TRIM) * (values.length - 1))]
    centre[axis] = (low + high) / 2
    half[axis] = ((high - low) / 2) * FRAME_PAD
  }
  return { centre, half, radius: Math.hypot(half[0], half[1], half[2]) || 1 }
}

export function pointAt(positions: Float32Array, index: number): [number, number, number] {
  return [positions[index * 3], positions[index * 3 + 1], positions[index * 3 + 2]]
}

/** The shown point nearest to a place, used as the anchor when the shape changes. */
export function nearestPoint(positions: Float32Array, target: number[], kept: Float32Array): number | null {
  let best: number | null = null
  let bestDistance = Infinity
  const n = positions.length / 3
  for (let i = 0; i < n; i += 1) {
    if (kept[i] < 0.5) continue
    const d =
      (positions[i * 3] - target[0]) ** 2 +
      (positions[i * 3 + 1] - target[1]) ** 2 +
      (positions[i * 3 + 2] - (target[2] ?? 0)) ** 2
    if (d < bestDistance) {
      bestDistance = d
      best = i
    }
  }
  return best
}
