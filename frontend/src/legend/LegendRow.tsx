import type { CSSProperties, ReactElement } from 'react'
import type { LegendEntry } from '../colour/legend'
import { cssColour } from '../colour/palette'
import { formatCount } from '../text/format'

interface LegendRowProps {
  entry: LegendEntry
  count: number
  hidden: boolean
  onToggle(entry: number): void
  onSolo(entry: number): void
  onPeek(entry: number | null): void
}

/** One legend entry. Click hides or shows its points; Shift+click keeps it alone. */
export function LegendRow({ entry, count, hidden, onToggle, onSolo, onPeek }: LegendRowProps): ReactElement {
  const swatch: CSSProperties = { '--swatch': cssColour(entry.colour) } as CSSProperties
  const hint = entry.hint ? `${entry.hint}\n` : ''
  return (
    <button
      type="button"
      className={`nm-legend__row${hidden ? ' is-hidden' : ''}`}
      title={`${hint}Click: hide or show. Shift+click: this one alone.`}
      aria-pressed={!hidden}
      onClick={(event) => (event.shiftKey ? onSolo(entry.id) : onToggle(entry.id))}
      onPointerEnter={() => onPeek(hidden ? null : entry.id)}
      onFocus={() => onPeek(hidden ? null : entry.id)}
      onBlur={() => onPeek(null)}
    >
      <span className="nm-legend__swatch" style={swatch} aria-hidden />
      <span className="nm-legend__label">{entry.label}</span>
      <span className="nm-legend__count nm-num">{formatCount(count)}</span>
    </button>
  )
}
