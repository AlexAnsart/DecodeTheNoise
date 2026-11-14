import { ArrowRight, X } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import { Link } from '../route/Link'
import { PATHS } from '../route/useRoute'
import './promo.css'

const DISMISSED_KEY = 'noisemap.promo'

function dismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) !== null
  } catch {
    return false
  }
}

/** On the demo, the way to one's own map: a small card that can be followed or closed for good. */
export function ApiPromo(): ReactElement | null {
  const [open, setOpen] = useState(() => !dismissed())
  if (!open) return null
  const close = (): void => {
    setOpen(false)
    try {
      localStorage.setItem(DISMISSED_KEY, 'closed')
    } catch {
      // Not remembered: the card comes back on the next visit.
    }
  }
  return (
    <aside className="nm-promo" aria-labelledby="nm-promo-title">
      <header className="nm-promo__head">
        <code className="nm-promo__route">POST /api/v1/items</code>
        <button type="button" className="nm-icon-btn" onClick={close} title="Close: My workspace stays in the header" aria-label="Close">
          <X size={14} aria-hidden />
        </button>
      </header>
      <h2 id="nm-promo-title">Map your own posts via our API</h2>
      <p>Send posts with one HTTP call, get their scores back, and watch your own map build.</p>
      <Link to={PATHS.workspace} className="nm-btn-primary nm-btn-small nm-promo__go">
        Get an API key
        <ArrowRight size={13} aria-hidden />
      </Link>
    </aside>
  )
}
