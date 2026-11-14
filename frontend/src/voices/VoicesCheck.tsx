import { ChevronDown, ChevronUp } from 'lucide-react'
import { useId, useState } from 'react'
import type { ReactElement } from 'react'
import type { Voices } from '../api/voicesSchema'
import { VoicesResult } from './VoicesResult'
import { useVoices } from './useVoices'
import './voices.css'

interface VoicesCheckProps {
  /** The lasso selection the check reads. */
  indices: Uint32Array
  /** Opens an item on the map. */
  onOpen(index: number): void
}

const OUTCOME_WORD: Record<Voices['outcome'], string> = {
  'one voice': 'Possible: one voice',
  'separate voices': 'Separate voices',
  'not enough evidence': 'Not enough evidence',
}

/** Asks of a selection: do its actors each have a voice of their own, or could any post have
 *  come from any of them? One click, then an answer with its evidence and its reliability. */
export function VoicesCheck({ indices, onOpen }: VoicesCheckProps): ReactElement {
  const { state, sent, check } = useVoices(indices)
  const [folded, setFolded] = useState(false)
  const title = useId()
  const ready = state.status === 'ready'
  const run = (): void => {
    setFolded(false)
    check()
  }

  return (
    <section className="nm-voices" aria-labelledby={title}>
      <header className="nm-voices__head">
        <h3 id={title}>One voice, or several?</h3>
        {ready && folded ? <span className={`nm-voices__chip nm-voices__chip--${state.data.outcome.replaceAll(' ', '-')}`}>{OUTCOME_WORD[state.data.outcome]}</span> : null}
        {ready ? (
          <button
            type="button"
            className="nm-drawer__icon"
            onClick={() => setFolded((value) => !value)}
            title={folded ? 'Show the answer' : 'Fold the answer to see the list'}
            aria-label={folded ? 'Show the answer' : 'Fold the answer'}
            aria-expanded={!folded}
          >
            {folded ? <ChevronDown size={15} aria-hidden /> : <ChevronUp size={15} aria-hidden />}
          </button>
        ) : null}
      </header>

      {/* The title stays in place; what is under it scrolls when the answer is tall. */}
      <div className="nm-voices__body">
        {state.status === 'idle' || state.status === 'loading' ? (
          <>
            <p className="nm-voices__intro">
              Checks whether the actors in this selection each have a voice of their own, or whether any post could have come from any of them.
            </p>
            <div className="nm-voices__run">
              <button type="button" className="nm-btn-primary nm-btn-small" onClick={run} disabled={state.status === 'loading'}>
                Check this selection
              </button>
              {state.status === 'loading' ? (
                <span className="nm-voices__busy" role="status">
                  Comparing the posts of each actor…
                </span>
              ) : null}
            </div>
            <p className="nm-voices__fine">
              Needs at least 4 actors with 4 posts each.{' '}
              <a className="nm-link" href="/method#voices">
                How it works
              </a>
            </p>
          </>
        ) : null}

        {state.status === 'error' ? (
          <>
            <p className="nm-verdicts__note nm-verdicts__note--error" role="alert">
              The check did not complete. {state.message}
            </p>
            <div className="nm-voices__run">
              <button type="button" className="nm-btn-secondary nm-btn-small" onClick={run}>
                Try again
              </button>
            </div>
          </>
        ) : null}

        {ready && !folded ? <VoicesResult voices={state.data} selected={indices.length} sent={sent} onOpen={onOpen} /> : null}
      </div>
    </section>
  )
}
