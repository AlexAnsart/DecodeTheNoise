import type { ReactElement } from 'react'
import { Disclosure } from '../Disclosure'
import { LabelFacts } from '../labels/LabelFacts'
import { disagreed } from '../probeFiles'
import { stateWord, purposeWord } from '../words'
import { LevelCard } from './LevelCard'
import { ProbeActions } from './ProbeActions'
import { ProbeExtras } from './ProbeExtras'
import { ProbeMaking } from './ProbeMaking'
import type { ProbeRow } from './probeRows'
import type { ProbeSetting } from './setting'

/** Why a level is absent, in the place where its measures would be. */
function missing(row: ProbeRow, setting: ProbeSetting): { possible: string; probable: string } {
  const { starts } = setting
  const between = starts ? `a score between ${starts.possible} and ${starts.probable}` : 'a score under probable'
  return {
    possible: row.probable
      ? `This probe has one level, probable: ${between} has no name for it, and nothing is flagged there.`
      : 'No threshold reached the precision asked of this level.',
    probable: 'No threshold reached the precision asked of this level: the probe stops at possible.',
  }
}

interface ProbeDetailProps {
  row: ProbeRow
  setting: ProbeSetting
}

/** A probe opened: what it asks, what each level measured, how it was made, and the way to
 *  the posts it gets wrong. */
export function ProbeDetail({ row, setting }: ProbeDetailProps): ReactElement {
  const state = stateWord(row.state)
  const agreement = setting.files.agreement(row.key)
  const why = missing(row, setting)
  return (
    <div className="nm-probe-detail">
      <div className="nm-probe-detail__about">
        <p className="nm-probe-detail__question">{row.question ?? 'The question of this label was not published.'}</p>
        <p>
          {state.meaning}
          {row.use ? ` Use of the label: ${purposeWord(row.use).label.toLowerCase()}. ${purposeWord(row.use).meaning}` : ''}
        </p>
        <ProbeActions row={row} explorable={setting.explorable} />
      </div>
      <LabelFacts agreement={agreement} prevalence={setting.files.prevalence(row.key)} />
      {disagreed(agreement) ? null : row.possible || row.probable ? (
        <div className="nm-probe-detail__levels">
          <LevelCard name="Possible" from={setting.starts?.possible ?? null} level={row.possible} missing={why.possible} />
          <LevelCard name="Probable" from={setting.starts?.probable ?? null} level={row.probable} missing={why.probable} />
        </div>
      ) : (
        <p className="nm-method__empty">This probe has no level: no score of it is ever shown as a hit.</p>
      )}
      {row.report ? <ProbeExtras report={row.report} lift={row.lift} levels={[row.possible ? 'possible' : '', row.probable ? 'probable' : '']} /> : <p className="nm-note">The evaluation report holds no detail for this probe.</p>}
      <Disclosure title="How it was made" hint="training, other readers, thresholds">
        {setting.files.training(row.key) || setting.files.diagnostics(row.key) || setting.files.calibration(row.key) ? (
          <ProbeMaking probe={row.key} files={setting.files} />
        ) : (
          <p className="nm-method__empty">Not published yet: the files of the evaluation that say how this probe was fitted and calibrated.</p>
        )}
      </Disclosure>
    </div>
  )
}
