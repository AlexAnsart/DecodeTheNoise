import type { ReactElement } from 'react'
import type { ActorVerdict, SwarmLayer } from '../api/schema'
import { plural } from '../text/format'
import { reliabilityLines } from '../verdict/reliability'
import { VerdictBlock } from '../verdict/VerdictBlock'

interface SwarmVerdictProps {
  layer: SwarmLayer
  /** The verdict on the account that posted the item. */
  verdict: ActorVerdict
  onOpenSwarm(id: number): void
  onReliability(): void
}

/** The coordination verdict on the account behind an item: what its posting shares with other
 *  accounts, and how reliable the detector measured to be. */
export function SwarmVerdict({ layer, verdict, onOpenSwarm, onReliability }: SwarmVerdictProps): ReactElement {
  const swarm = layer.swarms.find((candidate) => candidate.id === verdict.swarm)
  const together = `${plural(verdict.n_events, 'time', 'times')}, this account posted the same text as ${plural(verdict.n_partners, 'other account', 'other accounts')} within ${layer.window_seconds} seconds.`
  const group = swarm ? ` They are part of ${swarm.name}: ${plural(swarm.n_actors, 'account', 'accounts')}.` : ''
  return (
    <VerdictBlock
      label="Coordinated posting"
      confidence={verdict.confidence}
      evidence={together + group}
      measured={reliabilityLines(layer.reliability)}
    >
      <button type="button" className="nm-btn-secondary nm-btn-small" onClick={() => onOpenSwarm(verdict.swarm)}>
        See the evidence
      </button>
      <button type="button" className="nm-btn-secondary nm-btn-small" onClick={onReliability}>
        How reliable is this?
      </button>
    </VerdictBlock>
  )
}
