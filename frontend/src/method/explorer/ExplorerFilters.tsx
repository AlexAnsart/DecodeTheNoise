import { Search } from 'lucide-react'
import { useState } from 'react'
import type { ReactElement } from 'react'
import type { LabelDoc, LabelledSummary } from '../../api/methodSchema'
import type { ProbeInfo } from '../../api/workspaceSchema'
import { formatCount } from '../../text/format'
import type { ExplorerQuery } from '../hash'
import { readable } from '../words'
import { CLOSED_ANSWERS, LEVELS } from './explorerWords'

interface ExplorerFiltersProps {
  query: ExplorerQuery
  summary: LabelledSummary
  labels: LabelDoc[]
  /** The probes the server scores posts with. */
  probes: ProbeInfo[]
  onChange(patch: Partial<ExplorerQuery>): void
}

/** The labels that have a settled answer, by family when the families are published. */
function labelGroups(summary: LabelledSummary, labels: LabelDoc[]): [family: string, names: string[]][] {
  const groups = new Map<string, string[]>()
  for (const name of summary.labels) {
    const family = labels.find((label) => label.name === name)?.family ?? 'labels'
    groups.set(family, [...(groups.get(family) ?? []), name])
  }
  return [...groups.entries()]
}

/** Narrows the labelled posts: by label and answer, by where they come from, by words, and by
 *  a probe set against the annotation. */
export function ExplorerFilters({ query, summary, labels, probes, onChange }: ExplorerFiltersProps): ReactElement {
  const [words, setWords] = useState(query.q)
  const own = labels.find((label) => label.name === query.label)?.values.filter((value) => !CLOSED_ANSWERS.includes(value)) ?? []
  const shown = probes.filter((probe) => probe.state === 'shown')
  return (
    <div className="nm-explorer__filters">
      <label>
        <span>Label</span>
        <select className="nm-field" value={query.label} onChange={(event) => onChange({ label: event.target.value, answer: event.target.value ? query.answer || 'yes' : '' })}>
          <option value="">Any label</option>
          {labelGroups(summary, labels).map(([family, names]) => (
            <optgroup key={family} label={readable(family)}>
              {names.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      <label>
        <span>Settled answer</span>
        <select className="nm-field" value={query.answer} disabled={!query.label} onChange={(event) => onChange({ answer: event.target.value })}>
          <option value="">Any answer</option>
          {[...CLOSED_ANSWERS, ...own].map((answer) => (
            <option key={answer} value={answer}>
              {answer}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Probe</span>
        <select className="nm-field" value={query.probe} disabled={shown.length === 0} onChange={(event) => onChange({ probe: event.target.value, level: event.target.value ? query.level : '' })}>
          <option value="">{shown.length === 0 ? 'No probe is served' : 'No probe'}</option>
          {shown.map((probe) => (
            <option key={probe.key} value={probe.key}>
              {probe.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Against the annotation</span>
        <select className="nm-field" value={query.level} disabled={!query.probe} onChange={(event) => onChange({ level: event.target.value })} title={LEVELS.find((level) => level.value === query.level)?.meaning}>
          <option value="">Its highest scores first</option>
          {LEVELS.map((level) => (
            <option key={level.value} value={level.value}>
              {level.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Split</span>
        <select className="nm-field" value={query.split} onChange={(event) => onChange({ split: event.target.value })}>
          <option value="">Every split</option>
          {Object.entries(summary.splits).map(([split, count]) => (
            <option key={split} value={split}>
              {split} ({formatCount(count)})
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Round</span>
        <select className="nm-field" value={query.round} onChange={(event) => onChange({ round: event.target.value })}>
          <option value="">Every round</option>
          {summary.rounds.map((round) => (
            <option key={round} value={round}>
              {round}
              {summary.round_kinds[round] && summary.round_kinds[round] !== 'annotation' ? ` (${summary.round_kinds[round]})` : ''}
            </option>
          ))}
        </select>
      </label>
      <form
        className="nm-explorer__words"
        onSubmit={(event) => {
          event.preventDefault()
          onChange({ q: words.trim() })
        }}
      >
        <label>
          <span>Words in the text</span>
          <input className="nm-field" type="search" value={words} onChange={(event) => setWords(event.target.value)} placeholder="every word must be there" />
        </label>
        <button type="submit" className="nm-btn-secondary nm-btn-small" disabled={words.trim() === query.q}>
          <Search size={12} aria-hidden />
          Search
        </button>
      </form>
    </div>
  )
}
