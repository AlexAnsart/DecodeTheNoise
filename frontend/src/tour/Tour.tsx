import { X } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactElement } from 'react'
import { createPortal } from 'react-dom'
import type { Box } from './useTourStep'
import { useTourStep } from './useTourStep'
import './tour.css'

const GAP = 10
const EDGE = 10
/** Past this share of the window, a target is a region (the map), not a control. */
const REGION_SHARE = 0.5
const RING_MARGIN = 4

function isRegion(box: Box): boolean {
  return box.width > window.innerWidth * REGION_SHARE && box.height > window.innerHeight * REGION_SHARE
}

/** Under a control (above when the room is short); at the top of a region, so its content shows. */
function place(box: Box, card: DOMRect): CSSProperties {
  const centred = box.left + box.width / 2 - card.width / 2
  const left = Math.min(Math.max(EDGE, centred), window.innerWidth - card.width - EDGE)
  if (isRegion(box)) return { left, top: box.top + 2 * GAP }
  const below = box.top + box.height + GAP
  const fits = below + card.height <= window.innerHeight - EDGE
  return { left, top: fits ? below : Math.max(EDGE, box.top - GAP - card.height) }
}

function ring(box: Box): CSSProperties {
  // A region is ringed just inside its edge, a control just outside.
  const margin = isRegion(box) ? -RING_MARGIN : RING_MARGIN
  return { left: box.left - margin, top: box.top - margin, width: box.width + 2 * margin, height: box.height + 2 * margin }
}

/** The guided tour: one small card at a time, beside the control it explains. */
export function Tour({ onEnd }: { onEnd(): void }): ReactElement | null {
  const { index, step, box, present, next, back } = useTourStep(onEnd)
  const card = useRef<HTMLDivElement>(null)
  const forward = useRef<HTMLButtonElement>(null)
  const [style, setStyle] = useState<CSSProperties>({ visibility: 'hidden' })

  useLayoutEffect(() => {
    const size = card.current?.getBoundingClientRect()
    if (box && size) setStyle({ ...place(box, size), visibility: 'visible' })
  }, [box, index])

  // The card is on the page once its target is measured: "Next" then takes the focus.
  const shown = box !== null
  useEffect(() => {
    if (index === null || !shown) return undefined
    forward.current?.focus({ preventScroll: true })
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') onEnd()
      else if (event.key === 'ArrowRight') next()
      else if (event.key === 'ArrowLeft') back()
      else return
      event.stopPropagation()
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [index, shown, next, back, onEnd])

  if (index === null || !step || !box) return null
  const at = present.indexOf(index)
  const last = at === present.length - 1
  return createPortal(
    <>
      {/* A new ring for each step: its three beats play again where the eye should go. */}
      <div key={index} className="nm-tour__ring" style={ring(box)} aria-hidden />
      <div ref={card} className="nm-tour" role="dialog" aria-label={`Tour, step ${at + 1} of ${present.length}: ${step.title}`} style={style}>
        <header className="nm-tour__head">
          <h2>{step.title}</h2>
          <button type="button" className="nm-icon-btn" onClick={onEnd} title="Skip the tour" aria-label="Skip the tour">
            <X size={14} aria-hidden />
          </button>
        </header>
        <p>{step.text}</p>
        <footer className="nm-tour__foot">
          <span className="nm-tour__dots" aria-hidden>
            {present.map((other) => (
              <i key={other} className={other === index ? 'is-current' : ''} />
            ))}
          </span>
          <button type="button" className="nm-tour__skip" onClick={onEnd}>
            Skip
          </button>
          {at > 0 ? (
            <button type="button" className="nm-btn-secondary nm-btn-small" onClick={back}>
              Back
            </button>
          ) : null}
          <button ref={forward} type="button" className="nm-btn-primary nm-btn-small" onClick={last ? onEnd : next}>
            {last ? 'Done' : 'Next'}
          </button>
        </footer>
      </div>
    </>,
    document.body,
  )
}
