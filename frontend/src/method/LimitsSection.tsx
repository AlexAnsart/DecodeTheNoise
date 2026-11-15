import { useMemo } from 'react'
import type { ReactElement } from 'react'
import type { Method } from '../api/methodSchema'
import type { Request } from '../api/useRequest'
import type { PublicConfig } from '../api/workspaceSchema'
import { Disclosure } from './Disclosure'
import { LimitsTable } from './LimitsTable'
import { Markdown } from './markdown/Markdown'
import { sectionOfMarkdown } from './markdown/sections'
import { Part } from './Part'

/** The heading of the report's own section on what the probes cannot be trusted for. */
const LIMITS = /^(\d+\.\s*)?limits\b/i

interface LimitsSectionProps {
  config: Request<PublicConfig>
  method: Method | null
}

/** Two kinds of limits: what the measures do not cover, in the words of the report, and what
 *  the service allows, as the server states it. */
export function LimitsSection({ config, method }: LimitsSectionProps): ReactElement {
  const report = method?.documents.find((document) => document.name === 'report')
  const limits = useMemo(() => (report ? sectionOfMarkdown(report.markdown, (heading) => LIMITS.test(heading)) : null), [report])
  return (
    <>
      <h3>Of the measures</h3>
      {limits && report ? (
        <Disclosure title="What the probes were not measured on, and what their numbers do not say" hint="from the report">
          <Markdown source={limits.body} base={report.path} ids="limits" shift={3} />
        </Disclosure>
      ) : (
        <p className="nm-method__empty">Not published yet: the limits the report of the probe campaign states for its own numbers.</p>
      )}
      <h3>Of the service</h3>
      <Part request={config} what="the limits of the service">
        {(data) => <LimitsTable limits={data.limits} />}
      </Part>
    </>
  )
}
