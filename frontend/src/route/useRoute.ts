/* The three pages of the app, read from the address bar. The History API is enough: no library. */

import { useEffect, useSyncExternalStore } from 'react'

export type Page = 'demo' | 'workspace' | 'method'

export const PATHS: Record<Page, string> = { demo: '/', workspace: '/workspace', method: '/method' }

const NAVIGATED = 'noisemap:navigated'

/** An unknown path is the demo: the app always has something to show. */
export function pageOf(pathname: string): Page {
  const path = pathname.replace(/\/+$/, '')
  if (path === PATHS.workspace) return 'workspace'
  if (path === PATHS.method) return 'method'
  return 'demo'
}

function subscribe(notify: () => void): () => void {
  window.addEventListener('popstate', notify)
  window.addEventListener('hashchange', notify)
  window.addEventListener(NAVIGATED, notify)
  return () => {
    window.removeEventListener('popstate', notify)
    window.removeEventListener('hashchange', notify)
    window.removeEventListener(NAVIGATED, notify)
  }
}

/** Goes to a path of the app without loading the page again. */
export function navigate(to: string): void {
  const { pathname, search, hash } = window.location
  if (to !== pathname + search + hash) window.history.pushState(null, '', to)
  window.dispatchEvent(new Event(NAVIGATED))
}

export function useRoute(): Page {
  return useSyncExternalStore(subscribe, () => pageOf(window.location.pathname))
}

/** The part after `#`, without it: the section a link points at. */
export function useHash(): string {
  return useSyncExternalStore(subscribe, () => window.location.hash.slice(1))
}

function isPlainClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey
}

/** Whether a click on this link should move inside the app instead of loading a page. */
export function staysInApp(event: MouseEvent, anchor: HTMLAnchorElement): boolean {
  if (event.defaultPrevented || !isPlainClick(event)) return false
  if (anchor.target || anchor.hasAttribute('download')) return false
  const url = new URL(anchor.href, window.location.href)
  return url.origin === window.location.origin && !url.pathname.startsWith('/api')
}

/** Makes any plain link to a page of the app (`<a href="/method#probes">`) navigate in place. */
export function useInternalLinks(): void {
  useEffect(() => {
    const onClick = (event: MouseEvent): void => {
      const anchor = event.target instanceof Element ? event.target.closest('a') : null
      if (!anchor || !staysInApp(event, anchor)) return
      const url = new URL(anchor.href, window.location.href)
      event.preventDefault()
      navigate(url.pathname + url.search + url.hash)
    }
    document.addEventListener('click', onClick)
    return () => document.removeEventListener('click', onClick)
  }, [])
}
