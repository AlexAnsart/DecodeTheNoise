import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { formatCount } from '../text/format'

function Meter({ label, used, limit }: { label: string; used: number; limit: number }): ReactElement {
  const share = limit > 0 ? Math.min(1, used / limit) : 0
  return (
    <div className="nm-usage__row">
      <span>{label}</span>
      <span className="nm-num">
        {formatCount(used)} / {formatCount(limit)}
      </span>
      <div className="nm-meter" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={limit} aria-valuenow={used}>
        <i style={{ width: `${100 * share}%` }} />
      </div>
    </div>
  )
}

/** What the workspace has used of what it may. */
export function UsageMeters({ info }: { info: WorkspaceInfo }): ReactElement {
  return (
    <div className="nm-usage">
      <Meter label="Posts stored" used={info.items} limit={info.limits.items} />
      <Meter label="LLM reviews today" used={info.usage.reviews_today} limit={info.limits.reviews_per_day} />
      <p className="nm-note nm-num">
        {formatCount(info.usage.names_today)} topic names asked today. Up to {formatCount(info.limits.batch_items)} posts per batch,{' '}
        {formatCount(info.limits.requests_per_minute)} requests a minute, {formatCount(info.limits.text_chars)} characters per post.
      </p>
    </div>
  )
}
