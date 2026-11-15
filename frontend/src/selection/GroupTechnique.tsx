import { useState } from 'react'
import type { ReactElement } from 'react'
import type { TechniqueInGroup } from '../api/reviewSchema'
import '../probes/review.css'
import { plural } from '../text/format'

/** Example quotes shown before the rest goes behind "more". */
const FIRST_EXAMPLES = 3

interface GroupTechniqueProps {
  technique: TechniqueInGroup
  /** Opens a post on the map. */
  onOpen(index: number): void
}

/** A technique the review names in a selection: what it is, and the words of the posts that
 *  show it. A click on a quote opens its post on the map. */
export function GroupTechnique({ technique, onOpen }: GroupTechniqueProps): ReactElement {
  const [all, setAll] = useState(false)
  const { examples } = technique
  const shown = all ? examples : examples.slice(0, FIRST_EXAMPLES)

  return (
    <div className="nm-technique nm-gtechnique" role="group" aria-label={`Technique: ${technique.name}`}>
      <p className="nm-technique__head">
        <span className="nm-technique__name">{technique.name}</span>
        {examples.length > 0 ? <span className="nm-gtechnique__count">{plural(examples.length, 'post quoted', 'posts quoted')}</span> : null}
      </p>
      <p className="nm-technique__says">{technique.explanation}</p>
      {shown.map((example) => (
        <button
          key={`${example.index}:${example.quote}`}
          type="button"
          className="nm-gtechnique__example"
          onClick={() => onOpen(example.index)}
          title="Open this post on the map"
        >
          “{example.quote}”
        </button>
      ))}
      {examples.length > FIRST_EXAMPLES ? (
        <button type="button" className="nm-sreview__more" onClick={() => setAll((value) => !value)} aria-expanded={all}>
          {all ? 'Show fewer quotes' : `Show ${examples.length - FIRST_EXAMPLES} more`}
        </button>
      ) : null}
    </div>
  )
}
