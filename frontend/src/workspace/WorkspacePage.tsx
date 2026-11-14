import { useCallback, useState } from 'react'
import type { ReactElement } from 'react'
import type { WorkspaceCreated } from '../api/workspaceSchema'
import { OpenWorkspace } from './OpenWorkspace'
import type { WorkspacePanel } from './panel'
import { StartCard } from './StartCard'
import { storeWorkspace, useStoredWorkspace } from './storedKey'

const KEY_GONE = 'The key kept in this browser is no longer valid: it was replaced, or its workspace is gone. Create a workspace to start again.'

interface WorkspacePageProps {
  panel: WorkspacePanel | null
  onPanel(panel: WorkspacePanel | null): void
}

/** "My workspace": a card to create one, then the workspace itself. */
export function WorkspacePage({ panel, onPanel }: WorkspacePageProps): ReactElement {
  const stored = useStoredWorkspace()
  const [notice, setNotice] = useState<string | null>(null)

  const remember = useCallback((apiKey: string, workspaceId: string): void => {
    setNotice(null)
    storeWorkspace({ apiKey, workspaceId })
  }, [])
  const forget = useCallback((): void => {
    setNotice(KEY_GONE)
    onPanel(null)
    storeWorkspace(null)
  }, [onPanel])

  if (!stored) {
    const created = (workspace: WorkspaceCreated): void => remember(workspace.api_key, workspace.workspace.id)
    return <StartCard notice={notice} onCreated={created} />
  }
  // A new key is a new connection: the workspace is opened again from scratch.
  return <OpenWorkspace key={stored.apiKey} apiKey={stored.apiKey} panel={panel} onPanel={onPanel} onUnknownKey={forget} onKey={remember} />
}
