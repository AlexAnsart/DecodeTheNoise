import { BookOpen } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Method, MethodDocument } from '../../api/methodSchema'
import { plural } from '../../text/format'
import { useMethodShared } from '../MethodContext'
import { SourceLink } from '../SourceLink'
import './documents.css'

/** What each document of the campaign is, by its name. A document not named here shows its title alone. */
const WHAT: Record<string, string> = {
  report: 'The method and the results of the probe campaign, with its figures. Start here.',
  taxonomy: 'Every label by family, and what each one is for.',
  journal: 'What was run, in order, with what it gave and what was decided from it.',
  review: 'The note on the LLM review.',
}

function Card({ file }: { file: MethodDocument }): ReactElement {
  const { nav } = useMethodShared()
  const target = { kind: 'doc', name: file.name } as const
  const sections = (file.markdown.match(/^## /gm) ?? []).length
  return (
    <li className="nm-doc">
      <h3>{file.title}</h3>
      <p>{WHAT[file.name] ?? 'A document of the repository, shown as it is written.'}</p>
      <p className="nm-doc__meta nm-num">
        <SourceLink path={file.path} />
        {sections > 0 ? <span>{plural(sections, 'section', 'sections')}</span> : null}
      </p>
      <a
        className="nm-btn-secondary nm-btn-small"
        href={nav.href(target)}
        onClick={(event) => {
          event.preventDefault()
          nav.set(target)
        }}
      >
        <BookOpen size={12} aria-hidden />
        Read it here
      </a>
    </li>
  )
}

/** The documents of the campaign, each readable in the page and linked to its source file. */
export function DocumentsSection({ method }: { method: Method }): ReactElement {
  if (method.documents.length === 0) {
    return <p className="nm-method__empty">Not published yet: the report, the taxonomy and the journal of the probe campaign.</p>
  }
  return (
    <ul className="nm-docs">
      {method.documents.map((file) => (
        <Card key={file.name} file={file} />
      ))}
    </ul>
  )
}
