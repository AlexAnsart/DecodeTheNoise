/* Saves one change of the workspace settings and says how it went. */

import { useState } from 'react'
import { useAction } from '../api/useRequest'
import { patchSettings } from '../api/workspace'
import type { SettingsPatch, WorkspaceInfo } from '../api/workspaceSchema'

export interface SettingsSaver {
  saving: boolean
  /** The last change reached the server. */
  saved: boolean
  error: string | null
  save(patch: SettingsPatch): void
}

export function useSettings(apiKey: string, onInfo: (info: WorkspaceInfo) => void): SettingsSaver {
  const [saved, setSaved] = useState(false)
  const action = useAction(async (patch: SettingsPatch) => {
    setSaved(false)
    onInfo(await patchSettings(apiKey, patch))
    setSaved(true)
  })
  return { saving: action.busy, saved: saved && !action.busy && action.error === null, error: action.error, save: action.run }
}
