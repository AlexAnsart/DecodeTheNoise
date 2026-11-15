import { useMemo, useRef } from 'react'
import type { ReactElement } from 'react'
import { Overlay } from './documents/Overlay'
import type { MethodShared } from './MethodContext'
import { MethodContext } from './MethodContext'
import { MethodSections } from './MethodSections'
import { Toc } from './Toc'
import { useActiveSection } from './useActiveSection'
import { useMethodData } from './useMethodData'
import { useMethodNav } from './useMethodNav'
import './method.css'

/** The method page: the whole method in two minutes from its top, and any part of it open
 *  down to the file that produced a number. What is open is in the address. */
export function MethodPage(): ReactElement {
  const scroller = useRef<HTMLDivElement>(null)
  const nav = useMethodNav(scroller)
  const active = useActiveSection(scroller)
  const page = useMethodData()
  const { data } = page
  const shared = useMemo<MethodShared>(
    () => ({
      nav,
      source: data ? { repository: data.repository, commit: data.commit } : null,
      guides: data?.guides ?? [],
      documents: data?.documents ?? [],
    }),
    [nav, data],
  )

  return (
    <MethodContext value={shared}>
      <div ref={scroller} className="nm-method">
        <div className="nm-method__layout">
          <Toc active={active} />
          <article className="nm-method__page">
            <header className="nm-method__head">
              <p className="nm-eyebrow">Method and scores</p>
              <h1>How NoiseMap reads a post, and how far each reading can be trusted</h1>
              <p>
                Every post becomes a vector of meaning. A map places close meanings together; small probes read the vector and flag what they were
                trained to see; an LLM reads again what they flag and quotes its evidence. Nothing is shown without what it measured, and every
                number on this page leads to the file that produced it.
              </p>
            </header>
            <MethodSections page={page} />
          </article>
        </div>
        <Overlay method={data} />
      </div>
    </MethodContext>
  )
}
