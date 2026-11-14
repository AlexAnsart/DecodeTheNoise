import { MousePointerClick, Move, Rotate3d, ZoomIn } from 'lucide-react'
import type { ReactElement } from 'react'

interface ControlsHintProps {
  /** The map is in depth: dragging turns it. Flat: dragging moves it. */
  deep: boolean
}

/** How to move around the map, always in view at the bottom right. */
export function ControlsHint({ deep }: ControlsHintProps): ReactElement {
  return (
    <ul className="nm-controls" aria-label="How to move around the map">
      {deep ? (
        <>
          <li>
            <Rotate3d size={13} aria-hidden />
            <strong>Drag</strong> to turn
          </li>
          <li>
            <Move size={13} aria-hidden />
            <strong>Right-drag</strong> to move
          </li>
        </>
      ) : (
        <li>
          <Move size={13} aria-hidden />
          <strong>Drag</strong> to move
        </li>
      )}
      <li>
        <ZoomIn size={13} aria-hidden />
        <strong>Scroll</strong> to zoom
      </li>
      <li>
        <MousePointerClick size={13} aria-hidden />
        <strong>Click</strong> a point to open it, elsewhere to close
      </li>
    </ul>
  )
}
