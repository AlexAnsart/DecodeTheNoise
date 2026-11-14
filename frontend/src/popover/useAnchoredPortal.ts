/* Places a floating panel under its trigger, clamped to the window, flipped above when the room
   below is short. The panel renders in a portal, so no clipping parent can cut it. */

import { useLayoutEffect, useState } from 'react'
import type { CSSProperties, RefObject } from 'react'

const GAP = 6
const EDGE = 8

export type Align = 'start' | 'end'

export function useAnchoredPortal(
  anchor: RefObject<HTMLElement | null>,
  panel: RefObject<HTMLElement | null>,
  open: boolean,
  align: Align,
): CSSProperties {
  const [style, setStyle] = useState<CSSProperties>({ visibility: 'hidden' })

  useLayoutEffect(() => {
    if (!open) return undefined
    const place = (): void => {
      const trigger = anchor.current?.getBoundingClientRect()
      const box = panel.current?.getBoundingClientRect()
      if (!trigger || !box) return
      const wanted = align === 'end' ? trigger.right - box.width : trigger.left
      const left = Math.min(Math.max(EDGE, wanted), window.innerWidth - box.width - EDGE)
      const below = trigger.bottom + GAP
      const fitsBelow = below + box.height <= window.innerHeight - EDGE
      const top = fitsBelow ? below : Math.max(EDGE, trigger.top - GAP - box.height)
      setStyle({ left, top, visibility: 'visible' })
    }
    place()
    const observer = new ResizeObserver(place)
    if (panel.current) observer.observe(panel.current)
    window.addEventListener('resize', place)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', place)
    }
  }, [anchor, panel, open, align])

  return open ? style : { visibility: 'hidden' }
}
