/* The sections of the method page, in reading order: the title each one carries, and the
   shorter name the table of contents gives it. */

import type { SectionId } from './hash'

export interface SectionDoc {
  id: SectionId
  title: string
  short: string
}

export const SECTIONS: SectionDoc[] = [
  { id: 'overview', title: 'The method at a glance', short: 'At a glance' },
  { id: 'dataset', title: 'The dataset', short: 'Dataset' },
  { id: 'labels', title: 'Labels and annotation', short: 'Labels and annotation' },
  { id: 'probes', title: 'Probes and their reliability', short: 'Probes and scores' },
  { id: 'review', title: 'The LLM review', short: 'LLM review' },
  { id: 'voices', title: 'One voice or several: the check and its reliability', short: 'One voice or several' },
  { id: 'explorer', title: 'The labelled posts', short: 'Labelled posts' },
  { id: 'documents', title: 'Documents', short: 'Documents' },
  { id: 'claims', title: 'What NoiseMap does not claim', short: 'What it does not claim' },
  { id: 'limits', title: 'Limits', short: 'Limits' },
  { id: 'api', title: 'The API', short: 'API' },
  { id: 'trace', title: 'Traceability', short: 'Traceability' },
]
