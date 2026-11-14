import { Axis3d, X } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { Shape } from '../map/geometry'
import { Popover } from '../popover/Popover'
import type { Relief } from './relief'
import './axes.css'

const RECENT_KEY = 'noisemap.concepts'
const MAX_RECENT = 5

interface AxesMenuProps {
  shape: Shape
  relief: Relief | null
  hasDates: boolean
  /** A score is being computed. */
  busy: boolean
  error: string | null
  onShape(shape: '3d' | 'time'): void
  onConcept(text: string): void
  onClearRelief(): void
}

function recentConcepts(): string[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]')
    return Array.isArray(stored) ? stored.filter((value): value is string => typeof value === 'string') : []
  } catch {
    return []
  }
}

/** One more axis on the map: the date, or a height read from a concept you type. */
export function AxesMenu(props: AxesMenuProps): ReactElement {
  const { shape, relief, hasDates, busy, error, onShape, onConcept, onClearRelief } = props
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
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
      <button
        ref={trigger}
        type="button"
        className={`nm-tool nm-tool--icon${relief ? ' nm-tool--marked' : ''}`}
        title="Axes: add the date or a height to the map"
        aria-label="Axes"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Axis3d size={17} aria-hidden />
      </button>
      <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} width={340} label="Axes">
        <h3>Axes</h3>
        <p>The meaning map stays whole. One more axis is added to it.</p>
        <div className="nm-segmented nm-segmented--wide" role="group" aria-label="Added axis">
          <button type="button" className={shape === '3d' ? 'is-active' : ''} onClick={() => onShape('3d')}>
            Meaning only (3D)
          </button>
          <button
            type="button"
            className={shape === 'time' ? 'is-active' : ''}
            disabled={!hasDates}
            title={hasDates ? 'The date runs along an axis in front of the map' : 'No item of this map is dated.'}
            onClick={() => onShape('time')}
          >
            Date
          </button>
        </div>
        <section className="nm-axes__section">
          <h4>Raise by a concept</h4>
          <p>Type a few words. Each item rises by how much its meaning resembles them, whatever words it uses.</p>
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
        </section>
        {busy ? <p className="nm-axes__note">Computing the scores…</p> : null}
        {error ? <p className="nm-axes__note nm-axes__note--error">{error}</p> : null}
        {relief ? (
          <div className="nm-axes__current">
            <span title={relief.label}>Height: {relief.label}</span>
            <button type="button" className="nm-drawer__icon" onClick={onClearRelief} title="Remove the height" aria-label="Remove the height">
              <X size={13} aria-hidden />
            </button>
          </div>
        ) : null}
        {relief?.note ? <p className="nm-axes__note">{relief.note}</p> : null}
        <p className="nm-axes__foot">The layout is a display, not a measure: it keeps only part of the true neighbours.</p>
      </Popover>
    </>
  )
}
