/* What the tools of the map do: reliefs by meaning or by probe, the lasso stroke, going to a point. */

import { useCallback, useState } from 'react'
import type { ProbeInfo } from '../api/schema'
import type { Relief } from '../axes/relief'
import { MAX_LIKENESS_ITEMS, likenessRelief } from '../axes/relief'
import { useReliefRefresh } from '../axes/useReliefRefresh'
import type { LassoMode, Stroke } from '../lasso/lassoGeometry'
import { combine, pointsInside } from '../lasso/lassoGeometry'
import { logger } from '../log/logger'
import { probeRelief } from '../probes/probeRelief'
import { useMapApi, useScoreStore } from '../source/mapServices'
import type { MapData } from './mapData'
import type { MapModel } from './useMapModel'
import type { Stage } from './useMapStage'

const log = logger('map')
const NO_EMBEDDING = 'The scores could not be computed: the embedding model did not answer.'
const NO_PROBE_SCORES = 'The scores of this probe could not be read.'

export interface MapActions {
  /** A score is being computed. */
  busy: boolean
  error: string | null
  liftConcept(text: string): void
  liftSelection(): void
  /** Raises each point by its score for a probe. */
  liftProbe(probe: ProbeInfo): void
  /** Centres the camera on a point and selects it. */
  goTo(index: number): void
  /** Applies a lasso stroke to the selection; returns whether something is selected. */
  lasso(stroke: Stroke, mode: LassoMode): boolean
}

export function useMapActions(data: MapData, model: MapModel, stage: Stage, coveredRight: () => number): MapActions {
  const api = useMapApi()
  const scoreStore = useScoreStore()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { relief, setRelief, setSelected, setPicked, picked, positions, kept } = model
  const { camera, size, pixelMatrix } = stage
  useReliefRefresh(data, { relief, picked, setRelief })

  const lift = useCallback(
    (scores: Promise<Float32Array>, shape: (values: Float32Array) => Relief, failure: string) => {
      setBusy(true)
      setError(null)
      scores
        .then((values) => setRelief(shape(values)))
        .catch((cause: unknown) => {
          log.error('the scores could not be computed', cause)
          setError(failure)
        })
        .finally(() => setBusy(false))
    },
    [setRelief],
  )

  const liftConcept = useCallback(
    (text: string) =>
      lift(api.similarityToText(text), (values) => likenessRelief(`Resembles “${text}”`, values, { kind: 'concept', text }), NO_EMBEDDING),
    [api, lift],
  )

  const liftSelection = useCallback(() => {
    if (!picked) return
    const sample = Array.from(picked.slice(0, MAX_LIKENESS_ITEMS))
    // The selected items are the concept itself: they stay out of the statistics.
    lift(api.similarityToItems(sample), (values) => likenessRelief('Resembles the selection', values, { kind: 'selection' }, picked), NO_EMBEDDING)
  }, [api, lift, picked])

  const liftProbe = useCallback(
    (probe: ProbeInfo) => lift(scoreStore.read(probe.key, data.version), (values) => probeRelief(probe, values), NO_PROBE_SCORES),
    [scoreStore, data.version, lift],
  )

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

  return { busy, error, liftConcept, liftSelection, liftProbe, goTo, lasso }
}
