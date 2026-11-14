/* A relief raises each point by a score, the flat map staying whole underneath. */

export interface Relief {
  /** What the height reads, shown in the axis title and the menu. */
  label: string
  /** Height per point in [0, 1]; NaN where the score does not cover the point. */
  heights: Float32Array
  /** 1 for a point the score does not read: it stays on the floor, faint. */
  unread: Uint8Array | null
  /** Said under the menu when little stands out. */
  note: string | null
}

const FLOOR_Z = 2.5
const MIN_TOP_Z = 6
const CLEAR_Z = 3.5
const MIN_CLEAR_POINTS = 5

function quantile(sorted: Float32Array, share: number): number {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor(share * sorted.length)))]
}

/** Heights from a similarity to a concept. Similarities bunch together, so the height reads how
 *  far a point stands out of the crowd (a robust z-score), not the raw cosine. `skip` leaves the
 *  given points out of the statistics: they are the concept itself. */
export function likenessRelief(label: string, scores: Float32Array, skip: ArrayLike<number> = []): Relief {
  const left = new Set<number>(Array.from(skip))
  const crowd = Float32Array.from(Array.from(scores).filter((_, i) => !left.has(i))).sort()
  const median = quantile(crowd, 0.5)
  const spread = Float32Array.from(crowd, (s) => Math.abs(s - median)).sort()
  const mad = 1.4826 * quantile(spread, 0.5) || 1e-6
  const z = (s: number): number => (s - median) / mad
  const top = Math.max(MIN_TOP_Z, z(quantile(crowd, 0.999)))
  const heights = new Float32Array(scores.length)
  let clear = 0
  for (let i = 0; i < scores.length; i += 1) {
    const value = z(scores[i])
    if (value > CLEAR_Z) clear += 1
    heights[i] = Math.min(1, Math.max(0, (value - FLOOR_Z) / (top - FLOOR_Z)))
  }
  return {
    label,
    heights,
    unread: null,
    note: clear < MIN_CLEAR_POINTS ? 'Nothing stands out for this concept.' : null,
  }
}
