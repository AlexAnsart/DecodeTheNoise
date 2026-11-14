/* What the map's columns say about a swarm and its accounts. */

import type { MapData } from '../map/mapData'
import { columnOf } from '../map/mapData'

const ACTOR_PREFIX = 'acct-'

/** The display name of an account, cut like the names of the map's account column. */
export function actorLabel(data: MapData, actorId: string): string {
  const sample = columnOf(data, 'actor')?.names[0]
  const chars = sample?.startsWith(ACTOR_PREFIX) ? sample.length - ACTOR_PREFIX.length : 6
  return `${ACTOR_PREFIX}${actorId.slice(0, chars)}`
}

/** One byte per point: 1 for the posts of the swarm's accounts. Null when the map has no
 *  swarm column or none of its posts. */
export function swarmMask(data: MapData, swarmName: string): Uint8Array | null {
  const column = columnOf(data, 'swarm')
  if (!column) return null
  // The column names a swarm with its size after the name: "Swarm 3 · 23 accounts".
  const code = column.names.findIndex((name) => name === swarmName || name.startsWith(`${swarmName} `))
  if (code < 0) return null
  const mask = new Uint8Array(data.n)
  for (let i = 0; i < data.n; i += 1) mask[i] = column.codes[i] === code ? 1 : 0
  return mask.includes(1) ? mask : null
}
