/* What every line of the table of probes is drawn with. */

import type { ProbeFiles } from '../probeFiles'

/** Where the two levels start on the score scale, the same for every probe. */
export interface LevelStarts {
  possible: number
  probable: number
}

export interface ProbeSetting {
  /** Null while the server has not said where the levels start. */
  starts: LevelStarts | null
  /** The labelled posts are published: the mistakes of a served probe can be listed. */
  explorable: boolean
  /** The other files of the evaluation: agreement, prevalence, training, calibration. */
  files: ProbeFiles
}
