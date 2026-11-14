import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent, ReactElement } from 'react'
import type { ProbeInfo } from '../api/schema'
import { NO_MARKS, reliefMarks, timeMarks } from '../axes/axisMarks'
import type { AxisWordsHandle } from '../axes/AxisWords'
import { AxisWords } from '../axes/AxisWords'
import type { Relief } from '../axes/relief'
import { readPalette } from '../colour/palette'
import { ComposePanel } from '../compose/ComposePanel'
import { useDrafts } from '../compose/useDrafts'
import { hasFilters } from '../filters/mask'
import { LassoOverlay } from '../lasso/LassoOverlay'
import { Legend } from '../legend/Legend'
import { PastedLabel } from '../paste/PastedLabel'
import { PastePanel } from '../paste/PastePanel'
import { usePasteFlow, usePasteLocate } from '../paste/usePasteFlow'
import { HoverTip } from '../picking/HoverTip'
import { ItemCard } from '../picking/ItemCard'
import { TimeScrubber } from '../scrubber/TimeScrubber'
import { SelectionPill } from '../selection/SelectionPill'
import { useTheme } from '../theme/theme'
import { ControlsHint } from './ControlsHint'
import { boundsOf, flatSpan } from './geometry'
import { MapBar } from './MapBar'
import type { MapData } from './mapData'
import { MapDrawers } from './MapDrawers'
import { useMapActions } from './useMapActions'
import { useMapModel } from './useMapModel'
import { useMapStage } from './useMapStage'
import './map.css'

interface MapViewProps {
  /** The map on screen. On a live map a newer one replaces it in place: points keep their index. */
  data: MapData
  /** Why the map on screen could not be read again, when it could not. */
  stale: string | null
}

/** The probe a relief reads, when it reads one. */
function reliefProbe(data: MapData, relief: Relief): ProbeInfo | null {
  const { source } = relief
  return source.kind === 'probe' ? (data.probes.find((probe) => probe.key === source.key) ?? null) : null
}

