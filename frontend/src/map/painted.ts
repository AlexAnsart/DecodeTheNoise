/* A pause that lets the page paint what it holds before a long, blocking piece of work. */

const PAINT_WAIT_MS = 250

/** Resolves once the page has painted a frame that holds what was just rendered, or shortly
 *  after when it is not on screen (a tab in the background paints nothing). Two frames are
 *  waited for: the first may be drawn before the pending render is committed. */
export function painted(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 0)))
    setTimeout(resolve, PAINT_WAIT_MS)
  })
}
