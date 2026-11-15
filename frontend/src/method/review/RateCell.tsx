import type { ReactElement } from 'react'
import type { Rate } from '../../api/reviewReportSchema'
import { formatInterval, formatRate } from '../figures'

interface RateCellProps {
  rate: Rate | null | undefined
  /** What stands in the cell when the report holds no rate. */
  none?: string
}

/** A measured rate in a table: the value, and its 95% interval under it. */
export function RateCell({ rate, none = '–' }: RateCellProps): ReactElement {
  if (!rate) return <td className="nm-num nm-review-eval__none">{none}</td>
  return (
    <td className="nm-num">
      {formatRate(rate.value)}
      <span>{formatInterval(rate.low, rate.high)}</span>
    </td>
  )
}
