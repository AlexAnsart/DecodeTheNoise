/* The open workspace: read once, then kept up to date by the server's event stream. One
   stream per open page feeds the walkthrough, the status strip, the map and the panels. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { streamWorkspace } from '../api/events'
import { ApiError } from '../api/http'
import { describeError } from '../api/useRequest'
import { fetchWorkspace } from '../api/workspace'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { logger } from '../log/logger'
import { ingestChange } from './progress'

const log = logger('workspace')
const FIRST_RETRY_MS = 1_000
const MAX_RETRY_MS = 15_000

export type WorkspaceLoad =
  | { status: 'loading' }
  /** `live` is false while the stream is being opened again: the counts may be late. */
  | { status: 'ready'; info: WorkspaceInfo; live: boolean }
  /** The server does not know the key any more. */
  | { status: 'unknown-key' }
  | { status: 'error'; message: string }

export interface Workspace {
  load: WorkspaceLoad
  /** Takes the fresher state an action returned, without waiting for the stream. */
  apply(info: WorkspaceInfo): void
  retry(): void
}

export function useWorkspace(apiKey: string): Workspace {
  const [load, setLoad] = useState<WorkspaceLoad>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  // The last state seen, to say in the log when embedding starts, stalls, resumes or ends.
  const seen = useRef<WorkspaceInfo | null>(null)
  const note = useCallback((info: WorkspaceInfo): void => {
    const change = ingestChange(seen.current, info)
    seen.current = info
    if (change === null) return
    if (info.ingest.error !== null) log.warn(change)
    else log.info(change)
  }, [])

  useEffect(() => {
    const abort = new AbortController()
    let delay = FIRST_RETRY_MS
    let timer: number | undefined
    const settle = (info: WorkspaceInfo, live: boolean): void => {
      note(info)
      setLoad({ status: 'ready', info, live })
    }
    const refused = (error: unknown): boolean => {
      if (!(error instanceof ApiError) || error.status !== 401) return false
      setLoad({ status: 'unknown-key' })
      return true
    }
    // The stream is the source of updates. When it ends (a deploy, a proxy timeout), the wait
    // before opening it again only keeps a server that is down from being hammered.
    const later = (): void => {
      timer = window.setTimeout(() => void resume(), delay)
      delay = Math.min(delay * 2, MAX_RETRY_MS)
    }
    const listen = async (): Promise<void> => {
      const onOpen = (): void => {
        delay = FIRST_RETRY_MS
        setLoad((current) => (current.status === 'ready' ? { ...current, live: true } : current))
      }
      try {
        await streamWorkspace(apiKey, { onOpen, onInfo: (info) => settle(info, true) }, abort.signal)
      } catch (error) {
        if (abort.signal.aborted || refused(error)) return
        log.warn('the event stream stopped', error)
      }
      if (abort.signal.aborted) return
      setLoad((current) => (current.status === 'ready' ? { ...current, live: false } : current))
      later()
    }
    const resume = async (): Promise<void> => {
      try {
        // What changed while the stream was closed.
        settle(await fetchWorkspace(apiKey, abort.signal), false)
      } catch (error) {
        if (abort.signal.aborted || refused(error)) return
        later()
        return
      }
      void listen()
    }
    fetchWorkspace(apiKey, abort.signal)
      .then((info) => {
        settle(info, false)
        void listen()
      })
      .catch((error: unknown) => {
        if (abort.signal.aborted || refused(error)) return
        log.error('the workspace could not be read', error)
        setLoad({ status: 'error', message: describeError(error) })
      })
    return () => {
      abort.abort()
      window.clearTimeout(timer)
    }
  }, [apiKey, attempt, note])

  const apply = useCallback(
    (info: WorkspaceInfo): void => {
      // An answer can arrive after a newer state came through the stream: the newer one stays.
      if (seen.current !== null && info.version < seen.current.version) return
      note(info)
      setLoad((current) => ({ status: 'ready', info, live: current.status === 'ready' && current.live }))
    },
    [note],
  )
  const retry = useCallback((): void => {
    setLoad({ status: 'loading' })
    setAttempt((count) => count + 1)
  }, [])

  return { load, apply, retry }
}
