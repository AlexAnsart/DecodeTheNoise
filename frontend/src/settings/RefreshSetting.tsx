import { useState } from 'react'
import type { ReactElement } from 'react'

/** Bounds of backend/workspace/schema.py. */
const MIN_EVERY = 50
const MAX_EVERY = 2_000

interface RefreshSettingProps {
  every: number
  /** Posts the workspace can hold: a refresh further apart than that would never come. */
  capacity: number
  disabled: boolean
  onSave(every: number): void
}

/** How many new posts bring a new layout, new topics and new names. */
export function RefreshSetting({ every, capacity, disabled, onSave }: RefreshSettingProps): ReactElement {
  const [draft, setDraft] = useState<string | null>(null)
  const typed = draft === null ? every : Number(draft)
  const most = Math.max(MIN_EVERY, Math.min(MAX_EVERY, capacity))
  const valid = Number.isInteger(typed) && typed >= MIN_EVERY && typed <= most
  const changed = draft !== null && typed !== every
  return (
    <>
      <form
        className="nm-every"
        onSubmit={(event) => {
          event.preventDefault()
          if (!valid || !changed) return
          onSave(typed)
          setDraft(null)
        }}
      >
        <label htmlFor="nm-refresh-every">Refresh topics every</label>
        <input
          id="nm-refresh-every"
          className="nm-field nm-num"
          type="number"
          min={MIN_EVERY}
          max={most}
          step={10}
          value={draft ?? String(every)}
          disabled={disabled}
          onChange={(event) => setDraft(event.target.value)}
          aria-invalid={!valid}
        />
        <span>posts</span>
        {changed ? (
          <button type="submit" className="nm-btn-primary nm-btn-small" disabled={!valid || disabled}>
            Save
          </button>
        ) : null}
      </form>
      {valid ? null : (
        <p className="nm-note nm-note--error" role="alert">
          Between {MIN_EVERY} and {most.toLocaleString('en-US')} posts.
        </p>
      )}
    </>
  )
}
