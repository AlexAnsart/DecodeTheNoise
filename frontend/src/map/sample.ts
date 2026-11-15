/* A fixed sample of the points of a map, for a browser that draws on the CPU: there every
   point costs the same to draw, so fewer are drawn. The sample is a view: indices stay those
   of the map, and nothing is counted on it. Pure and seeded: one map, one sample. */

const SEED = 20261115

/** `size` indices of a map of `n` points, in ascending order. The same sizes always give the
 *  same indices (a partial Fisher–Yates shuffle on a seeded generator, mulberry32). */
export function sampleIndices(n: number, size: number): Uint32Array {
  const pool = new Uint32Array(n)
  for (let i = 0; i < n; i += 1) pool[i] = i
  let state = SEED
  const next = (): number => {
    state = (state + 0x6d2b79f5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const count = Math.min(size, n)
  for (let i = 0; i < count; i += 1) {
    const j = i + Math.floor(next() * (n - i))
    const moved = pool[i]
    pool[i] = pool[j]
    pool[j] = moved
  }
  return pool.slice(0, count).sort()
}

/** One value per point of the map: the given value where the point is in the sample, 0
 *  elsewhere. What reads it (the lasso, picking) then sees the points that are drawn. */
export function onSample(values: Float32Array, sample: Uint32Array): Float32Array {
  const out = new Float32Array(values.length)
  for (let k = 0; k < sample.length; k += 1) out[sample[k]] = values[sample[k]]
  return out
}

/** The rows of a per-point array for the sampled points only, `width` values per point. */
export function gatherFloats(values: Float32Array, sample: Uint32Array, width: number): Float32Array {
  const out = new Float32Array(sample.length * width)
  for (let k = 0; k < sample.length; k += 1) {
    const from = sample[k] * width
    for (let w = 0; w < width; w += 1) out[k * width + w] = values[from + w]
  }
  return out
}

export function gatherBytes(values: Uint8Array, sample: Uint32Array, width: number): Uint8Array {
  const out = new Uint8Array(sample.length * width)
  for (let k = 0; k < sample.length; k += 1) {
    const from = sample[k] * width
    for (let w = 0; w < width; w += 1) out[k * width + w] = values[from + w]
  }
  return out
}