/** The meaning map: a bar of filters and tools, then one canvas with everything else floating. */
export function MapView({ data, stale }: MapViewProps): ReactElement {
  const [theme] = useTheme()
  // The canvas cannot read CSS variables: its colours are read again when the theme changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const palette = useMemo(() => readPalette(), [theme])
  const model = useMapModel(data, palette)
  const { colouring, scrubber, shape, relief, selected, picked, range, kept, filters } = model

  const refs = {
    stage: useRef<HTMLDivElement>(null),
    host: useRef<HTMLDivElement>(null),
    card: useRef<HTMLDivElement>(null),
    pivot: useRef<HTMLDivElement>(null),
    drawers: useRef<HTMLDivElement>(null),
    words: useRef<AxisWordsHandle>(null),
    pastedLabel: useRef<HTMLDivElement>(null),
  }
  const [lasso, setLasso] = useState(false)
  const [edges, setEdges] = useState(true)
  const [ringed, setRinged] = useState<number | null>(null)
  const [listOpen, setListOpen] = useState(false)
  const [composing, setComposing] = useState(false)
  const [drafts, setDrafts] = useDrafts(data)
  const [neighboursClosedFor, setNeighboursClosedFor] = useState<number | null>(null)
  const flow = usePasteFlow(model, lasso)
  const { analysis, pasted, pasting } = flow

  const marks = useMemo(() => {
    if (shape === 'time' && range) return timeMarks(range, flatSpan(data), boundsOf(model.positions))
    if (shape === 'relief' && relief) return reliefMarks(relief.label, relief.ticks, flatSpan(data), boundsOf(model.positions))
    return NO_MARKS
  }, [shape, range, relief, data, model.positions])

  const stage = useMapStage({ data, model, palette, refs, lasso, edges, ringed, marks, pasted, onCanvasClick: () => flow.setOpen(false) })
  const coveredRight = useCallback(() => refs.drawers.current?.offsetWidth ?? 0, [refs.drawers])
  const actions = useMapActions(data, model, stage, coveredRight)
  usePasteLocate(flow, model, stage, coveredRight)

  const showNeighbours = selected !== null && stage.neighbours.length > 0 && !lasso && neighboursClosedFor !== selected
  const showList = picked !== null && listOpen
  const showPastedNeighbours = flow.neighbours !== null

  useEffect(() => {
    // The floating panels keep clear of the drawers, and the card is placed in the free part.
    refs.stage.current?.style.setProperty('--nm-covered-right', `${coveredRight()}px`)
    stage.place()
  }, [showNeighbours, showList, showPastedNeighbours, coveredRight, refs.stage, stage])

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      if (lasso) setLasso(false)
      else if (selected !== null) model.setSelected(null)
      else flow.setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lasso, selected, model, flow])

  const onStageKey = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key.toLowerCase() !== 'l' || event.ctrlKey || event.metaKey || event.altKey || event.repeat) return
    // Typing an "l" in a field of a floating panel is not the shortcut.
    const target = event.target
    if (target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return
    setLasso((value) => !value)
  }

  const tipEntry = stage.pointer.tipIndex === null ? null : colouring.legend.entries[colouring.legend.entryOf[stage.pointer.tipIndex]]
  const tipScore =
    shape === 'relief' && relief && stage.pointer.tipIndex !== null
      ? { label: relief.label, value: relief.heights[stage.pointer.tipIndex], probe: reliefProbe(data, relief) }
      : null
  const deep = shape !== '2d'
  const status = actions.busy ? 'Computing the scores…' : stale

  return (
    <div className="nm-map">
      <MapBar
        data={data}
        model={model}
        actions={actions}
        lasso={lasso}
        edges={edges}
        composing={composing}
        pasting={pasting}
        onLasso={setLasso}
        onEdges={setEdges}
        onComposing={(open) => {
          setComposing(open)
          if (open) flow.setPasting(false)
        }}
        onPasting={(open) => {
          flow.setPasting(open)
          setComposing(false)
        }}
      />
      <div ref={refs.stage} className={`nm-stage${lasso ? ' is-lasso' : ''}`} tabIndex={0} onKeyDown={onStageKey} aria-label="Meaning map" data-tour="map">
        <div ref={refs.host} className="nm-stage__canvas" />
        {stage.failed ? <p className="nm-stage__message">The map needs WebGL, and this browser could not start it.</p> : null}
        {!stage.failed && kept.shown === 0 ? <p className="nm-stage__message nm-stage__message--over">No point matches the filter.</p> : null}
        {status ? (
          <p className="nm-stage__status" role="status">
            {status}
          </p>
        ) : null}
        {marks.words.length > 0 ? <AxisWords ref={refs.words} words={marks.words} /> : null}
        {pasted && analysis ? (
          <PastedLabel
            analysis={analysis}
            label={refs.pastedLabel}
            open={pasted.highlighted}
            onToggle={() => {
              model.setSelected(null)
              flow.setOpen(!pasted.highlighted)
            }}
          />
        ) : null}
        {deep ? <div ref={refs.pivot} className="nm-pivot" aria-hidden /> : null}
        {lasso ? (
          <LassoOverlay
            deep={deep}
            onStroke={(stroke, mode) => {
              setListOpen(actions.lasso(stroke, mode))
              setLasso(false)
            }}
          />
        ) : null}
        {picked && !showList ? <SelectionPill count={picked.length} onOpen={() => setListOpen(true)} onClear={() => model.setPicked(null)} /> : null}
        <Legend
          legend={colouring.legend}
          counts={kept.perEntry}
          hidden={colouring.hidden}
          raised={scrubber.on}
          onToggle={colouring.toggle}
          onSolo={colouring.solo}
          onHideAll={colouring.hideAll}
          onPeek={colouring.setPeek}
        />
        {scrubber.on && range && scrubber.window ? (
          <TimeScrubber range={range} window={scrubber.window} playing={scrubber.playing} onWindow={scrubber.setWindow} onPlaying={scrubber.setPlaying} />
        ) : null}
        <HoverTip
          data={data}
          index={stage.pointer.tipIndex}
          tip={stage.pointer.tip}
          entry={tipEntry ? { title: colouring.legend.title, entry: tipEntry } : null}
          score={tipScore}
          neighbourOfSelected={stage.onEdge}
          onSettle={stage.pointer.settle}
        />
        {selected !== null ? (
          <div className="nm-card-layer">
            <ItemCard
              data={data}
              index={selected}
              card={refs.card}
              neighbours={stage.neighbours.length}
              canOpenNeighbours={neighboursClosedFor === selected}
              onOpenNeighbours={() => setNeighboursClosedFor(null)}
              onClose={() => model.setSelected(null)}
            />
          </div>
        ) : null}
        {composing ? (
          <ComposePanel
            sources={{ data, selection: picked, filtered: hasFilters(filters) ? Uint8Array.from(kept.values) : null }}
            active={colouring.composed !== null}
            drafts={drafts}
            onDrafts={setDrafts}
            onApply={colouring.compose}
            onLeave={() => colouring.compose(null)}
            onClose={() => setComposing(false)}
          />
        ) : null}
        {pasting ? (
          <PastePanel
            paste={flow.paste}
            unplaced={analysis && !pasted ? 'The date view has no place for a text without a date: switch to 2D or 3D to see it.' : null}
            onLocate={() => {
              model.setSelected(null)
              flow.setOpen(true)
              flow.locate()
            }}
            onClose={() => flow.setPasting(false)}
          />
        ) : null}
        <MapDrawers
          data={data}
          drawers={refs.drawers}
          model={model}
          actions={actions}
          neighbours={showNeighbours ? stage.neighbours : null}
          pastedNeighbours={flow.neighbours}
          listed={showList ? picked : null}
          onShow={(index) => stage.camera.centreOn(index, coveredRight())}
          onRing={setRinged}
          onCloseNeighbours={() => setNeighboursClosedFor(selected)}
          onClosePasted={() => flow.setOpen(false)}
          onCloseList={() => setListOpen(false)}
        />
        {lasso ? null : <ControlsHint deep={deep} />}
      </div>
    </div>
  )
}
