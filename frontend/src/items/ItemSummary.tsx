import { ExternalLink } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Item } from '../api/schema'
import { formatMoment } from '../text/format'
import { partsAround } from './quotes'
import './items.css'

interface ItemSummaryProps {
  item: Item
  /** Account label of the point, from the map's columns. */
  actor: string | null
  /** Lines of text shown before the rest is cut; null shows all of it. */
  clamp: number | null
  /** Spans of the text to mark: the words a review leaned on. */
  quotes?: string[]
}

function label(key: string): string {
  const words = key.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

function host(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, '')
  } catch {
    return url
  }
}

/** What an item says and where it comes from: used by the card, the tooltip lists and the drawers. */
export function ItemSummary({ item, actor, clamp, quotes = [] }: ItemSummaryProps): ReactElement {
  const facts = Object.entries(item.attrs).filter(([, value]) => value !== null && value !== '')
  return (
    <div className="nm-item">
      <div className="nm-item__who">
        <span className="nm-item__actor">{actor ?? item.actor_id}</span>
        <span className="nm-item__when nm-num">{item.created_at ? formatMoment(item.created_at) : 'No date'}</span>
      </div>
      <p className="nm-item__text" style={clamp ? { WebkitLineClamp: clamp } : undefined} data-clamped={clamp !== null}>
        {quotes.length === 0
          ? item.text
          : partsAround(item.text, quotes).map((part, position) =>
              // The parts are positional: the text is cut again whole when the quotes change.
              // eslint-disable-next-line react/no-array-index-key
              part.quoted ? <mark key={position}>{part.text}</mark> : part.text,
            )}
      </p>
      {facts.length > 0 || item.lang ? (
        <dl className="nm-item__facts">
          {facts.map(([key, value]) => (
            <div key={key}>
              <dt>{label(key)}</dt>
              <dd>{String(value)}</dd>
            </div>
          ))}
          {item.lang ? (
            <div>
              <dt>Language</dt>
              <dd>{item.lang}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      {item.urls.length > 0 ? (
        <ul className="nm-item__links">
          {item.urls.slice(0, 3).map((url) => (
            <li key={url}>
              <a href={url} target="_blank" rel="noopener noreferrer nofollow" title={url}>
                <ExternalLink size={11} aria-hidden />
                {host(url)}
              </a>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
