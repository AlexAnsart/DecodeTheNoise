import type { ReactElement } from 'react'
import type { VoicesSize } from '../api/voicesSchema'
import { formatRate } from '../method/figures'
import { formatCount } from '../text/format'

/** The shares of coordinated groups a flag's precision is given for. */
const BASE_RATES = ['0.01', '0.05', '0.2']

interface Tally {
  groups: number
  flagged: number
}

function Share({ tally }: { tally: Tally }): ReactElement {
  return (
    <td className="nm-num">
      {formatCount(tally.flagged)} of {formatCount(tally.groups)}
      <span>{tally.groups > 0 ? formatRate(tally.flagged / tally.groups) : 'no group'}</span>
    </td>
  )
}

function byMode(size: VoicesSize): string {
  return Object.entries(size.one_brief.by_mode)
    .map(([mode, tally]) => `${mode} ${formatCount(tally.flagged)} of ${formatCount(tally.groups)}`)
    .join(' · ')
}

/** One row per group size the check was measured at: its threshold, and what that threshold
 *  did on real groups and on groups written from one brief that it never saw. */
export function VoicesSizeTable({ sizes }: { sizes: VoicesSize[] }): ReactElement {
  return (
    <div className="nm-table-wrap">
      <table className="nm-table nm-voices-method__sizes">
        <thead>
          <tr>
            <th scope="col">Group read</th>
            <th scope="col">One voice under</th>
            <th scope="col">False alarms, real groups</th>
            <th scope="col">False alarms, most alike</th>
            <th scope="col">One-brief groups caught</th>
            <th scope="col">A flag is right, if 1% / 5% / 20% of groups are coordinated</th>
          </tr>
        </thead>
        <tbody>
          {sizes.map((size) => (
            <tr key={`${size.actors}x${size.posts_each}`}>
              <th scope="row">
                {size.actors} actors × {size.posts_each} posts
              </th>
              <td className="nm-num">
                {size.threshold.toFixed(1)}
                <span>
                  independent actors: {size.reference.independent[0].toFixed(1)} to {size.reference.independent[1].toFixed(1)}
                </span>
              </td>
              <Share tally={size.real} />
              <Share tally={size.real_alike} />
              <td className="nm-num">
                {formatCount(size.one_brief.flagged)} of {formatCount(size.one_brief.groups)}
                <span>{byMode(size)}</span>
              </td>
              <td className="nm-num">
                {BASE_RATES.map((rate) => formatRate(size.precision_at_base_rate[rate]?.measured ?? null)).join(' / ')}
                <span>worst case {BASE_RATES.map((rate) => formatRate(size.precision_at_base_rate[rate]?.worst_case ?? null)).join(' / ')}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
