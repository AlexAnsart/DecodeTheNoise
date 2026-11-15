import { BookOpen, ChevronRight, ScanSearch } from 'lucide-react'
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { LabelDoc } from '../../api/methodSchema'
import type { Target } from '../hash'
import { Markdown } from '../markdown/Markdown'
import { useMethodShared } from '../MethodContext'
import type { ProbeFiles } from '../probeFiles'
import { StateChip } from '../StateChip'
import { UseChip } from '../UseChip'
import { guideOf } from './guideSection'
import { LabelFacts } from './LabelFacts'

const CLOSED = ['yes', 'no', 'unclear']

interface LabelLineProps {
  label: LabelDoc
  open: boolean
  /** Where its measures are: its own probe, or the probes of its values. Null without a probe. */
  scores: Target | null
  /** The files of the evaluation: how far annotators agree on the label, how frequent it is. */
  files: ProbeFiles
  onToggle(): void
}

/** A label: its question, what it is for, what became of it. Opened, it shows the exact
 *  instructions the annotators received for it. */
export function LabelLine({ label, open, scores, files, onToggle }: LabelLineProps): ReactElement {
  const { nav, guides } = useMethodShared()
  const excerpt = useMemo(() => (open ? guideOf(guides, label.family, label.name) : null), [open, guides, label])
  const own = label.values.length > 0 && label.values.some((value) => !CLOSED.includes(value))
  const go = (target: Target) => (event: { preventDefault(): void }) => {
    event.preventDefault()
    nav.go(target)
  }
  const whole: Target | null = excerpt ? { kind: 'guide', name: excerpt.guide.name } : null
  return (
    <div id={`label-${label.name}`} className={`nm-label${open ? ' is-open' : ''}`}>
      <button type="button" className="nm-label__row" aria-expanded={open} onClick={onToggle}>
        <ChevronRight size={13} aria-hidden />
        <code>{label.name}</code>
        <span className="nm-label__question">{label.question ?? 'Its question was not published.'}</span>
        <UseChip use={label.use} />
        <StateChip state={label.state} />
      </button>
      {open ? (
        <div className="nm-label__body">
          {own ? (
            <p className="nm-note">
              Answers: {label.values.join(', ')}. One probe is fitted for each answer that has enough posts.
            </p>
          ) : null}
          <LabelFacts agreement={files.agreement(label.name)} prevalence={files.prevalence(label.name)} />
          {excerpt?.body ? (
            <Markdown source={excerpt.body} base={excerpt.guide.path} ids={`label-${label.name}`} shift={3} />
          ) : (
            <p className="nm-method__empty">
              {excerpt ? 'The guide of this family has no heading for this label: read the whole guide.' : 'Not published yet: the guide of this family is not served.'}
            </p>
          )}
          <div className="nm-label__actions">
            {whole ? (
              <a className="nm-btn-secondary nm-btn-small" href={nav.href(whole)} onClick={go(whole)}>
                <BookOpen size={12} aria-hidden />
                The whole guide, as the annotators received it
              </a>
            ) : null}
            {scores ? (
              <a className="nm-btn-secondary nm-btn-small" href={nav.href(scores)} onClick={go(scores)}>
                <ScanSearch size={12} aria-hidden />
                What its probe measured
              </a>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
