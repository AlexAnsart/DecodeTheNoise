import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { createPortal } from 'react-dom'
import './sidePanel.css'

interface SidePanelProps {
  title: string
  onClose(): void
  children: ReactNode
}

/** A panel over the right side of the page, for what belongs to the whole workspace. Rendered
 *  in a portal; closes on Escape and on a press outside. Mount it only while it is open. */
export function SidePanel({ title, onClose, children }: SidePanelProps): ReactElement {
  const panel = useRef<HTMLElement>(null)

  useEffect(() => {
    const before = document.activeElement
    panel.current?.focus()
    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      onClose()
    }
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('keydown', onKey, true)
      if (before instanceof HTMLElement) before.focus()
    }
  }, [onClose])

  return createPortal(
    <div className="nm-side" onPointerDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside ref={panel} className="nm-side__panel" role="dialog" aria-modal aria-label={title} tabIndex={-1}>
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
