/* The lines and words that say what an added axis reads: dates along the front edge of the
   time shape, the height scale up a back corner of a relief. */

import type { Bounds, TimeRange } from '../map/geometry'
import { RELIEF_TOP, TIME_STRETCH, timePlace } from '../map/geometry'
import type { AxisLine, Vec3 } from '../map/layers'
import { formatDay, formatMonth } from '../text/format'
import type { ReliefTick } from './relief'

export interface AxisWord {
  position: Vec3
  text: string
  title: boolean
}

export interface AxisMarks {
  lines: AxisLine[]
  words: AxisWord[]
}

export const NO_MARKS: AxisMarks = { lines: [], words: [] }

const DAY = 86_400_000
const MAX_TICKS = 7
/** Tick steps in months, tried after the day and the week. */
const MONTH_STEPS = [1, 3, 6, 12, 24, 60, 120]

function calendarTicks(range: TimeRange): { at: number; text: string }[] {
  const span = range.to - range.from
  for (const days of [1, 7]) {
    if (span / (days * DAY) > MAX_TICKS) continue
    const ticks: { at: number; text: string }[] = []
    const start = Math.ceil(range.from / DAY) * DAY
    for (let t = start; t <= range.to; t += days * DAY) ticks.push({ at: t, text: formatDay(t) })
    return ticks
  }
  for (const months of MONTH_STEPS) {
    const ticks: { at: number; text: string }[] = []
    const cursor = new Date(range.from)
    cursor.setUTCDate(1)
    cursor.setUTCHours(0, 0, 0, 0)
    cursor.setUTCMonth(Math.ceil((cursor.getUTCMonth() + 1) / months) * months)
    while (cursor.getTime() <= range.to && ticks.length <= MAX_TICKS) {
      const text = months >= 12 ? String(cursor.getUTCFullYear()) : formatMonth(cursor.getTime())
      ticks.push({ at: cursor.getTime(), text })
      cursor.setUTCMonth(cursor.getUTCMonth() + months)
    }
    if (ticks.length <= MAX_TICKS) return ticks
  }
  return []
}

/** The date axis: a line along the front bottom edge of the points, a tick per calendar step. */
export function timeMarks(range: TimeRange, span: number, bounds: Bounds): AxisMarks {
  const reach = span * TIME_STRETCH
  const y = bounds.centre[1] - bounds.half[1] - span * 0.06
  const z = bounds.centre[2] - bounds.half[2]
  const tick = span * 0.035
  const lines: AxisLine[] = [{ path: [[-reach, y, z], [reach, y, z]], major: true }]
  const words: AxisWord[] = [{ position: [reach + span * 0.08, y, z], text: 'Date', title: true }]
  for (const { at, text } of calendarTicks(range)) {
    const x = timePlace(at, range) * reach
    lines.push({ path: [[x, y, z], [x, y, z - tick]], major: false })
    words.push({ position: [x, y, z - tick * 2.4], text, title: false })
  }
  return { lines, words }
}

/** The height axis of a relief: the floor of the points outlined, a scale up a back corner. */
export function reliefMarks(label: string, ticks: ReliefTick[], span: number, bounds: Bounds): AxisMarks {
  const top = span * RELIEF_TOP
  const pad = span * 0.04
  const west = bounds.centre[0] - bounds.half[0] - pad
  const east = bounds.centre[0] + bounds.half[0] + pad
  const south = bounds.centre[1] - bounds.half[1] - pad
  const north = bounds.centre[1] + bounds.half[1] + pad
  const corner: [number, number] = [west, north]
  const tick = span * 0.035
  const floor: Vec3[] = [[west, south, 0], [east, south, 0], [east, north, 0], [west, north, 0], [west, south, 0]]
  const lines: AxisLine[] = [
    { path: floor, major: false },
    { path: [[corner[0], corner[1], 0], [corner[0], corner[1], top]], major: true },
  ]
  const words: AxisWord[] = [{ position: [corner[0], corner[1], top + span * 0.09], text: label, title: true }]
  for (const { at, text } of ticks) {
    const z = at * top
    lines.push({ path: [[corner[0], corner[1], z], [corner[0] - tick, corner[1], z]], major: false })
    if (text) words.push({ position: [corner[0] - tick * 2.4, corner[1], z], text, title: false })
  }
  return { lines, words }
}
