import type { ReactElement } from 'react'
import type { Voices } from '../api/voicesSchema'
import { formatCount } from '../text/format'

type Reliability = NonNullable<Voices['reliability']>

/** What the check measured to be worth on groups it never saw: how often it cries wolf on
 *  real actors, and how many groups written from one brief it catches. */
export function VoicesTrust({ reliability }: { reliability: Reliability }): ReactElement {
  const { false_alarms, real_groups, hard_false_alarms, hard_real_groups, caught, one_brief_groups } = reliability
  return (
    <div className="nm-voices__trust">
      <p className="nm-voices__label">How far to trust this</p>
      <p>
        On real groups of independent actors, this check gave a false alarm for{' '}
        <b className="nm-num">
          {formatCount(false_alarms)} of {formatCount(real_groups)}
        </b>{' '}
        (
        <span className="nm-num">
          {formatCount(hard_false_alarms)} of {formatCount(hard_real_groups)}
        </span>{' '}
        when the actors are the most alike). It caught{' '}
        <b className="nm-num">
          {formatCount(caught)} of {formatCount(one_brief_groups)}
        </b>{' '}
        groups written from one brief.{' '}
        <a className="nm-link" href="/method#voices">
          How it is measured
        </a>
      </p>
    </div>
  )
}
