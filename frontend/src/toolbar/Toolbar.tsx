import { Blend, Box, Lasso, Square } from 'lucide-react'
import type { ReactElement, ReactNode } from 'react'
import type { Shape } from '../map/geometry'
import { formatCount } from '../text/format'
import './toolbar.css'

interface ToolbarProps {
  shown: number
  total: number
  shape: Shape
  lasso: boolean
  composing: boolean
  composed: boolean
  onFlat(flat: boolean): void
  onLasso(on: boolean): void
  onCompose(open: boolean): void
  /** The menus, in the order they are drawn: colour, axes, then display. */
  colourMenu: ReactNode
  axesMenu: ReactNode
  displayMenu: ReactNode
}

/** The tools of the map, at the right end of the bar. */
export function Toolbar(props: ToolbarProps): ReactElement {
  const { shown, total, shape, lasso, composing, composed } = props
  const flat = shape === '2d'
  return (
    <div className="nm-tools">
      <span className="nm-tools__count nm-num" title={`${formatCount(shown)} shown out of ${formatCount(total)}`}>
        {formatCount(shown)} points
      </span>
      {props.colourMenu}
      {props.axesMenu}
      <button
        type="button"
        className={`nm-tool nm-tool--icon${composed ? ' is-active' : ''}`}
        title="Composed colours: one colour per group you define"
        aria-label="Composed colours"
        aria-pressed={composing}
        onClick={() => props.onCompose(!composing)}
      >
        <Blend size={15} aria-hidden />
      </button>
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
      {props.displayMenu}
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
