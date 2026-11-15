import { Play } from 'lucide-react'
import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { formatCount, plural } from '../text/format'
import { IngestProgress } from '../workspace/IngestProgress'
import type { SampleSender as Sender } from './useSampleSender'
import { SAMPLE_POSTS } from './useSampleSender'
import './connect.css'

function Sending({ sent, total }: { sent: number; total: number }): ReactElement {
  return (
    <div className="nm-sampler__progress" role="status">
      <p className="nm-num">
        Sending {formatCount(sent)} of {formatCount(total)}
      </p>
      <div className="nm-meter" role="progressbar" aria-label="Posts sent" aria-valuemin={0} aria-valuemax={total} aria-valuenow={sent}>
        <i style={{ width: `${total > 0 ? (100 * sent) / total : 0}%` }} />
      </div>
    </div>
  )
}

interface SampleSenderProps {
  sender: Sender
  info: WorkspaceInfo
  /** The event stream is open: the embedding progress shown is current. */
  live: boolean
}

/** "No code": posts of the demo dataset go through the real API into the workspace. The
 *  progress does not stop when the posts are sent: it goes on until they are embedded. */
export function SampleSender({ sender, info, live }: SampleSenderProps): ReactElement {
  const { state, busy } = sender
  const waiting = info.pending > 0
  // What the last run did. It is not said any more once the workspace was emptied.
  const done = state.status === 'done' && info.items > 0 ? state : null
  return (
    <div className="nm-sampler">
      <p>
        Try it without writing code: {SAMPLE_POSTS} posts of the demo dataset are sent to your workspace through the same API, a
        few at a time.
      </p>
      <button type="button" className="nm-btn-primary nm-btn-small" onClick={sender.send} disabled={busy || waiting}>
        <Play size={12} aria-hidden />
        {busy ? 'Sending…' : waiting ? 'Embedding…' : done ? `Send the ${SAMPLE_POSTS} sample posts again` : `Send ${SAMPLE_POSTS} sample posts`}
      </button>
      {state.status === 'fetching' ? (
        <p className="nm-sampler__note" role="status">
          Reading the sample…
        </p>
      ) : null}
      {state.status === 'sending' ? <Sending sent={state.sent} total={state.total} /> : null}
      {done ? (
        <p className="nm-sampler__note" role="status">
          {plural(done.sent, 'post', 'posts')} sent{waiting ? '. They are being embedded.' : ' and embedded: they are on your map.'}
        </p>
      ) : null}
      {done && done.rejected > 0 ? (
        <p className="nm-sampler__note nm-sampler__note--error" role="alert">
          {plural(done.rejected, 'post was', 'posts were')} refused: {done.refused ?? 'the server gave no reason'}
        </p>
      ) : null}
      {busy ? null : <IngestProgress info={info} live={live} />}
      {state.status === 'error' ? (
        <p className="nm-sampler__note nm-sampler__note--error" role="alert">
          {state.message}
        </p>
      ) : null}
    </div>
  )
}
