/* The quotes of a review, placed in the text of the item. Each quote gets a number, in the
   order it appears, and the text is cut at every start and end: where two quotes overlap, the
   shared part belongs to both and neither hides the other. Pure. */

export interface TextPart {
  text: string
  /** Numbers of the quotes that cover this part; empty for plain text. */
  quotes: number[]
  /** Numbers of the quotes that end with this part: their mark goes right after it. */
  ends: number[]
}

export interface PlacedQuotes {
  parts: TextPart[]
  /** The number of a quote in the text; null when the text does not hold it. */
  numberOf(quote: string): number | null
}

interface Span {
  start: number
  end: number
}

/** Where `text` holds the quote: as written, or with other spacing between its words. */
function find(text: string, quote: string): Span | null {
  const exact = text.indexOf(quote)
  if (exact >= 0) return { start: exact, end: exact + quote.length }
  const words = quote.split(/\s+/).filter(Boolean)
  if (words.length === 0) return null
  const loose = new RegExp(words.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+')).exec(text)
  return loose ? { start: loose.index, end: loose.index + loose[0].length } : null
}

export function placeQuotes(text: string, quotes: string[]): PlacedQuotes {
  const found = new Map<string, Span>()
  for (const quote of quotes) {
    if (!quote || found.has(quote)) continue
    const span = find(text, quote)
    if (span) found.set(quote, span)
  }
  // Numbered in reading order. Two quotes of the same span share one number.
  const numbers = new Map<string, number>()
  const spans: Array<Span & { number: number }> = []
  for (const [quote, span] of Array.from(found).sort((a, b) => a[1].start - b[1].start || a[1].end - b[1].end)) {
    const same = spans.find((other) => other.start === span.start && other.end === span.end)
    const number = same ? same.number : spans.length + 1
    if (!same) spans.push({ ...span, number })
    numbers.set(quote, number)
  }
  const cuts = Array.from(new Set([0, text.length, ...spans.flatMap((span) => [span.start, span.end])])).sort((a, b) => a - b)
  const parts: TextPart[] = []
  for (let i = 0; i + 1 < cuts.length; i += 1) {
    const from = cuts[i]
    const to = cuts[i + 1]
    parts.push({
      text: text.slice(from, to),
      quotes: spans.filter((span) => span.start <= from && span.end >= to).map((span) => span.number),
      ends: spans.filter((span) => span.end === to).map((span) => span.number),
    })
  }
  return {
    parts: parts.length > 0 ? parts : [{ text, quotes: [], ends: [] }],
    numberOf: (quote) => numbers.get(quote) ?? null,
  }
}
