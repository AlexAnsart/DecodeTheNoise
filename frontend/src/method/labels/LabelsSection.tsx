import { useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import type { LabelDoc, Method } from '../../api/methodSchema'
import { useMethodShared } from '../MethodContext'
import { Unpublished } from '../Part'
import type { ProbeFiles } from '../probeFiles'
import { StateChip } from '../StateChip'
import { AnnotationSummary } from './AnnotationSummary'
import { FamilyBlock } from './FamilyBlock'
import './labels.css'

/** As the report lists them, then the labels that were never evaluated. */
const STATES: (string | null)[] = ['shown', 'review-only', 'dropped', null]

function byFamily(labels: LabelDoc[]): [family: string, labels: LabelDoc[]][] {
  const families = new Map<string, LabelDoc[]>()
  for (const label of labels) families.set(label.family, [...(families.get(label.family) ?? []), label])
  return [...families.entries()]
}

interface LabelsSectionProps {
  method: Method
  /** Keys of the probes that exist. */
  probes: ReadonlySet<string>
  files: ProbeFiles
}

/** Every label by family, with what it is for and what became of it; any label opens on the
 *  exact instructions its annotators received. */
export function LabelsSection({ method, probes, files }: LabelsSectionProps): ReactElement {
  const { nav } = useMethodShared()
  const families = useMemo(() => byFamily(method.labels), [method.labels])
  const [opened, setOpened] = useState<ReadonlySet<string>>(new Set())
  // The family of the label an address points at is open, whatever was toggled.
  const target = nav.target.kind === 'label' ? nav.target.name : null
  const pinned = method.labels.find((label) => label.name === target)?.family ?? null

  if (method.labels.length === 0) return <Unpublished what="the list of labels" />
  return (
    <>
      <p className="nm-states nm-num">
        {STATES.map((state) => {
          const count = method.labels.filter((label) => label.state === state).length
          return count > 0 ? (
            <span key={state ?? 'none'}>
              <StateChip state={state} /> {count}
            </span>
          ) : null
        })}
      </p>
      <AnnotationSummary method={method} />
      <div className="nm-families">
        {families.map(([family, labels]) => (
          <FamilyBlock
            key={family}
            family={family}
            labels={labels}
            probes={probes}
            files={files}
            open={opened.has(family) || pinned === family}
            onToggle={(open) => {
              const next = new Set(opened)
              if (open) next.add(family)
              else next.delete(family)
              setOpened(next)
              // Closing the family of the label in the address closes that label too.
              if (!open && pinned === family) nav.set({ kind: 'section', section: 'labels' })
            }}
          />
        ))}
      </div>
    </>
  )
}
