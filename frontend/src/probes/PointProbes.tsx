import type { ReactElement } from 'react'
import type { ProbeInfo } from '../api/schema'
import { shownProbes } from './levels'
import { ProbeVerdict } from './ProbeVerdict'
import type { ReadingState } from './usePointReading'
import './probes.css'

interface PointProbesProps {
  /** The probes of the map. */
  probes: ProbeInfo[]
  state: ReadingState
}

/** What the probes say of one item, in its card: the probes that flagged it, each with its
 *  level and its measured reliability. The LLM review comes after, in its own block. */
export function PointProbes({ probes, state }: PointProbesProps): ReactElement | null {
  // Probes that only feed the review are never listed.
  if (state.status === 'none' || shownProbes(probes).length === 0) return null
  const flags = state.status === 'ready' ? state.reading.probes : []

  return (
    <section className="nm-verdicts" aria-label="Probes">
      <p className="nm-verdicts__title">Probes</p>
      {state.status === 'loading' ? <p className="nm-verdicts__note">Reading the probes…</p> : null}
      {state.status === 'error' ? <p className="nm-verdicts__note nm-verdicts__note--error">The probes could not be read for this item.</p> : null}
      {flags.map((reading) => (
        <ProbeVerdict key={reading.key} reading={reading} />
      ))}
      {state.status === 'ready' && flags.length === 0 ? <p className="nm-verdicts__note">No probe flags this item.</p> : null}
    </section>
  )
}
