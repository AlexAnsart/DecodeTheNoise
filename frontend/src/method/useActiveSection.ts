/* Which section of the page the reader is in, for the table of contents. */

import { useEffect, useState } from 'react'
import type { RefObject } from 'react'
import type { SectionId } from './hash'
import { SECTION_IDS } from './hash'

/** A section counts as being read once its title has come this close to the top, in pixels. */
const READING_LINE = 140

/** The last section whose title has passed the reading line: sections follow one another, so
 *  that is the one on screen under the line. */
function sectionAt(root: HTMLElement): SectionId {
  const line = root.getBoundingClientRect().top + READING_LINE
  let current: SectionId = SECTION_IDS[0]
  for (const id of SECTION_IDS) {
    const section = document.getElementById(id)
    if (section && section.getBoundingClientRect().top <= line) current = id
  }
  return current
}

export function useActiveSection(scroller: RefObject<HTMLElement | null>): SectionId {
  const [active, setActive] = useState<SectionId>(SECTION_IDS[0])

  useEffect(() => {
    const root = scroller.current
    if (!root) return undefined
    let frame = 0
    // Measured once per frame at most, however many scroll events the frame holds.
    const measure = (): void => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => setActive(sectionAt(root)))
    }
    // Sections grow when what they hold arrives or opens: the one under the line can change
    // without a scroll.
    const resized = new ResizeObserver(measure)
    if (root.firstElementChild) resized.observe(root.firstElementChild)
    root.addEventListener('scroll', measure, { passive: true })
    measure()
    return () => {
      cancelAnimationFrame(frame)
      resized.disconnect()
      root.removeEventListener('scroll', measure)
    }
  }, [scroller])

  return active
}
