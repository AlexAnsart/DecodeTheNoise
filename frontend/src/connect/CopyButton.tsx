import { Check, Copy } from 'lucide-react'
import type { ReactElement } from 'react'
import { useCopy } from './useCopy'
import './connect.css'

interface CopyButtonProps {
  text: string
  /** What is copied, for the button: "Copy the prompt". */
  label: string
  primary?: boolean
}

/** Copies a text and confirms it on the button itself. */
export function CopyButton({ text, label, primary = false }: CopyButtonProps): ReactElement {
  const { copied, failed, copy } = useCopy()
  return (
    <span className="nm-copy">
      <button type="button" className={`${primary ? 'nm-btn-primary' : 'nm-btn-secondary'} nm-btn-small`} onClick={() => copy(text)}>
        {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
        {copied ? 'Copied' : label}
      </button>
      {failed ? (
        <span className="nm-copy__failed" role="alert">
          The browser did not allow the copy: select the text and copy it by hand.
        </span>
      ) : null}
    </span>
  )
}
