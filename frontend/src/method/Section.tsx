import type { ReactElement, ReactNode } from 'react'
import type { SectionId } from './hash'
import { SECTIONS } from './sections'

interface SectionProps {
  id: SectionId
  /** What the section says, in one or two sentences: enough for a reader who opens nothing. */
  summary: ReactNode
  children: ReactNode
}

/** A section of the method page: its title, its summary, then what can be opened. */
export function Section({ id, summary, children }: SectionProps): ReactElement {
  const title = SECTIONS.find((section) => section.id === id)?.title ?? id
  return (
    <section id={id} className="nm-method__section" aria-labelledby={`${id}-title`}>
      <header className="nm-method__section-head">
        <h2 id={`${id}-title`}>{title}</h2>
        <p className="nm-method__summary">{summary}</p>
      </header>
      {children}
    </section>
  )
}
