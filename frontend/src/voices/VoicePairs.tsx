import type { ReactElement } from 'react'
import type { VoicePair } from '../api/voicesSchema'

interface VoicePairsProps {
  pairs: VoicePair[]
  /** Opens an item on the map. */
  onOpen(index: number): void
}

type Side = VoicePair['a']

function Quote({ side, onOpen }: { side: Side; onOpen(index: number): void }): ReactElement {
  return (
    <button type="button" className="nm-voice-pair__post" onClick={() => onOpen(side.index)} title="Open this post on the map">
      <span className="nm-voice-pair__actor">{side.actor}</span>
      <span className="nm-voice-pair__text">“{side.text}”</span>
    </button>
  )
}

/** The evidence of a "one voice" reading: posts by different actors that say the same thing. */
export function VoicePairs({ pairs, onOpen }: VoicePairsProps): ReactElement | null {
  if (pairs.length === 0) return null
  return (
    <div className="nm-voice-pairs">
      <p className="nm-voices__label">Closest posts by different actors</p>
      {pairs.map((pair) => (
        <div key={`${pair.a.index}:${pair.b.index}`} className="nm-voice-pair">
          <Quote side={pair.a} onOpen={onOpen} />
          <Quote side={pair.b} onOpen={onOpen} />
        </div>
      ))}
    </div>
  )
}
