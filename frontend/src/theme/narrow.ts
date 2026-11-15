/* The sizes of a phone-sized window. The same numbers are written in theme/small-screens.css. */

const NARROW = '(max-width: 760px)'
const SHORT = '(max-height: 520px)'

/** Whether the window is as narrow as a phone held upright: panels are then sheets at the
 *  bottom of the map, and none of them opens by itself. */
export function isNarrow(): boolean {
  return window.matchMedia(NARROW).matches
}

/** Whether the map has little room, upright or sideways: what floats over it starts folded. */
export function isCramped(): boolean {
  return isNarrow() || window.matchMedia(SHORT).matches
}
