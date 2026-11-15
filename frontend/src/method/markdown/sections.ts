/* Cutting one section out of a document: from a heading to the next heading of the same
   depth or higher. Pure. */

import { marked } from 'marked'
import type { Tokens } from 'marked'

export interface DocumentSection {
  heading: string
  /** The markdown under the heading, as it is written in the document. */
  body: string
}

/** The first section whose heading passes `matches`; null when the document has none. */
export function sectionOfMarkdown(markdown: string, matches: (heading: string) => boolean): DocumentSection | null {
  const tokens = marked.lexer(markdown)
  const isHeading = (index: number): Tokens.Heading | null => {
    const token = tokens[index]
    return token.type === 'heading' ? (token as Tokens.Heading) : null
  }
  const start = tokens.findIndex((_, index) => {
    const heading = isHeading(index)
    return heading !== null && matches(heading.text)
  })
  const opening = start === -1 ? null : isHeading(start)
  if (!opening) return null
  const next = tokens.findIndex((_, index) => {
    const heading = isHeading(index)
    return index > start && heading !== null && heading.depth <= opening.depth
  })
  const body = tokens.slice(start + 1, next === -1 ? tokens.length : next)
  return { heading: opening.text, body: body.map((token) => token.raw).join('') }
}

/** The headings of a document at one depth, for a short table of contents. */
export function headingsOf(markdown: string, depth: number): string[] {
  return marked
    .lexer(markdown)
    .filter((token): token is Tokens.Heading => token.type === 'heading' && (token as Tokens.Heading).depth === depth)
    .map((heading) => heading.text)
}
