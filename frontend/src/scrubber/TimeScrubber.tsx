import { Pause, Play } from 'lucide-react'
import { useRef } from 'react'
import type { KeyboardEvent, PointerEvent, ReactElement } from 'react'
import type { TimeRange } from '../map/geometry'
import { formatDay } from '../text/format'
import { MIN_DRAWN_SHARE, monthTicks, moveWindow, resizeWindow } from './scrubWindow'
import './scrubber.css'

interface TimeScrubberProps {
  range: TimeRange
  window: TimeRange
  playing: boolean
  onWindow(window: TimeRange): void
  onPlaying(playing: boolean): void
}

type Grip = 'body' | 'from' | 'to'

/** A window over the dates of the map: the points inside stay lit, the others fade. */
export function TimeScrubber({ range, window, playing, onWindow, onPlaying }: TimeScrubberProps): ReactElement {
  const track = useRef<HTMLDivElement>(null)
  const drag = useRef<{ grip: Grip; x: number; start: TimeRange } | null>(null)
  const span = range.to - range.from
  const left = (window.from - range.from) / span
  const width = Math.max(MIN_DRAWN_SHARE, (window.to - window.from) / span)

  const begin = (grip: Grip) => (event: PointerEvent<HTMLElement>) => {
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    drag.current = { grip, x: event.clientX, start: window }
    onPlaying(false)
  }
  const move = (event: PointerEvent<HTMLElement>): void => {
    const state = drag.current
    const box = track.current?.getBoundingClientRect()
    if (!state || !box) return
    const delta = ((event.clientX - state.x) / box.width) * span
    onWindow(state.grip === 'body' ? moveWindow(state.start, range, delta) : resizeWindow(state.start, range, state.grip, delta))
  }
  const end = (): void => {
    drag.current = null
  }
  const onKey = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const step = (window.to - window.from) * (event.key === 'ArrowLeft' ? -1 : 1)
    onWindow(moveWindow(window, range, step))
  }

  return (
    <div className="nm-scrub" role="group" aria-label="Time window">
      <button
        type="button"
        className="nm-tool nm-tool--icon"
        onClick={() => onPlaying(!playing)}
        title={playing ? 'Pause' : 'Play the window through time'}
        aria-label={playing ? 'Pause' : 'Play'}
      >
        {playing ? <Pause size={14} aria-hidden /> : <Play size={14} aria-hidden />}
      </button>
      <div ref={track} className="nm-scrub__track" tabIndex={0} onKeyDown={onKey} aria-label="Move the window with the arrow keys">
        {monthTicks(range).map((share) => (
          <span key={share} className="nm-scrub__tick" style={{ left: `${share * 100}%` }} />
        ))}
        <div
          className="nm-scrub__window"
          style={{ left: `${Math.min(left, 1 - width) * 100}%`, width: `${width * 100}%` }}
          onPointerDown={begin('body')}
          onPointerMove={move}
          onPointerUp={end}
          onPointerCancel={end}
        >
          <span className="nm-scrub__handle nm-scrub__handle--from" onPointerDown={begin('from')} onPointerMove={move} onPointerUp={end} onPointerCancel={end} />
          <span className="nm-scrub__handle nm-scrub__handle--to" onPointerDown={begin('to')} onPointerMove={move} onPointerUp={end} onPointerCancel={end} />
        </div>
      </div>
      <span className="nm-scrub__dates nm-num">
        {formatDay(window.from)} – {formatDay(window.to)}
      </span>
    </div>
  )
}
