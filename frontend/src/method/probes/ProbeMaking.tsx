import type { ReactElement } from 'react'
import type { Diagnostics, Training } from '../../api/reportSchema'
import { formatCount } from '../../text/format'
import { formatNumber, formatRate } from '../figures'
import type { ProbeFiles } from '../probeFiles'
import { reportPath } from '../reports'
import { SourceLink } from '../SourceLink'
import { CalibrationTable } from './CalibrationTable'

const known = (value: number | null | undefined): value is number => value !== null && value !== undefined

/** "64: 0.41 · 128: 0.50": a table of the evaluation written on one line, smallest key first. */
function series(values: Record<string, number | null> | undefined, name: (key: number) => string): string | null {
  const points = Object.entries(values ?? {})
    .map(([key, value]): [number, number | null] => [Number(key), value])
    .filter((point): point is [number, number] => Number.isFinite(point[0]) && point[1] !== null)
    .sort(([a], [b]) => a - b)
  return points.length > 0 ? points.map(([key, value]) => `${name(key)}: ${formatNumber(value)}`).join(' · ') : null
}

function TrainingLine({ training }: { training: Training }): ReactElement {
  return (
    <li>
      <strong>Fitted on</strong> {known(training.n) ? formatCount(training.n) : 'an unpublished number of'} labelled posts of the train split
      {known(training.positives) ? `, ${formatCount(training.positives)} of them a yes` : ''}
      {known(training.c) ? `, with a regularisation strength of ${formatNumber(training.c)}` : ''}.
      {known(training.oof_ap) ? ` Average precision on posts of actors it had not seen, inside train: ${formatNumber(training.oof_ap)}.` : ''}
    </li>
  )
}

function ReadersLine({ diagnostics }: { diagnostics: Diagnostics }): ReactElement | null {
  const readers: [name: string, value: number | null | undefined][] = [
    ['linear probe', diagnostics.linear],
    ['nearest centroid', diagnostics.centroid],
    ['k nearest neighbours', diagnostics.knn],
    ['small neural network', diagnostics.mlp],
  ]
  const read = readers.filter((reader): reader is [string, number] => known(reader[1]))
  if (read.length === 0) return null
  return (
    <li>
      <strong>Other readers of the same vector</strong> (average precision
      {known(diagnostics.chance) ? `, ${formatNumber(diagnostics.chance)} by chance` : ''}): {read.map(([name, value]) => `${name} ${formatNumber(value)}`).join(' · ')}.
    </li>
  )
}

interface ProbeMakingProps {
  probe: string
  files: ProbeFiles
}

/** How a probe was made: what it was fitted on, how other readers of the same vector do, and
 *  how its thresholds were placed. Each line is read from a file of the evaluation. */
export function ProbeMaking({ probe, files }: ProbeMakingProps): ReactElement | null {
  const training = files.training(probe)
  const diagnostics = files.diagnostics(probe)
  const calibration = files.calibration(probe)
  if (!training && !diagnostics && !calibration) return null
  const sizes = series(diagnostics?.dims, (dims) => `${dims} dimensions`)
  const curve = series(diagnostics?.learning_curve, (share) => `${formatRate(share)} of the train posts`)
  return (
    <div className="nm-probe-making">
      <ul className="nm-probe-extras nm-num">
        {training ? <TrainingLine training={training} /> : null}
        {diagnostics ? <ReadersLine diagnostics={diagnostics} /> : null}
        {sizes ? (
          <li>
            <strong>By size of the vector</strong> (average precision): {sizes}.
          </li>
        ) : null}
        {curve ? (
          <li>
            <strong>With less data</strong> (average precision): {curve}.
          </li>
        ) : null}
      </ul>
      {calibration ? <CalibrationTable calibration={calibration} /> : null}
      <p className="nm-note">
        Read from <SourceLink path={reportPath('probes').replace('metrics.json', '')} />: the files the evaluation wrote beside its metrics.
      </p>
    </div>
  )
}
