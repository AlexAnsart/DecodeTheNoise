/* The live state of a workspace: a server-sent event stream read with `fetch`, because
   `EventSource` cannot send the key as a header. */

import { send, withKey } from './http'
import { workspaceInfoSchema } from './workspaceSchema'
import type { WorkspaceInfo } from './workspaceSchema'

const EVENTS = '/api/v1/events'
const WORKSPACE_EVENT = 'workspace'

/** The event name and the data of one block of the stream; null for a heartbeat or a comment. */
export function parseEvent(block: string): { event: string; data: string } | null {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''))
  }
  return data.length > 0 ? { event, data: data.join('\n') } : null
}

export interface WorkspaceStream {
  /** The server accepted the stream: updates will come through it. */
  onOpen(): void
  onInfo(info: WorkspaceInfo): void
}

/**
 * Calls `onInfo` with every state the server announces, until the stream ends or `signal`
 * aborts. Resolves when the server closes the stream; rejects with an `ApiError` when it
 * refuses the request (401 for an unknown key).
 */
export async function streamWorkspace(apiKey: string, { onOpen, onInfo }: WorkspaceStream, signal: AbortSignal): Promise<void> {
  const response = await send(EVENTS, withKey({ signal, headers: { Accept: 'text/event-stream' } }, apiKey))
  if (!response.body) return
  onOpen()
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) return
    pending += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
    let end = pending.indexOf('\n\n')
    while (end !== -1) {
      const parsed = parseEvent(pending.slice(0, end))
      pending = pending.slice(end + 2)
      if (parsed?.event === WORKSPACE_EVENT) onInfo(workspaceInfoSchema.parse(JSON.parse(parsed.data)))
      end = pending.indexOf('\n\n')
    }
  }
}
