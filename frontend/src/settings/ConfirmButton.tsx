import { useState } from 'react'
import type { ReactElement, ReactNode } from 'react'

interface ConfirmButtonProps {
  /** The action, as the button names it. */
  label: ReactNode
  /** What happens, said before it does. */
  question: string
  /** The button that goes ahead. */
  confirm: string
  busy: boolean
  busyLabel: string
  onConfirm(): void
}

/** An action that cannot be undone: asked a second time in the page, never in a browser dialog. */
export function ConfirmButton({ label, question, confirm, busy, busyLabel, onConfirm }: ConfirmButtonProps): ReactElement {
  const [asking, setAsking] = useState(false)
  if (!asking || busy) {
    return (
      <button type="button" className="nm-btn-secondary nm-btn-small" onClick={() => setAsking(true)} disabled={busy}>
        {busy ? busyLabel : label}
      </button>
    )
  }
  return (
    <div className="nm-confirm" role="group" aria-label={question}>
      <p>{question}</p>
      <div className="nm-confirm__actions">
        <button
          type="button"
          className="nm-btn-secondary nm-btn-small nm-confirm__go"
          onClick={() => {
            setAsking(false)
            onConfirm()
          }}
        >
          {confirm}
        </button>
        <button type="button" className="nm-btn-secondary nm-btn-small" onClick={() => setAsking(false)} autoFocus>
          Cancel
        </button>
      </div>
    </div>
  )
}
