import { ListChecks, X } from 'lucide-react'
import type { ReactElement } from 'react'
import { plural } from '../text/format'
import './selection.css'

interface SelectionPillProps {
  count: number
  onOpen(): void
  onClear(): void
}

/** What remains of a selection once its list is closed: the count, and a way back or out. */
export function SelectionPill({ count, onOpen, onClear }: SelectionPillProps): ReactElement {
  return (
    <div className="nm-selection-pill">
      <button type="button" className="nm-selection-pill__open" onClick={onOpen} title="Open the list of selected items">
        <ListChecks size={14} aria-hidden />
        {plural(count, 'selected', 'selected')}
      </button>
      <button type="button" className="nm-selection-pill__clear" onClick={onClear} title="Clear the selection" aria-label="Clear the selection">
        <X size={13} aria-hidden />
      </button>
    </div>
  )
}
