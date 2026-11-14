import { SlidersHorizontal } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import { Popover } from '../popover/Popover'
import './toolbar.css'

export interface DisplayOption {
  id: string
  label: string
  hint: string
  on: boolean
  /** Why the option cannot be used, when it cannot. */
  disabled: string | null
  set(on: boolean): void
}

/** Switches for what is drawn over the map. */
export function DisplayMenu({ options }: { options: DisplayOption[] }): ReactElement {
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="nm-tool nm-tool--icon"
        title="Display"
        aria-label="Display"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <SlidersHorizontal size={16} aria-hidden />
      </button>
      <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} variant="menu" width={248} label="Display">
        <p className="nm-menu-title">Display</p>
        {options.map((option) => (
          <label key={option.id} className={`nm-display-row${option.disabled ? ' is-disabled' : ''}`} title={option.disabled ?? option.hint}>
            <span>{option.label}</span>
            <button
              type="button"
              role="switch"
              className="nm-switch"
              aria-checked={option.on}
              aria-label={option.label}
              disabled={option.disabled !== null}
              onClick={() => option.set(!option.on)}
            />
          </label>
        ))}
      </Popover>
    </>
  )
}
