import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { createPortal } from 'react-dom'
import './sidePanel.css'

interface SidePanelProps {
  title: string
  /** Room for a document or a figure, instead of a column of settings. */
  wide?: boolean
  onClose(): void
  children: ReactNode
}

/** A panel over the right side of the page, for what belongs to the whole workspace. Rendered
 *  in a portal; closes on Escape and on a press outside. Mount it only while it is open. */
export function SidePanel({ title, wide = false, onClose, children }: SidePanelProps): ReactElement {
  const panel = useRef<HTMLElement>(null)
  // The focus is taken once, when the panel opens. A parent that renders again hands a new
  // `onClose`: it must not take the focus back from a field being typed in.
  const latest = useRef(onClose)
  useEffect(() => {
    latest.current = onClose
  })

  useEffect(() => {
    const before = document.activeElement
    panel.current?.focus()
    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      latest.current()
    }
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('keydown', onKey, true)
      if (before instanceof HTMLElement) before.focus()
    }
  }, [])

  return createPortal(
    <div className="nm-side" onPointerDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside ref={panel} className={`nm-side__panel${wide ? ' nm-side__panel--wide' : ''}`} role="dialog" aria-modal aria-label={title} tabIndex={-1}>
        <header className="nm-side__head">
          <h2>{title}</h2>
          <button type="button" className="nm-icon-btn" onClick={onClose} title="Close" aria-label="Close">
            <X size={15} aria-hidden />
          </button>
        </header>
        <div className="nm-side__body">{children}</div>
      </aside>
    </div>,
    document.body,
  )
}
