import { ArrowRight, ExternalLink } from 'lucide-react'
import type { ReactElement } from 'react'
import type { Method } from '../../api/methodSchema'
import { Link } from '../../route/Link'
import { PATHS } from '../../route/useRoute'
import { formatCount, plural } from '../../text/format'
import { Disclosure } from '../Disclosure'
import { Unpublished } from '../Part'
import { DrawnSample } from './DrawnSample'
import { SampleFacts } from './SampleFacts'

const IS = [
  'Public posts from X, collected by sweeping a vocabulary of search terms.',
  'Real posts by real actors. Account identifiers are hashed before they reach this site.',
  'Unlabelled: nothing in it says what a post is. Every label used here was made for this project.',
]

const IS_NOT = [
  'Not a random sample of X: a keyword sweep holds part of each actor and part of each campaign.',
  'Not a ground truth: no post is marked as coordinated, automated or false.',
  'Not even over time: volumes follow the collection, so a period is read as a share, not as a count.',
]

/** Where the posts of the demo come from, what that corpus is and is not, and how the sample
 *  on the map was drawn from it. */
export function DatasetSection({ method }: { method: Method }): ReactElement {
  const { provenance, build } = method
  if (!provenance) return <Unpublished what="the provenance of the demo dataset" />
  return (
    <>
      <dl className="nm-facts nm-facts--wide">
        <div>
          <dt>Source</dt>
          <dd>
            {provenance.source_url ? (
              <a className="nm-link" href={provenance.source_url} target="_blank" rel="noopener noreferrer">
                {provenance.dataset ?? provenance.source_url}
                <ExternalLink size={11} aria-hidden />
              </a>
            ) : (
              (provenance.dataset ?? 'not published')
            )}
          </dd>
        </div>
        <div>
          <dt>Revision</dt>
          <dd className="nm-num">{provenance.revision ?? 'not stated'}</dd>
        </div>
        <div>
          <dt>Licence</dt>
          <dd>{provenance.licence ?? 'Not stated: the dataset gives no licence, so no post of it is committed to the repository.'}</dd>
        </div>
        {build ? (
          <div>
            <dt>On the demo map</dt>
            <dd className="nm-num">
              {formatCount(build.points)} posts, build {build.name}
            </dd>
          </div>
        ) : null}
      </dl>
      {provenance.files.length > 0 ? (
        <Disclosure title="Files read from the dataset" hint={plural(provenance.files.length, 'file', 'files')}>
          <ul className="nm-files nm-num">
            {provenance.files.map((file) => (
              <li key={file}>{file}</li>
            ))}
          </ul>
        </Disclosure>
      ) : null}
      <div className="nm-two">
        <div>
          <h3>What the corpus is</h3>
          <ul>
            {IS.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>What it is not</h3>
          <ul>
            {IS_NOT.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      </div>
      <h3>How the demo sample was drawn</h3>
      <p>
        The demo keeps whole actors: when an actor is drawn, every post it has in the files above is on the map, so what one actor wrote can be read
        together and set against the others.
      </p>
      <DrawnSample sample={provenance.sample} />
      <SampleFacts sample={provenance.sample} />
      <Link to={PATHS.demo} className="nm-btn-primary nm-btn-small nm-method__cta">
        Explore it on the map
        <ArrowRight size={13} aria-hidden />
      </Link>
    </>
  )
}
