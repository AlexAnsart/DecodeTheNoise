import type { ReactElement } from 'react'
import { formatCount } from '../../text/format'
import { readable } from '../words'

/** A value of the sampling record, as text: the record is written by the pipeline and read as it is. */
function written(value: unknown): string {
  if (typeof value === 'number') return Number.isInteger(value) && Math.abs(value) >= 10_000 ? formatCount(value) : String(value)
  if (typeof value === 'string') return value
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  if (value === null) return 'not stated'
  if (Array.isArray(value)) return value.map(written).join(', ')
  return JSON.stringify(value)
}

/** The accounts kept on purpose are said in sentences above the record, with their list. */
const SAID_APART = 'kept'

/** How the demo sample was drawn, field by field, as the sampling step recorded it. */
export function SampleFacts({ sample }: { sample: Record<string, unknown> | null }): ReactElement {
  const fields = Object.entries(sample ?? {}).filter(([name]) => name !== SAID_APART)
  if (fields.length === 0) {
    return <p className="nm-method__empty">Not published yet: the record of how the sample was drawn is not served.</p>
  }
  return (
    <dl className="nm-facts">
      {fields.map(([name, value]) => (
        <div key={name}>
          <dt>{readable(name)}</dt>
          <dd className="nm-num">{written(value)}</dd>
        </div>
      ))}
    </dl>
  )
}
