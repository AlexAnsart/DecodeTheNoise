import type { ReactElement } from 'react'
import type { ProbeInfo } from '../api/schema'
import { shownProbes } from './levels'
import { ProbeVerdict } from './ProbeVerdict'
import { ReviewBlock } from './ReviewBlock'
import type { ReadingState } from './usePointReading'
import './probes.css'

interface PointProbesProps {
  /** The probes of the map. */
  probes: ProbeInfo[]
  state: ReadingState
}

/** What the probes say of one item, in its card: the probes that flagged it, each with its
 *  level and its measured reliability, then the LLM review when there is one. */
export function PointProbes({ probes, state }: PointProbesProps): ReactElement | null {
  if (state.status === 'none') return null
  const review = state.status === 'ready' && state.reading.review?.status !== 'none' ? (state.reading.review ?? null) : null
  const flags = state.status === 'ready' ? state.reading.probes : []
  const hasShown = shownProbes(probes).length > 0
  // Probes that only feed the review are never listed: without a review there is nothing to say.
  if (state.status === 'ready' && !hasShown && !review) return null

  return (
    <section className="nm-verdicts" aria-label="Probes">
      <p className="nm-verdicts__title">Probes</p>
      {state.status === 'loading' ? <p className="nm-verdicts__note">Reading the probes…</p> : null}
      {state.status === 'error' ? <p className="nm-verdicts__note nm-verdicts__note--error">The probes could not be read for this item.</p> : null}
      {flags.map((reading) => (
        <ProbeVerdict key={reading.key} reading={reading} />
      ))}
      {state.status === 'ready' && flags.length === 0 && hasShown ? <p className="nm-verdicts__note">No probe flags this item.</p> : null}
      {review ? <ReviewBlock review={review} probes={probes} /> : null}
    </section>
  )
}
