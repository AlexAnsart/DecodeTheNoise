/* A read made when a view opens, and a write started by a click: each with the loading and
   failure states the view has to show. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { logger } from '../log/logger'
import { ApiError } from './http'

const log = logger('api')

export type Request<T> =
  | { status: 'loading' }
  | { status: 'ready'; data: T }
  | { status: 'error'; message: string }

/** A failure in words the person can act on. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return `Too many requests: ${error.message}`
    if (error.status >= 500) return `The server could not answer (${error.status}). Try again in a moment.`
    return error.message
  }
  return 'The server could not be reached. Check the connection and try again.'
}

/** Reads once when the view opens. `load` must be a stable function (declared in a module). */
export function useRequest<T>(load: (signal: AbortSignal) => Promise<T>): Request<T> {
  const [state, setState] = useState<Request<T>>({ status: 'loading' })
  useEffect(() => {
    const abort = new AbortController()
    load(abort.signal)
      .then((data) => setState({ status: 'ready', data }))
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.error('a request failed', error)
        setState({ status: 'error', message: describeError(error) })
      })
    return () => abort.abort()
  }, [load])
  return state
}

export interface Action<A extends unknown[]> {
  busy: boolean
  /** Why the last run failed; null while it runs and once one succeeds. */
  error: string | null
  run(...args: A): void
}

/** A request started by a click. A second click while it runs is ignored. */
export function useAction<A extends unknown[]>(perform: (...args: A) => Promise<unknown>): Action<A> {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = useRef(perform)
  const running = useRef(false)
  useEffect(() => {
    latest.current = perform
  })
  const run = useCallback((...args: A): void => {
    if (running.current) return
    running.current = true
    setBusy(true)
    setError(null)
    latest
      .current(...args)
      .catch((cause: unknown) => {
        log.error('an action failed', cause)
        setError(describeError(cause))
      })
      .finally(() => {
        running.current = false
        setBusy(false)
      })
  }, [])
  return { busy, error, run }
}
