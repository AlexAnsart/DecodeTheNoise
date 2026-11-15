import { ChevronLeft, ChevronRight, Download, X } from 'lucide-react'
import type { ReactElement } from 'react'
import { LABELLED_DOWNLOAD } from '../../api/method'
import type { LabelledPost, LabelledSummary, Method } from '../../api/methodSchema'
import type { ProbeInfo } from '../../api/workspaceSchema'
import { formatCount, plural } from '../../text/format'
import { NO_QUERY } from '../hash'
import type { ExplorerQuery } from '../hash'
import { useMethodShared } from '../MethodContext'
import type { LevelStarts } from '../probes/setting'
import { ExplorerFilters } from './ExplorerFilters'
import { KindSwitch } from './KindSwitch'
import { PostRow } from './PostRow'
import { PAGE_SIZE, useLabelled } from './useLabelled'
import './explorer.css'

/** A post read in two rounds appears once for each: the round is part of what names it. */
const keyOf = (post: LabelledPost): string => `${post.round}~${post.id}`

interface ExplorerProps {
  method: Method
  summary: LabelledSummary
  probes: ProbeInfo[]
  starts: LevelStarts | null
}

/** The posts the annotators read: filtered, paged, and each one opening on its readings. */
export function Explorer({ method, summary, probes, starts }: ExplorerProps): ReactElement {
  const { nav } = useMethodShared()
  const query = nav.target.kind === 'explorer' ? nav.target.query : NO_QUERY
  const { page, busy, error } = useLabelled(query)
  const change = (patch: Partial<ExplorerQuery>): void => nav.set({ kind: 'explorer', query: { ...query, offset: 0, post: '', ...patch } })
  const filtered = Object.entries(query).some(([name, value]) => name !== 'offset' && name !== 'post' && value !== '')
  const total = page?.total ?? 0
  const last = Math.min(total, query.offset + PAGE_SIZE)
  return (
    <div className="nm-explorer">
      <ExplorerFilters key={query.q} query={query} summary={summary} labels={method.labels} probes={probes} onChange={change} />
      <div className="nm-explorer__bar">
        <KindSwitch summary={summary} kind={query.kind} onKind={(kind) => change({ kind })} />
        <p className="nm-num" role="status">
          {busy ? 'Reading the posts…' : page ? `${plural(total, 'post matches', 'posts match')}, of ${formatCount(summary.posts)} read` : ''}
        </p>
        {filtered ? (
          <button type="button" className="nm-chip-btn" onClick={() => nav.set({ kind: 'explorer', query: NO_QUERY })}>
            <X size={11} aria-hidden />
            Clear the filters
          </button>
        ) : null}
        <a className="nm-btn-secondary nm-btn-small nm-explorer__download" href={LABELLED_DOWNLOAD} download title="Every labelled post with its readings, one JSON object per line">
          <Download size={12} aria-hidden />
          Download as JSON lines
        </a>
      </div>
      <p className="nm-note">
        Only posts drawn at random are a sample of the corpus. The others were searched for or drawn by score, to find rare labels: a count on this
        page is never a rate of the corpus.
      </p>
      {error ? (
        <p className="nm-note nm-note--error" role="alert">
          The posts could not be listed. {error}
        </p>
      ) : null}
      {page && page.posts.length > 0 ? (
        <ol className={`nm-posts${busy ? ' is-busy' : ''}`}>
          {page.posts.map((post) => (
            <PostRow
              key={keyOf(post)}
              post={post}
              open={query.post === keyOf(post)}
              focus={{ label: query.label, probe: query.probe }}
              starts={starts}
              onToggle={() => nav.set({ kind: 'explorer', query: { ...query, post: query.post === keyOf(post) ? '' : keyOf(post) } })}
            />
          ))}
        </ol>
      ) : null}
      {page && page.posts.length === 0 && !error ? <p className="nm-method__empty">No labelled post matches these filters.</p> : null}
      {total > PAGE_SIZE ? (
        <nav className="nm-explorer__pages nm-num" aria-label="Pages of the list">
          <button type="button" className="nm-btn-secondary nm-btn-small" disabled={query.offset === 0 || busy} onClick={() => change({ offset: Math.max(0, query.offset - PAGE_SIZE) })}>
            <ChevronLeft size={12} aria-hidden />
            Previous
          </button>
          <span>
            {formatCount(query.offset + 1)} to {formatCount(last)} of {formatCount(total)}
          </span>
          <button type="button" className="nm-btn-secondary nm-btn-small" disabled={last >= total || busy} onClick={() => change({ offset: query.offset + PAGE_SIZE })}>
            Next
            <ChevronRight size={12} aria-hidden />
          </button>
        </nav>
      ) : null}
    </div>
  )
}
