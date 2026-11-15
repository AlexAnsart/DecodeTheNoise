import { useMemo } from 'react'
import type { ReactElement } from 'react'
import { useMethodShared } from '../MethodContext'
import type { Facts } from './facts'
import { StageDetail } from './StageDetail'
import { stagesOf } from './stages'
import './pipeline.css'

/** The pipeline at a glance: six stages in a row, each opening on its detail. */
export function Pipeline({ facts }: { facts: Facts }): ReactElement {
  const { nav } = useMethodShared()
  const stages = useMemo(() => stagesOf(facts), [facts])
  const open = nav.target.kind === 'stage' ? nav.target.id : null
  const opened = stages.find((stage) => stage.id === open) ?? null
  return (
    <div id="pipeline" className="nm-pipeline">
      <ol className="nm-pipeline__stages">
        {stages.map(({ id, icon: Icon, title, line, fact }, index) => (
          <li key={id}>
            <button
              type="button"
              className={`nm-pipeline__stage${open === id ? ' is-open' : ''}`}
              aria-expanded={open === id}
              aria-controls="stage-detail"
              onClick={() => nav.set(open === id ? { kind: 'section', section: 'overview' } : { kind: 'stage', id })}
            >
              <span className="nm-pipeline__step">
                <b>{index + 1}</b>
                <Icon size={15} aria-hidden />
              </span>
              <strong>{title}</strong>
              <span>{line}</span>
              {fact ? <em className="nm-num">{fact}</em> : null}
            </button>
          </li>
        ))}
      </ol>
      {opened ? (
        <StageDetail stage={opened} />
      ) : (
        <p className="nm-note">Open a stage to read what it does, with which model and parameters, what was measured, and where its code is.</p>
      )}
    </div>
  )
}
