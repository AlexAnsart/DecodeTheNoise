/* Moving inside the method page. The address is the state: what is open is read from it, and
   opening something writes it, so the view on screen can always be linked. */

import { useCallback, useEffect, useMemo, useRef } from 'react'
import type { RefObject } from 'react'
import { PATHS, navigate, useHash } from '../route/useRoute'
import type { Target } from './hash'
import { anchorOf, hashOf, parseHash } from './hash'

export interface MethodNav {
  target: Target
  /** Goes to a part of the page: it is brought into view, and "Back" returns from it. */
  go(target: Target): void
  /** Opens or closes something where the reader already is: nothing scrolls, and "Back" does
   *  not walk through it. */
  set(target: Target): void
  /** The address of a target, for a real link. */
  href(target: Target): string
}

function hrefOf(target: Target): string {
  return `${PATHS.method}#${hashOf(target)}`
}

/** Brings an element into view once it is on the page. What it shows may still be loading:
 *  the wait ends when the reader scrolls, clicks or types, so the page never jumps later. */
function reveal(scroller: HTMLElement, id: string): () => void {
  const show = (): boolean => {
    const element = document.getElementById(id)
    if (element) element.scrollIntoView({ block: 'start' })
    return element !== null
  }
  if (show()) return () => undefined
  const stop = (): void => {
    observer.disconnect()
    for (const event of TAKEOVER) scroller.removeEventListener(event, stop)
  }
  const observer = new MutationObserver(() => {
    if (show()) stop()
  })
  observer.observe(scroller, { childList: true, subtree: true })
  for (const event of TAKEOVER) scroller.addEventListener(event, stop, { passive: true })
  return stop
}

const TAKEOVER = ['wheel', 'pointerdown', 'keydown', 'touchstart'] as const

export function useMethodNav(scroller: RefObject<HTMLElement | null>): MethodNav {
  const hash = useHash()
  const target = useMemo(() => parseHash(hash), [hash])
  // Set by `set`: the change of address that follows must leave the scroll where it is.
  const quiet = useRef(false)

  useEffect(() => {
    if (quiet.current) {
      quiet.current = false
      return undefined
    }
    // No address: the page opens at its top.
    if (!hash || !scroller.current) return undefined
    return reveal(scroller.current, anchorOf(parseHash(hash)))
  }, [hash, scroller])

  const go = useCallback((next: Target): void => navigate(hrefOf(next)), [])
  const set = useCallback((next: Target): void => {
    const to = hrefOf(next)
    // The same address again changes nothing, so no effect would clear the mark.
    quiet.current = to !== window.location.pathname + window.location.hash
    navigate(to, { replace: true })
  }, [])

  return useMemo(() => ({ target, go, set, href: hrefOf }), [target, go, set])
}
