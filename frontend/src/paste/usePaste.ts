/* The paste box: a text, or the page behind a link, is embedded by the server with the model
   that built the map, and lands among its nearest items. */

import { useCallback, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import type { Analysis } from '../api/schema'
import { logger } from '../log/logger'
import { useMapApi } from '../source/mapServices'

const log = logger('paste')

export type PasteState =
  | { status: 'idle' }
  | { status: 'reading'; what: 'text' | 'link' }
  | { status: 'done'; analysis: Analysis }
  | { status: 'error'; message: string }

export interface Paste {
  state: PasteState
  submit(input: string): void
  clear(): void
}

/** A single line that starts like a web address is read as a link; anything else is a text. */
export function asLink(input: string): string | null {
  const clean = input.trim()
  return /^https?:\/\/\S+$/i.test(clean) ? clean : null
}

function explain(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) return 'Too many requests for now. Try again in a minute.'
  if (error instanceof ApiError) return error.message
  return 'The server did not answer.'
}

export function usePaste(): Paste {
  const api = useMapApi()
  const [state, setState] = useState<PasteState>({ status: 'idle' })
  const running = useRef<AbortController | null>(null)

  const submit = useCallback(
    (input: string) => {
      const link = asLink(input)
      running.current?.abort()
      const abort = new AbortController()
      running.current = abort
      setState({ status: 'reading', what: link ? 'link' : 'text' })
      api
        .analyze(link ? { url: link } : { text: input.trim() }, abort.signal)
        .then((analysis) => setState({ status: 'done', analysis }))
        .catch((error: unknown) => {
          if (abort.signal.aborted) return
          log.error('the paste could not be analysed', error)
          setState({ status: 'error', message: explain(error) })
        })
    },
    [api],
  )

  const clear = useCallback(() => {
    running.current?.abort()
    setState({ status: 'idle' })
  }, [])

  return { state, submit, clear }
}
