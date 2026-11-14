import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import type { SampleState } from '../connect/useSampleSender'
import { formatCount, plural } from '../text/format'
import { IngestWarning } from './IngestWarning'
import { embeddingOf, queueWords, refreshWords, timeWords } from './progress'

interface StatusStripProps {
  info: WorkspaceInfo
  live: boolean
  sample: SampleState
}

/** One slim line above the map: what the workspace holds and what it is doing right now. A
 *  second line appears, and stays, while the embedding model does not answer. */
export function StatusStrip({ info, live, sample }: StatusStripProps): ReactElement {
  const embedding = embeddingOf(info)
  const queue = embedding ? queueWords(info.ingest.ahead) : null
  const refresh = refreshWords(info)
  const full = info.items >= info.limits.items
  return (
    <div className="nm-status">
      <div className="nm-strip" role="status" aria-label="State of the workspace">
        <span className={`nm-strip__live${live ? ' is-live' : ''}`} title={live ? 'Updates arrive as posts do' : 'Connecting again: the counts may be late'}>
          <i aria-hidden />
          {live ? 'Live' : 'Reconnecting…'}
        </span>
        <span className="nm-strip__part nm-num">{plural(info.points, 'post placed', 'posts placed')}</span>
        {sample.status === 'sending' ? (
          <span className="nm-strip__part nm-num">
            sending sample {formatCount(sample.sent)} of {formatCount(sample.total)}
          </span>
        ) : null}
        {embedding ? (
          <span className="nm-strip__part nm-strip__embedding nm-num">
            embedding {formatCount(embedding.done)} of {formatCount(embedding.total)}
            <span className="nm-meter" aria-hidden>
              <i style={{ width: `${(100 * embedding.done) / embedding.total}%` }} />
            </span>
            {timeWords(info, live)}
          </span>
        ) : null}
        {queue ? <span className="nm-strip__part nm-num">{queue}</span> : null}
        {refresh ? <span className="nm-strip__part nm-num">{refresh}</span> : null}
        {info.zones > 0 ? <span className="nm-strip__part nm-num">{plural(info.zones, 'topic', 'topics')}</span> : null}
        <span className={`nm-strip__room nm-num${full ? ' is-full' : ''}`} title="Posts stored out of what this workspace can hold">
          {formatCount(info.items)} / {formatCount(info.limits.items)} posts{full ? ': full' : ''}
        </span>
      </div>
      {info.ingest.error !== null ? <IngestWarning message={info.ingest.error} /> : null}
    </div>
  )
}
