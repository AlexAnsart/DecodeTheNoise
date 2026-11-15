import type { ReactElement } from 'react'
import type { SectionId } from './hash'
import { useMethodShared } from './MethodContext'
import { SECTIONS } from './sections'

/** The table of contents: always in view, with the section being read marked. */
export function Toc({ active }: { active: SectionId }): ReactElement {
  const { nav } = useMethodShared()
  return (
    <nav className="nm-toc" aria-label="Sections of this page">
      <p className="nm-toc__title">On this page</p>
      <ol>
        {SECTIONS.map((section) => {
          const target = { kind: 'section', section: section.id } as const
          return (
            <li key={section.id}>
              <a
                href={nav.href(target)}
                className={active === section.id ? 'is-active' : ''}
                aria-current={active === section.id ? 'location' : undefined}
                onClick={(event) => {
                  event.preventDefault()
                  nav.go(target)
                }}
              >
                {section.short}
              </a>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
