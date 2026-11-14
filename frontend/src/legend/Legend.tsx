import { ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import type { Legend as LegendModel } from '../colour/legend'
import { cssColour } from '../colour/palette'
import { formatDay } from '../text/format'
import { LegendRow } from './LegendRow'
import './legend.css'

const FOLD_KEY = 'noisemap.legend.folded'

interface LegendProps {
  legend: LegendModel
  /** Points shown per entry under the current filters. */
  counts: Uint32Array
  hidden: ReadonlySet<number>
  /** Lifted above the time scrubber while it shows. */
  raised: boolean
  onToggle(entry: number): void
  onSolo(entry: number): void
  onHideAll(hide: boolean): void
  onPeek(entry: number | null): void
}

function storedFold(): boolean {
  try {
    return localStorage.getItem(FOLD_KEY) === '1'
  } catch {
    return false
  }
}

export function Legend(props: LegendProps): ReactElement {
  const { legend, counts, hidden, raised, onToggle, onSolo, onHideAll, onPeek } = props
  const [folded, setFolded] = useState(storedFold)
  const anyHidden = hidden.size > 0
  const rows = legend.entries.filter(
    (entry) => (counts[entry.id] > 0 || hidden.has(entry.id)) && !(legend.dateBar && entry.id === 0),
  )

  const fold = (): void => {
    setFolded((value) => {
      try {
        localStorage.setItem(FOLD_KEY, value ? '0' : '1')
      } catch {
        // Not remembered.
      }
      return !value
    })
  }

  return (
    <section className={`nm-legend${raised ? ' is-raised' : ''}`} aria-label="Legend">
      <header className="nm-legend__head">
        <button type="button" className="nm-legend__title" onClick={fold} aria-expanded={!folded} title={folded ? 'Unfold the legend' : 'Fold the legend'}>
          <span>{legend.title}</span>
          {folded ? <ChevronUp size={13} aria-hidden /> : <ChevronDown size={13} aria-hidden />}
        </button>
        <button
          type="button"
          className="nm-legend__eye"
          onClick={() => onHideAll(!anyHidden)}
          title={anyHidden ? 'Show all' : 'Hide all'}
          aria-label={anyHidden ? 'Show all' : 'Hide all'}
        >
          {anyHidden ? <EyeOff size={15} aria-hidden /> : <Eye size={15} aria-hidden />}
        </button>
      </header>
      {folded ? null : (
        <div className="nm-legend__rows" onPointerLeave={() => onPeek(null)}>
          {legend.dateBar ? (
            <div className="nm-legend__dates">
              <div
                className="nm-legend__gradient"
                style={{ background: `linear-gradient(90deg, ${legend.dateBar.stops.map(cssColour).join(', ')})` }}
              />
              <div className="nm-legend__ticks nm-num">
                {legend.dateBar.ticks.map((tick, i) => (
                  // The four ticks are positional: start, one third, two thirds, end.
                  // eslint-disable-next-line react/no-array-index-key
                  <span key={i}>{formatDay(tick)}</span>
                ))}
              </div>
              <p className="nm-legend__note">Each stretch of colour holds as many items.</p>
            </div>
          ) : null}
          {rows.map((entry) => (
            <LegendRow
              key={entry.id}
              entry={entry}
              count={counts[entry.id]}
              hidden={hidden.has(entry.id)}
              onToggle={onToggle}
              onSolo={onSolo}
              onPeek={onPeek}
            />
          ))}
        </div>
      )}
    </section>
  )
}
