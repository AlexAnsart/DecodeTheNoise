/* One line per probe: what the evaluation report measured, joined with how the probe is named
   and what its label asks. Pure. */

import type { LabelDoc } from '../../api/methodSchema'
import type { Interval, LevelReport, ProbesReport, TargetReport } from '../../api/reportSchema'
import type { LevelMeasure, ProbeInfo } from '../../api/workspaceSchema'
import { labelOf, readable } from '../words'

/** A measured rate. The interval is null when only the value was published. */
export interface Rate {
  value: number
  low: number | null
  high: number | null
}

export interface LevelView {
  precision: Rate | null
  recall: Rate | null
  falsePositives: Rate | null
  prevalence: Rate | null
  /** Share of the test split flagged at this level, and how many posts that is. */
  flagRate: number | null
  flagged: number | null
  /** Flagged posts that were read, and how many of them the annotators settled as yes. */
  read: number | null
  positives: number | null
  /** The cut on the raw output of the probe. */
  threshold: number | null
  /** Base rate of the label, to the precision the level would have there. */
  baseRates: [rate: number, precision: number][]
}

export interface ProbeRow {
  key: string
  name: string
  question: string | null
  family: string | null
  use: string | null
  /** shown, review-only, dropped; null when the probe has no evaluation. */
  state: string | null
  /** The server scores posts with it. */
  served: boolean
  possible: LevelView | null
  probable: LevelView | null
  /** Average precision over chance on the random test sample; null without enough positives. */
  lift: number | null
  report: TargetReport | null
}

const rate = (interval: Interval | null | undefined): Rate | null => interval ?? null

function fromReport(level: LevelReport | undefined): LevelView | null {
  if (!level) return null
  return {
    precision: rate(level.precision),
    recall: rate(level.recall),
    falsePositives: rate(level.fpr),
    prevalence: rate(level.prevalence),
    flagRate: level.flag_rate ?? null,
    flagged: level.flagged ?? null,
    read: level.read_flagged ?? null,
    positives: level.positive_flagged ?? null,
    threshold: level.threshold ?? null,
    baseRates: Object.entries(level.precision_at_base_rate ?? {})
      .map(([base, precision]): [number, number] => [Number(base), precision])
      .filter(([base]) => Number.isFinite(base))
      .sort(([a], [b]) => a - b),
  }
}

/** What the server publishes with a probe it serves: less than the report, enough for a line. */
function fromInfo(measure: LevelMeasure | null): LevelView | null {
  if (!measure) return null
  const bare = (value: number | null): Rate | null => (value === null ? null : { value, low: null, high: null })
  return {
    precision: { value: measure.precision, low: measure.precision_low, high: measure.precision_high },
    recall: bare(measure.recall),
    falsePositives: bare(measure.false_positive_rate),
    prevalence: null,
    flagRate: measure.flag_rate,
    flagged: null,
    read: measure.read,
    positives: null,
    threshold: null,
    baseRates: [],
  }
}

/** Two levels cut at the same place are one level. Without the cuts (the report did not
 *  read), the same measures at both levels say the same thing. */
function sameCut(a: LevelView, b: LevelView): boolean {
  if (a.threshold !== null && b.threshold !== null) return a.threshold === b.threshold
  return a.flagRate === b.flagRate && a.read === b.read && a.precision?.value === b.precision?.value
}

/** A probe with one cut has one level, probable: a score under it has no name for that probe,
 *  so nothing is said of a "possible" level it does not have. */
function levelsOf(possible: LevelView | null, probable: LevelView | null): Pick<ProbeRow, 'possible' | 'probable'> {
  if (possible && probable && sameCut(possible, probable)) return { possible: null, probable }
  return { possible, probable }
}

function liftOf(target: TargetReport | undefined): number | null {
  const ranking = target?.ranking
  if (!ranking || ranking.average_precision === undefined || !ranking.chance) return null
  return ranking.average_precision / ranking.chance
}

/** Every probe of the report in its order, then the probes served that the report does not
 *  hold. Without a report, the probes served alone. */
export function probeRows(infos: ProbeInfo[], report: ProbesReport | null, labels: LabelDoc[]): ProbeRow[] {
  const targets = report?.targets ?? {}
  const keys = [...Object.keys(targets), ...infos.map((info) => info.key).filter((key) => !(key in targets))]
  return keys.map((key) => {
    const info = infos.find((probe) => probe.key === key)
    const target = targets[key]
    const doc = labels.find((label) => label.name === labelOf(key))
    return {
      key,
      name: info?.label ?? readable(key),
      question: doc?.question ?? info?.description ?? null,
      family: doc?.family ?? info?.family ?? null,
      use: doc?.use ?? null,
      state: target?.state ?? info?.state ?? null,
      served: info !== undefined,
      ...(target
        ? levelsOf(fromReport(target.levels?.possible), fromReport(target.levels?.probable))
        : levelsOf(fromInfo(info?.possible ?? null), fromInfo(info?.probable ?? null))),
      lift: liftOf(target),
      report: target ?? null,
    }
  })
}

/** The deepest level a probe keeps: the one that flags most. */
export function widestLevel(row: ProbeRow): LevelView | null {
  return row.possible ?? row.probable
}
