import { ClipboardPaste, ExternalLink } from 'lucide-react'
import type { ReactElement, RefObject } from 'react'
import type { Analysis } from '../api/schema'
import { plural } from '../text/format'
import './paste.css'

interface PastedLabelProps {
  analysis: Analysis
  /** Moved after each frame to where the pasted text sits on the screen. */
  label: RefObject<HTMLDivElement | null>
  /** Just placed, or clicked: it wears its label. Otherwise it looks like any other point. */
  open: boolean
  onToggle(): void
}

/** The pasted text as a point of the map. Open when it has just been placed: labelled, tied to
 *  its neighbours, their list beside the map. After a click elsewhere it is a point like the
 *  others, which still says what it is on hover and opens again on click. */
export function PastedLabel({ analysis, label, open, onToggle }: PastedLabelProps): ReactElement {
  const { source } = analysis
  const isLink = source.kind === 'url'
  return (
    <div ref={label} className={`nm-pasted${open ? ' is-lit' : ''}`}>
      <button
        type="button"
        className="nm-pasted__dot"
        onClick={onToggle}
        aria-expanded={open}
        aria-label={isLink ? 'The page you pasted' : 'The text you pasted'}
      />
      {open ? (
        <span className="nm-pasted__pill">
          <ClipboardPaste size={12} aria-hidden />
          {isLink ? 'Your link' : 'Your text'}
        </span>
      ) : null}
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
          {open
            ? `Placed among its ${plural(analysis.neighbours.length, 'nearest item', 'nearest items')} by meaning: the lines lead to them.`
            : 'Click to see the items it resembles most.'}
        </p>
      </div>
    </div>
  )
}
