import { Bot, Play, SquareTerminal } from 'lucide-react'
import { useId, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { agentPrompt, curlExample } from './apiReference'
import { CopyBlock } from './CopyBlock'
import { SampleSender } from './SampleSender'
import type { SampleSender as Sender } from './useSampleSender'
import './connect.css'

type Way = 'agent' | 'curl' | 'sample'

const WAYS: { id: Way; label: string; icon: typeof Bot }[] = [
  { id: 'agent', label: 'Coding agent', icon: Bot },
  { id: 'curl', label: 'curl', icon: SquareTerminal },
  { id: 'sample', label: 'No code', icon: Play },
]

interface SendTabsProps {
  apiKey: string
  /** The workspace: the prompt states its batch limit, the sample shows its embedding. */
  info: WorkspaceInfo
  live: boolean
  sender: Sender
}

/** Three ways to send posts: hand a prompt to a coding agent, run one command, or press a button. */
export function SendTabs({ apiKey, info, live, sender }: SendTabsProps): ReactElement {
  const [way, setWay] = useState<Way>('agent')
  const id = useId()
  const origin = window.location.origin
  const batchItems = info.limits.batch_items
  const prompt = useMemo(() => agentPrompt(origin, apiKey, batchItems), [origin, apiKey, batchItems])
  const curl = useMemo(() => curlExample(origin, apiKey), [origin, apiKey])

  return (
    <div className="nm-send">
      <div className="nm-segmented nm-segmented--wide" role="tablist" aria-label="How to send posts">
        {WAYS.map(({ id: key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`${id}-${key}`}
            aria-selected={way === key}
            aria-controls={`${id}-panel`}
            className={way === key ? 'is-active' : ''}
            onClick={() => setWay(key)}
          >
            <Icon size={13} aria-hidden />
            {label}
          </button>
        ))}
      </div>
      <div className="nm-send__panel" role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${way}`}>
        {way === 'agent' ? (
          <>
            <p>Paste this prompt into your coding agent. It holds the address, the fields and your key.</p>
            <CopyBlock text={prompt} what="the prompt" />
          </>
        ) : null}
        {way === 'curl' ? (
          <>
            <p>One post from a terminal. The answer holds its scores and what surrounds it.</p>
            <CopyBlock text={curl} what="the command" />
          </>
        ) : null}
        {way === 'sample' ? <SampleSender sender={sender} info={info} live={live} /> : null}
      </div>
    </div>
  )
}
