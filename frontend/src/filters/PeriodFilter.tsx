import { CalendarDays } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { TimeRange } from '../map/geometry'
import { Popover } from '../popover/Popover'
import { formatDay, fromFieldValue, toFieldValue } from '../text/format'
import { PeriodHistogram } from './PeriodHistogram'

interface PeriodFilterProps {
  ts: Float64Array
  /** The span that holds the dated items; null when the map has no date. */
  range: TimeRange | null
  period: TimeRange | null
  onPeriod(period: TimeRange | null): void
}

/** Keeps the items dated inside a period. */
export function PeriodFilter({ ts, range, period, onPeriod }: PeriodFilterProps): ReactElement {
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<TimeRange | null>(period)

  const toggle = (): void => {
    setDraft(period)
    setOpen((value) => !value)
  }
  const edit = (edge: 'from' | 'to', value: string): void => {
    const ms = fromFieldValue(value)
    if (ms === null || !range) return
    const base = draft ?? range
    setDraft(edge === 'from' ? { from: ms, to: Math.max(ms, base.to) } : { from: Math.min(ms, base.from), to: ms })
  }
  const shown = draft ?? range

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={`nm-tool${period ? ' is-active' : ''}`}
        disabled={!range}
        title={range ? 'Keep the items dated inside a period' : 'No item of this map is dated.'}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={toggle}
      >
        <CalendarDays size={13} aria-hidden />
        {period ? `${formatDay(period.from)} – ${formatDay(period.to)}` : 'Period'}
      </button>
      <Popover anchor={trigger} open={open && range !== null} onClose={() => setOpen(false)} align="start" width={480} label="Period">
        {range && shown ? (
          <div className="nm-period">
            <PeriodHistogram ts={ts} range={range} chosen={draft} onChoose={setDraft} />
            <div className="nm-period__fields">
              <label>
                From
                <input className="nm-field" type="datetime-local" value={toFieldValue(shown.from)} onChange={(event) => edit('from', event.target.value)} />
              </label>
              <label>
                To
                <input className="nm-field" type="datetime-local" value={toFieldValue(shown.to)} onChange={(event) => edit('to', event.target.value)} />
              </label>
            </div>
            <div className="nm-filter-foot">
              <button
                type="button"
                className="nm-btn-secondary nm-btn-small"
                disabled={!period && !draft}
                onClick={() => {
                  setDraft(null)
                  onPeriod(null)
                  setOpen(false)
                }}
              >
                Clear
              </button>
              <button
                type="button"
                className="nm-btn-primary nm-btn-small"
                disabled={!draft}
                onClick={() => {
                  onPeriod(draft)
                  setOpen(false)
                }}
              >
                Apply
              </button>
            </div>
          </div>
        ) : null}
      </Popover>
    </>
  )
}
