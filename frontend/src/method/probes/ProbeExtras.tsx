import type { ReactElement } from 'react'
import type { TargetReport } from '../../api/reportSchema'
import { formatCount } from '../../text/format'
import { formatLift, formatNumber, formatRate } from '../figures'

const LANGUAGES: Record<string, string> = { en: 'English', de: 'German', other: 'Other languages' }

function share(part: number, whole: number): string {
  return whole > 0 ? ` (${formatRate(part / whole)})` : ''
}

function Ranking({ ranking, lift }: { ranking: NonNullable<TargetReport['ranking']>; lift: number | null }): ReactElement {
  const sample = ranking.n !== undefined ? `${formatCount(ranking.n)} random test posts` : 'the random test sample'
  const positives = ranking.positives !== undefined ? `, ${formatCount(ranking.positives)} of them a yes` : ''
  if (ranking.average_precision === undefined || ranking.chance === undefined) {
    return (
      <li>
        <strong>Ranking.</strong> Not computed: {sample}
        {positives}, which is too few positives for an average precision.
      </li>
    )
  }
  return (
    <li>
      <strong>Ranking.</strong> Average precision {formatNumber(ranking.average_precision)} on {sample}
      {positives}, against {formatNumber(ranking.chance)} by chance: {formatLift(lift)} chance.
    </li>
  )
}

interface ProbeExtrasProps {
  report: TargetReport
  lift: number | null
  /** The levels the probe keeps: nothing is said of a level it does not have. */
  levels: string[]
}

/** What the report holds about a probe beyond its two levels: how it ranks, what a second
 *  reader said of its labels, how it does by language, and what was withdrawn. */
export function ProbeExtras({ report, lift, levels }: ProbeExtrasProps): ReactElement {
  const { audit, head } = report
  const withdrawn = Object.entries(report.withdrawn ?? {})
  const languages = Object.entries(report.by_language ?? {}).filter(([level]) => levels.includes(level))
  const [confirmed, yes] = audit?.yes ?? []
  const [overturned, no] = audit?.no ?? []
  return (
    <ul className="nm-probe-extras nm-num">
      {report.ranking ? <Ranking ranking={report.ranking} lift={lift} /> : null}
      {yes !== undefined && confirmed !== undefined ? (
        <li>
          <strong>Second reader.</strong> A stronger model read test posts again with the same guide: it confirmed {formatCount(confirmed)} of{' '}
          {formatCount(yes)} settled yes answers{share(confirmed, yes)}
          {no !== undefined && overturned !== undefined ? ` and overturned ${formatCount(overturned)} of ${formatCount(no)} settled no answers${share(overturned, no)}` : ''}.
        </li>
      ) : null}
      {report.demoted ? (
        <li>
          <strong>Not shown.</strong> It passed the bar and was withdrawn after the {report.demoted}.
        </li>
      ) : null}
      {withdrawn.map(([level, measure]) => (
        <li key={level}>
          <strong>Level withdrawn on test: {level}.</strong> It met its target on calibration, then measured a precision of{' '}
          {formatRate(measure.precision?.value ?? null)} on test, under the bar.
        </li>
      ))}
      {head ? (
        <li>
          <strong>Head of its scores.</strong> It has no threshold. Among its highest-scored test posts,{' '}
          {head.positive_flagged !== undefined && head.read_flagged !== undefined
            ? `${formatCount(head.positive_flagged)} of the ${formatCount(head.read_flagged)} read are a yes${share(head.positive_flagged, head.read_flagged)}.`
            : 'the share of yes was not published.'}
        </li>
      ) : null}
      {languages.map(([level, byLanguage]) => (
        <li key={level}>
          <strong>By language, {level}.</strong>{' '}
          {Object.entries(byLanguage)
            .map(([language, [positives = 0, read = 0]]) => `${LANGUAGES[language] ?? language}: ${formatCount(positives)} yes of ${formatCount(read)} read`)
            .join('; ')}
          .
        </li>
      ))}
    </ul>
  )
}
