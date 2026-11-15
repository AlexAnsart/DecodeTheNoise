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
import type { ExtraPoint, Ring, Segment, Vec3 } from './layers'
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
const PASTED_RING_PX = 9
/** A press released this close to where it started is a click, with no double-click wait. */
const CLICK_SLOP_PX = 5
/** A line picked this close to the selected point stands for the point itself. */
const NEAR_SELECTED_PX = 9

export interface Pasted {
  position: Vec3
  neighbours: number[]
  /** Labelled and tied to its neighbours; otherwise drawn like any other point. */
  highlighted: boolean
}

export interface StageRefs {
  stage: RefObject<HTMLDivElement | null>
  host: RefObject<HTMLDivElement | null>
  card: RefObject<HTMLDivElement | null>
  pivot: RefObject<HTMLDivElement | null>
  drawers: RefObject<HTMLDivElement | null>
  words: RefObject<AxisWordsHandle | null>
  /** The label that follows a pasted text. */
  pastedLabel: RefObject<HTMLDivElement | null>
}

export interface StageInput {
  data: MapData
  model: MapModel
  palette: Palette
  refs: StageRefs
  lasso: boolean
  /** Point whose card is under the pointer in a list. */
  ringed: number | null
  marks: AxisMarks
  /** A pasted text placed on the map: where it sits and the points it resembles most. */
  pasted: Pasted | null
  /** Called on every click on the canvas, on a point or not. */
  onCanvasClick(): void
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
  /** World-to-pixel matrix of the current frame, for tests done on the CPU. */
  pixelMatrix(): number[] | null
  place(): void
}

export function useMapStage(input: StageInput): Stage {
  const { data, model, palette, refs, lasso, ringed, marks, pasted } = input
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
      let hit = pick(info)
      const chosen = latest.current.model.selected
      if (hit?.viaEdge && chosen !== null) {
        const at = currentViewport(deck.current)?.project(pointAt(latest.current.model.positions, chosen))
        if (at && Math.hypot(at[0] - info.x, at[1] - info.y) < NEAR_SELECTED_PX) hit = null
      }
      setOnEdge(hit?.viaEdge ?? false)
      // The selected point already has its card: no tooltip on top of it.
      pointer.onHover(hit && hit.index !== latest.current.model.selected ? hit.index : null, info.x, info.y)
    },
    onFrame: () => place(),
    cursor: ({ isDragging, isHovering }) => (isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'),
  })

  const frame = useMemo(
    () => [...marks.lines.flatMap((line) => line.path), ...marks.words.map((word) => word.position)],
    [marks],
  )
  const camera = useCamera({ deck, size, shape, positions, gap, kept: kept.values, selected, frame })

  const pixelMatrix = useCallback(
    (): number[] | null => currentViewport(deck.current)?.pixelProjectionMatrix ?? null,
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
    const label = now.refs.pastedLabel.current
    if (label && now.pasted) {
      const [x, y] = viewport.project(now.pasted.position)
      const inside = x >= 0 && y >= 0 && x <= stage.clientWidth && y <= stage.clientHeight
      label.style.visibility = inside ? 'visible' : 'hidden'
      label.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`
    }
  }, [deck, camera, freeWidth])

  // Clicks are read from the pointer itself: a press released where it started selects the point
  // under it, or clears the selection on empty canvas. The selected point clicked again lets go.
  useEffect(() => {
    const host = refs.host.current
    if (!host) return undefined
    let down: { x: number; y: number } | null = null
    const onDown = (event: PointerEvent): void => {
      down = event.button === 0 ? { x: event.clientX, y: event.clientY } : null
      // While a button is held the map is being turned or moved: the pivot mark shows plainly.
      latest.current.refs.stage.current?.classList.add('is-turning')
    }
    const onRelease = (): void => latest.current.refs.stage.current?.classList.remove('is-turning')
    const onUp = (event: PointerEvent): void => {
      const start = down
      down = null
      if (!start || Math.hypot(event.clientX - start.x, event.clientY - start.y) > CLICK_SLOP_PX) return
      if (!deck.current?.isInitialized) return
      const box = host.getBoundingClientRect()
      const info = deck.current.pickObject({ x: event.clientX - box.left, y: event.clientY - box.top, radius: CLICK_SLOP_PX })
      const hit = info ? pick(info)?.index ?? null : null
      const model = latest.current.model
      model.setSelected(hit !== null && hit === model.selected ? null : hit)
      latest.current.onCanvasClick()
    }
    host.addEventListener('pointerdown', onDown)
    host.addEventListener('pointerup', onUp)
    // In the capture phase: the canvas keeps some of these events for itself.
    window.addEventListener('pointerup', onRelease, true)
    window.addEventListener('pointercancel', onRelease, true)
    window.addEventListener('blur', onRelease)
    return () => {
      host.removeEventListener('pointerdown', onDown)
      host.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointerup', onRelease, true)
      window.removeEventListener('pointercancel', onRelease, true)
      window.removeEventListener('blur', onRelease)
    }
    // `pick` reads only its argument; the model is read through the latest ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deck, refs.host])

  const segments = useMemo<Segment[]>(() => {
    const out: Segment[] = []
    if (selected !== null) {
      const from = pointAt(positions, selected)
      for (const other of neighbours) out.push({ from, to: pointAt(positions, other), index: other })
    }
    if (pasted?.highlighted) {
      for (const other of pasted.neighbours) {
        if (kept.values[other] >= 0.5) out.push({ from: pasted.position, to: pointAt(positions, other), index: other })
      }
    }
    return out
  }, [selected, neighbours, positions, pasted, kept])

  const rings = useMemo<Ring[]>(() => {
    const out: Ring[] = []
    if (selected !== null) out.push({ position: pointAt(positions, selected), radius: SELECTED_RING_PX, fill: 'none' })
    if (ringed !== null && ringed !== selected) out.push({ position: pointAt(positions, ringed), radius: LISTED_RING_PX, fill: 'tint' })
    if (pasted?.highlighted) out.push({ position: pasted.position, radius: PASTED_RING_PX, fill: 'solid' })
    return out
  }, [selected, ringed, positions, pasted])

  // The pasted text as a point: it takes the colour its nearest item has right now, so it
  // follows the colouring and the dimming like the points around it.
  const extra = useMemo<ExtraPoint | null>(() => {
    if (!pasted || pasted.neighbours.length === 0) return null
    const nearest = pasted.neighbours[0] * 4
    return {
      position: pasted.position,
      colour: [colours[nearest], colours[nearest + 1], colours[nearest + 2], colours[nearest + 3]],
    }
  }, [pasted, colours])

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
        extra,
        axes: marks.lines,
        accent: palette.accent,
        muted: palette.muted,
        highlight: palette.highlight,
      }),
    })
  }, [deck, data, positions, colours, kept, gap, shape, segments, rings, extra, marks, palette, size])

  useEffect(() => {
    deck.current?.setProps({ controller: lasso ? false : CONTROLLER })
  }, [deck, lasso, size])

  // The card and the words mount after a render that draws no new frame: place them now.
  useLayoutEffect(() => place(), [place, selected, marks, shape, pasted])

  return { failed, size, camera, pointer, onEdge, neighbours, freeWidth, pixelMatrix, place }
}
