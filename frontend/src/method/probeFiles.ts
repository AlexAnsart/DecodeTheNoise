/* The other files of the probe evaluation (`reports/probes/*.json`), served as they were
   written. Each entry is read on its own and leniently: a file that is absent or changed gives
   null, and the page says "not published". Pure. */

import type { z } from 'zod'
import { agreementSchema, calibrationSchema, diagnosticsSchema, prevalenceSchema, trainingSchema } from '../api/reportSchema'
import type { Agreement, Calibration, Diagnostics, Prevalence, Training } from '../api/reportSchema'
import { labelOf } from './words'

/** Under this kappa the report does not take a label as a reference (its section on limits). */
const AGREEMENT_FLOOR = 0.5

export interface ProbeFiles {
  /** The names of the files served, for the traceability table. */
  names: string[]
  /** By label: `theme:sport` reads the agreement of `theme`. */
  agreement(key: string): Agreement | null
  prevalence(key: string): Prevalence | null
  /** By probe. */
  training(key: string): Training | null
  diagnostics(key: string): Diagnostics | null
  calibration(key: string): Calibration | null
}

function tableOf(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function readProbeFiles(files: Record<string, unknown>): ProbeFiles {
  const entry = <T>(table: unknown, key: string, schema: z.ZodType<T>): T | null => {
    const parsed = schema.safeParse(tableOf(table)[key])
    return parsed.success ? parsed.data : null
  }
  return {
    names: Object.keys(files),
    agreement: (key) => entry(files.agreement, labelOf(key), agreementSchema),
    prevalence: (key) => entry(files.prevalence, key, prevalenceSchema) ?? entry(files.prevalence, labelOf(key), prevalenceSchema),
    training: (key) => entry(tableOf(files.train).targets, key, trainingSchema),
    diagnostics: (key) => entry(files.diagnostics, key, diagnosticsSchema),
    calibration: (key) => entry(files.thresholds, key, calibrationSchema),
  }
}

/** The annotators themselves disagree on the label: nothing measured against their answers is
 *  a reliability. The kappa is compared as it is printed, to two decimals. */
export function disagreed(agreement: Agreement | null): boolean {
  const kappa = agreement?.kappa
  return kappa !== null && kappa !== undefined && Math.round(kappa * 100) / 100 < AGREEMENT_FLOOR
}
