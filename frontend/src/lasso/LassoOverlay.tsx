import { useEffect, useRef, useState } from 'react'
import type { PointerEvent, ReactElement } from 'react'
import type { LassoMode, Stroke } from './lassoGeometry'
import { MIN_STROKE_POINTS, modeOf } from './lassoGeometry'
import './lasso.css'

interface LassoOverlayProps {
  /** In depth, the hint says the lasso takes the whole depth. */
  deep: boolean
  onStroke(stroke: Stroke, mode: LassoMode): void
}

const HINTS: Record<LassoMode, string> = {
  new: 'Draw around the points to select',
  add: 'Shift: add to the selection',
  remove: 'Alt: remove from the selection',
  overlap: 'Shift+Alt: keep only the overlap',
}

/** A layer over the canvas that takes the pointer and draws the stroke without React renders. */
export function LassoOverlay({ deep, onStroke }: LassoOverlayProps): ReactElement {
  const path = useRef<SVGPathElement>(null)
  const stroke = useRef<Stroke | null>(null)
  const strokeMode = useRef<LassoMode>('new')
  const [mode, setMode] = useState<LassoMode>('new')

  useEffect(() => {
    // The modifier is read at the start of a stroke, and previewed while the key is held.
    const onKey = (event: KeyboardEvent): void => {
      if (stroke.current === null) setMode(modeOf(event.shiftKey, event.altKey))
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('keyup', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('keyup', onKey)
    }
  }, [])

  const draw = (): void => {
    const points = stroke.current
    if (!path.current) return
    path.current.setAttribute('d', points && points.length > 1 ? `M${points.map(([x, y]) => `${x},${y}`).join('L')}Z` : '')
  }
  const place = (event: PointerEvent<HTMLDivElement>): [number, number] => {
    const box = event.currentTarget.getBoundingClientRect()
    return [event.clientX - box.left, event.clientY - box.top]
  }
  const begin = (event: PointerEvent<HTMLDivElement>): void => {
    if (event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    strokeMode.current = modeOf(event.shiftKey, event.altKey)
    setMode(strokeMode.current)
    stroke.current = [place(event)]
    draw()
  }
  const extend = (event: PointerEvent<HTMLDivElement>): void => {
    if (!stroke.current) return
    stroke.current.push(place(event))
    draw()
  }
  const finish = (): void => {
    const points = stroke.current
    stroke.current = null
    draw()
    // A click without a stroke leaves the lasso on.
    if (points && points.length >= MIN_STROKE_POINTS) onStroke(points, strokeMode.current)
  }

  return (
    <div
      className={`nm-lasso nm-lasso--${mode}`}
      onPointerDown={begin}
      onPointerMove={extend}
      onPointerUp={finish}
      onPointerCancel={finish}
    >
      <svg className="nm-lasso__svg" aria-hidden>
        <path ref={path} />
      </svg>
      <p className="nm-lasso__hint">
        {HINTS[mode]}
        {deep ? <span>In depth the lasso takes everything under the stroke. Turn the map and draw again with Shift+Alt to keep one island.</span> : null}
      </p>
    </div>
  )
}
