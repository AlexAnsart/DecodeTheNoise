import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { formatCount } from '../text/format'
import { embeddingOf, queueWords, rateWords, timeWords } from './progress'
import './ingest.css'

interface IngestProgressProps {
  info: WorkspaceInfo
  /** The event stream is open: the count and the estimate are current. */
  live: boolean
}

/** The batch being embedded: how far it is, how long is left, and why it may pause. Nothing
 *  is drawn when no post waits. */
export function IngestProgress({ info, live }: IngestProgressProps): ReactElement | null {
  const embedding = embeddingOf(info)
  if (!embedding) return null
  const { done, total } = embedding
  // One line under the bar: the queue when it explains a pause, the measured speed otherwise.
  // While the model does not answer, the warning says what matters and the speed says nothing.
  const detail = queueWords(info.ingest.ahead) ?? (info.ingest.error === null ? rateWords(info.ingest.rate) : null)
  return (
    <div className="nm-ingest" role="status">
      <p className="nm-ingest__line nm-num">
        <strong>
          Embedding {formatCount(done)} of {formatCount(total)}
        </strong>
        <span>{timeWords(info, live)}</span>
      </p>
      <div className="nm-meter" role="progressbar" aria-label="Posts embedded" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
        <i style={{ width: `${(100 * done) / total}%` }} />
      </div>
      {detail ? <p className="nm-note nm-num">{detail.endsWith('.') ? detail : `${detail}.`}</p> : null}
    </div>
  )
}
