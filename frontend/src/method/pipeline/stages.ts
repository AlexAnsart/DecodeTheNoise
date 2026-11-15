/* The stages a post goes through, from its text to a verdict. The sentences are written here;
   every number and every name of a model comes from the server. */

import { BadgeCheck, Binary, FileText, Map, MessageSquareQuote, ScanSearch } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { formatCount } from '../../text/format'
import type { Target } from '../hash'
import { headline } from '../review/evaluation'
import type { Facts } from './facts'
import { probeCounts } from './facts'

export interface Stage {
  id: string
  icon: LucideIcon
  title: string
  /** What the stage does, in a few words: read on its card. */
  line: string
  /** One fact from the server, on the card; null while it is not known. */
  fact: string | null
  does: string[]
  /** A value that is null is said "not published". */
  parameters: [name: string, value: string | null][]
  measured: string
  /** Where the page says more about the stage. */
  more: { label: string; target: Target } | null
  code: string[]
}

const count = (value: number | undefined): string | null => (value === undefined ? null : formatCount(value))

export function stagesOf(facts: Facts): Stage[] {
  const { method, reports, starts } = facts
  const build = method?.build ?? null
  const review = method?.review ?? null
  const probes = probeCounts(facts)
  return [
    {
      id: 'post',
      icon: FileText,
      title: 'Post',
      line: 'A text, with its author and its date kept beside it.',
      fact: build ? `${formatCount(build.points)} posts on the demo map` : null,
      does: [
        'A post is read as its text. Its author, its date and its links are kept beside it and are never part of what the model reads: a probe cannot learn who wrote a post.',
        'A text too short to carry a meaning is not placed on the map: the answer is "not enough evidence", not a guess.',
      ],
      parameters: [
        ['Dataset', method?.provenance?.dataset ?? null],
        ['Demo build', build?.name ?? null],
        ['Built', build?.built_at ?? null],
      ],
      measured: 'Nothing is measured at this stage. Where the posts come from, and how the demo sample was drawn, is in the dataset section.',
      more: { label: 'The dataset', target: { kind: 'section', section: 'dataset' } },
      code: ['pipelines/ingest/', 'backend/ingest/'],
    },
    {
      id: 'vector',
      icon: Binary,
      title: 'Vector',
      line: 'EmbeddingGemma turns the text into a vector of meaning.',
      fact: build ? `${formatCount(build.dims)} dimensions` : null,
      does: [
        'An open-weight embedding model, EmbeddingGemma, turns each text into a vector: two texts that mean the same thing get close vectors, whatever words they use.',
        'The same weights embed the corpus offline and a post sent live, so the two can be compared. The key below names the model, its revision, the prefix and the dimensions kept; it travels with every vector and every probe, and a probe is never applied to vectors of another key.',
      ],
      parameters: [
        ['Embedding key', build?.embedding_key ?? null],
        ['Dimensions kept', count(build?.dims)],
      ],
      measured: 'The report of the probe campaign compares the vector size that is served with smaller ones, and a linear read-out with other readers of the same vector.',
      more: { label: 'The report', target: { kind: 'doc', name: 'report' } },
      code: ['pipelines/embed/', 'backend/model_client/embedding.py'],
    },
    {
      id: 'map',
      icon: Map,
      title: 'Map and zones',
      line: 'Posts that mean the same sit together; zones name the subjects.',
      fact: build ? `${formatCount(build.zones)} zones` : null,
      does: [
        'UMAP gives each vector a place in three dimensions and in two, so that close meanings sit together. The nearest neighbours of a post are computed on the vectors themselves, not on the layout.',
        'Zones are clusters of the vectors. Each is described by the words that set it apart, then named by an LLM that reads those words and a few of its posts: the name says what the posts are about, never whether they are true or who wrote them.',
      ],
      parameters: [
        ['Points', count(build?.points)],
        ['Zones', count(build?.zones)],
      ],
      measured: 'No accuracy is claimed for the layout or for the zones. The layout is a display, not a measure: two points close on the map prove nothing by themselves.',
      more: null,
      code: ['pipelines/layout/', 'pipelines/neighbours/', 'pipelines/zones/', 'backend/map/'],
    },
    {
      id: 'probes',
      icon: ScanSearch,
      title: 'Probes',
      line: 'Small linear read-outs of the vector, one per label.',
      fact: probes ? `${formatCount(probes.shown)} shown, ${formatCount(probes.reviewOnly)} review only` : null,
      does: [
        'A probe is a linear classifier on the vector: standardise, one dot product, a bias. It costs nothing next to the embedding, so every post gets a score from every probe.',
        'Each probe answers one closed question, learnt from posts that annotators labelled by following a written guide. Its score is put on one scale for every probe, cut in two levels: possible, then probable.',
      ],
      parameters: [
        ['Run', reports.probes?.run ?? null],
        ['Labels annotated', count(method?.labels.length)],
        ['Posts read by annotators', count(method?.labelled?.posts)],
        ['Probes measured', count(probes?.measured)],
        ['Vectors', reports.probes?.model_key ?? null],
      ],
      measured: 'Each probe is measured once, at thresholds frozen beforehand, on a test split it never touched: precision with its interval, recall and false-positive rate, level by level.',
      more: { label: 'Probes and their reliability', target: { kind: 'section', section: 'probes' } },
      code: ['pipelines/probes/', 'backend/probes/', 'reports/probes/metrics.json'],
    },
    {
      id: 'review',
      icon: MessageSquareQuote,
      title: 'LLM review',
      line: 'An LLM reads again what a probe flags, and quotes its evidence.',
      fact: review ? (review.model ?? 'No model set up') : null,
      does: [
        'A probe flags; the review reads again. The model gets the flagged post, the question of each probe that flagged it, its nearest posts and other posts of the same actor, as context only.',
        'It answers each question with the exact span of the post that shows it, and names the manipulation techniques it finds, each with its quote. A quote that is not in the text is dropped.',
      ],
      parameters: [
        ['Model', review ? (review.model ?? 'none set up on this server') : null],
        ['Prompt version', review?.prompt_version ?? null],
        ['Techniques screened', count(review?.techniques.length)],
      ],
      measured: reports.review
        ? headline(reports.review)
        : 'Not measured yet: until the review has its own evaluation report, every reading it gives is marked as not measured.',
      more: { label: 'The LLM review', target: { kind: 'section', section: 'review' } },
      code: ['backend/review/', 'pipelines/review/', 'reports/review/metrics.json'],
    },
    {
      id: 'verdict',
      icon: BadgeCheck,
      title: 'Verdict',
      line: 'A label, a level, the evidence, and how reliable it measured to be.',
      fact: starts ? `possible from ${starts.possible}, probable from ${starts.probable}` : null,
      does: [
        'What the interface shows is never a bare score. A verdict is a label, a level, the evidence, and the measured reliability of what produced it.',
        'There are three outcomes, not two: flagged, not flagged, and not enough evidence.',
      ],
      parameters: [
        ['Possible starts at a score of', starts ? String(starts.possible) : null],
        ['Probable starts at a score of', starts ? String(starts.probable) : null],
      ],
      measured: 'The reliability beside a verdict is read from the evaluation reports: no number of the interface is typed by hand.',
      more: { label: 'What NoiseMap does not claim', target: { kind: 'section', section: 'claims' } },
      code: ['backend/probes/schema.py', 'backend/review/schema.py', 'frontend/src/probes/'],
    },
  ]
}
