import { useState } from 'react'
import type { ReactElement } from 'react'
import type { LabelledPost } from '../../api/methodSchema'
import { formatNumber } from '../figures'
import type { LevelStarts } from '../probes/setting'
import { labelOf } from '../words'
import { SECOND_READER, isRandom, stratumWords } from './explorerWords'
import { MarkedText } from './MarkedText'
import { ReadingsTable } from './ReadingsTable'

interface PostDetailProps {
  post: LabelledPost
  /** The label and the probe the list is filtered on: always shown, and their spans marked. */
  focus: { label: string; probe: string }
  starts: LevelStarts | null
}

const NO = 'no'

/** Labels on which someone said something other than no, in the order the readings list them. */
function spokenLabels(post: LabelledPost): string[] {
  const labels = new Set<string>()
  for (const reading of post.readings) {
    for (const [label, answer] of Object.entries(reading.answers)) if (answer !== NO) labels.add(label)
  }
  for (const [label, answer] of Object.entries(post.answers)) if (answer !== NO) labels.add(label)
  return [...labels]
}

function everyLabel(post: LabelledPost): string[] {
  return [...new Set([...post.readings.flatMap((reading) => Object.keys(reading.answers)), ...Object.keys(post.answers)])]
}

/** A labelled post opened: its text with the quoted spans marked, each reading beside the
 *  others, the settled answers, and what the probes score on it now. */
export function PostDetail({ post, focus, starts }: PostDetailProps): ReactElement {
  const [all, setAll] = useState(false)
  const focused = [focus.label, labelOf(focus.probe)].filter((label) => label !== '')
  const labels = all ? everyLabel(post) : [...new Set([...focused.filter((label) => everyLabel(post).includes(label)), ...spokenLabels(post)])]
  const quotes = post.readings.flatMap((reading) => labels.map((label) => reading.quotes[label]).filter((quote) => quote))
  const flagAt = starts?.possible ?? 0
  const scores = Object.entries(post.scores)
    .filter(([key, score]) => all || key === focus.probe || (starts !== null && score >= flagAt))
    .sort(([, a], [, b]) => b - a)
  const second = post.kind === SECOND_READER
  return (
    <div className="nm-post__detail">
      <MarkedText text={post.text} quotes={quotes} />
      <p className="nm-note">
        Read because it was {stratumWords(post.stratum)}.{' '}
        {isRandom(post.stratum) ? 'It is part of the sample of the corpus.' : 'It is not part of a sample of the corpus: no rate can be read from posts drawn this way.'}
        {second ? ' This is a second reading by another model: it settles nothing, and is never mixed with the answers of the annotators.' : ''}
      </p>
      {labels.length > 0 ? (
        <ReadingsTable post={post} labels={labels} settles={!second} />
      ) : (
        <p className="nm-note">Every reading answered no on every label.</p>
      )}
      <div className="nm-post__scores nm-num">
        <span className="nm-chips__label">{all ? 'Every probe, scored now' : 'Probes that flag it, scored now'}</span>
        {scores.map(([key, score]) => (
          <span key={key} className={`nm-score${starts && score >= starts.probable ? ' is-probable' : starts && score >= starts.possible ? ' is-possible' : ''}`}>
            {key} <b>{formatNumber(score)}</b>
          </span>
        ))}
        {scores.length === 0 ? <span className="nm-note">{Object.keys(post.scores).length === 0 ? 'No score: the probes of this server do not read these posts.' : 'None.'}</span> : null}
      </div>
      <button type="button" className="nm-chip-btn" aria-pressed={all} onClick={() => setAll(!all)}>
        {all ? 'Show only what was found' : 'Show every label and every score'}
      </button>
    </div>
  )
}
