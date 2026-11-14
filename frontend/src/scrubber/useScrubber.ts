import { useCallback, useEffect, useState } from 'react'
import type { TimeRange } from '../map/geometry'
import { openingWindow, stepWindow } from './scrubWindow'

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
  const [window, setWindow] = useState<TimeRange | null>(() => (range ? openingWindow(range) : null))
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    if (!playing || !range) return undefined
    const timer = setInterval(() => {
      setWindow((current) => {
        const next = current ? stepWindow(current, range) : null
        if (!next) setPlaying(false)
        return next ?? current
      })
    }, PLAY_STEP_MS)
    return () => clearInterval(timer)
  }, [playing, range])

  const setOn = useCallback((next: boolean) => {
    setOnState(next)
    if (!next) setPlaying(false)
  }, [])

  return { on: on && range !== null, window, playing, setOn, setWindow, setPlaying }
}
