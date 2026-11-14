import { ExternalLink, LocateFixed, X } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import type { Analysis } from '../api/schema'
import { formatCount, formatMoment } from '../text/format'
import type { Paste } from './usePaste'
import { asLink } from './usePaste'
import './paste.css'

interface PastePanelProps {
  paste: Paste
  /** Set when the current shape of the map has no place for a pasted text. */
  unplaced: string | null
  /** Why the pasted text carries no verdict. */
  noVerdict: string
  /** Brings the camera back onto the pasted text. */
  onLocate(): void
  onClose(): void
}

type ResultProps = Pick<PastePanelProps, 'unplaced' | 'noVerdict' | 'onLocate'> & { analysis: Analysis }

function Result({ analysis, unplaced, noVerdict, onLocate }: ResultProps): ReactElement {
  const { source } = analysis
  return (
    <div className="nm-paste__result">
      {source.kind === 'url' && source.url ? (
        <p className="nm-paste__source">
          <a href={source.url} target="_blank" rel="noopener noreferrer nofollow" title={source.url}>
            <ExternalLink size={11} aria-hidden />
            {source.title ?? source.url}
          </a>
          {source.read_at ? <span>Read on {formatMoment(Date.parse(source.read_at))}</span> : null}
        </p>
      ) : null}
      {analysis.outcome === 'placed' ? (
        <p className="nm-paste__verdict">
          It is on the map now, as a point like the others. Click it to see the items it resembles most.
          {analysis.characters > analysis.text.length
            ? ` The first ${formatCount(analysis.text.length)} of ${formatCount(analysis.characters)} characters were read.`
            : ''}
        </p>
      ) : (
        <p className="nm-paste__verdict nm-paste__verdict--abstain">
          Not enough evidence. {analysis.reason}
        </p>
      )}
      {analysis.outcome === 'placed' && unplaced ? <p className="nm-paste__note">{unplaced}</p> : null}
      {analysis.outcome === 'placed' && !unplaced ? (
        <button type="button" className="nm-btn-secondary nm-btn-small nm-paste__locate" onClick={onLocate}>
          <LocateFixed size={12} aria-hidden />
          Show it on the map
        </button>
      ) : null}
      {analysis.outcome === 'placed' ? (
        <p className="nm-paste__note">{noVerdict}</p>
      ) : null}
    </div>
  )
}

/** A text or a link pasted by the user, placed on the map as a point among the others. */
export function PastePanel({ paste, unplaced, noVerdict, onLocate, onClose }: PastePanelProps): ReactElement {
  const [input, setInput] = useState('')
  const { state } = paste
  const busy = state.status === 'reading'
  const link = asLink(input)
  const done = state.status === 'done' ? state.analysis : null

  return (
    <section
      className="nm-paste"
      role="dialog"
      aria-label="Paste a text or a link"
      onPointerDown={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        if (event.key !== 'Escape') return
        event.stopPropagation()
        onClose()
      }}
    >
      <header className="nm-paste__head">
        <p>Paste a text or a link</p>
        <button type="button" className="nm-drawer__icon" onClick={onClose} title="Close" aria-label="Close">
          <X size={14} aria-hidden />
        </button>
      </header>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (input.trim() && !busy) paste.submit(input)
        }}
      >
        <textarea
          className="nm-field nm-paste__input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="A post, a paragraph, or the address of a page (https://…)"
          aria-label="Text or link"
          maxLength={20000}
          rows={4}
        />
        <div className="nm-paste__actions">
          <span className="nm-muted">{link ? 'A link: the page is read live.' : input.trim() ? `${formatCount(input.trim().length)} characters` : ''}</span>
          {done || state.status === 'error' ? (
            <button
              type="button"
              className="nm-btn-secondary nm-btn-small"
              onClick={() => {
                paste.clear()
                setInput('')
              }}
            >
              Clear
            </button>
          ) : null}
          <button type="submit" className="nm-btn-primary nm-btn-small" disabled={!input.trim() || busy}>
            {busy ? 'Reading…' : 'Place on the map'}
          </button>
        </div>
      </form>
      {busy ? <p className="nm-paste__note">{state.what === 'link' ? 'Reading the page, then placing it…' : 'Placing the text…'}</p> : null}
      {state.status === 'error' ? <p className="nm-paste__note nm-paste__note--error">{state.message}</p> : null}
      {done ? <Result analysis={done} unplaced={unplaced} noVerdict={noVerdict} onLocate={onLocate} /> : null}
    </section>
  )
}
