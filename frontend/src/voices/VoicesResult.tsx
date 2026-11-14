import type { ReactElement } from 'react'
import type { Voices } from '../api/voicesSchema'
import { formatCount, plural } from '../text/format'
import { VoicePairs } from './VoicePairs'
import { VoiceScale } from './VoiceScale'
import { VoicesTrust } from './VoicesTrust'

interface VoicesResultProps {
  voices: Voices
  /** Items of the selection, and how many of them were sent to the check. */
  selected: number
  sent: number
  onOpen(index: number): void
}

function percent(share: number): string {
  return `${Math.round(share * 100)}%`
}

/** The headline of the answer: one of three distinct states, each in its own words. */
function Headline({ voices }: { voices: Voices }): ReactElement {
  if (voices.outcome === 'one voice') {
    return (
      <div className="nm-verdict nm-verdict--possible">
        <div className="nm-verdict__head">
          <span className="nm-verdict__level">Possible</span>
          <span className="nm-verdict__label">One voice</span>
        </div>
        <p className="nm-voices__reading">
          These actors are interchangeable: a post by one could have come from any other. That is what several names fed by one source of text look like.
        </p>
      </div>
    )
  }
  if (voices.outcome === 'separate voices') {
    // Over the threshold, yet under where most independent groups score: said as it is.
    const between = voices.score !== null && voices.reference !== null && voices.score < voices.reference.independent[0]
    return (
      <div className="nm-verdict nm-voices__verdict--separate">
        <div className="nm-verdict__head">
          <span className="nm-verdict__label">Separate voices</span>
        </div>
        <p className="nm-voices__reading">
          {between
            ? "Each actor's posts resemble each other more than they resemble the others', though less clearly than in most groups of independent actors. Not enough to call it one voice."
            : "Each actor's posts resemble each other more than they resemble the others'. This is what independent actors look like."}
        </p>
      </div>
    )
  }
  return (
    <div className="nm-verdict nm-voices__verdict--none">
      <div className="nm-verdict__head">
        <span className="nm-verdict__label">Not enough evidence</span>
      </div>
      <p className="nm-voices__reading">{voices.reason ?? 'This selection is too small for the check.'}</p>
      <p className="nm-voices__reading nm-voices__reading--muted">
        Select a wider area, or a zone where the same actors post often. Reposts are not counted.
      </p>
    </div>
  )
}

/** What the check says of a selection, with what it rests on and how far it can be trusted. */
export function VoicesResult({ voices, selected, sent, onOpen }: VoicesResultProps): ReactElement {
  const { score, threshold, reference, authorship, reliability, read } = voices
  const scored = score !== null && threshold !== null && reference !== null
  return (
    <div className="nm-voices__result">
      <Headline voices={voices} />
      {scored ? <VoiceScale score={score} threshold={threshold} independent={reference.independent} oneBrief={reference.one_brief} /> : null}
      {scored && authorship ? (
        <p className="nm-voices__line">
          Guessing who wrote a post: right <b className="nm-num">{percent(authorship.found)}</b> of the time. Chance alone gives{' '}
          <span className="nm-num">{percent(authorship.chance)}</span>.
        </p>
      ) : null}
      {scored && reliability ? <VoicesTrust reliability={reliability} /> : null}
      {voices.outcome === 'one voice' ? <VoicePairs pairs={voices.pairs} onOpen={onOpen} /> : null}
      {voices.outcome === 'one voice' ? (
        <p className="nm-voices__fine">
          It does not say who is behind these actors, nor that a model wrote the posts. A fan campaign or a news feed can look the same.
        </p>
      ) : null}
      {read ? (
        <p className="nm-voices__fine">
          Read: {formatCount(read.actors)} actors × {plural(read.posts_each, 'post', 'posts')}, drawn {plural(read.draws, 'time', 'times')} among{' '}
          {plural(read.eligible_actors, 'actor', 'actors')} with enough posts.
        </p>
      ) : (
        <p className="nm-voices__fine">
          In this selection: {plural(voices.selection.items, 'post', 'posts')} by {plural(voices.selection.actors, 'actor', 'actors')}, reposts left out.
        </p>
      )}
      {sent < selected ? (
        <p className="nm-voices__fine">
          The check read {formatCount(sent)} of the {formatCount(selected)} selected items, taken evenly.
        </p>
      ) : null}
      {voices.caveats.map((caveat) => (
        <p key={caveat} className="nm-voices__fine">
          {caveat}
        </p>
      ))}
    </div>
  )
}
