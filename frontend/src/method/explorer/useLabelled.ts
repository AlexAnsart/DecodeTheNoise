/* A page of the labelled posts for the filters in the address. The page on screen stays while
   the next one loads, so the list never blinks empty. */

import { useEffect, useState } from 'react'
import { ApiError } from '../../api/http'
import { fetchLabelled } from '../../api/method'
import type { LabelledPage } from '../../api/methodSchema'
import { describeError } from '../../api/useRequest'
import { logger } from '../../log/logger'
import type { ExplorerQuery } from '../hash'

const log = logger('method')
export const PAGE_SIZE = 20

export interface Labelled {
  /** The last page read; null before the first answer. */
  page: LabelledPage | null
  /** A page is being read. */
  busy: boolean
  error: string | null
  /** The server has no labelled posts to serve. */
  missing: boolean
}

export function useLabelled(query: ExplorerQuery): Labelled {
  const { label, answer, split, round, kind, probe, level, q, offset } = query
  const [state, setState] = useState<Omit<Labelled, 'busy'> & { of: string | null }>({ page: null, error: null, missing: false, of: null })
  // The post opened is not a filter: opening one must not read the page again.
  const key = JSON.stringify([label, answer, split, round, kind, probe, level, q, offset])

  useEffect(() => {
    const abort = new AbortController()
    fetchLabelled({ label, answer, split, round, kind, probe, level, q, offset, limit: PAGE_SIZE }, abort.signal)
      .then((page) => setState({ page, error: null, missing: false, of: key }))
      .catch((cause: unknown) => {
        if (abort.signal.aborted) return
        log.error('the labelled posts could not be read', cause)
        const missing = cause instanceof ApiError && cause.status === 404 && probe === ''
        setState((current) => ({ page: current.page, error: describeError(cause), missing, of: key }))
      })
    return () => abort.abort()
  }, [key, label, answer, split, round, kind, probe, level, q, offset])

  return { page: state.page, busy: state.of !== key, error: state.of === key ? state.error : null, missing: state.missing }
}
