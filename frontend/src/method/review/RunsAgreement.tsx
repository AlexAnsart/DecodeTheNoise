import type { ReactElement } from 'react'
import type { ReviewRuns } from '../../api/reviewReportSchema'
import { formatCount } from '../../text/format'
import { known, rateWords } from './evaluation'

interface RunsAgreementProps {
  runs: ReviewRuns
  /** The temperature the review is asked at, when the report says it. */
  temperature: number | null | undefined
}

/** The same posts asked twice with the cache off: how often the review answers the same. */
export function RunsAgreement({ runs, temperature }: RunsAgreementProps): ReactElement {
  const asked = known(runs.asked) ? `The same ${formatCount(runs.asked)} posts` : 'The same posts'
  const both = known(runs.posts) ? `Of the ${formatCount(runs.posts)} read both times` : 'Of the posts read both times'
  const decisions = known(runs.decisions) ? `the ${formatCount(runs.decisions)} decisions on a post and a technique` : 'the decisions on a post and a technique'
  const heat = known(temperature) ? `, even at temperature ${temperature}` : ''
  return (
    <p className="nm-num">
      {asked} were sent twice with the cache off, same model and same prompt. {both}, {rateWords(runs.same_posts)} got the same list of techniques,
      and {rateWords(runs.same_decisions)} of {decisions} were the same. The review does not answer the same way every time{heat}. In the product an
      answer is cached, so a post that was reviewed keeps its reading.
    </p>
  )
}
