import type { ReactElement } from 'react'
import { figureUrl } from '../../api/method'
import type { MethodDocument } from '../../api/methodSchema'
import { SidePanel } from '../../app/SidePanel'
import { useMethodShared } from '../MethodContext'
import { figureUses } from './figureCaptions'
import './documents.css'

interface FigureViewProps {
  name: string
  documents: MethodDocument[]
  onClose(): void
}

/** A figure of the report, whole, with what it shows and the document that explains it. */
export function FigureView({ name, documents, onClose }: FigureViewProps): ReactElement {
  const { nav } = useMethodShared()
  const use = figureUses(documents).get(name)
  const source = use ? documents.find((document) => document.name === use.document) : undefined
  return (
    <SidePanel title={use?.caption ?? name} wide onClose={onClose}>
      <img className="nm-md__figure" src={figureUrl(name)} alt={use?.caption ?? name} />
      {source ? (
        <p className="nm-note">
          From{' '}
          <a
            className="nm-link"
            href={nav.href({ kind: 'doc', name: source.name })}
            onClick={(event) => {
              event.preventDefault()
              nav.go({ kind: 'doc', name: source.name })
            }}
          >
            {source.title}
          </a>
          , which says how it was made and how to read it.
        </p>
      ) : null}
    </SidePanel>
  )
}
