import type { ReactElement, ReactNode } from 'react'
import { quoteRanges } from './explorerWords'

interface MarkedTextProps {
  text: string
  /** The spans the annotators quoted: each is marked where it stands in the text. */
  quotes: string[]
}

/** The text of a post with the quoted spans marked in place. */
export function MarkedText({ text, quotes }: MarkedTextProps): ReactElement {
  const parts: ReactNode[] = []
  let at = 0
  for (const [start, end] of quoteRanges(text, quotes)) {
    if (start > at) parts.push(text.slice(at, start))
    parts.push(<mark key={start}>{text.slice(start, end)}</mark>)
    at = end
  }
  if (at < text.length) parts.push(text.slice(at))
  return <p className="nm-post__text">{parts}</p>
}
