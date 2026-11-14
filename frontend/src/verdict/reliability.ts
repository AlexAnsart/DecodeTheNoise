/* How a measured rate is written, wherever a verdict or a report shows one. */

import type { DetectorMetrics, Measure } from '../api/schema'
import { formatCount, formatRate } from '../text/format'

/** `0.4% (95% interval 0.1% to 1.2%, n = 1,140)`. */
export function describeRate(measure: Pick<Measure, 'value' | 'low' | 'high' | 'n'>): string {
  const interval =
    measure.low !== null && measure.high !== null
      ? `95% interval ${formatRate(measure.low)} to ${formatRate(measure.high)}, `
      : ''
  return `${formatRate(measure.value)} (${interval}n = ${formatCount(measure.n)})`
}

/** The lines every verdict of a detector carries: how often it is wrong on controls, and how
 *  much of what it looks for it finds. */
export function reliabilityLines(metrics: DetectorMetrics): string[] {
  return ['false_positive_rate', 'recall']
    .map((kind) => metrics.results.find((measure) => measure.kind === kind))
    .filter((measure) => measure !== undefined)
    .map((measure) => `${measure.name}: ${describeRate(measure)}`)
}
