import type { ReactElement } from 'react'
import type { Method } from '../../api/methodSchema'
import { SidePanel } from '../../app/SidePanel'
import { sectionOf } from '../hash'
import { useMethodShared } from '../MethodContext'
import { FigureView } from './FigureView'
import { Reader } from './Reader'

/** What the address opens over the page: a guide, a document, a figure. Null when it opens
 *  nothing of the kind. */
export function Overlay({ method }: { method: Method | null }): ReactElement | null {
  const { nav } = useMethodShared()
  const { target } = nav
  if (target.kind !== 'guide' && target.kind !== 'doc' && target.kind !== 'figure') return null
  // Closing returns to the section the document was opened from.
  const close = (): void => nav.set({ kind: 'section', section: sectionOf(target) })
  if (target.kind === 'figure' && method?.figures.includes(target.name)) {
    return <FigureView name={target.name} documents={method.documents} onClose={close} />
  }
  const found = target.kind === 'figure' ? undefined : (target.kind === 'guide' ? method?.guides : method?.documents)?.find((file) => file.name === target.name)
  if (found) return <Reader document={found} onClose={close} />
  return (
    <SidePanel title={target.name} onClose={close}>
      <p className="nm-method__empty">
        {method ? 'Not published yet: this server does not serve a document of that name.' : 'Reading the documents…'}
      </p>
    </SidePanel>
  )
}
