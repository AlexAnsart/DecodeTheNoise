/* The time window of the scrubber: a span inside the busy range of the map. */

import type { TimeRange } from '../map/geometry'

const DAY = 86_400_000
/** The window is always drawn at least this wide, so it can be grabbed. */
export const MIN_DRAWN_SHARE = 0.02

export function clampWindow(window: TimeRange, range: TimeRange): TimeRange {
  const width = Math.min(Math.max(DAY, window.to - window.from), range.to - range.from)
  const from = Math.min(Math.max(range.from, window.from), range.to - width)
  return { from, to: from + width }
}

/** One calendar month from the start of the range. */
export function openingWindow(range: TimeRange): TimeRange {
  const start = new Date(range.from)
  const end = new Date(start)
  end.setMonth(end.getMonth() + 1)
  return clampWindow({ from: range.from, to: end.getTime() }, range)
}

export function moveWindow(window: TimeRange, range: TimeRange, delta: number): TimeRange {
  return clampWindow({ from: window.from + delta, to: window.to + delta }, range)
}

export function resizeWindow(window: TimeRange, range: TimeRange, edge: 'from' | 'to', delta: number): TimeRange {
  if (edge === 'from') {
    const from = Math.min(Math.max(range.from, window.from + delta), window.to - DAY)
    return { from, to: window.to }
  }
  const to = Math.max(Math.min(range.to, window.to + delta), window.from + DAY)
  return { from: window.from, to }
}

/** Next window when playing: one width further. Null once the end is reached. */
export function stepWindow(window: TimeRange, range: TimeRange): TimeRange | null {
  if (window.to >= range.to) return null
  return moveWindow(window, range, window.to - window.from)
}

/** Month starts inside the range, as shares of its width, for the tick marks. */
export function monthTicks(range: TimeRange): number[] {
  const ticks: number[] = []
  const cursor = new Date(range.from)
  cursor.setDate(1)
  cursor.setHours(0, 0, 0, 0)
  cursor.setMonth(cursor.getMonth() + 1)
  while (cursor.getTime() < range.to && ticks.length < 400) {
    ticks.push((cursor.getTime() - range.from) / (range.to - range.from))
    cursor.setMonth(cursor.getMonth() + 1)
  }
  return ticks
}
