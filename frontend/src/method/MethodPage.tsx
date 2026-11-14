import { useEffect } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { PATHS, navigate, useHash } from '../route/useRoute'
import { VoicesMethod } from '../voices/VoicesMethod'
import { ApiReference } from './ApiReference'
import { LimitsTable } from './LimitsTable'
import { ProbeTable } from './ProbeTable'
import './method.css'

/** The sections of the page. Those without a body yet say so in one line. */
const SECTIONS: { id: string; title: string; body: ReactNode | null }[] = [
  { id: 'how', title: 'How it works', body: null },
  { id: 'probes', title: 'Probes and their reliability', body: <ProbeTable /> },
  { id: 'voices', title: 'One voice or several: the check and its reliability', body: <VoicesMethod /> },
  { id: 'api', title: 'The API', body: <ApiReference /> },
  { id: 'limits', title: 'Limits', body: <LimitsTable /> },
  { id: 'claims', title: 'What NoiseMap does not claim', body: null },
]

function show(id: string, smooth: boolean): void {
  document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: smooth ? 'smooth' : 'auto' })
}

/** The method page: how it works, what each probe measured to be worth, and the API. */
export function MethodPage(): ReactElement {
  const hash = useHash()
  // A link from elsewhere (`/method#probes`) opens the page on its section.
  useEffect(() => {
    if (hash) show(hash, false)
  }, [hash])

  return (
    <div className="nm-method">
      <article className="nm-method__page">
        <header className="nm-method__head">
          <p className="nm-eyebrow">Method</p>
          <h1>How NoiseMap works, and what it measured</h1>
          <nav className="nm-method__toc" aria-label="Sections of this page">
            {SECTIONS.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                onClick={(event) => {
                  event.preventDefault()
                  navigate(`${PATHS.method}#${section.id}`)
                  show(section.id, true)
                }}
              >
                {section.title}
              </a>
            ))}
          </nav>
        </header>
        {SECTIONS.map((section) => (
          <section key={section.id} id={section.id} className="nm-method__section" aria-labelledby={`${section.id}-title`}>
            <h2 id={`${section.id}-title`}>{section.title}</h2>
            {section.body ?? <p className="nm-method__empty">To be written.</p>}
          </section>
        ))}
      </article>
    </div>
  )
}
