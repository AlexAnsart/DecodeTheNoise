import type { ReactElement } from 'react'
import type { LabelledSummary } from '../../api/methodSchema'
import { formatCount } from '../../text/format'
import { readable } from '../words'

interface KindSwitchProps {
  summary: LabelledSummary
  kind: string
  onKind(kind: string): void
}

/** The annotators' readings and the second reader's are kept apart: one or the other is
 *  listed, or both side by side, never mixed in an answer. */
export function KindSwitch({ summary, kind, onKind }: KindSwitchProps): ReactElement | null {
  const kinds = Object.entries(summary.kinds)
  if (kinds.length < 2) return null
  return (
    <div className="nm-segmented" role="group" aria-label="Whose readings are listed">
      <button type="button" className={kind === '' ? 'is-active' : ''} aria-pressed={kind === ''} onClick={() => onKind('')}>
        All
      </button>
      {kinds.map(([name, count]) => (
        <button key={name} type="button" className={kind === name ? 'is-active' : ''} aria-pressed={kind === name} onClick={() => onKind(name)}>
          {readable(name)}
          <span className="nm-num">{formatCount(count)}</span>
        </button>
      ))}
    </div>
  )
}
