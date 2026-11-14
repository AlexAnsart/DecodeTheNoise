/* Which points stay at full strength. Each source lights a set; the lit points are the ones
   every source lights, and the rest are left in the shade rather than hidden. */

import { ALPHA_DIM, ALPHA_FULL } from './palette'

const ALPHA_UNREAD = 40

/** Intersection of the masks that are set. Null when nothing dims the map. */
export function litPoints(n: number, sources: Array<Uint8Array | null>): Uint8Array | null {
  const active = sources.filter((source): source is Uint8Array => source !== null)
  if (active.length === 0) return null
  if (active.length === 1) return active[0]
  const lit = new Uint8Array(n).fill(1)
  for (const source of active) for (let i = 0; i < n; i += 1) if (source[i] !== 1) lit[i] = 0
  return lit
}

/** RGBA per point for the canvas. `unread` marks points a relief's score does not cover. */
export function paintPoints(base: Uint8Array, lit: Uint8Array | null, unread: Uint8Array | null): Uint8Array {
  const colours = new Uint8Array(base)
  const n = base.length / 4
  for (let i = 0; i < n; i += 1) {
    let alpha = Math.min(ALPHA_FULL, base[i * 4 + 3])
    if (lit && lit[i] !== 1) alpha = ALPHA_DIM
    else if (unread && unread[i] === 1) alpha = Math.min(alpha, ALPHA_UNREAD)
    colours[i * 4 + 3] = alpha
  }
  return colours
}

export function maskOfEntry(entryOf: Uint16Array, entry: number): Uint8Array {
  const mask = new Uint8Array(entryOf.length)
  for (let i = 0; i < entryOf.length; i += 1) if (entryOf[i] === entry) mask[i] = 1
  return mask
}

export function maskOfIndices(n: number, indices: ArrayLike<number>): Uint8Array {
  const mask = new Uint8Array(n)
  for (let j = 0; j < indices.length; j += 1) mask[indices[j]] = 1
  return mask
}

export function maskOfPeriod(ts: Float64Array, from: number, to: number): Uint8Array {
  const mask = new Uint8Array(ts.length)
  for (let i = 0; i < ts.length; i += 1) if (ts[i] >= from && ts[i] <= to) mask[i] = 1
  return mask
}
