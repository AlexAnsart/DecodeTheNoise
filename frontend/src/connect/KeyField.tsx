import { Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import { CopyButton } from './CopyButton'
import './connect.css'

const HIDDEN_CHARS = 14

/** The API key: hidden until asked for, copied in one click. */
export function KeyField({ apiKey }: { apiKey: string }): ReactElement {
  const [shown, setShown] = useState(false)
  const masked = `${apiKey.slice(0, 3)}${'•'.repeat(HIDDEN_CHARS)}${apiKey.slice(-4)}`
  return (
    <div className="nm-key">
      <code className="nm-key__value" aria-label={shown ? 'API key' : 'API key, hidden'}>
        {shown ? apiKey : masked}
      </code>
      <button
        type="button"
        className="nm-tool nm-tool--icon"
        onClick={() => setShown((value) => !value)}
        aria-pressed={shown}
        title={shown ? 'Hide the key' : 'Show the key'}
        aria-label={shown ? 'Hide the key' : 'Show the key'}
      >
        {shown ? <EyeOff size={14} aria-hidden /> : <Eye size={14} aria-hidden />}
      </button>
      <CopyButton text={apiKey} label="Copy" primary />
    </div>
  )
}
