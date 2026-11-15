import type { ReactElement } from 'react'
import { CopyButton } from './CopyButton'
import './connect.css'

interface CopyBlockProps {
  /** What the button copies. */
  text: string
  /** What the box shows when it is not the text itself: the text with its key hidden. */
  shown?: string
  /** What the block holds, for the button and for screen readers: "the prompt". */
  what: string
}

/** A text to copy as it is, shown whole in a box that scrolls. */
export function CopyBlock({ text, shown = text, what }: CopyBlockProps): ReactElement {
  return (
    <div className="nm-code">
      <pre className="nm-code__text" tabIndex={0} aria-label={what}>
        {shown}
      </pre>
      <CopyButton text={text} label={`Copy ${what}`} primary />
    </div>
  )
}
