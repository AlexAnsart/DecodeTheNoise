import { ArrowRight } from 'lucide-react'
import type { ReactElement } from 'react'
import { useMethodShared } from '../MethodContext'
import { SourceLink } from '../SourceLink'
import type { Stage } from './stages'

/** A stage of the pipeline, opened: what it does, with what, what was measured, where its code is. */
export function StageDetail({ stage }: { stage: Stage }): ReactElement {
  const { nav } = useMethodShared()
  const { more } = stage
  return (
    <section id="stage-detail" className="nm-stage-detail" aria-label={`Stage: ${stage.title}`}>
      <div>
        <h3>What it does</h3>
        {stage.does.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
      <div>
        <h3>Model and parameters</h3>
        <dl className="nm-facts">
          {stage.parameters.map(([name, value]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd className={value === null ? 'nm-facts__none' : 'nm-num'}>{value ?? 'not published'}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div>
        <h3>What was measured</h3>
        <p>{stage.measured}</p>
        {more ? (
          <a
            className="nm-link nm-stage-detail__more"
            href={nav.href(more.target)}
            onClick={(event) => {
              event.preventDefault()
              nav.go(more.target)
            }}
          >
            {more.label}
            <ArrowRight size={12} aria-hidden />
          </a>
        ) : null}
      </div>
      <div>
        <h3>Code</h3>
        <ul className="nm-sources">
          {stage.code.map((path) => (
            <li key={path}>
              <SourceLink path={path} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
