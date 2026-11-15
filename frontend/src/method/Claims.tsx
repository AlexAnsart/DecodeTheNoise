import type { ReactElement } from 'react'

/** What the product never says, each with what it says in its place. They are the rules the
 *  project was built under, not a disclaimer added after it. */
const CLAIMS: { never: string; instead: string }[] = [
  {
    never: 'It never states an intent.',
    instead: 'It says what a text does: it asks its readers to share, it attacks a named person. Why it was written is not in the data.',
  },
  {
    never: 'It never names an organisation, a sponsor or a campaign behind a text or an actor.',
    instead: 'Public data shows whether voices are independent, not who stands behind them.',
  },
  {
    never: 'It never says that an actor is a bot, a troll or paid, or that a text is propaganda, as a fact.',
    instead: 'A reading has a level, possible or probable, and "not enough evidence" is an answer of its own.',
  },
  {
    never: 'A probe flags, it does not convict.',
    instead: 'Every hit is shown with the precision its level measured on posts the probe never saw, and with the way to read its mistakes.',
  },
  {
    never: 'It never says whether a statement is true.',
    instead: 'No label needs to know what is true: the annotators were told that truth never matters, and so is the LLM review.',
  },
  {
    never: 'The layout is a display, not a measure.',
    instead: 'Two points close on the map prove nothing by themselves. The neighbours listed for a post are computed on the vectors, not on the picture.',
  },
  {
    never: 'Sharing a view is not coordination.',
    instead: 'A group is compared with what independent actors on the same subjects produce, and the answer can be "separate voices".',
  },
]

export function Claims(): ReactElement {
  return (
    <dl className="nm-claims">
      {CLAIMS.map((claim) => (
        <div key={claim.never}>
          <dt>{claim.never}</dt>
          <dd>{claim.instead}</dd>
        </div>
      ))}
    </dl>
  )
}
