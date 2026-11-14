import { ChevronDown, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import { columnOptions } from '../filters/columnOptions'
import { OptionList } from '../popover/OptionList'
import { Popover } from '../popover/Popover'
import type { Draft, DraftSources, GroupKind, KindOption } from './groups'
import { emptyDraft } from './groups'

interface GroupSlotProps {
  position: number
  draft: Draft
  kinds: KindOption[]
  sources: DraftSources
  /** Set when the slot can be removed. */
  onRemove: (() => void) | null
  onDraft(draft: Draft): void
}

function dayValue(ms: number | null): string {
  return ms === null ? '' : new Date(ms).toISOString().slice(0, 10)
}

function dayStart(value: string, endOfDay: boolean): number | null {
  const ms = Date.parse(`${value}T${endOfDay ? '23:59:59' : '00:00:00'}Z`)
  return Number.isNaN(ms) ? null : ms
}

/** One group: its kind, then its value. */
export function GroupSlot({ position, draft, kinds, sources, onRemove, onDraft }: GroupSlotProps): ReactElement {
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const column = sources.data.columns.find((c) => `column:${c.key}` === draft.kind)
  const options = useMemo(() => (column ? columnOptions(column) : []), [column])
  const chosen = column && draft.value !== null ? column.names[draft.value] : null

  return (
    <div className="nm-compose__slot">
      <select
        className="nm-field"
        value={draft.kind}
        aria-label={`Kind of group ${position}`}
        onChange={(event) => onDraft(emptyDraft(event.target.value as GroupKind))}
      >
        {kinds.map((kind) => (
          <option key={kind.kind} value={kind.kind} disabled={kind.disabled !== null && kind.kind !== draft.kind} title={kind.disabled ?? undefined}>
            {kind.label}
          </option>
        ))}
      </select>
      {column ? (
        <>
          <button ref={trigger} type="button" className="nm-field nm-compose__value" onClick={() => setOpen((value) => !value)} aria-haspopup="dialog" aria-expanded={open}>
            <span className={chosen ? '' : 'nm-muted'}>{chosen ?? 'Choose a value'}</span>
            <ChevronDown size={13} aria-hidden />
          </button>
          <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} align="start" variant="menu" width={280} label={column.label}>
            <OptionList
              options={options}
              chosen={new Set(draft.value === null ? [] : [draft.value])}
              label={column.label}
              onPick={(value) => {
                onDraft({ ...draft, value })
                setOpen(false)
              }}
            />
          </Popover>
        </>
      ) : null}
      {draft.kind === 'period' ? (
        <div className="nm-compose__period">
          <input className="nm-field" type="date" value={dayValue(draft.from)} aria-label="From" onChange={(event) => onDraft({ ...draft, from: dayStart(event.target.value, false) })} />
          <input className="nm-field" type="date" value={dayValue(draft.to)} aria-label="To" onChange={(event) => onDraft({ ...draft, to: dayStart(event.target.value, true) })} />
        </div>
      ) : null}
      {draft.kind === 'selection' ? <p className="nm-compose__says">The points chosen with the lasso.</p> : null}
      {draft.kind === 'filters' ? <p className="nm-compose__says">The points the filters keep now.</p> : null}
      {onRemove ? (
        <button type="button" className="nm-drawer__icon nm-compose__remove" onClick={onRemove} title="Remove this group" aria-label="Remove this group">
          <X size={13} aria-hidden />
        </button>
      ) : null}
    </div>
  )
}
