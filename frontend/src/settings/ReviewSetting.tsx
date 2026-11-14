import { useState } from 'react'
import type { ReactElement } from 'react'
import type { ReviewMode, SettingsPatch, WorkspaceSettings } from '../api/workspaceSchema'

const MODES: { id: ReviewMode; label: string }[] = [
  { id: 'off', label: 'Off' },
  { id: 'probable', label: 'Probable' },
  { id: 'possible', label: 'Possible and above' },
  { id: 'score', label: 'Custom score' },
]
const SCORE_STEP = 0.05

interface ReviewSettingProps {
  settings: WorkspaceSettings
  /** Where the two levels start on the score scale, the same for every probe. */
  possibleScore: number
  probableScore: number
  disabled: boolean
  onSave(patch: SettingsPatch): void
}

function meaning(mode: ReviewMode, score: number, possible: number, probable: number): string {
  if (mode === 'off') return 'No post is sent to the review.'
  if (mode === 'probable') return `Posts a probe finds probable (score ${probable} or more) are reviewed.`
  if (mode === 'possible') return `Posts a probe finds possible or probable (score ${possible} or more) are reviewed.`
  return `Posts with a score of ${score.toFixed(2)} or more are reviewed.`
}

/** Which flagged posts an LLM reads again. One scale for every probe, so one setting is enough. */
export function ReviewSetting({ settings, possibleScore, probableScore, disabled, onSave }: ReviewSettingProps): ReactElement {
  // The slider moves freely; the value is saved when it is released.
  const [draft, setDraft] = useState<number | null>(null)
  const score = draft ?? settings.review_min_score
  const commit = (): void => {
    if (draft !== null && draft !== settings.review_min_score) onSave({ review_min_score: draft })
    setDraft(null)
  }
  return (
    <>
      <div className="nm-segmented nm-segmented--wide nm-review-modes" role="group" aria-label="Which flagged posts are reviewed">
        {MODES.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={settings.review_mode === id ? 'is-active' : ''}
            aria-pressed={settings.review_mode === id}
            disabled={disabled}
            onClick={() => settings.review_mode !== id && onSave({ review_mode: id })}
          >
            {label}
          </button>
        ))}
      </div>
      {settings.review_mode === 'score' ? (
        <label className="nm-slider">
          <span>Review from</span>
          <input
            type="range"
            min={0}
            max={1}
            step={SCORE_STEP}
            value={score}
            disabled={disabled}
            onChange={(event) => setDraft(Number(event.target.value))}
            onPointerUp={commit}
            onKeyUp={commit}
            onBlur={commit}
            aria-label="Lowest score sent to the review"
          />
          <output className="nm-num">{score.toFixed(2)}</output>
        </label>
      ) : null}
      <p className="nm-note">{meaning(settings.review_mode, score, possibleScore, probableScore)}</p>
    </>
  )
}
