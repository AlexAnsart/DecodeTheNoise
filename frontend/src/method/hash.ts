/* What the address of the method page points at: a section, or one thing opened in it. The
   part after `#` is the only state of what is open, so any view of the page can be linked. */

export const SECTION_IDS = [
  'overview',
  'dataset',
  'labels',
  'probes',
  'review',
  'voices',
  'explorer',
  'documents',
  'claims',
  'limits',
  'api',
  'trace',
] as const

export type SectionId = (typeof SECTION_IDS)[number]

/** The filters of the labelled posts, and the post opened among them. Empty: not filtered. */
export interface ExplorerQuery {
  label: string
  answer: string
  split: string
  round: string
  kind: string
  probe: string
  level: string
  q: string
  offset: number
  post: string
}

export const NO_QUERY: ExplorerQuery = { label: '', answer: '', split: '', round: '', kind: '', probe: '', level: '', q: '', offset: 0, post: '' }

export type Target =
  | { kind: 'section'; section: SectionId }
  /** A stage of the pipeline, opened under the row of stages. */
  | { kind: 'stage'; id: string }
  | { kind: 'label'; name: string }
  | { kind: 'probe'; key: string }
  /** A document read in full over the page: an annotation guide, the report, a figure. */
  | { kind: 'guide'; name: string }
  | { kind: 'doc'; name: string }
  | { kind: 'figure'; name: string }
  | { kind: 'explorer'; query: ExplorerQuery }

const OPENED = ['stage', 'label', 'probe', 'guide', 'doc', 'figure'] as const
type Opened = (typeof OPENED)[number]

function isSection(value: string): value is SectionId {
  return (SECTION_IDS as readonly string[]).includes(value)
}

function decoded(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    // A hand-written address with a stray "%": taken as it is.
    return value
  }
}

function queryOf(params: URLSearchParams): ExplorerQuery {
  const text = (name: string): string => params.get(name) ?? ''
  const offset = Number(params.get('offset') ?? 0)
  return {
    label: text('label'),
    answer: text('answer'),
    split: text('split'),
    round: text('round'),
    kind: text('kind'),
    probe: text('probe'),
    level: text('level'),
    q: text('q'),
    offset: Number.isInteger(offset) && offset > 0 ? offset : 0,
    post: text('post'),
  }
}

/** `probe-call_amplify`, `guide-calls`, `explorer?probe=…&level=missed`, or a section id. An
 *  address that names nothing known is the top of the page. */
export function parseHash(hash: string): Target {
  const [head, query = ''] = hash.split('?')
  if (head === 'explorer') return { kind: 'explorer', query: queryOf(new URLSearchParams(query)) }
  const dash = head.indexOf('-')
  if (dash !== -1) {
    const kind = OPENED.find((name) => name === head.slice(0, dash))
    const rest = decoded(head.slice(dash + 1))
    if (kind && rest) return opened(kind, rest)
  }
  return { kind: 'section', section: isSection(head) ? head : 'overview' }
}

function opened(kind: Opened, value: string): Target {
  if (kind === 'stage') return { kind, id: value }
  if (kind === 'probe') return { kind, key: value }
  return { kind, name: value }
}

export function hashOf(target: Target): string {
  switch (target.kind) {
    case 'section':
      return target.section
    case 'stage':
      return `stage-${encodeURIComponent(target.id)}`
    case 'probe':
      return `probe-${encodeURIComponent(target.key)}`
    case 'label':
    case 'guide':
    case 'doc':
    case 'figure':
      return `${target.kind}-${encodeURIComponent(target.name)}`
    case 'explorer': {
      const params = new URLSearchParams()
      for (const [name, value] of Object.entries(target.query)) {
        if (value !== '' && value !== 0) params.set(name, String(value))
      }
      const query = params.toString()
      return query ? `explorer?${query}` : 'explorer'
    }
  }
}

/** The section a target lives in. */
export function sectionOf(target: Target): SectionId {
  switch (target.kind) {
    case 'section':
      return target.section
    case 'stage':
      return 'overview'
    case 'label':
    case 'guide':
      return 'labels'
    case 'probe':
    case 'figure':
      return 'probes'
    case 'doc':
      return 'documents'
    case 'explorer':
      return 'explorer'
  }
}

/** The element of the page to bring into view for a target. */
export function anchorOf(target: Target): string {
  if (target.kind === 'probe') return `probe-${target.key}`
  if (target.kind === 'label') return `label-${target.name}`
  if (target.kind === 'stage') return 'pipeline'
  return sectionOf(target)
}
