/* A relief raises each point by a score, the flat map staying whole underneath. */

/** What the heights were read from: enough to read them again when the map grows. */
export type ReliefSource =
  | { kind: 'concept'; text: string }
  | { kind: 'selection' }
  | { kind: 'probe'; key: string }

/** A mark on the height axis: a share of the height in [0, 1], and the word beside it. */
export interface ReliefTick {
  at: number
  text: string
}

export interface Relief {
  /** What the height reads, shown in the axis title and the menu. */
  label: string
  /** Height per point in [0, 1]; NaN where the score does not cover the point. */
  heights: Float32Array
  /** 1 for a point the score does not read: it stays on the floor, faint. */
  unread: Uint8Array | null
  /** Said under the menu when little stands out. */
  note: string | null
  source: ReliefSource
  ticks: ReliefTick[]
}

// Set on the similarities this embedding model gives (four concepts on 3,000 posts: the 99th
// percentile sits 2.1 to 4.1 robust deviations above the median, the 99.9th 3.1 to 6.2).
// A point leaves the floor from 1.5 deviations and reaches the top at 4, or at the 99.9th
// percentile when that is higher.
/** The server takes at most this many points to resemble. */
export const MAX_LIKENESS_ITEMS = 5000

const FLOOR_Z = 1.5
const MIN_TOP_Z = 4
const CLEAR_Z = 2.5
const MIN_CLEAR_POINTS = 5
const LIKENESS_TICKS: ReliefTick[] = [
  { at: 0, text: 'like the rest' },
  { at: 0.5, text: '' },
  { at: 1, text: 'stands out' },
]

function quantile(sorted: Float32Array, share: number): number {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor(share * sorted.length)))]
}

/** Heights from a similarity to a concept. Similarities bunch together, so the height reads how
 *  far a point stands out of the crowd (a robust z-score), not the raw cosine. `skip` leaves the
 *  given points out of the statistics: they are the concept itself. */
export function likenessRelief(label: string, scores: Float32Array, source: ReliefSource, skip: ArrayLike<number> = []): Relief {
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
    source,
    ticks: LIKENESS_TICKS,
  }
}

/** The relief on a map of `n` points. Points added since the heights were read have none yet:
 *  they wait on the floor, marked unread, until the heights are read again. */
export function fitRelief(relief: Relief, n: number): Relief {
  if (relief.heights.length === n) return relief
  const kept = Math.min(n, relief.heights.length)
  const heights = new Float32Array(n).fill(Number.NaN)
  heights.set(relief.heights.subarray(0, kept))
  const unread = new Uint8Array(n).fill(1)
  if (relief.unread) unread.set(relief.unread.subarray(0, kept))
  else unread.fill(0, 0, kept)
  return { ...relief, heights, unread }
}
