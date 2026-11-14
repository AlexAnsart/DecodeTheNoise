/* Copies a text to the clipboard and says so for a moment. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { logger } from '../log/logger'

const log = logger('connect')
/** How long the button says "Copied". */
const SHOWN_MS = 1_800

export interface Copier {
  copied: boolean
  /** The browser refused (no permission, or a page not served over HTTPS). */
  failed: boolean
  copy(text: string): void
}

export function useCopy(): Copier {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])

  const copy = useCallback((text: string): void => {
    window.clearTimeout(timer.current)
    if (!('clipboard' in navigator)) {
      setState('failed')
      return
    }
    navigator.clipboard.writeText(text).then(
      () => {
        setState('copied')
        timer.current = window.setTimeout(() => setState('idle'), SHOWN_MS)
      },
      (cause: unknown) => {
        log.warn('the clipboard refused the text', cause)
        setState('failed')
      },
    )
  }, [])

  return { copied: state === 'copied', failed: state === 'failed', copy }
}
