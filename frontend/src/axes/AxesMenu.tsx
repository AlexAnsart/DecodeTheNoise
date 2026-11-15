import { Axis3d, X } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { ProbeInfo } from '../api/schema'
import type { Shape } from '../map/geometry'
import { Popover } from '../popover/Popover'
import { shownProbes } from '../probes/levels'
import { ProbeList } from '../probes/ProbeList'
import { ConceptForm } from './ConceptForm'
import type { Relief } from './relief'
import './axes.css'

interface AxesMenuProps {
  shape: Shape
  relief: Relief | null
  /** The probes of the map: each can be read as a height. */
  probes: ProbeInfo[]
  hasDates: boolean
  /** A score is being computed. */
  busy: boolean
  error: string | null
  onShape(shape: '3d' | 'time'): void
  onProbe(probe: ProbeInfo): void
  onConcept(text: string): void
  onClearRelief(): void
}

/** One more axis on the map: the date, or a height read from a probe or from a concept you type. */
export function AxesMenu(props: AxesMenuProps): ReactElement {
  const { shape, relief, probes, hasDates, busy, error, onShape, onProbe, onConcept, onClearRelief } = props
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const raisedBy = relief?.source.kind === 'probe' ? relief.source.key : null

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={`nm-tool nm-tool--icon${relief ? ' nm-tool--marked' : ''}`}
        title="Axes: add the date or a height to the map"
        aria-label="Axes"
        aria-haspopup="dialog"
        aria-expanded={open}
        data-tour="axes"
        onClick={() => setOpen((value) => !value)}
      >
        <Axis3d size={17} aria-hidden />
      </button>
      <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} width={340} label="Axes">
        <h3>Axes</h3>
        <p>The meaning map stays whole. One more axis is added to it.</p>
        <div className="nm-segmented nm-segmented--wide" role="group" aria-label="Added axis">
          <button type="button" className={shape === '3d' ? 'is-active' : ''} onClick={() => onShape('3d')}>
            Meaning only (3D)
          </button>
          <button
            type="button"
            className={shape === 'time' ? 'is-active' : ''}
            disabled={!hasDates}
            title={hasDates ? 'The date runs along an axis in front of the map' : 'No item of this map is dated.'}
            onClick={() => onShape('time')}
          >
            Date
          </button>
        </div>
        <section className="nm-axes__section">
          <h4>Raise by a probe</h4>
          {shownProbes(probes).length > 0 ? (
            <p>Each item rises by its score for the probe. The axis marks the levels the probe was measured at, at the same height for every probe.</p>
          ) : null}
          <ProbeList probes={probes} current={raisedBy} disabled={busy} onPick={onProbe} />
        </section>
        <section className="nm-axes__section">
          <h4>Raise by a concept</h4>
          <p>Type a few words. Each item rises by how much its meaning resembles them, whatever words it uses.</p>
          <ConceptForm busy={busy} onConcept={onConcept} />
        </section>
        {busy ? <p className="nm-axes__note">Computing the scores…</p> : null}
        {error ? <p className="nm-axes__note nm-axes__note--error">{error}</p> : null}
        {relief ? (
          <div className="nm-axes__current">
            <span title={relief.label}>Height: {relief.label}</span>
            <button type="button" className="nm-drawer__icon" onClick={onClearRelief} title="Remove the height" aria-label="Remove the height">
              <X size={13} aria-hidden />
            </button>
          </div>
        ) : null}
        {relief?.note ? <p className="nm-axes__note">{relief.note}</p> : null}
        <p className="nm-axes__foot">The layout is a display, not a measure: it keeps only part of the true neighbours.</p>
      </Popover>
    </>
  )
}
