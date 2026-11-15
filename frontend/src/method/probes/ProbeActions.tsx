import { BookOpen, ListFilter } from 'lucide-react'
import type { ReactElement } from 'react'
import { NO_QUERY } from '../hash'
import type { Target } from '../hash'
import { useMethodShared } from '../MethodContext'
import { labelOf } from '../words'
import type { ProbeRow } from './probeRows'

/** How a probe stands against the annotation of its own label, as the explorer filters it. */
const MISTAKES: { level: string; label: string; title: string }[] = [
  { level: 'false alarm', label: 'Its false alarms', title: 'Labelled posts it flags that the annotators settled as no' },
  { level: 'missed', label: 'What it missed', title: 'Labelled posts the annotators settled as yes that it does not flag' },
  { level: 'agreed', label: 'Where it is right', title: 'Labelled posts it flags that the annotators settled as yes' },
]

interface ProbeActionsProps {
  row: ProbeRow
  /** The labelled posts are published. */
  explorable: boolean
}

/** From a probe to what stands behind it: the guide of its label, and the labelled posts where
 *  it was wrong or right. */
export function ProbeActions({ row, explorable }: ProbeActionsProps): ReactElement {
  const { nav } = useMethodShared()
  const guide: Target = { kind: 'label', name: labelOf(row.key) }
  const link = (target: Target) => ({
    href: nav.href(target),
    onClick: (event: { preventDefault(): void }): void => {
      event.preventDefault()
      nav.go(target)
    },
  })
  return (
    <>
      <div className="nm-probe-detail__actions">
        <a className="nm-btn-secondary nm-btn-small" {...link(guide)}>
          <BookOpen size={12} aria-hidden />
          Its annotation guide
        </a>
        {row.served && explorable
          ? MISTAKES.map((mistake) => (
              <a
                key={mistake.level}
                className="nm-btn-secondary nm-btn-small"
                title={mistake.title}
                {...link({ kind: 'explorer', query: { ...NO_QUERY, probe: row.key, level: mistake.level } })}
              >
                <ListFilter size={12} aria-hidden />
                {mistake.label}
              </a>
            ))
          : null}
      </div>
      {row.served ? null : <p className="nm-note">The server does not score posts with this probe, so the posts it gets wrong cannot be listed here.</p>}
      {row.served && !explorable ? <p className="nm-note">The labelled posts are not published on this server: its mistakes cannot be listed.</p> : null}
    </>
  )
}
