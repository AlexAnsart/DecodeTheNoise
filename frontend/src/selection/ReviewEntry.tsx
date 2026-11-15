import { LoaderCircle } from 'lucide-react'
import { useId } from 'react'
import type { ReactElement } from 'react'
import { formatCount, plural } from '../text/format'
import type { SelectionReviewRun, SelectionReviewState } from './useSelectionReview'
import './selectionReview.css'

interface ReviewEntryProps {
  review: SelectionReviewRun
  /** Opens the panel of the review. */
  onOpen(): void
}

const BUTTON: Record<SelectionReviewState['status'], string> = {
  idle: 'Review this selection',
  loading: 'See the review',
  ready: 'Open the review',
  error: 'Try again',
}

function says(state: SelectionReviewState): string {
  if (state.status === 'idle') {
    return 'Counts which probes flag these posts more than the rest of the map, then has the LLM read a sample: what they say, the techniques they use, with quotes.'
  }
  if (state.status === 'loading') return 'Counting the probes, then reading a sample with the LLM. About ten seconds.'
  if (state.status === 'error') return state.message
  const { data } = state
  if (data.status !== 'done') return 'The probes were counted. The LLM did not read the posts.'
  return `${plural(data.techniques.length, 'technique named', 'techniques named')} · ${formatCount(data.read.length)} of ${plural(data.posts, 'post', 'posts')} read.`
}

/** The way into the review of a selection, in the drawer beside the other checks: one line
 *  that says what it does, one button. Once made, what it found in a line, and the way back in. */
export function ReviewEntry({ review, onOpen }: ReviewEntryProps): ReactElement {
  const { state, run } = review
  const title = useId()
  const open = (): void => {
    onOpen()
    if (state.status === 'idle' || state.status === 'error') run()
  }

  return (
    <section className="nm-sreview-entry" aria-labelledby={title}>
      <div className="nm-sreview-entry__head">
        <h3 id={title}>What do these posts share?</h3>
        <button type="button" className={`${state.status === 'idle' ? 'nm-btn-primary' : 'nm-btn-secondary'} nm-btn-small`} onClick={open}>
          {BUTTON[state.status]}
        </button>
      </div>
      <p className={`nm-sreview-entry__says${state.status === 'error' ? ' is-error' : ''}`} role={state.status === 'error' ? 'alert' : undefined}>
        {state.status === 'loading' ? <LoaderCircle size={12} className="nm-spin" aria-hidden /> : null}
        {says(state)}
      </p>
    </section>
  )
}
