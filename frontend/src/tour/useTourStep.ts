/* Which card of the tour is shown, and where its target sits on the page. */

import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import type { TourStep } from './steps'
import { TOUR_STEPS, targetOf } from './steps'

export interface Box {
  left: number
  top: number
  width: number
  height: number
}

export interface TourPosition {
  /** Index in `TOUR_STEPS`; null while the first target is not on the page yet. */
  index: number | null
  step: TourStep | null
  box: Box | null
  /** Steps whose target is on the page, in order: the dots of the card. */
  present: number[]
  next(): void
  back(): void
}

function presentSteps(): number[] {
  return TOUR_STEPS.map((step, index) => (targetOf(step) ? index : -1)).filter((index) => index >= 0)
}

function boxOf(element: HTMLElement): Box {
  const { left, top, width, height } = element.getBoundingClientRect()
  return { left, top, width, height }
}

/** Walks the steps whose target exists. `onEnd` is called past the last one. */
export function useTourStep(onEnd: () => void): TourPosition {
  const [index, setIndex] = useState<number | null>(null)
  const [present, setPresent] = useState<number[]>([])
  // The box is kept with the step it was measured for: a new step starts without one.
  const [measured, setMeasured] = useState<{ index: number; box: Box } | null>(null)

  // The map loads after the page: the tour opens once the first target is there.
  useEffect(() => {
    if (index !== null) return undefined
    const open = (): boolean => {
      if (!targetOf(TOUR_STEPS[0])) return false
      setPresent(presentSteps())
      setIndex(0)
      return true
    }
    if (open()) return undefined
    const observer = new MutationObserver(() => {
      if (open()) observer.disconnect()
    })
    observer.observe(document.body, { childList: true, subtree: true })
    return () => observer.disconnect()
  }, [index])

  // The target moves when the window is resized or the toolbar wraps: the card follows.
  useLayoutEffect(() => {
    const element = index === null ? null : targetOf(TOUR_STEPS[index])
    if (index === null || !element) return undefined
    const measure = (): void => setMeasured({ index, box: boxOf(element) })
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [index])

  const move = useCallback(
    (by: 1 | -1): void => {
      if (index === null) return
      // A control can leave the page between two steps (a menu closed, a panel opened).
      const still = presentSteps()
      setPresent(still)
      const target = by === 1 ? still.find((other) => other > index) : still.findLast((other) => other < index)
      if (target === undefined) {
        if (by === 1) onEnd()
        return
      }
      setIndex(target)
    },
    [index, onEnd],
  )
  const next = useCallback(() => move(1), [move])
  const back = useCallback(() => move(-1), [move])

  const box = measured !== null && measured.index === index ? measured.box : null
  return { index, step: index === null ? null : TOUR_STEPS[index], box, present, next, back }
}
