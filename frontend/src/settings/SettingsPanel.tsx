import { KeyRound, Trash2 } from 'lucide-react'
import type { ReactElement } from 'react'
import { useAction, useRequest } from '../api/useRequest'
import { emptyWorkspace, fetchConfig, rotateKey } from '../api/workspace'
import type { WorkspaceInfo } from '../api/workspaceSchema'
import { SidePanel } from '../app/SidePanel'
import { ConfirmButton } from './ConfirmButton'
import { RefreshSetting } from './RefreshSetting'
import { ReviewSetting } from './ReviewSetting'
import { UsageMeters } from './UsageMeters'
import { useSettings } from './useSettings'
import './settings.css'

/** Where the levels start when the server has not said yet (backend/probes/schema.py). */
const POSSIBLE_SCORE = 0.5
const PROBABLE_SCORE = 0.8

interface SettingsPanelProps {
  apiKey: string
  info: WorkspaceInfo
  onInfo(info: WorkspaceInfo): void
  onNewKey(apiKey: string): void
  onClose(): void
}

/** The settings of the workspace: what is reviewed, how often topics refresh, its key, its data. */
export function SettingsPanel({ apiKey, info, onInfo, onNewKey, onClose }: SettingsPanelProps): ReactElement {
  const config = useRequest(fetchConfig)
  const saver = useSettings(apiKey, onInfo)
  const rotate = useAction(async () => onNewKey(await rotateKey(apiKey)))
  const empty = useAction(async () => onInfo(await emptyWorkspace(apiKey)))
  const ready = config.status === 'ready' ? config.data : null

  return (
    <SidePanel title="Workspace settings" onClose={onClose}>
      <section className="nm-block">
        <h3>
          LLM review
          {saver.saving ? <span className="nm-saved">Saving…</span> : saver.saved ? <span className="nm-saved nm-saved--ok">Saved</span> : null}
        </h3>
        <p>
          A probe flags a post. The review reads the flagged post again with its nearest posts. Scores are on one scale for every
          probe: {ready?.possible_score ?? POSSIBLE_SCORE} is possible, {ready?.probable_score ?? PROBABLE_SCORE} probable.
        </p>
        <ReviewSetting
          settings={info.settings}
          possibleScore={ready?.possible_score ?? POSSIBLE_SCORE}
          probableScore={ready?.probable_score ?? PROBABLE_SCORE}
          disabled={saver.saving}
          onSave={saver.save}
        />
        {ready && !ready.llm ? <p className="nm-note">No LLM is set up on this server: nothing is reviewed, whatever is chosen here.</p> : null}
      </section>
      <section className="nm-block">
        <h3>Topics</h3>
        <p>The layout, the topics and their names are computed again as posts arrive. New posts sit beside their neighbours until then.</p>
        <RefreshSetting
          every={info.settings.refresh_every}
          capacity={info.limits.items}
          disabled={saver.saving}
          onSave={(every) => saver.save({ refresh_every: every })}
        />
        {saver.error ? (
          <p className="nm-note nm-note--error" role="alert">
            Not saved. {saver.error}
          </p>
        ) : null}
      </section>
      <section className="nm-block">
        <h3>Usage</h3>
        <UsageMeters info={info} />
      </section>
      <section className="nm-block">
        <h3>Key and data</h3>
        <div className="nm-danger">
          <ConfirmButton
            label={
              <>
                <KeyRound size={12} aria-hidden />
                New key
              </>
            }
            question="The current key stops working at once. Every program that uses it needs the new one, and it is the only way into this workspace."
            confirm="Make a new key"
            busy={rotate.busy}
            busyLabel="Making a new key…"
            onConfirm={() => rotate.run()}
          />
          <ConfirmButton
            label={
              <>
                <Trash2 size={12} aria-hidden />
                Empty this workspace
              </>
            }
            question="Every post of this workspace is removed. The key and the settings stay."
            confirm="Empty it"
            busy={empty.busy}
            busyLabel="Emptying…"
            onConfirm={() => empty.run()}
          />
        </div>
        {rotate.error || empty.error ? (
          <p className="nm-note nm-note--error" role="alert">
            {rotate.error ?? empty.error}
          </p>
        ) : null}
      </section>
    </SidePanel>
  )
}
