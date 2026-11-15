import type { ReactElement } from 'react'
import { Disclosure } from '../Disclosure'
import { LabelFacts } from '../labels/LabelFacts'
import { disagreed } from '../probeFiles'
import { stateWord, purposeWord } from '../words'
import { absenceOf } from './absence'
import { LevelCard } from './LevelCard'
import { ProbeActions } from './ProbeActions'
import { ProbeExtras } from './ProbeExtras'
import { ProbeMaking } from './ProbeMaking'
import type { ProbeRow } from './probeRows'
import { LEVELS } from './probeRows'
import type { ProbeSetting } from './setting'

interface ProbeDetailProps {
  row: ProbeRow
  setting: ProbeSetting
}

/** A probe opened: what it asks, what each level measured, how it was made, and the way to
 *  the posts it gets wrong. */
export function ProbeDetail({ row, setting }: ProbeDetailProps): ReactElement {
  const state = stateWord(row.state)
  const agreement = setting.files.agreement(row.key)
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
          {LEVELS.map((level) => (
            <LevelCard key={level} name={level} from={setting.starts?.[level] ?? null} level={row[level]} missing={absenceOf(row, level, setting.starts)?.long ?? ''} />
          ))}
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
