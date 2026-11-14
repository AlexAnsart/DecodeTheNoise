/* The point under the pointer. The highlight is immediate; the tooltip waits for the pointer
   to rest, so sweeping across the cloud does not fetch an item per point crossed. */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { placeTip } from './placement'

const REST_MS = 120

export interface Pointer {
  /** Point whose tooltip shows, once the pointer has rested on it. */
  tipIndex: number | null
  tip: RefObject<HTMLDivElement | null>
  onHover(index: number | null, x: number, y: number): void
  /** Re-measures the tooltip once its content has changed. */
  settle(): void
}

export function usePointer(stage: RefObject<HTMLDivElement | null>, freeWidth: () => number): Pointer {
  const tip = useRef<HTMLDivElement | null>(null)
  const hovered = useRef<number | null>(null)
  const at = useRef({ x: 0, y: 0 })
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [tipIndex, setTipIndex] = useState<number | null>(null)

  const settle = useCallback(() => {
    const box = tip.current
    const host = stage.current
    if (!box || !host) return
    const placed = placeTip(
      at.current.x,
      at.current.y,
      { width: box.offsetWidth, height: box.offsetHeight },
      { width: host.clientWidth, height: host.clientHeight },
      freeWidth(),
    )
    box.style.transform = `translate(${Math.round(placed.left)}px, ${Math.round(placed.top)}px)`
  }, [stage, freeWidth])

  const onHover = useCallback(
    (index: number | null, x: number, y: number) => {
      at.current = { x, y }
      settle()
      if (index === hovered.current) return
      hovered.current = index
      if (timer.current) clearTimeout(timer.current)
      setTipIndex(null)
      if (index !== null) timer.current = setTimeout(() => setTipIndex(index), REST_MS)
    },
    [settle],
  )

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    [],
  )

  return { tipIndex, tip, onHover, settle }
}
