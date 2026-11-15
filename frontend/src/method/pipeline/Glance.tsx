import type { ReactElement } from 'react'
import { formatCount } from '../../text/format'
import type { Facts } from './facts'
import { probeCounts } from './facts'

/** The few numbers that size the product, each read from the server; one that is not known
 *  yet is left out rather than guessed. */
export function Glance({ facts }: { facts: Facts }): ReactElement | null {
  const { method } = facts
  const probes = probeCounts(facts)
  const known: [value: number | undefined, label: string][] = [
    [method?.build?.points, 'posts on the demo map'],
    [method?.build?.zones, 'zones'],
    [method?.labels.length || undefined, 'labels annotated'],
    [method?.labelled?.posts, 'posts read by annotators'],
    [probes?.shown, 'probes shown'],
    [probes?.reviewOnly, 'probes for review only'],
    [probes?.dropped, 'probes dropped'],
  ]
  const stats = known.filter((stat): stat is [number, string] => stat[0] !== undefined)
  if (stats.length === 0) return null
  return (
    <dl className="nm-glance">
      {stats.map(([value, label]) => (
        <div key={label}>
          <dd className="nm-num">{formatCount(value)}</dd>
          <dt>{label}</dt>
        </div>
      ))}
    </dl>
  )
}
