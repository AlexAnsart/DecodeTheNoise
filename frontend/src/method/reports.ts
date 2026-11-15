/* The evaluation reports the page reads its numbers from, picked out of what
   `GET /api/metrics` serves. A report that is absent, or does not read as expected, is null:
   the page then says "not measured" instead of showing a number. */

import { probesReportSchema } from '../api/reportSchema'
import type { ProbesReport } from '../api/reportSchema'
import { reviewReportSchema } from '../api/reviewReportSchema'
import type { ReviewReport } from '../api/reviewReportSchema'
import type { Metrics } from '../api/workspaceSchema'

export interface Reports {
  probes: ProbesReport | null
  review: ReviewReport | null
  /** Every report served, by the folder it lives in under `reports/`. */
  detectors: string[]
}

export const NO_REPORTS: Reports = { probes: null, review: null, detectors: [] }

export function readReports(metrics: Metrics): Reports {
  const of = (detector: string): unknown => metrics.reports.find((report) => report.detector === detector)?.metrics
  const probes = probesReportSchema.safeParse(of('probes'))
  const review = reviewReportSchema.safeParse(of('review'))
  return {
    probes: probes.success ? probes.data : null,
    // The review report is read field by field, so anything reads: one without a technique measured nothing.
    review: review.success && Object.keys(review.data.labels).length > 0 ? review.data : null,
    detectors: metrics.reports.map((report) => report.detector),
  }
}

/** The file a report is read from, in the repository. */
export function reportPath(detector: string): string {
  return `reports/${detector}/metrics.json`
}
