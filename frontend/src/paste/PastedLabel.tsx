import { ClipboardPaste, ExternalLink } from 'lucide-react'
import type { ReactElement, RefObject } from 'react'
import type { Analysis } from '../api/schema'
import { plural } from '../text/format'
import './paste.css'

interface PastedLabelProps {
  analysis: Analysis
  /** Moved after each frame to where the pasted text sits on the screen. */
  label: RefObject<HTMLDivElement | null>
}

/** The pasted text as a point of its own: a label that follows it on the map, and what was
 *  pasted when the pointer rests on it. */
export function PastedLabel({ analysis, label }: PastedLabelProps): ReactElement {
  const { source } = analysis
  const isLink = source.kind === 'url'
  return (
    <div ref={label} className="nm-pasted" tabIndex={0} aria-label={isLink ? 'The page you pasted' : 'The text you pasted'}>
      <span className="nm-pasted__dot" aria-hidden />
      <span className="nm-pasted__pill">
        <ClipboardPaste size={12} aria-hidden />
        {isLink ? 'Your link' : 'Your text'}
      </span>
      <div className="nm-pasted__bubble" role="tooltip">
        <p className="nm-pasted__title">{isLink ? (source.title ?? 'The page you pasted') : 'The text you pasted'}</p>
        {isLink && source.url ? (
          <p className="nm-pasted__link">
            <ExternalLink size={11} aria-hidden />
            {source.url}
          </p>
        ) : null}
        <p className="nm-pasted__text">{analysis.text}</p>
        <p className="nm-pasted__meta">
          Placed among its {plural(analysis.neighbours.length, 'nearest item', 'nearest items')} by meaning: the lines lead to them.
        </p>
      </div>
    </div>
  )
}
