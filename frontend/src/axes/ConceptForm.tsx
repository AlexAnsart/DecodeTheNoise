import { useState } from 'react'
import type { ReactElement } from 'react'

const RECENT_KEY = 'noisemap.concepts'
const MAX_RECENT = 5

interface ConceptFormProps {
  /** A score is being computed. */
  busy: boolean
  onConcept(text: string): void
}

function recentConcepts(): string[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]')
    return Array.isArray(stored) ? stored.filter((value): value is string => typeof value === 'string') : []
  } catch {
    return []
  }
}

/** A few words to raise the map by, and the last ones that were typed. */
export function ConceptForm({ busy, onConcept }: ConceptFormProps): ReactElement {
  const [text, setText] = useState('')
  const [recent, setRecent] = useState(recentConcepts)

  const apply = (concept: string): void => {
    const clean = concept.trim()
    if (!clean) return
    const next = [clean, ...recent.filter((value) => value !== clean)].slice(0, MAX_RECENT)
    setRecent(next)
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(next))
    } catch {
      // Not remembered.
    }
    setText('')
    onConcept(clean)
  }

  return (
    <>
      <form
        className="nm-axes__form"
        onSubmit={(event) => {
          event.preventDefault()
          apply(text)
        }}
      >
        <input className="nm-field" value={text} onChange={(event) => setText(event.target.value)} placeholder="a call to violence, a giveaway…" aria-label="Concept" maxLength={300} />
        <button type="submit" className="nm-btn-primary nm-btn-small" disabled={!text.trim() || busy}>
          Raise
        </button>
      </form>
      {recent.length > 0 ? (
        <div className="nm-axes__recent">
          {recent.map((concept) => (
            <button key={concept} type="button" className="nm-axes__chip" disabled={busy} onClick={() => apply(concept)}>
              {concept}
            </button>
          ))}
        </div>
      ) : null}
    </>
  )
}
