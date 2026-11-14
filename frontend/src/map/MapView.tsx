import { ClipboardPaste } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent, ReactElement } from 'react'
import { AxesMenu } from '../axes/AxesMenu'
import { NO_MARKS, reliefMarks, timeMarks } from '../axes/axisMarks'
import type { AxisWordsHandle } from '../axes/AxisWords'
import { AxisWords } from '../axes/AxisWords'
import { ColourMenu } from '../colour/ColourMenu'
import { maskOfIndices } from '../colour/emphasis'
import { readPalette } from '../colour/palette'
import { ComposePanel } from '../compose/ComposePanel'
import type { Draft } from '../compose/groups'
import { FilterBar } from '../filters/FilterBar'
import { hasFilters } from '../filters/mask'
import { LassoOverlay } from '../lasso/LassoOverlay'
import { Legend } from '../legend/Legend'
import { NeighbourDrawer } from '../neighbours/NeighbourDrawer'
import { PastedLabel } from '../paste/PastedLabel'
import { PastePanel } from '../paste/PastePanel'
import { ReliabilityDialog } from '../reliability/ReliabilityDialog'
import { usePaste } from '../paste/usePaste'
import { usePastedPoint } from '../paste/usePastedPoint'
import { HoverTip } from '../picking/HoverTip'
import { ItemCard } from '../picking/ItemCard'
import { TimeScrubber } from '../scrubber/TimeScrubber'
import { SelectionDrawer } from '../selection/SelectionDrawer'
import { SelectionPill } from '../selection/SelectionPill'
import { SwarmDrawer } from '../swarms/SwarmDrawer'
import { swarmMask } from '../swarms/swarmPoints'
import { SwarmVerdict } from '../swarms/SwarmVerdict'
import { useSwarmLayer } from '../swarms/useSwarmLayer'
import { plural } from '../text/format'
import { useTheme } from '../theme/theme'
import { DisplayMenu } from '../toolbar/DisplayMenu'
import { Toolbar } from '../toolbar/Toolbar'
import { ControlsHint } from './ControlsHint'
import { boundsOf, flatSpan, pointAt } from './geometry'
import type { MapData } from './mapData'
import { useMapActions } from './useMapActions'
import { useMapModel } from './useMapModel'
import { useMapStage } from './useMapStage'
import './map.css'

/** Width the paste panel covers on the right of the stage, margins included. */
const PASTE_PANEL_WIDTH = 396

