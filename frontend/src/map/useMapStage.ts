/* The canvas side of the map view: deck.gl host, camera, layers, and the HTML that follows a
   point (card, pivot, axis words), placed after each frame without a React render. */

import type { PickingInfo } from '@deck.gl/core'
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { RefObject } from 'react'
import type { AxisMarks } from '../axes/axisMarks'
import type { AxisWordsHandle } from '../axes/AxisWords'
import type { Palette } from '../colour/palette'
import { placeCard } from '../picking/placement'
import type { Pointer } from '../picking/usePointer'
import { usePointer } from '../picking/usePointer'
import { pointAt } from './geometry'
import type { Ring, Segment } from './layers'
import { EDGES_LAYER, POINTS_LAYER, buildLayers } from './layers'
import type { MapData } from './mapData'
import { neighboursOf } from './mapData'
import type { Camera } from './useCamera'
import { useCamera } from './useCamera'
import { currentViewport, useDeck } from './useDeck'
import type { MapModel } from './useMapModel'
import type { Size } from './views'
import { isFlat } from './views'

const CONTROLLER = { doubleClickZoom: false, inertia: 300 }
const SELECTED_RING_PX = 7
const LISTED_RING_PX = 9

export interface StageRefs {
  stage: RefObject<HTMLDivElement | null>
  host: RefObject<HTMLDivElement | null>
  card: RefObject<HTMLDivElement | null>
  pivot: RefObject<HTMLDivElement | null>
  drawers: RefObject<HTMLDivElement | null>
  words: RefObject<AxisWordsHandle | null>
}

export interface StageInput {
  data: MapData
  model: MapModel
  palette: Palette
  refs: StageRefs
  lasso: boolean
  /** Lines from the selected point to its neighbours are drawn. */
  edges: boolean
  /** Point whose card is under the pointer in a list. */
  ringed: number | null
  marks: AxisMarks
}

export interface Stage {
  failed: boolean
  size: Size | null
  camera: Camera
  pointer: Pointer
  /** The pointer is on a line to a neighbour of the selected point. */
  onEdge: boolean
  /** Neighbours of the selected point that the filters still show, nearest first. */
  neighbours: number[]
  /** Width of the stage no drawer covers. */
  freeWidth(): number
  project(position: number[]): number[] | null
  place(): void
}

export function useMapStage(input: StageInput): Stage {
  const { data, model, palette, refs, lasso, edges, ringed, marks } = input
  const { positions, colours, kept, gap, shape, selected } = model
  const latest = useRef(input)
  const [onEdge, setOnEdge] = useState(false)

  useEffect(() => {
    latest.current = input
  })

  const freeWidth = useCallback(
    () => (refs.stage.current?.clientWidth ?? 0) - (refs.drawers.current?.offsetWidth ?? 0),
    [refs],
  )
  const pointer = usePointer(refs.stage, freeWidth)

  const neighbours = useMemo(
    () => (selected === null ? [] : neighboursOf(data, selected).filter((other) => kept.values[other] >= 0.5)),
    [data, selected, kept],
  )

  const pick = (info: PickingInfo): { index: number; viaEdge: boolean } | null => {
    if (info.layer?.id === POINTS_LAYER && info.index >= 0) return { index: info.index, viaEdge: false }
    if (info.layer?.id === EDGES_LAYER && info.object) return { index: (info.object as Segment).index, viaEdge: true }
    return null
  }

  const { deck, size, failed } = useDeck(refs.host, shape, {
    onView: (view) => camera.onView(view),
    onHover: (info) => {
      const hit = pick(info)
      setOnEdge(hit?.viaEdge ?? false)
      // The selected point already has its card: no tooltip on top of it.
      pointer.onHover(hit && hit.index !== latest.current.model.selected ? hit.index : null, info.x, info.y)
    },
    onClick: (info) => latest.current.model.setSelected(pick(info)?.index ?? null),
    onFrame: () => place(),
    cursor: ({ isDragging, isHovering }) => (isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'),
  })

  const camera = useCamera({ deck, size, shape, positions, gap, kept: kept.values, selected })

  const project = useCallback(
    (position: number[]): number[] | null => currentViewport(deck.current)?.project(position) ?? null,
    [deck],
  )

  const place = useCallback(() => {
    const now = latest.current
    const stage = now.refs.stage.current
    const viewport = currentViewport(deck.current)
    if (!stage || !viewport) return
    const card = now.refs.card.current
    if (card) {
      const chosen = now.model.selected
      const at = chosen === null ? null : viewport.project(pointAt(now.model.positions, chosen))
      const placed = at
        ? placeCard(at[0], at[1], card.offsetWidth, { width: stage.clientWidth, height: stage.clientHeight }, freeWidth())
        : null
      card.style.visibility = placed ? 'visible' : 'hidden'
      if (placed) {
        card.style.transform = `translate(${Math.round(placed.left)}px, ${Math.round(placed.top)}px)`
        card.style.maxHeight = `${Math.round(placed.maxHeight)}px`
      }
    }
    const pivot = now.refs.pivot.current
    const view = camera.view.current
    if (pivot && view) {
      const [x, y] = viewport.project(view.target)
      pivot.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px) translate(-50%, -50%)`
    }
    now.refs.words.current?.place((position) => viewport.project(position))
  }, [deck, camera, freeWidth])

  const segments = useMemo<Segment[]>(() => {
    if (selected === null || !edges) return []
    const from = pointAt(positions, selected)
    return neighbours.map((other) => ({ from, to: pointAt(positions, other), index: other }))
  }, [selected, edges, neighbours, positions])

  const rings = useMemo<Ring[]>(() => {
    const out: Ring[] = []
    if (selected !== null) out.push({ position: pointAt(positions, selected), radius: SELECTED_RING_PX, filled: false })
    if (ringed !== null && ringed !== selected) out.push({ position: pointAt(positions, ringed), radius: LISTED_RING_PX, filled: true })
    return out
  }, [selected, ringed, positions])

  useEffect(() => {
    deck.current?.setProps({
      layers: buildLayers({
        n: data.n,
        positions,
        colours,
        kept: kept.values,
        gap,
        flat: isFlat(shape),
        segments,
        rings,
        axes: marks.lines,
        accent: palette.accent,
        muted: palette.muted,
        highlight: palette.highlight,
      }),
    })
  }, [deck, data, positions, colours, kept, gap, shape, segments, rings, marks, palette, size])

  useEffect(() => {
    deck.current?.setProps({ controller: lasso ? false : CONTROLLER })
  }, [deck, lasso, size])

  // The card and the words mount after a render that draws no new frame: place them now.
  useLayoutEffect(() => place(), [place, selected, marks, shape])

  return { failed, size, camera, pointer, onEdge, neighbours, freeWidth, project, place }
}
