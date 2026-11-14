import { useEffect, useMemo, useRef } from 'react'
import type { PointerEvent, ReactElement } from 'react'
import type { TimeRange } from '../map/geometry'
import { useTheme } from '../theme/theme'

const BINS = 120
const HEIGHT = 56

interface PeriodHistogramProps {
  ts: Float64Array
  range: TimeRange
  chosen: TimeRange | null
  onChoose(period: TimeRange): void
}

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/** How many items per slice of time. Drag across it to choose a period. */
export function PeriodHistogram({ ts, range, chosen, onChoose }: PeriodHistogramProps): ReactElement {
  const canvas = useRef<HTMLCanvasElement>(null)
  const anchor = useRef<number | null>(null)
  const [theme] = useTheme()
  const bins = useMemo(() => {
    const counts = new Uint32Array(BINS)
    const span = range.to - range.from
    for (let i = 0; i < ts.length; i += 1) {
      if (ts[i] < range.from || ts[i] > range.to) continue
      counts[Math.min(BINS - 1, Math.floor(((ts[i] - range.from) / span) * BINS))] += 1
    }
    return counts
  }, [ts, range])

  useEffect(() => {
    const node = canvas.current
    const context = node?.getContext('2d')
    if (!node || !context) return
    const ratio = window.devicePixelRatio || 1
    const width = node.clientWidth
    node.width = width * ratio
    node.height = HEIGHT * ratio
    context.scale(ratio, ratio)
    context.fillStyle = token('--nm-minimap-bg')
    context.fillRect(0, 0, width, HEIGHT)
    const peak = Math.max(1, ...bins)
    const step = width / BINS
    context.fillStyle = token('--nm-minimap-bar')
    bins.forEach((value, i) => {
      // A square root keeps quiet months visible beside a burst.
      const h = Math.sqrt(value / peak) * (HEIGHT - 4)
      if (value > 0) context.fillRect(i * step, HEIGHT - h, Math.max(1, step - 0.5), h)
    })
    if (chosen) {
      const span = range.to - range.from
      const from = ((chosen.from - range.from) / span) * width
      const to = ((chosen.to - range.from) / span) * width
      context.fillStyle = token('--nm-minimap-mask')
      context.fillRect(0, 0, Math.max(0, from), HEIGHT)
      context.fillRect(to, 0, Math.max(0, width - to), HEIGHT)
      context.strokeStyle = token('--nm-accent')
      context.lineWidth = 1
      context.strokeRect(from + 0.5, 0.5, Math.max(1, to - from - 1), HEIGHT - 1)
    }
  }, [bins, chosen, range, theme])

  const at = (event: PointerEvent<HTMLCanvasElement>): number => {
    const box = event.currentTarget.getBoundingClientRect()
    const share = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width))
    return range.from + share * (range.to - range.from)
  }
  const begin = (event: PointerEvent<HTMLCanvasElement>): void => {
    event.currentTarget.setPointerCapture(event.pointerId)
    anchor.current = at(event)
  }
  const move = (event: PointerEvent<HTMLCanvasElement>): void => {
    if (anchor.current === null) return
    const now = at(event)
    if (Math.abs(now - anchor.current) > 0) onChoose({ from: Math.min(anchor.current, now), to: Math.max(anchor.current, now) })
  }

  return (
    <canvas
      ref={canvas}
      className="nm-period__histogram"
      style={{ height: HEIGHT }}
      onPointerDown={begin}
      onPointerMove={move}
      onPointerUp={() => {
        anchor.current = null
      }}
      aria-label="Items over time. Drag to choose a period."
    />
  )
}
