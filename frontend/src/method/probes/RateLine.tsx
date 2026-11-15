import type { ReactElement } from 'react'
import { formatInterval, formatRate } from '../figures'
import type { Rate } from './probeRows'

interface RateLineProps {
  label: string
  /** What the rate is a rate of, said under the label. */
  hint?: string
  rate: Rate | null
  /** Drawn on a 0 to 100% track. Left out for rates too small to see on it. */
  bar?: boolean
}

/** One measured rate: its value, its 95% interval, and both drawn on a track when that reads. */
export function RateLine({ label, hint, rate, bar = false }: RateLineProps): ReactElement {
  const interval = rate && rate.low !== null && rate.high !== null ? { low: rate.low, high: rate.high } : null
  return (
    <div className="nm-rate">
      <dt>
        {label}
        {hint ? <span>{hint}</span> : null}
      </dt>
      <dd className="nm-num">
        <strong>{formatRate(rate?.value ?? null)}</strong>
        {rate && bar ? (
          <span className="nm-rate__track" aria-hidden>
            {interval ? <i className="nm-rate__band" style={{ left: `${100 * interval.low}%`, width: `${100 * (interval.high - interval.low)}%` }} /> : null}
            <i className="nm-rate__tick" style={{ left: `${100 * rate.value}%` }} />
          </span>
        ) : null}
        {interval ? <span className="nm-rate__interval">{formatInterval(interval.low, interval.high)}</span> : null}
      </dd>
    </div>
  )
}
