/* Sends posts of the demo dataset to the workspace through the public batch route, chunk by
   chunk, so the map is seen building without a line of code. */

import { useCallback, useRef, useState } from 'react'
import { describeError } from '../api/useRequest'
import { fetchSample, fetchWorkspace, sendBatch } from '../api/workspace'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { logger } from '../log/logger'

const log = logger('connect')
export const SAMPLE_POSTS = 200
const CHUNK = 25

export type SampleState =
  | { status: 'idle' }
  | { status: 'fetching' }
  | { status: 'sending'; sent: number; total: number }
  /** Every chunk reached the server. `refused` is its reason for the first post it turned down. */
  | { status: 'done'; sent: number; rejected: number; refused: string | null }
  | { status: 'error'; message: string }

export interface SampleSender {
  state: SampleState
  busy: boolean
  send(): void
}

/** `onInfo` receives the state of the workspace once the last chunk is in, so that what is
 *  shown next (the embedding of those posts) starts from what the server holds. */
export function useSampleSender(apiKey: string, onInfo: (info: WorkspaceInfo) => void): SampleSender {
  const [state, setState] = useState<SampleState>({ status: 'idle' })
  const running = useRef(false)

  const send = useCallback((): void => {
    if (running.current) return
    running.current = true
    const run = async (): Promise<void> => {
      setState({ status: 'fetching' })
      const { items } = await fetchSample(SAMPLE_POSTS)
      let rejected = 0
      let refused: string | null = null
      for (let start = 0; start < items.length; start += CHUNK) {
        setState({ status: 'sending', sent: start, total: items.length })
        // One request after the other: the server answers each chunk before the next leaves.
        const accepted = await sendBatch(apiKey, items.slice(start, start + CHUNK))
        rejected += accepted.rejected.length
        refused ??= accepted.rejected[0]?.reason ?? null
      }
      log.info(`sample sent: ${items.length - rejected} posts accepted, ${rejected} refused`)
      onInfo(await fetchWorkspace(apiKey))
      setState({ status: 'done', sent: items.length - rejected, rejected, refused })
    }
    run()
      .catch((cause: unknown) => {
        log.error('the sample posts could not be sent', cause)
        setState({ status: 'error', message: describeError(cause) })
      })
      .finally(() => {
        running.current = false
      })
  }, [apiKey, onInfo])

  return { state, busy: state.status === 'fetching' || state.status === 'sending', send }
}
