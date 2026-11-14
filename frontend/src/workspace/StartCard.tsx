import { ArrowRight, KeyRound, Radio, Zap } from 'lucide-react'
import type { ReactElement } from 'react'
import { useAction, useRequest } from '../api/useRequest'
import { createWorkspace, fetchConfig } from '../api/workspace'
import type { WorkspaceCreated } from '../api/workspaceSchema'
import { formatCount } from '../text/format'
import './workspace.css'

const GAINS = [
  { icon: Zap, text: 'One HTTP call per post. Its scores and what surrounds it come back at once.' },
  { icon: Radio, text: 'Your map builds live, and its topics are named as posts arrive.' },
  { icon: KeyRound, text: 'Free, with nothing to sign up for. Your API key stays in this browser.' },
]

interface StartCardProps {
  /** Why the person is back here, when a key was forgotten. */
  notice: string | null
  onCreated(created: WorkspaceCreated): void
}

/** No workspace in this browser yet: one click makes one. */
export function StartCard({ notice, onCreated }: StartCardProps): ReactElement {
  const config = useRequest(fetchConfig)
  const create = useAction(async () => onCreated(await createWorkspace()))

  return (
    <div className="nm-page">
      <section className="nm-start" aria-labelledby="nm-start-title">
        {notice ? (
          <p className="nm-start__notice" role="status">
            {notice}
          </p>
        ) : null}
        <p className="nm-eyebrow">Through our API</p>
        <h1 id="nm-start-title">Map your own posts</h1>
        <p className="nm-start__lead">
          A workspace is your private map. It starts empty and grows with every post you send.
        </p>
        <ul className="nm-start__gains">
          {GAINS.map(({ icon: Icon, text }) => (
            <li key={text}>
              <Icon size={15} aria-hidden />
              {text}
            </li>
          ))}
        </ul>
        <button type="button" className="nm-btn-primary nm-start__create" onClick={() => create.run()} disabled={create.busy}>
          {create.busy ? 'Creating your workspace…' : 'Create my workspace'}
          {create.busy ? null : <ArrowRight size={15} aria-hidden />}
        </button>
        {create.error ? (
          <p className="nm-note nm-note--error" role="alert">
            {create.error}
          </p>
        ) : null}
        {config.status === 'ready' ? (
          <p className="nm-note nm-num">
            Up to {formatCount(config.data.limits.items)} posts in a workspace, {formatCount(config.data.limits.batch_items)} per batch call.
          </p>
        ) : null}
      </section>
    </div>
  )
}
