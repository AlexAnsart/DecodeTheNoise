/* Whether the guided tour runs. It opens by itself on the first visit, and again when asked. */

import { useCallback, useState } from 'react'

const SEEN_KEY = 'noisemap.tour'

export interface TourControl {
  active: boolean
  start(): void
  /** Finished or skipped: it does not open by itself again. */
  end(): void
}

function seen(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) !== null
  } catch {
    // No storage: the tour would open on every visit, so it stays closed until asked for.
    return true
  }
}

export function useTour(): TourControl {
  const [active, setActive] = useState(() => !seen())
  const start = useCallback(() => setActive(true), [])
  const end = useCallback(() => {
    setActive(false)
    try {
      localStorage.setItem(SEEN_KEY, 'seen')
    } catch {
      // Not remembered.
    }
  }, [])
  return { active, start, end }
}
