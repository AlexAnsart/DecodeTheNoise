/* The lasso on the CPU: each shown point is projected to the screen and tested against the
   stroke. In depth it takes everything under the stroke, whatever its distance. */

export type LassoMode = 'new' | 'add' | 'remove' | 'overlap'
export type Stroke = Array<[number, number]>

export const MIN_STROKE_POINTS = 3

export function modeOf(shift: boolean, alt: boolean): LassoMode {
  if (shift && alt) return 'overlap'
  if (shift) return 'add'
  if (alt) return 'remove'
  return 'new'
}

function inside(x: number, y: number, stroke: Stroke): boolean {
  let within = false
  for (let i = 0, j = stroke.length - 1; i < stroke.length; j = i, i += 1) {
    const [xi, yi] = stroke[i]
    const [xj, yj] = stroke[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) within = !within
  }
  return within
}

/** Indices of the shown points whose screen position falls inside the stroke. */
export function pointsInside(
  project: (position: number[]) => number[],
  positions: Float32Array,
  kept: Float32Array,
  stroke: Stroke,
  width: number,
  height: number,
): number[] {
  let left = Infinity
  let right = -Infinity
  let top = Infinity
  let bottom = -Infinity
  for (const [x, y] of stroke) {
    left = Math.min(left, x)
    right = Math.max(right, x)
    top = Math.min(top, y)
    bottom = Math.max(bottom, y)
  }
  const found: number[] = []
  const n = positions.length / 3
  for (let i = 0; i < n; i += 1) {
    if (kept[i] < 0.5) continue
    const [x, y, depth] = project([positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]])
    // Behind the camera, off the canvas, or outside the box of the stroke: no polygon test.
    if (depth !== undefined && (depth < 0 || depth > 1)) continue
    if (x < 0 || y < 0 || x > width || y > height) continue
    if (x < left || x > right || y < top || y > bottom) continue
    if (inside(x, y, stroke)) found.push(i)
  }
  return found
}

/** The selection after a stroke: replace, add to, remove from, or keep only the overlap. */
export function combine(previous: Uint32Array | null, stroke: number[], mode: LassoMode): Uint32Array | null {
  const before = new Set(previous ?? [])
  let next: number[]
  if (mode === 'new') next = stroke
  else if (mode === 'add') next = Array.from(new Set([...before, ...stroke]))
  else if (mode === 'remove') {
    const removed = new Set(stroke)
    next = Array.from(before).filter((index) => !removed.has(index))
  } else next = stroke.filter((index) => before.has(index))
  return next.length > 0 ? Uint32Array.from(next) : null
}
