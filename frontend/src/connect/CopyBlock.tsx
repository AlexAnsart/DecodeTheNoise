import type { ReactElement } from 'react'
import { CopyButton } from './CopyButton'
import './connect.css'

interface CopyBlockProps {
  text: string
  /** What the block holds, for the button and for screen readers: "the prompt". */
  what: string
}

/** A text to copy as it is, shown whole in a box that scrolls. */
export function CopyBlock({ text, what }: CopyBlockProps): ReactElement {
  return (
    <div className="nm-code">
      <pre className="nm-code__text" tabIndex={0} aria-label={what}>
        {text}
      </pre>
      <CopyButton text={text} label={`Copy ${what}`} primary />
    </div>
  )
}
