/* Picking on the CPU: the drawn point under the pointer, found by projecting the points to the
   screen. Used where the GPU cannot be asked: a browser that draws in software answers a
   picking pass as slowly as it draws a frame, and blocks the page meanwhile. Pure. */

/** The drawn point nearest to (x, y) on the screen, within `radius` pixels; of two as near, the
 *  one in front. `matrix` is the 4x4 world-to-pixel matrix of the view, column-major, origin
 *  at the top left. `sample` lists the points to try, or is null for every point. Null when no
 *  drawn point is that close. */
export function pickPoint(
  matrix: ArrayLike<number>,
  positions: Float32Array,
  drawn: Float32Array,
  sample: Uint32Array | null,
  x: number,
  y: number,
  radius: number,
): number | null {
  const count = sample ? sample.length : positions.length / 3
  let best: number | null = null
  let bestDistance = radius * radius
  let bestDepth = Infinity
  for (let k = 0; k < count; k += 1) {
    const i = sample ? sample[k] : k
    if (drawn[i] < 0.5) continue
    const px = positions[i * 3]
    const py = positions[i * 3 + 1]
    const pz = positions[i * 3 + 2]
    const w = matrix[3] * px + matrix[7] * py + matrix[11] * pz + matrix[15]
    // Behind the camera.
    if (w <= 0) continue
    const dx = (matrix[0] * px + matrix[4] * py + matrix[8] * pz + matrix[12]) / w - x
    if (dx > radius || dx < -radius) continue
    const dy = (matrix[1] * px + matrix[5] * py + matrix[9] * pz + matrix[13]) / w - y
    const distance = dx * dx + dy * dy
    if (distance > bestDistance) continue
    // Within a pixel of the nearest so far, the one in front wins: it is the one that is seen.
    if (best !== null && bestDistance - distance < 1 && w >= bestDepth) continue
    best = i
    bestDistance = distance
    bestDepth = w
  }
  return best
}
