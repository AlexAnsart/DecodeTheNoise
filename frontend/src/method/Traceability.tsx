import { ExternalLink } from 'lucide-react'
import type { ReactElement, ReactNode } from 'react'
import type { Method } from '../api/methodSchema'
import type { Reports } from './reports'
import { reportPath } from './reports'
import { SourceLink } from './SourceLink'

interface TraceabilityProps {
  method: Method | null
  reports: Reports
}

/** One fact of the deployed version. Without a value, it says that it is not published. */
function Fact({ name, children }: { name: string; children: ReactNode }): ReactElement {
  return (
    <div>
      <dt>{name}</dt>
      <dd className="nm-num">{children ?? <span className="nm-facts__none">not published</span>}</dd>
    </div>
  )
}

function Paths({ paths }: { paths: string[] }): ReactElement {
  return (
    <ul className="nm-sources">
      {paths.map((path) => (
        <li key={path}>
          <SourceLink path={path} />
        </li>
      ))}
    </ul>
  )
}

/** What exactly is deployed, and the file behind every number of the page: the commit, the
 *  build, the key of the vectors, the run of the probes, the model and the prompt of the review. */
export function Traceability({ method, reports }: TraceabilityProps): ReactElement {
  const build = method?.build
  const review = method?.review
  const files = Object.keys(method?.probe_files ?? {})
  return (
    <dl className="nm-facts nm-facts--wide">
      <Fact name="Source">
        {method ? (
          <a className="nm-link" href={`${method.repository.replace(/\/+$/, '')}/tree/${method.commit}`} target="_blank" rel="noopener noreferrer">
            {method.repository.replace(/^https?:\/\//, '')} at {method.commit.slice(0, 12)} <ExternalLink size={11} aria-hidden />
          </a>
        ) : null}
      </Fact>
      <Fact name="Demo build">{build ? `${build.name}, built ${build.built_at}` : null}</Fact>
      <Fact name="Key of the vectors">{build?.embedding_key}</Fact>
      <Fact name="Run of the probes">{reports.probes?.run}</Fact>
      <Fact name="Vectors the probes were measured on">{reports.probes?.model_key}</Fact>
      <Fact name="Rounds the probes were measured on">{reports.probes?.rounds?.join(', ')}</Fact>
      <Fact name="Model of the review">{review ? (review.model ?? 'none set up on this server') : null}</Fact>
      <Fact name="Prompts of the review">{review ? `${review.prompt_version} for one post, ${review.selection_prompt_version} for a selection` : null}</Fact>
      <Fact name="Evaluation reports">{reports.detectors.length > 0 ? <Paths paths={reports.detectors.map(reportPath)} /> : null}</Fact>
      <Fact name="Other files of the probe evaluation">{files.length > 0 ? <Paths paths={files.map((file) => `reports/probes/${file}.json`)} /> : null}</Fact>
      <Fact name="Code of every step">
        <Paths paths={['pipelines/', 'backend/', 'frontend/src/']} />
      </Fact>
    </dl>
  )
}
