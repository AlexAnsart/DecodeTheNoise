/* What the evaluation of the review says, put into the words of the page. Pure. */

import type { Rate, ReviewLabel, ReviewReport } from '../../api/reviewReportSchema'
import { formatCount } from '../../text/format'
import { formatInterval, formatRate } from '../figures'

/** From this many posts named by the review, the product shows a technique's own precision
 *  beside a reading. It mirrors `MIN_MARKED` of `backend/review/measures.py`, which no route
 *  serves. */
export const OWN_FIGURE_FROM = 20

export const known = (value: number | null | undefined): value is number => value !== null && value !== undefined

export const counted = (value: number | null | undefined): string => (known(value) ? formatCount(value) : '–')

/** "78% (73% to 82.4%)", or the words for a rate the report does not hold. */
export function rateWords(rate: Rate | null | undefined): string {
  return rate ? `${formatRate(rate.value)} (${formatInterval(rate.low, rate.high)})` : 'not measured'
}

/** Why a technique has counts and no rate. */
export function noRateReason(label: ReviewLabel): string {
  return label.measurable === false ? 'annotators agree too little' : 'too few posts'
}

/** The techniques whose own precision the product shows beside a reading. */
export function ownFigures(report: ReviewReport): [name: string, precision: Rate][] {
  return Object.entries(report.labels).flatMap(([name, label]): [string, Rate][] =>
    label.measurable !== false && label.precision && known(label.marked) && label.marked >= OWN_FIGURE_FROM ? [[name, label.precision]] : [],
  )
}

/** The evaluation in one sentence, for the pipeline at a glance. */
export function headline(report: ReviewReport): string {
  const posts = known(report.asked) ? `${formatCount(report.asked)} held-out posts` : 'held-out posts'
  const { pooled } = report
  const figures = pooled?.precision ? `: over the measurable techniques, precision ${rateWords(pooled.precision)} and recall ${rateWords(pooled.recall)}` : ', technique by technique'
  return `Its technique screen was compared with the annotation on ${posts}${figures}.`
}

/** Where the review was run, from what the report says of it. */
export function setting(report: ReviewReport): string {
  const posts = known(report.asked) ? `${formatCount(report.asked)} random posts` : 'random posts'
  const split = report.split ? ` of the ${report.split} split` : ''
  const accounts = known(report.accounts) ? `, written by ${formatCount(report.accounts)} accounts` : ', written by accounts'
  return `The review was run on ${posts}${split}${accounts} that neither the probes nor the guides saw while they were developed. Its technique screen is compared with the settled annotation, technique by technique.`
}
