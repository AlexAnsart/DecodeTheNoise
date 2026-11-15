/* The method of the LLM review, step by step, in the words of the page. It follows the prompt
   the server sends, which the page shows in full under it; every number comes from the server. */

import type { ReviewDoc } from '../../api/methodSchema'
import { plural } from '../../text/format'

export const WHEN = [
  'On a workspace, when a probe flags a post at the level chosen in the settings of the workspace.',
  'On one post, when its reader asks for it.',
  'On a selection of posts, when its reader asks: the probes are counted on the whole selection, then the model reads a sample of it.',
]

function context(review: ReviewDoc): string {
  const neighbours = review.neighbours === undefined ? 'its nearest posts by meaning' : `its ${plural(review.neighbours, 'nearest post', 'nearest posts')} by meaning`
  const actor = review.actor_items === undefined ? 'other posts of the same actor' : `up to ${plural(review.actor_items, 'other post', 'other posts')} of the same actor`
  return `${neighbours} and ${actor}`
}

export function stepsOf(review: ReviewDoc): string[] {
  return [
    'It decides whose voice the post is in: the author\'s own, words reported or quoted without agreeing, irony, or unclear.',
    'For each probe that flagged the post, it applies the annotation guide of that label, condition by condition, and answers supported, not supported or unclear, in one or two sentences a reader can check.',
    review.techniques.length > 0
      ? `It screens the post for ${plural(review.techniques.length, 'technique', 'techniques')}, whether a probe flagged it or not, and reports one only when every condition of its guide is visibly met. Most posts show none.`
      : 'It screens the post for manipulation techniques when its technique guides are loaded: on this server they are not.',
    'It says what the post asks its readers to do and whom it is aimed at, as spans of the post.',
    'The quote check: every span is searched in the text of the post, character for character. A span that is not there is thrown away, and the reading it backed with it.',
    `Context is read for one thing only, to resolve what the post refers to: ${context(review)}. It is never quoted and never judged.`,
    'An answer that cannot be read gives a failed review, never a guess. What is kept is stored with the model and the prompt version that produced it.',
  ]
}

/** How a selection is read, when the server says how much of it. */
export function selectionLine(review: ReviewDoc): string | null {
  const { selection_posts: posts, selection_posts_per_actor: perActor, selection_post_chars: chars } = review
  if (posts === undefined) return null
  const each = perActor === undefined ? '' : `, ${perActor} of one actor at most`
  const length = chars === undefined ? '' : `, the first ${chars.toLocaleString('en-US')} characters of each`
  return `For a selection, the model reads up to ${plural(posts, 'post', 'posts')}${each}${length}. What the probes measure on the selection is counted on all of it, without the model.`
}

export const NEVER =
  'The review describes what a text does. It is told never to state the intent of an author, never to name an organisation or a campaign behind a text, never to say that an actor is a bot, a troll or paid, and never to say whether a statement is true.'
