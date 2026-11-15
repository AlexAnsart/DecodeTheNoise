import type { ReactElement } from 'react'
import type { LabelDoc } from '../../api/methodSchema'
import { plural } from '../../text/format'
import { Disclosure } from '../Disclosure'
import type { Target } from '../hash'
import { useMethodShared } from '../MethodContext'
import type { ProbeFiles } from '../probeFiles'
import { readable } from '../words'
import { LabelLine } from './LabelLine'

interface FamilyBlockProps {
  family: string
  labels: LabelDoc[]
  open: boolean
  /** Keys of the probes that exist, to link a label to its measures. */
  probes: ReadonlySet<string>
  files: ProbeFiles
  onToggle(open: boolean): void
}

/** Where the measures of a label are: its own probe when it has one, the table of probes when
 *  its probes are those of its values (`theme:sport`). */
function scoresOf(label: string, probes: ReadonlySet<string>): Target | null {
  if (probes.has(label)) return { kind: 'probe', key: label }
  for (const key of probes) {
    if (key.startsWith(`${label}:`)) return { kind: 'section', section: 'probes' }
  }
  return null
}

/** One family of labels: one annotation pass, one guide. */
export function FamilyBlock({ family, labels, open, probes, files, onToggle }: FamilyBlockProps): ReactElement {
  const { nav } = useMethodShared()
  const opened = nav.target.kind === 'label' ? nav.target.name : null
  const shown = labels.filter((label) => label.state === 'shown').length
  return (
    <Disclosure
      title={readable(family)}
      hint={`${plural(labels.length, 'label', 'labels')}${shown > 0 ? `, ${shown} shown` : ''}`}
      open={open}
      onToggle={onToggle}
    >
      <div className="nm-labels">
        {labels.map((label) => (
          <LabelLine
            key={label.name}
            label={label}
            open={opened === label.name}
            scores={scoresOf(label.name, probes)}
            files={files}
            onToggle={() => nav.set(opened === label.name ? { kind: 'section', section: 'labels' } : { kind: 'label', name: label.name })}
          />
        ))}
      </div>
    </Disclosure>
  )
}
