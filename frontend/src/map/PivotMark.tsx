import type { ReactElement, RefObject } from 'react'

/** The point the map turns around, in depth: a target inside an orbit ring, moved after each
 *  frame to where the camera aims. Translucent at rest, plain and named while the map turns. */
export function PivotMark({ mark }: { mark: RefObject<HTMLDivElement | null> }): ReactElement {
  return (
    <div ref={mark} className="nm-pivot" aria-hidden>
      <svg viewBox="0 0 72 72" width="72" height="72">
        <circle className="nm-pivot__glow" cx="36" cy="36" r="30" />
        <ellipse className="nm-pivot__orbit" cx="36" cy="36" rx="31" ry="11" />
        <path className="nm-pivot__arrow" d="M64.5 29.5 L68.6 36.6 L60.6 36.9 Z" />
        <path className="nm-pivot__arrow" d="M7.5 42.5 L3.4 35.4 L11.4 35.1 Z" />
        <circle className="nm-pivot__ring" cx="36" cy="36" r="12" />
        <path className="nm-pivot__cross" d="M36 19 V27 M36 45 V53 M19 36 H27 M45 36 H53" />
        <circle className="nm-pivot__dot" cx="36" cy="36" r="3.6" />
      </svg>
      <span>Centre of rotation</span>
    </div>
  )
}
