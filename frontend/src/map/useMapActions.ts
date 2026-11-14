/* What the tools of the map do: reliefs by meaning, the lasso stroke, going to a point. */

import { useCallback, useState } from 'react'
import { similarityToItems, similarityToText } from '../api/client'
import { likenessRelief } from '../axes/relief'
import type { LassoMode, Stroke } from '../lasso/lassoGeometry'
import { combine, pointsInside } from '../lasso/lassoGeometry'
import { logger } from '../log/logger'
import type { MapModel } from './useMapModel'
import type { Stage } from './useMapStage'

const log = logger('map')
/** The server takes at most this many points to resemble. */
const MAX_LIKENESS_ITEMS = 5000

export interface MapActions {
  /** A score is being computed. */
  busy: boolean
  error: string | null
  liftConcept(text: string): void
  liftSelection(): void
  /** Centres the camera on a point and selects it. */
  goTo(index: number): void
  /** Applies a lasso stroke to the selection; returns whether something is selected. */
  lasso(stroke: Stroke, mode: LassoMode): boolean
}

export function useMapActions(model: MapModel, stage: Stage, coveredRight: () => number): MapActions {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { setRelief, setSelected, setPicked, picked, positions, kept } = model
  const { camera, size, pixelMatrix } = stage

  const lift = useCallback(
    (label: string, scores: Promise<Float32Array>, skip: ArrayLike<number>) => {
      setBusy(true)
      setError(null)
      scores
        .then((values) => setRelief(likenessRelief(label, values, skip)))
        .catch((cause: unknown) => {
          log.error('the scores could not be computed', cause)
          setError('The scores could not be computed: the embedding model did not answer.')
        })
        .finally(() => setBusy(false))
    },
    [setRelief],
  )

  const liftConcept = useCallback(
    (text: string) => lift(`Resembles “${text}”`, similarityToText(text), []),
    [lift],
  )

  const liftSelection = useCallback(() => {
    if (!picked) return
    const sample = Array.from(picked.slice(0, MAX_LIKENESS_ITEMS))
    // The selected items are the concept itself: they stay out of the statistics.
    lift('Resembles the selection', similarityToItems(sample), picked)
  }, [lift, picked])

  const goTo = useCallback(
    (index: number) => {
      camera.centreOn(index, coveredRight())
      setSelected(index)
    },
    [camera, coveredRight, setSelected],
  )

  const lasso = useCallback(
    (stroke: Stroke, mode: LassoMode): boolean => {
      const matrix = pixelMatrix()
      if (!size || !matrix) return picked !== null
      const found = pointsInside(
        matrix,
        positions,
        kept.values,
        stroke,
        size.width,
        size.height,
      )
      const next = combine(picked, found, mode)
      setPicked(next)
      return next !== null
    },
    [size, pixelMatrix, positions, kept, picked, setPicked],
  )

  return { busy, error, liftConcept, liftSelection, goTo, lasso }
}
