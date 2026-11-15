import { ChevronRight } from 'lucide-react'
import { useId, useState } from 'react'
import type { ReactElement, ReactNode } from 'react'

interface DisclosureProps {
  title: ReactNode
  /** Said at the right end of the row: a count, a version. */
  hint?: ReactNode
  /** Given: the row is opened and closed from outside. Left out: it keeps its own state. */
  open?: boolean
  onToggle?(open: boolean): void
  /** Id of the row, so an address can point at it. */
  id?: string
  children: ReactNode
}

/** A row that opens in place: the summary stays, the detail comes under it. What is closed is
 *  not rendered, so a long page stays light. */
export function Disclosure({ title, hint, open, onToggle, id, children }: DisclosureProps): ReactElement {
  const [own, setOwn] = useState(false)
  const region = useId()
  const shown = open ?? own
  const toggle = (): void => {
    if (open === undefined) setOwn(!shown)
    onToggle?.(!shown)
  }
  return (
    <div id={id} className={`nm-disclosure${shown ? ' is-open' : ''}`}>
      <button type="button" className="nm-disclosure__row" aria-expanded={shown} aria-controls={region} onClick={toggle}>
        <ChevronRight size={14} aria-hidden />
        <span className="nm-disclosure__title">{title}</span>
        {hint ? <span className="nm-disclosure__hint">{hint}</span> : null}
      </button>
      {shown ? (
        <div id={region} className="nm-disclosure__body">
          {children}
        </div>
      ) : null}
    </div>
  )
}
