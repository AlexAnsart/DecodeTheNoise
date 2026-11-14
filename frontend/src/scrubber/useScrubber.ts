import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { TimeRange } from '../map/geometry'
import { clampWindow, openingWindow, stepWindow } from './scrubWindow'

const PLAY_STEP_MS = 1200

export interface Scrubber {
  on: boolean
  window: TimeRange | null
  playing: boolean
  setOn(on: boolean): void
  setWindow(window: TimeRange): void
  setPlaying(playing: boolean): void
}

/** A time window that lights the points inside it. Playing moves it one width at a time. */
export function useScrubber(range: TimeRange | null): Scrubber {
  const [on, setOnState] = useState(false)
  const [chosen, setChosen] = useState<TimeRange | null>(null)
  const [playing, setPlaying] = useState(false)
  // The range moves when a live map gains dated points: the window stays inside it, and opens
  // on the first month until the user places it.
  const window = useMemo(() => (range ? clampWindow(chosen ?? openingWindow(range), range) : null), [chosen, range])

  const latestRange = useRef(range)
  useEffect(() => {
    latestRange.current = range
  })
  const dated = range !== null

  useEffect(() => {
    if (!playing || !dated) return undefined
    // The range is read when the step falls due: a map that grows must not restart the clock.
    const timer = setInterval(() => {
      const now = latestRange.current
      if (!now) return
      setChosen((current) => {
        const from = clampWindow(current ?? openingWindow(now), now)
        const next = stepWindow(from, now)
        if (!next) setPlaying(false)
        return next ?? from
      })
    }, PLAY_STEP_MS)
    return () => clearInterval(timer)
  }, [playing, dated])

  const setOn = useCallback((next: boolean) => {
    setOnState(next)
    if (!next) setPlaying(false)
  }, [])

  return { on: on && range !== null, window, playing, setOn, setWindow: setChosen, setPlaying }
}
