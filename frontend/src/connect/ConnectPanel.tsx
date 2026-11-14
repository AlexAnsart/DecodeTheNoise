import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { SidePanel } from '../app/SidePanel'
import { formatCount } from '../text/format'
import { IngestWarning } from '../workspace/IngestWarning'
import { KeyField } from './KeyField'
import { SendTabs } from './SendTabs'
import type { SampleSender } from './useSampleSender'
import './connect.css'

interface ConnectPanelProps {
  apiKey: string
  info: WorkspaceInfo
  live: boolean
  sender: SampleSender
  onClose(): void
}

/** The key and the ways to send posts, at hand once the map is on screen. */
export function ConnectPanel({ apiKey, info, live, sender, onClose }: ConnectPanelProps): ReactElement {
  return (
    <SidePanel title="Connect your posts" onClose={onClose}>
      {info.ingest.error !== null ? <IngestWarning message={info.ingest.error} /> : null}
      <section className="nm-block">
        <h3>Your API key</h3>
        <p>The only credential, kept in this browser. Copy it somewhere safe: nothing else opens this workspace.</p>
        <KeyField apiKey={apiKey} />
      </section>
      <section className="nm-block">
        <h3>Send your posts</h3>
        <SendTabs apiKey={apiKey} info={info} live={live} sender={sender} />
      </section>
      <section className="nm-block">
        <h3>Room left</h3>
        <p className="nm-num">
          {formatCount(info.items)} of {formatCount(info.limits.items)} posts stored. Up to {formatCount(info.limits.batch_items)} posts per
          batch call, {formatCount(info.limits.requests_per_minute)} requests a minute.
        </p>
      </section>
    </SidePanel>
  )
}