/** The meaning map: a bar of filters and tools, then one canvas with everything else floating. */
export function MapView({ data }: { data: MapData }): ReactElement {
  const [theme, toggleTheme] = useTheme()
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
  const [drafts, setDrafts] = useState<Draft[] | null>(null)
  const [neighboursClosedFor, setNeighboursClosedFor] = useState<number | null>(null)
  const [pasting, setPasting] = useState(false)
  const swarmLayer = useSwarmLayer()
  const [openSwarm, setOpenSwarm] = useState<number | null>(null)
  const [reliability, setReliability] = useState(false)
  const [locateAsked, setLocateAsked] = useState(0)
  const paste = usePaste()
  const pastedPoint = usePastedPoint(paste.state, shape, selected)
  const { analysis, point: pasted } = pastedPoint
  // The list beside the pasted text while it is open: its nearest items the filters still show.
  const pastedNeighbours = useMemo(
    () => (pasted?.highlighted && !lasso ? pasted.neighbours.filter((other) => kept.values[other] >= 0.5) : null),
    [pasted, lasso, kept],
  )

  const marks = useMemo(() => {
    if (shape === 'time' && range) return timeMarks(range, flatSpan(data), boundsOf(model.positions))
    if (shape === 'relief' && relief) return reliefMarks(relief.label, flatSpan(data), boundsOf(model.positions))
    return NO_MARKS
  }, [shape, range, relief, data, model.positions])

  const stage = useMapStage({ data, model, palette, refs, lasso, edges, ringed, marks, pasted, onCanvasClick: () => pastedPoint.setOpen(false) })
  const coveredRight = useCallback(() => refs.drawers.current?.offsetWidth ?? 0, [refs.drawers])
  const actions = useMapActions(model, stage, coveredRight)

  const showNeighbours = selected !== null && stage.neighbours.length > 0 && !lasso && neighboursClosedFor !== selected
  const showList = picked !== null && listOpen
  const showPastedNeighbours = pastedNeighbours !== null

  useEffect(() => {
    // The floating panels keep clear of the drawers, and the card is placed in the free part.
    refs.stage.current?.style.setProperty('--nm-covered-right', `${coveredRight()}px`)
    stage.place()
  }, [showNeighbours, showList, showPastedNeighbours, openSwarm, coveredRight, refs.stage, stage])

  const { centreAt } = stage.camera
  const { positions } = model
  // Brings the camera onto the pasted text, close enough to read the items it is tied to.
  const locatePasted = useCallback(() => {
    if (!pasted) return
    // The typical distance to its nearest items: one far neighbour must not keep the camera away.
    const distances = pasted.neighbours
      .map((other) => {
        const at = pointAt(positions, other)
        return Math.hypot(at[0] - pasted.position[0], at[1] - pasted.position[1], at[2] - pasted.position[2])
      })
      .sort((a, b) => a - b)
    const reach = distances[Math.floor(distances.length / 2)] ?? 0
    centreAt(pasted.position, coveredRight() + (pasting ? PASTE_PANEL_WIDTH : 0), reach)
  }, [pasted, positions, centreAt, coveredRight, pasting])
  useEffect(() => {
    // A text that has just been placed opens like a clicked point: the panel gives way to the
    // list of its neighbours, and the camera is asked to go to it.
    if (!analysis) return
    model.setSelected(null)
    setPasting(false)
    setLocateAsked((count) => count + 1)
    // Only a new placement does this, not a change of what surrounds it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis])
  useEffect(() => {
    // After the render that opened the list: the camera knows the width the list covers.
    if (locateAsked > 0) locatePasted()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locateAsked])

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      if (lasso) setLasso(false)
      else if (selected !== null) model.setSelected(null)
      else pastedPoint.setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lasso, selected, model, pastedPoint])

  const onStageKey = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key.toLowerCase() !== 'l' || event.ctrlKey || event.metaKey || event.altKey || event.repeat) return
    // Typing an "l" in a field of a floating panel is not the shortcut.
    const target = event.target
    if (target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return
    setLasso((value) => !value)
  }

  // Colours the posts of a swarm against the rest, when the map draws some of them.
  const swarmColouring = (id: number): (() => void) | null => {
    const name = swarmLayer?.swarms.find((swarm) => swarm.id === id)?.name
    const mask = name ? swarmMask(data, name) : null
    return name && mask ? () => colouring.compose([{ label: name, mask }]) : null
  }

  const tipEntry = stage.pointer.tipIndex === null ? null : colouring.legend.entries[colouring.legend.entryOf[stage.pointer.tipIndex]]
  const tipScore =
    shape === 'relief' && relief && stage.pointer.tipIndex !== null
      ? { label: relief.label, value: relief.heights[stage.pointer.tipIndex] }
      : null
  const deep = shape !== '2d'

  return (
    <div className="nm-map">
      <FilterBar
        data={data}
        range={range}
        filters={filters}
        onFilters={model.setFilters}
        onPick={actions.goTo}
        onLift={actions.liftConcept}
        beside={
          <button
            type="button"
            className={`nm-tool${pasting ? ' is-active' : ''}`}
            aria-pressed={pasting}
            title="Place a text or the page behind a link on the map"
            onClick={() => {
              setPasting((value) => !value)
              setComposing(false)
            }}
          >
            <ClipboardPaste size={13} aria-hidden />
            Paste a text or a link
          </button>
        }
        tools={
          <Toolbar
            shown={kept.shown}
            total={data.n}
            shape={shape}
            lasso={lasso}
            composing={composing}
            composed={colouring.composed !== null}
            onFlat={(flat) => model.setShape(flat ? '2d' : '3d')}
            onLasso={setLasso}
            onCompose={(open) => {
              setComposing(open)
              if (open) setPasting(false)
            }}
            onReliability={() => setReliability(true)}
            colourMenu={<ColourMenu data={data} choice={colouring.choice} composed={colouring.composed !== null} hasDates={range !== null} onChoose={colouring.choose} />}
            axesMenu={
              <AxesMenu
                shape={shape}
                relief={relief}
                hasDates={range !== null}
                busy={actions.busy}
                error={actions.error}
                onShape={model.setShape}
                onConcept={actions.liftConcept}
                onClearRelief={() => model.setRelief(null)}
              />
            }
            displayMenu={
              <DisplayMenu
                options={[
                  { id: 'scrubber', label: 'Time window', hint: 'A window over the dates: the items inside stay lit', on: scrubber.on, disabled: range ? null : 'No item of this map is dated.', set: scrubber.setOn },
                  { id: 'edges', label: 'Lines to neighbours', hint: 'Lines from the selected item to its nearest by meaning', on: edges, disabled: null, set: setEdges },
                  { id: 'dark', label: 'Dark theme', hint: 'Light or dark', on: theme === 'dark', disabled: null, set: toggleTheme },
                ]}
              />
            }
          />
        }
      />
      <div ref={refs.stage} className={`nm-stage${lasso ? ' is-lasso' : ''}`} tabIndex={0} onKeyDown={onStageKey} aria-label="Meaning map">
        <div ref={refs.host} className="nm-stage__canvas" />
        {stage.failed ? <p className="nm-stage__message">The map needs WebGL, and this browser could not start it.</p> : null}
        {!stage.failed && kept.shown === 0 ? <p className="nm-stage__message nm-stage__message--over">No point matches the filter.</p> : null}
        {actions.busy ? <p className="nm-stage__status">Computing the scores…</p> : null}
        {marks.words.length > 0 ? <AxisWords ref={refs.words} words={marks.words} /> : null}
        {pasted && analysis ? (
          <PastedLabel
            analysis={analysis}
            label={refs.pastedLabel}
            open={pasted.highlighted}
            onToggle={() => {
              model.setSelected(null)
              pastedPoint.setOpen(!pasted.highlighted)
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
              onOpenNeighbours={() => {
                setOpenSwarm(null)
                setNeighboursClosedFor(null)
              }}
              verdicts={(item) => {
                const verdict = swarmLayer?.actors[item.actor_id]
                return swarmLayer && verdict ? (
                  <SwarmVerdict layer={swarmLayer} verdict={verdict} onOpenSwarm={setOpenSwarm} onReliability={() => setReliability(true)} />
                ) : null
              }}
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
            paste={paste}
            unplaced={analysis && !pasted ? 'The date view has no place for a text without a date: switch to 2D or 3D to see it.' : null}
            noVerdict={
              swarmLayer
                ? 'No verdict on a pasted text: the coordination detector judges an account by its posting history, which a pasted text does not have. Not enough evidence.'
                : 'No detector is shown yet: a layer appears here only once its precision and false-positive rate are measured.'
            }
            onLocate={() => {
              model.setSelected(null)
              pastedPoint.setOpen(true)
              setLocateAsked((count) => count + 1)
            }}
            onClose={() => setPasting(false)}
          />
        ) : null}
        <div ref={refs.drawers} className="nm-drawers">
          {openSwarm !== null && swarmLayer ? (
            <SwarmDrawer
              data={data}
              layer={swarmLayer}
              id={openSwarm}
              onColour={swarmColouring(openSwarm)}
              onReliability={() => setReliability(true)}
              onClose={() => setOpenSwarm(null)}
            />
          ) : null}
          {openSwarm === null && showNeighbours && selected !== null ? (
            <NeighbourDrawer
              data={data}
              listKey={`neighbours:${selected}`}
              neighbours={stage.neighbours}
              onShow={(index) => stage.camera.centreOn(index, coveredRight())}
              onOpen={actions.goTo}
              onRing={setRinged}
              onClose={() => setNeighboursClosedFor(selected)}
            />
          ) : null}
          {openSwarm === null && pastedNeighbours ? (
            <NeighbourDrawer
              data={data}
              listKey={`neighbours:pasted:${pastedNeighbours.join('-')}`}
              neighbours={pastedNeighbours}
              onShow={(index) => stage.camera.centreOn(index, coveredRight())}
              onOpen={actions.goTo}
              onRing={setRinged}
              onClose={() => pastedPoint.setOpen(false)}
            />
          ) : null}
          {showList && picked ? (
            <SelectionDrawer
              data={data}
              indices={picked}
              actions={[
                { id: 'likeness', label: 'Raise what resembles this selection', disabled: actions.busy ? 'A score is being computed.' : null, run: actions.liftSelection },
                { id: 'colour', label: 'Colour this selection against the rest', disabled: null, run: () => colouring.compose([{ label: 'The selection', mask: maskOfIndices(data.n, picked) }]) },
                { id: 'clear', label: 'Clear the selection', disabled: null, run: () => model.setPicked(null) },
              ]}
              onKeepInFilters={() => {
                model.setFilters({ ...filters, kept: { label: plural(picked.length, 'selected item', 'selected items'), mask: maskOfIndices(data.n, picked) } })
                setListOpen(false)
              }}
              onShow={(index) => stage.camera.centreOn(index, coveredRight())}
              onOpen={actions.goTo}
              onRing={setRinged}
              onClose={() => setListOpen(false)}
            />
          ) : null}
        </div>
        {lasso ? null : <ControlsHint deep={deep} />}
      </div>
      {reliability ? <ReliabilityDialog onClose={() => setReliability(false)} /> : null}
    </div>
  )
}
