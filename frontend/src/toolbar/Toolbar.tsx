import { Box, Clock, Lasso, Square } from 'lucide-react'
import type { ReactElement, ReactNode } from 'react'
import type { Shape } from '../map/geometry'
import { formatCount } from '../text/format'
import './toolbar.css'

interface ToolbarProps {
  shown: number
  total: number
  shape: Shape
  lasso: boolean
  /** The window over the dates is on. */
  timeWindow: boolean
  /** Why the map has no time window, when it has none. */
  noDates: string | null
  onFlat(flat: boolean): void
  onLasso(on: boolean): void
  onTimeWindow(on: boolean): void
  /** The menus, in the order they are drawn: colour, then axes. */
  colourMenu: ReactNode
  axesMenu: ReactNode
}

/** The tools of the map, at the right end of the bar. */
export function Toolbar(props: ToolbarProps): ReactElement {
  const { shown, total, shape, lasso, timeWindow, noDates } = props
  const flat = shape === '2d'
  return (
    <div className="nm-tools">
      <span className="nm-tools__count nm-num" title={`${formatCount(shown)} shown out of ${formatCount(total)}`}>
        {formatCount(shown)} points
      </span>
      {props.colourMenu}
      {props.axesMenu}
      <div className="nm-segmented" role="group" aria-label="Flat or in depth">
        <button type="button" className={flat ? 'is-active' : ''} aria-pressed={flat} onClick={() => props.onFlat(true)} title="Flat map">
          <Square size={14} aria-hidden />
          2D
        </button>
        <button type="button" className={flat ? '' : 'is-active'} aria-pressed={!flat} onClick={() => props.onFlat(false)} title="Map in depth">
          <Box size={14} aria-hidden />
          3D
        </button>
      </div>
      <button
        type="button"
        className={`nm-tool nm-tool--icon${timeWindow ? ' is-active' : ''}`}
        title={noDates ?? 'Time window: the items dated inside stay lit'}
        aria-label="Time window"
        aria-pressed={timeWindow}
        disabled={noDates !== null}
        onClick={() => props.onTimeWindow(!timeWindow)}
      >
        <Clock size={15} aria-hidden />
      </button>
      <button
        type="button"
        className={`nm-tool nm-tool--icon${lasso ? ' is-active' : ''}`}
        title="Lasso: draw around points to select them (L)"
        aria-label="Lasso"
        data-tour="lasso"
        aria-pressed={lasso}
        onClick={() => props.onLasso(!lasso)}
      >
        <Lasso size={16} aria-hidden />
      </button>
    </div>
  )
}
