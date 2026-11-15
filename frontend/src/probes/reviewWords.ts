/* How the LLM review is worded: its readings, the voice of a text, what a reading measured to
   be worth, and a refusal of the server as a sentence. One place, so a post and a selection
   say the same things the same way. */

import { ApiError } from '../api/client'
import type { Finding, Review, ReviewMeasure, Voice } from '../api/reviewSchema'

/** What the review says of a label it checked. Three states, and `unclear` is one of them. */
export const READING_WORD: Record<Finding['reading'], string> = {
  supported: 'Confirmed by the review',
  'not supported': 'Not confirmed by the review',
  unclear: 'Unclear to the review',
}

/** What to say when the text is not plainly in its author's own voice. `own` says nothing. */
export const VOICE_LINE: Record<Voice, { word: string; says: string } | null> = {
  own: null,
  reported: { word: 'Reported words', says: 'The post quotes or reports what someone else says: it may not be its own claim.' },
  ironic: { word: 'Irony', says: 'The post may mean the opposite of what it says.' },
  unclear: { word: 'Voice unclear', says: 'The review cannot tell whether the post speaks in its own name.' },
}

/** Every span of the item a review cites, techniques first. */
export function quotesOf(review: Review): string[] {
  return [...review.techniques.map((technique) => technique.quote), ...review.findings.flatMap((finding) => (finding.quote ? [finding.quote] : []))]
}

function percent(share: number): string {
  return `${Math.round(share * 100)}%`
}

/** A measured share with its interval, never one without the other. */
function withInterval(measure: ReviewMeasure, counted: string): string {
  return `(${Math.round(measure.precision_low * 100)} to ${percent(measure.precision_high)}, ${measure.read} ${counted})`
}

/** What one technique of the review measured to be worth, on held-out posts. */
export function figureWords(measure: ReviewMeasure): string {
  return `${percent(measure.precision)} of the times the review named it, the annotation agreed ${withInterval(measure, 'posts')}.`
}

/** What the technique screen measured to be worth, every measurable technique together. */
export function overallWords(measure: ReviewMeasure): string {
  const found = measure.recall === null ? '' : `, and it finds ${percent(measure.recall)} of those annotated`
  return `All techniques together: ${percent(measure.precision)} of those the review named match the annotation ${withInterval(measure, 'named')}${found}.`
}

/** The model and the prompt a reading was made with, for the small print. */
export function pinnedWords(model: string | null, promptVersion: string | null): string | null {
  if (!model) return null
  return promptVersion ? `${model} · prompt ${promptVersion}` : model
}

/** Status texts a server sends when it has no sentence of its own. */
const BARE = new Set(['', 'Not Found', 'Too Many Requests', 'Service Unavailable', 'Internal Server Error'])

/** Why a review could not be made, as a sentence the person can act on. */
export function refusalWords(error: unknown): string {
  if (!(error instanceof ApiError)) return 'The server could not be reached. Check the connection and try again.'
  const said = BARE.has(error.message) ? null : error.message
  if (error.status === 429) return said ?? 'The review limit is reached for now. Try again later.'
  if (error.status === 503) return said ?? 'No LLM is set up on this server: nothing can be reviewed.'
  if (error.status === 404) return said ?? 'The review is not available on this server yet.'
  if (error.status === 401) return 'This workspace key is not known to the server any more.'
  return said ?? `The server could not answer (${error.status}). Try again in a moment.`
}
