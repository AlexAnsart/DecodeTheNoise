/* The words of the explorer of labelled posts. Pure. */

export const SECOND_READER = 'second reader'

/** How a probe is set against the annotation of its own label. */
export const LEVELS: { value: string; label: string; meaning: string }[] = [
  { value: 'false alarm', label: 'False alarms', meaning: 'It flags the post, and the annotators settled a no.' },
  { value: 'missed', label: 'Missed', meaning: 'It does not flag the post, and the annotators settled a yes.' },
  { value: 'agreed', label: 'Agreed', meaning: 'It flags the post, and the annotators settled a yes.' },
  { value: 'flagged', label: 'Flagged', meaning: 'It flags the post, whatever the annotators settled.' },
]

/** The answers every label takes. A label with answers of its own adds them. */
export const CLOSED_ANSWERS = ['yes', 'no', 'unclear']

/** A yes whose quote is not in the post: it counts as no reading. */
export const INVALID = 'invalid'

function oneStratum(part: string): string {
  const [kind, label, source] = part.split(':')
  if (kind === 'random') return 'drawn at random'
  if (kind === 'enrich') return `searched for, to find more posts of ${label}${source ? ` (${source})` : ''}`
  if (kind === 'band') return `drawn in a score band of the probe ${label}`
  if (kind === 'audit') return `read again by the second reader for ${label}`
  return part
}

/** Why a post was read, in words. Several reasons can hold for one post. */
export function stratumWords(stratum: string): string {
  const parts = stratum.split('|').filter((part) => part !== '')
  return parts.length > 0 ? parts.map(oneStratum).join('; ') : 'the reason it was drawn was not published'
}

/** Only a post drawn at random is part of a sample of the corpus. */
export function isRandom(stratum: string): boolean {
  return stratum.split('|').includes('random')
}

/** The reading a batch belongs to: "m1-calls-a-002" is reading "a". The whole name when it
 *  does not read that way. */
export function readerShort(reader: string): string {
  const parts = reader.split('-')
  return parts.length >= 4 ? parts[parts.length - 2] : reader
}

/** Start and end of each quote found in a text, overlaps merged, in order. */
export function quoteRanges(text: string, quotes: string[]): [start: number, end: number][] {
  const found: [number, number][] = []
  for (const quote of quotes) {
    const at = quote ? text.indexOf(quote) : -1
    if (at !== -1) found.push([at, at + quote.length])
  }
  found.sort(([a], [b]) => a - b)
  const merged: [number, number][] = []
  for (const [start, end] of found) {
    const last = merged[merged.length - 1]
    if (last && start <= last[1]) last[1] = Math.max(last[1], end)
    else merged.push([start, end])
  }
  return merged
}
