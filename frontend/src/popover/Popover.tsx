import { useEffect, useRef } from 'react'
import type { ReactElement, ReactNode, RefObject } from 'react'
import { createPortal } from 'react-dom'
import type { Align } from './useAnchoredPortal'
import { useAnchoredPortal } from './useAnchoredPortal'
import './popover.css'

interface PopoverProps {
  anchor: RefObject<HTMLElement | null>
  open: boolean
  onClose: () => void
  align?: Align
  /** A menu is a tight list of rows; a panel holds a form. */
  variant?: 'menu' | 'panel'
  width?: number
  label: string
  children: ReactNode
}

/** A floating panel under its trigger. Closes on Escape and on a press outside. */
export function Popover(props: PopoverProps): ReactElement | null {
  const { anchor, open, onClose, align = 'end', variant = 'panel', width, label, children } = props
  const panel = useRef<HTMLDivElement>(null)
  const style = useAnchoredPortal(anchor, panel, open, align)

  useEffect(() => {
    if (!open) return undefined
    const onPress = (event: PointerEvent): void => {
      const target = event.target
      if (!(target instanceof Node)) return
      if (panel.current?.contains(target) || anchor.current?.contains(target)) return
      // A nested floating panel (a date picker inside a form) belongs to this one.
      if (target instanceof Element && target.closest('.nm-popover')) return
      onClose()
    }
    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      onClose()
      anchor.current?.focus()
    }
    document.addEventListener('pointerdown', onPress, true)
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('pointerdown', onPress, true)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [open, onClose, anchor])

  if (!open) return null
  return createPortal(
    <div
      ref={panel}
      className={`nm-popover nm-popover--${variant}`}
      role="dialog"
      aria-label={label}
      style={{ ...style, width }}
    >
      {children}
    </div>,
    document.body,
  )
}
