import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { MethodDocument } from '../../api/methodSchema'
import { SidePanel } from '../../app/SidePanel'
import { formatCount } from '../../text/format'
import { slug } from '../markdown/links'
import { Markdown } from '../markdown/Markdown'
import { headingsOf } from '../markdown/sections'
import { SourceLink } from '../SourceLink'
import './documents.css'

interface ReaderProps {
  document: MethodDocument
  onClose(): void
}

/** A document of the repository read in full, as it is: an annotation guide as the annotators
 *  received it, the report, the journal. Its source file is one click away. */
export function Reader({ document: file, onClose }: ReaderProps): ReactElement {
  const ids = `doc-${file.name}`
  const headings = useMemo(() => headingsOf(file.markdown, 2), [file.markdown])
  const words = useMemo(() => file.markdown.split(/\s+/).filter((word) => word !== '').length, [file.markdown])
  return (
    <SidePanel title={file.title} wide onClose={onClose}>
      <p className="nm-reader__meta nm-num">
        <SourceLink path={file.path} />
        <span>{formatCount(words)} words, shown as the file is written</span>
      </p>
      {headings.length > 1 ? (
        <nav className="nm-reader__toc" aria-label="Sections of this document">
          {headings.map((heading) => {
            const id = `${ids}-${slug(heading)}`
            return (
              <a
                key={id}
                href={`#${id}`}
                onClick={(event) => {
                  // The address names the document that is open: a heading is reached without it.
                  event.preventDefault()
                  document.getElementById(id)?.scrollIntoView({ block: 'start' })
                }}
              >
                {heading.replace(/[`*_]/g, '')}
              </a>
            )
          })}
        </nav>
      ) : null}
      <Markdown source={file.markdown} base={file.path} ids={ids} />
    </SidePanel>
  )
}
