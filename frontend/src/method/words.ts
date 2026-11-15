/* The words of the method page for what a label is for and what became of its probe. They
   follow docs/probes/taxonomy.md and the report of the probe campaign. */

export interface Word {
  label: string
  meaning: string
}

export const NOT_EVALUATED: Word = {
  label: 'Not evaluated',
  meaning: 'No probe of this label was measured: nothing is shown or flagged from it.',
}

const STATES: Record<string, Word> = {
  shown: {
    label: 'Shown',
    meaning: 'Shown on the map: at least one of its levels passed the bar on the test split, so a hit appears with what that level measured.',
  },
  'review-only': {
    label: 'Review only',
    meaning: 'Used only to send posts to the LLM review: under the bar for a verdict, but it ranks its label far above chance. It never appears as a hit.',
  },
  dropped: {
    label: 'Dropped',
    meaning: 'Dropped: no level passed the bar, and it does not rank its label far enough above chance to be worth a review.',
  },
}

/** The states a probe can end in, in the order the report lists them. */
export const PROBE_STATES = Object.keys(STATES)

const USES: Record<string, Word> = {
  probe: { label: 'Probe', meaning: 'A candidate detector on single posts.' },
  descriptor: { label: 'Descriptor', meaning: 'Describes a group or splits a measure. Never a verdict on one post.' },
  llm_test: { label: 'LLM test', meaning: 'Too rare or too relational for a probe: kept to test the LLM review.' },
  auxiliary: { label: 'Auxiliary', meaning: 'Explains errors, or triggers abstention.' },
}

export function stateWord(state: string | null): Word {
  if (state === null) return NOT_EVALUATED
  return STATES[state] ?? { label: readable(state), meaning: '' }
}

export function purposeWord(use: string): Word {
  return USES[use] ?? { label: readable(use), meaning: '' }
}

/** `call_amplify` as "Call amplify", `theme:sport` as "Theme: sport". */
export function readable(name: string): string {
  const words = name.replace(/_/g, ' ').replace(/:/g, ': ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** The label a probe reads: `theme:sport` is a value of the label `theme`. */
export function labelOf(key: string): string {
  return key.split(':')[0]
}
