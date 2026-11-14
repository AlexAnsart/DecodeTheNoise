import { Paintbrush, ShieldCheck, X } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Swarm, SwarmLayer } from '../api/schema'
import type { MapData } from '../map/mapData'
import { formatDay, formatMoment, plural } from '../text/format'
import { actorLabel } from './swarmPoints'
import { useSwarm } from './useSwarmLayer'
import '../neighbours/drawers.css'
import './swarms.css'

/** Accounts named on one event before the rest is counted. */
const NAMED_ACCOUNTS = 6

interface SwarmDrawerProps {
  data: MapData
  layer: SwarmLayer
  id: number
  /** Set when the map draws posts of this swarm: they can be coloured against the rest. */
  onColour: (() => void) | null
  onReliability(): void
  onClose(): void
}

function Evidence({ data, layer, swarm }: { data: MapData; layer: SwarmLayer; swarm: Swarm }): ReactElement {
  return (
    <>
      <p className="nm-swarm__lead">
        {plural(swarm.n_events, 'time', 'times')} between {formatDay(swarm.first_at)} and {formatDay(swarm.last_at)}, accounts
        of this group posted the same text within {layer.window_seconds} seconds of each other. A pair of accounts is
        tied once it did so at least {plural(layer.min_events, 'time', 'times')}: the bar chance does not reach.
      </p>
      <h3>Same text, same moment</h3>
      <ul className="nm-swarm__events">
        {swarm.events.map((event) => (
          <li key={`${event.at}:${event.text}`}>
            <p className="nm-swarm__when nm-num">
              {formatMoment(event.at)} · {plural(event.actor_ids.length, 'account', 'accounts')}
              {event.spread_seconds > 0 ? ` within ${event.spread_seconds} s` : ' in the same minute'}
            </p>
            <p className="nm-swarm__text">{event.text}</p>
            <p className="nm-swarm__who">
              {event.actor_ids.slice(0, NAMED_ACCOUNTS).map((actor) => (
                <span key={actor} className="nm-chip">
                  {actorLabel(data, actor)}
                </span>
              ))}
              {event.actor_ids.length > NAMED_ACCOUNTS ? <span>and {event.actor_ids.length - NAMED_ACCOUNTS} more</span> : null}
            </p>
          </li>
        ))}
      </ul>
      <h3>Most active accounts</h3>
      <table className="nm-swarm__actors nm-num">
        <thead>
          <tr>
            <th scope="col">Account</th>
            <th scope="col">Shared posts</th>
            <th scope="col">With</th>
          </tr>
        </thead>
        <tbody>
          {swarm.actors.map((actor) => (
            <tr key={actor.actor_id}>
              <td>{actorLabel(data, actor.actor_id)}</td>
              <td>{actor.n_events}</td>
              <td>{plural(actor.n_partners, 'account', 'accounts')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="nm-swarm__note">
        Coordination is behaviour, not opinion: the detector looks at who posts the same text at the same moment, never
        at what the text says. Account names are hashed.
      </p>
    </>
  )
}

/** One swarm with its evidence: the texts its accounts posted together, and who they are. */
export function SwarmDrawer({ data, layer, id, onColour, onReliability, onClose }: SwarmDrawerProps): ReactElement {
  const load = useSwarm(id)
  const summary = layer.swarms.find((swarm) => swarm.id === id)
  return (
    <aside className="nm-drawer nm-drawer--neighbours nm-swarm" aria-label="Swarm">
      <header className="nm-drawer__head">
        <h2>
          {summary ? `${summary.name} · ${plural(summary.n_actors, 'account', 'accounts')}` : 'Swarm'}
        </h2>
        {summary ? <span className={`nm-level nm-level--${summary.confidence}`}>{summary.confidence}</span> : null}
        <button type="button" className="nm-drawer__icon" onClick={onClose} title="Close" aria-label="Close">
          <X size={15} aria-hidden />
        </button>
      </header>
      <div className="nm-swarm__body">
        <div className="nm-swarm__actions">
          {onColour ? (
            <button type="button" className="nm-btn-secondary nm-btn-small" onClick={onColour}>
              <Paintbrush size={12} aria-hidden />
              Colour its posts on the map
            </button>
          ) : null}
          <button type="button" className="nm-btn-secondary nm-btn-small" onClick={onReliability}>
            <ShieldCheck size={12} aria-hidden />
            How reliable is this?
          </button>
        </div>
        {load.status === 'loading' ? <p className="nm-item-state">Reading the evidence…</p> : null}
        {load.status === 'error' ? <p className="nm-item-state nm-item-state--error">The evidence could not be read.</p> : null}
        {load.status === 'ready' ? <Evidence data={data} layer={layer} swarm={load.swarm} /> : null}
      </div>
    </aside>
  )
}
