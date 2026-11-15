import { ArrowLeft, LoaderCircle } from 'lucide-react'
import { useId } from 'react'
import type { ReactElement } from 'react'
import { pinnedWords } from '../probes/reviewWords'
import { ReviewMeasured } from './ReviewMeasured'
import { ReviewRead } from './ReviewRead'
import type { SelectionReviewRun } from './useSelectionReview'
import './selectionReview.css'

interface SelectionReviewPanelProps {
  review: SelectionReviewRun
  /** Items of the selection. */
  selected: number
  /** Opens a post on the map. */
  onOpen(index: number): void
  /** Goes back to the list of the selection. */
  onClose(): void
}

/** The review of a selection, in place of its list: first what the probes measure on it, then
 *  what the LLM read in it, then what this is not. Slow to make: it says so while it runs. */
export function SelectionReviewPanel({ review, selected, onOpen, onClose }: SelectionReviewPanelProps): ReactElement {
  const { state, sent, run } = review
  const title = useId()
  const pinned = state.status === 'ready' ? pinnedWords(state.data.model, state.data.prompt_version) : null

  return (
    <section
      className="nm-sreview"
      aria-labelledby={title}
      onKeyDown={(event) => {
        if (event.key !== 'Escape') return
        event.stopPropagation()
        onClose()
      }}
    >
      <header className="nm-sreview__head">
        <button type="button" className="nm-drawer__icon" onClick={onClose} title="Back to the list" aria-label="Back to the list">
          <ArrowLeft size={15} aria-hidden />
        </button>
        <h3 id={title}>Review of this selection</h3>
      </header>
      <div className="nm-sreview__body">
        {state.status === 'loading' ? (
          <div className="nm-sreview__busy" role="status">
            <LoaderCircle size={16} className="nm-spin" aria-hidden />
            <p>
              <b>Reviewing the selection.</b> Counting the probes on these posts, then reading a sample with the LLM. About ten seconds.
            </p>
          </div>
        ) : null}
        {state.status === 'idle' || state.status === 'error' ? (
          <div className="nm-sreview__part">
            {state.status === 'error' ? (
              <p className="nm-sreview__error" role="alert">
                {state.message}
              </p>
            ) : (
              <p>Counts which probes flag these posts more than the rest of the map, then has the LLM read a sample of them.</p>
            )}
            <button type="button" className="nm-btn-primary nm-btn-small nm-sreview__run" onClick={run}>
              {state.status === 'error' ? 'Try again' : 'Review this selection'}
            </button>
          </div>
        ) : null}
        {state.status === 'ready' ? (
          <>
            <ReviewMeasured review={state.data} selected={selected} sent={sent} />
            <ReviewRead review={state.data} onOpen={onOpen} />
            <p className="nm-sreview__not">
              Posts that agree are not, by that alone, coordinated. This review describes what the posts share, not who is behind them.
            </p>
            {state.data.status === 'done' ? (
              <p className="nm-sreview__fine">
                {state.data.measured ? (
                  <>
                    What the LLM reads was measured against the annotation.{' '}
                    <a className="nm-link" href="/method#review">
                      How it is measured
                    </a>
                  </>
                ) : (
                  'LLM reading, not measured yet.'
                )}
                {pinned ? <span className="nm-review__pinned"> {pinned}</span> : null}
              </p>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  )
}
