import { BookOpen } from 'lucide-react'
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { Method } from '../../api/methodSchema'
import { Disclosure } from '../Disclosure'
import { Markdown } from '../markdown/Markdown'
import { sectionOfMarkdown } from '../markdown/sections'
import { useMethodShared } from '../MethodContext'
import { readable } from '../words'

/** The section of the report that says who annotated, and how readings were settled. */
const ANNOTATION = /\bannotation\b/i
const COMMON = 'common'

/** Who annotated and how, from the report of the campaign; then every guide, to read in full
 *  as the annotators received it. */
export function AnnotationSummary({ method }: { method: Method }): ReactElement {
  const { nav } = useMethodShared()
  const report = method.documents.find((document) => document.name === 'report')
  const annotation = useMemo(() => (report ? sectionOfMarkdown(report.markdown, (heading) => ANNOTATION.test(heading)) : null), [report])
  // The common rules first: every annotator read them before the guide of its pass.
  const guides = [...method.guides].sort((a, b) => Number(b.name === COMMON) - Number(a.name === COMMON))
  return (
    <>
      {annotation && report ? (
        <Disclosure title="Who annotated, and how readings were settled" hint="from the report">
          <Markdown source={annotation.body} base={report.path} ids="annotation" shift={3} />
        </Disclosure>
      ) : (
        <p className="nm-method__empty">Not published yet: the report of the campaign, which says who annotated and how readings were settled.</p>
      )}
      {guides.length > 0 ? (
        <div className="nm-guides" role="group" aria-label="The annotation guides">
          <span className="nm-chips__label">The guides, in full</span>
          {guides.map((guide) => {
            const target = { kind: 'guide', name: guide.name } as const
            return (
              <a
                key={guide.name}
                className="nm-chip-btn"
                href={nav.href(target)}
                title={guide.title}
                onClick={(event) => {
                  event.preventDefault()
                  nav.set(target)
                }}
              >
                <BookOpen size={11} aria-hidden />
                {guide.name === COMMON ? 'Common rules' : readable(guide.name)}
              </a>
            )
          })}
        </div>
      ) : (
        <p className="nm-method__empty">Not published yet: the annotation guides.</p>
      )}
    </>
  )
}
