/* The key of this browser's workspace. It is the only credential, and it lives here only:
   the server keeps a hash. Shared by the header and the pages, and across tabs. */

import { useSyncExternalStore } from 'react'
import { z } from 'zod'

const STORAGE_KEY = 'noisemap.workspace'

const storedSchema = z.object({ apiKey: z.string().min(1), workspaceId: z.string() })

export type StoredWorkspace = z.infer<typeof storedSchema>

const listeners = new Set<() => void>()

function read(): StoredWorkspace | null {
  try {
    const parsed = storedSchema.safeParse(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null'))
    return parsed.success ? parsed.data : null
  } catch {
    // No storage, or a value that is not ours: this browser has no workspace.
    return null
  }
}

let current = read()

function subscribe(notify: () => void): () => void {
  // Another tab created or forgot the workspace.
  const onStorage = (event: StorageEvent): void => {
    if (event.key !== STORAGE_KEY) return
    current = read()
    notify()
  }
  listeners.add(notify)
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(notify)
    window.removeEventListener('storage', onStorage)
  }
}

/** Remembers the workspace of this browser; null forgets it. */
export function storeWorkspace(next: StoredWorkspace | null): void {
  current = next
  try {
    if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Not remembered: the key lasts as long as this tab.
  }
  listeners.forEach((notify) => notify())
}

export function useStoredWorkspace(): StoredWorkspace | null {
  return useSyncExternalStore(subscribe, () => current)
}
