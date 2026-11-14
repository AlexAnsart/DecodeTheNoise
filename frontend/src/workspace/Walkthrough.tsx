import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { KeyField } from '../connect/KeyField'
import { SendTabs } from '../connect/SendTabs'
import type { SampleSender } from '../connect/useSampleSender'
import { formatCount } from '../text/format'
import { IngestProgress } from './IngestProgress'
import { IngestWarning } from './IngestWarning'
import { embeddingOf, waitingLine } from './progress'
import { StepCard } from './StepCard'
import './workspace.css'

interface WalkthroughProps {
  apiKey: string
  info: WorkspaceInfo
  /** The event stream is open: the third step is truly listening. */
  live: boolean
  sender: SampleSender
}

/** An empty workspace: three steps from a key to a map. */
export function Walkthrough({ apiKey, info, live, sender }: WalkthroughProps): ReactElement {
  const firstTopics = info.refresh.next_at
  return (
    <div className="nm-page">
      <div className="nm-walk">
        <header className="nm-walk__head">
          <p className="nm-eyebrow">Your workspace is ready</p>
          <h1>Three steps to your own map</h1>
          <p>It is empty for now. Send it posts and this page becomes your map.</p>
        </header>
        <div className="nm-walk__steps">
          <StepCard step={1} title="Your API key">
            <KeyField apiKey={apiKey} />
            <p>The only credential, kept in this browser. Copy it somewhere safe: nothing else opens this workspace.</p>
          </StepCard>
          <StepCard step={2} title="Send your posts">
            <SendTabs apiKey={apiKey} info={info} live={live} sender={sender} />
          </StepCard>
          <StepCard step={3} title="Watch your map build">
            {embeddingOf(info) ? (
              <div className="nm-waiting">
                <IngestProgress info={info} live={live} />
              </div>
            ) : (
              <p className={`nm-waiting${live ? ' is-live' : ''}`} role="status" title={live ? 'Listening to your workspace' : 'Connecting to your workspace'}>
                <i aria-hidden />
                {waitingLine(info)}
              </p>
            )}
            {info.ingest.error !== null ? <IngestWarning message={info.ingest.error} /> : null}
            <p>
              The map opens here with the first post placed.
              {firstTopics !== null ? ` Topics appear at ${formatCount(firstTopics)} posts.` : ''}
            </p>
          </StepCard>
        </div>
      </div>
    </div>
  )
}
