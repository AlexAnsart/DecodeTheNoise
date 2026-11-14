import { Plus, X } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import type { PaintGroup } from '../colour/legend'
import { GroupSlot } from './GroupSlot'
import type { Draft, DraftSources } from './groups'
import { MAX_GROUPS, MIN_GROUPS, draftGroup, emptyDraft, kindOptions, openingDrafts, paintedGroups } from './groups'
import './compose.css'

interface ComposePanelProps {
  sources: DraftSources
  /** Composed colours are on. */
  active: boolean
  drafts: Draft[] | null
  onDrafts(drafts: Draft[]): void
  onApply(groups: PaintGroup[]): void
  onLeave(): void
  onClose(): void
}

/** Colours composed by the user: two to six groups, one colour each, the rest in grey. */
export function ComposePanel({ sources, active, drafts, onDrafts, onApply, onLeave, onClose }: ComposePanelProps): ReactElement {
  const [note, setNote] = useState<string | null>(null)
  const slots = drafts ?? openingDrafts(sources.data)
  const kinds = kindOptions(sources)
  const ready = slots.length >= MIN_GROUPS && slots.every((draft) => draftGroup(draft, sources) !== null)

  const set = (position: number, next: Draft): void => {
    setNote(null)
    onDrafts(slots.map((draft, i) => (i === position ? next : draft)))
  }
  const apply = (): void => {
    const groups = paintedGroups(slots, sources)
    if (groups.length < MIN_GROUPS) {
      setNote('Fewer than two of these groups hold a point: there is nothing to tell apart.')
      return
    }
    onApply(groups)
    onClose()
  }

  return (
    <section
      className="nm-compose"
      role="dialog"
      aria-label="Composed colours"
      onPointerDown={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        if (event.key !== 'Escape') return
        event.stopPropagation()
        onClose()
      }}
    >
      <header className="nm-compose__head">
        <p>Composed colours</p>
        <button type="button" className="nm-drawer__icon" onClick={onClose} title="Close" aria-label="Close">
          <X size={14} aria-hidden />
        </button>
      </header>
      <p className="nm-compose__lead">Define two to six groups. Each takes a colour; the points in none turn grey. A point in several groups takes the first.</p>
      {slots.map((draft, position) => (
        <GroupSlot
          // Slots are positional: the user edits the n-th group.
          // eslint-disable-next-line react/no-array-index-key
          key={position}
          position={position + 1}
          draft={draft}
          kinds={kinds}
          sources={sources}
          onDraft={(next) => set(position, next)}
          onRemove={slots.length > MIN_GROUPS ? () => onDrafts(slots.filter((_, i) => i !== position)) : null}
        />
      ))}
      <button type="button" className="nm-btn-secondary nm-btn-small nm-compose__add" disabled={slots.length >= MAX_GROUPS} onClick={() => onDrafts([...slots, emptyDraft('period')])}>
        <Plus size={13} aria-hidden />
        Add a group
      </button>
      {note ? <p className="nm-compose__note">{note}</p> : null}
      <footer className="nm-compose__foot">
        {active ? (
          <button
            type="button"
            className="nm-btn-secondary nm-btn-small"
            onClick={() => {
              onLeave()
              onClose()
            }}
          >
            Leave these colours
          </button>
        ) : (
          <span />
        )}
        <button type="button" className="nm-btn-primary nm-btn-small" disabled={!ready} onClick={apply}>
          Apply
        </button>
      </footer>
    </section>
  )
}
