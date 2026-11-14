import { useEffect, useMemo } from 'react'
import type { ReactElement } from 'react'
import { ConnectPanel } from '../connect/ConnectPanel'
import { useSampleSender } from '../connect/useSampleSender'
import { MapScreen } from '../map/MapScreen'
import { SettingsPanel } from '../settings/SettingsPanel'
import { workspaceSource } from '../source/source'
import type { WorkspacePanel } from './panel'
import { StatusStrip } from './StatusStrip'
import { useWorkspace } from './useWorkspace'
import { Walkthrough } from './Walkthrough'
import './workspace.css'

interface OpenWorkspaceProps {
  apiKey: string
  panel: WorkspacePanel | null
  onPanel(panel: WorkspacePanel | null): void
  /** The server does not know the key any more. */
  onUnknownKey(): void
  /** The workspace has a new key: the one this browser held stops working. */
  onKey(apiKey: string, workspaceId: string): void
}

/** A workspace with its key: the walkthrough while it is empty, then its map. */
export function OpenWorkspace({ apiKey, panel, onPanel, onUnknownKey, onKey }: OpenWorkspaceProps): ReactElement {
  const { load, apply, retry } = useWorkspace(apiKey)
  const sender = useSampleSender(apiKey, apply)
  // The same object across renders: the map reloads when its source changes.
  const source = useMemo(() => workspaceSource(apiKey), [apiKey])
  const unknown = load.status === 'unknown-key'
  useEffect(() => {
    if (unknown) onUnknownKey()
  }, [unknown, onUnknownKey])

  if (load.status === 'error') {
    return (
      <div className="nm-screen-state nm-screen-state--error" role="alert">
        <strong>Your workspace could not be opened.</strong>
        {load.message}
        <button type="button" className="nm-btn-secondary nm-btn-small" onClick={retry}>
          Try again
        </button>
      </div>
    )
  }
  if (load.status !== 'ready') {
    return (
      <div className="nm-screen-state" role="status">
        <strong>Opening your workspace…</strong>
        Reading what it holds.
      </div>
    )
  }

  const { info, live } = load
  return (
    <>
      {info.points === 0 ? (
        <Walkthrough apiKey={apiKey} info={info} live={live} sender={sender} />
      ) : (
        <div className="nm-workspace">
          <StatusStrip info={info} live={live} sample={sender.state} />
          <MapScreen
            source={source}
            version={info.version}
            empty={
              <div className="nm-screen-state" role="status">
                <strong>Placing the first posts…</strong>
                The map opens as soon as one is placed.
              </div>
            }
          />
        </div>
      )}
      {panel === 'connect' ? <ConnectPanel apiKey={apiKey} info={info} live={live} sender={sender} onClose={() => onPanel(null)} /> : null}
      {panel === 'settings' ? (
        <SettingsPanel
          apiKey={apiKey}
          info={info}
          onInfo={apply}
          onNewKey={(key) => onKey(key, info.id)}
          onClose={() => onPanel(null)}
        />
      ) : null}
    </>
  )
}
