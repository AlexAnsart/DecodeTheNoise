import { ChevronRight } from 'lucide-react'
import type { ReactElement } from 'react'
import type { LabelledPost } from '../../api/methodSchema'
import { formatNumber } from '../figures'
import type { LevelStarts } from '../probes/setting'
import { labelOf } from '../words'
import { Answer } from './Answer'
import { SECOND_READER, isRandom } from './explorerWords'
import { PostDetail } from './PostDetail'

/** Settled yes answers shown on the line; the rest are counted. */
const SHOWN_LABELS = 4
const NO = 'no'
const UNCLEAR = 'unclear'

interface PostRowProps {
  post: LabelledPost
  open: boolean
  focus: { label: string; probe: string }
  starts: LevelStarts | null
  onToggle(): void
}

/** One labelled post of the list: its text, where it comes from, what was settled on it. It
 *  opens in place on its readings. */
export function PostRow({ post, open, focus, starts, onToggle }: PostRowProps): ReactElement {
  const found = Object.entries(post.answers).filter(([, answer]) => answer !== NO && answer !== UNCLEAR)
  const score = focus.probe in post.scores ? post.scores[focus.probe] : null
  // What was settled on the label asked for, or on the label of the probe asked for.
  const asked = focus.label || labelOf(focus.probe)
  const settled = asked ? post.answers[asked] : undefined
  return (
    <li className={`nm-post${open ? ' is-open' : ''}`}>
      <button type="button" className="nm-post__row" aria-expanded={open} onClick={onToggle}>
        <ChevronRight size={13} aria-hidden />
        <span className="nm-post__line">
          <span className="nm-post__excerpt">{post.text}</span>
          <span className="nm-post__chips">
            <span className="nm-tag">{post.split}</span>
            <span className="nm-tag">{post.round}</span>
            {post.kind === SECOND_READER ? <span className="nm-tag nm-tag--second">second reader</span> : null}
            <span className="nm-tag" title={isRandom(post.stratum) ? 'Part of the sample of the corpus' : 'Not drawn at random: no rate can be read from it'}>
              {isRandom(post.stratum) ? 'random' : 'not random'}
            </span>
            {settled ? <Answer value={settled} by={asked} /> : null}
            {found
              .filter(([label]) => label !== asked)
              .slice(0, SHOWN_LABELS)
              .map(([label, answer]) => (
                // A yes is named by its label; a label with answers of its own says which one.
                <span key={label} className={`nm-answer nm-answer--${answer === 'yes' ? 'yes' : 'own'}`}>
                  {answer === 'yes' ? label : `${label}: ${answer}`}
                </span>
              ))}
            {found.length > SHOWN_LABELS ? <span className="nm-tag">+{found.length - SHOWN_LABELS}</span> : null}
            {score !== null ? (
              <span className={`nm-score${starts && score >= starts.probable ? ' is-probable' : starts && score >= starts.possible ? ' is-possible' : ''}`}>
                {focus.probe} <b className="nm-num">{formatNumber(score)}</b>
              </span>
            ) : null}
          </span>
        </span>
      </button>
      {open ? <PostDetail post={post} focus={focus} starts={starts} /> : null}
    </li>
  )
}
