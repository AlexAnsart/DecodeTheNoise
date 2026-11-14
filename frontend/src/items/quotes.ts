/* A text cut around the quotes found in it, so they can be shown inside the text itself. Pure. */

export interface TextPart {
  text: string
  /** The part is a quote: words the review leaned on. */
  quoted: boolean
}

/** The parts of `text` in order. A quote absent from the text marks nothing; quotes that
 *  overlap are marked as one stretch. */
export function partsAround(text: string, quotes: string[]): TextPart[] {
  const spans: Array<[number, number]> = []
  for (const quote of quotes) {
    const start = quote ? text.indexOf(quote) : -1
    if (start >= 0) spans.push([start, start + quote.length])
  }
  if (spans.length === 0) return [{ text, quoted: false }]
  spans.sort((a, b) => a[0] - b[0])
  const parts: TextPart[] = []
  let cursor = 0
  for (const [start, end] of spans) {
    if (end <= cursor) continue
    const from = Math.max(start, cursor)
    if (from > cursor) parts.push({ text: text.slice(cursor, from), quoted: false })
    // A span that starts inside the previous quote lengthens it.
    const last = parts[parts.length - 1]
    if (from > start && last?.quoted) last.text += text.slice(from, end)
    else parts.push({ text: text.slice(from, end), quoted: true })
    cursor = end
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), quoted: false })
  return parts
}
