import { Fragment } from 'react'
import type { ReactElement } from 'react'
import type { TextPart } from './quotes'

interface QuotedTextProps {
  parts: TextPart[]
  /** Number of the quote to bring out; the others stay marked, lighter. */
  active: number | null
}

/** A text with the quotes of a review marked inside it. Each quote ends with its number, the
 *  one its row carries; a part two quotes share is marked twice as strong. */
export function QuotedText({ parts, active }: QuotedTextProps): ReactElement {
  return (
    <>
      {parts.map((part, position) =>
        part.quotes.length === 0 ? (
          part.text
        ) : (
          // The parts are positional: the text is cut again whole when the quotes change.
          // eslint-disable-next-line react/no-array-index-key
          <Fragment key={position}>
            <mark
              className={`nm-quote${part.quotes.length > 1 ? ' nm-quote--shared' : ''}${active !== null && part.quotes.includes(active) ? ' is-active' : ''}`}
            >
              {part.text}
            </mark>
            {part.ends.map((number) => (
              <sup key={number} className={`nm-quote-ref${number === active ? ' is-active' : ''}`}>
                {number}
              </sup>
            ))}
          </Fragment>
        ),
      )}
    </>
  )
}
