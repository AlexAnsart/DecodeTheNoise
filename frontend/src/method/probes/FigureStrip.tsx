import type { ReactElement } from 'react'
import { figureUrl } from '../../api/method'
import type { Method } from '../../api/methodSchema'
import { figureUses } from '../documents/figureCaptions'
import { useMethodShared } from '../MethodContext'

/** The figures of the report, small: one click shows a figure whole, with its caption. */
export function FigureStrip({ method }: { method: Method }): ReactElement | null {
  const { nav } = useMethodShared()
  if (method.figures.length === 0) return null
  const uses = figureUses(method.documents)
  return (
    <ul className="nm-figures" aria-label="Figures of the report">
      {method.figures.map((name) => {
        const caption = uses.get(name)?.caption ?? name
        return (
          <li key={name}>
            <button type="button" className="nm-figures__thumb" onClick={() => nav.set({ kind: 'figure', name })} title={`Show the figure: ${caption}`}>
              <img src={figureUrl(name)} alt="" loading="lazy" />
              <span>{caption}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
