import type { ReactElement } from 'react'
import { drawnSampleSchema } from '../../api/methodSchema'
import { plural } from '../../text/format'
import { Disclosure } from '../Disclosure'

/** The accounts of the demo that were kept on purpose, beside those that were drawn: every
 *  number and the reason come from the sampling record. Nothing shows when it kept none. */
export function DrawnSample({ sample }: { sample: Record<string, unknown> | null }): ReactElement | null {
  const record = drawnSampleSchema.safeParse(sample)
  const kept = record.success ? record.data.kept : undefined
  if (!record.success || !kept) return null
  const { items, actors } = record.data
  const drawn =
    items !== undefined && actors !== undefined
      ? `${plural(items - kept.items, 'post', 'posts')} of ${plural(actors - kept.actors.length, 'account', 'accounts')} are a seeded draw of whole accounts; `
      : ''
  return (
    <>
      <p className="nm-num">
        {drawn}
        {plural(kept.actors.length, 'account', 'accounts')} ({plural(kept.items, 'post', 'posts')}) {kept.actors.length === 1 ? 'was' : 'were'} kept on
        purpose. {kept.why}
      </p>
      <Disclosure title="The accounts kept on purpose" hint={plural(kept.actors.length, 'hashed id', 'hashed ids')}>
        <ul className="nm-files nm-num">
          {kept.actors.map((id) => (
            <li key={id}>{id}</li>
          ))}
        </ul>
      </Disclosure>
    </>
  )
}
