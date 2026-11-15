import type { ReactElement } from 'react'
import { VoicesMethod } from '../voices/VoicesMethod'
import { ApiReference } from './ApiReference'
import { Claims } from './Claims'
import { DatasetSection } from './dataset/DatasetSection'
import { DocumentsSection } from './documents/DocumentsSection'
import { Explorer } from './explorer/Explorer'
import { LabelsSection } from './labels/LabelsSection'
import { LimitsSection } from './LimitsSection'
import { Part, Unpublished } from './Part'
import { Glance } from './pipeline/Glance'
import { Pipeline } from './pipeline/Pipeline'
import { ProbesSection } from './probes/ProbesSection'
import { ReviewSection } from './review/ReviewSection'
import { Section } from './Section'
import { Traceability } from './Traceability'
import type { MethodData } from './useMethodData'

/** The sections of the page, in reading order. Each one says in a line or two what it holds,
 *  then lets the reader open what they want. */
export function MethodSections({ page }: { page: MethodData }): ReactElement {
  const { method, metrics, config, data, reports, files, starts, facts, probeKeys } = page
  const probes = metrics.status === 'ready' ? metrics.data.probes : []
  return (
    <>
      <Section id="overview" summary="A post goes through six stages, from its text to a verdict shown with its evidence. Each stage opens on what it does, what was measured, and its code.">
        {method.status === 'error' && !method.missing ? (
          <p className="nm-note nm-note--error" role="alert">
            The facts of this page could not be read from the server. {method.message}
          </p>
        ) : null}
        <Glance facts={facts} />
        <Pipeline facts={facts} />
      </Section>
      <Section id="dataset" summary="The demo shows real public posts from X. The corpus is a keyword sweep, not a random sample; the sample on the map keeps whole accounts, and says how they were drawn.">
        <Part request={method} what="the dataset">
          {(found) => <DatasetSection method={found} />}
        </Part>
      </Section>
      <Section id="labels" summary="Each label is one closed question, answered on the text alone by annotators who follow a written guide. The guides are shown here exactly as the annotators received them.">
        <Part request={method} what="the labels and their guides">
          {(found) => <LabelsSection method={found} probes={probeKeys} files={files} />}
        </Part>
      </Section>
      <Section id="probes" summary="One probe per label, or per answer of a label that has several, measured once on posts it never saw. Each is shown with its levels, what became of it, how it was made, and the way to the posts it gets wrong.">
        <Part request={metrics} what="the evaluation reports">
          {(measured) => <ProbesSection metrics={measured} reports={reports} method={data} files={files} starts={starts} />}
        </Part>
      </Section>
      <Section id="review" summary="A probe flags; an LLM reads again with the annotation guides and quotes the span that backs each reading. A quote that is not in the text is thrown away with its reading.">
        <Part request={method} what="the LLM review">
          {(found) => <ReviewSection method={found} reports={reports} />}
        </Part>
      </Section>
      <Section id="voices" summary="For a selection of actors: does each have a voice of its own, or could any post have come from any of them? A check on groups, with its own measured reliability.">
        <VoicesMethod />
      </Section>
      <Section id="explorer" summary="The posts the annotators read, with every reading, the settled answers and what the probes score on them now. Filter them, open one, or download them all.">
        <Part request={method} what="the labelled posts">
          {(found) => (found.labelled ? <Explorer method={found} summary={found.labelled} probes={probes} starts={starts} /> : <Unpublished what="the labelled posts" />)}
        </Part>
      </Section>
      <Section id="documents" summary="The report, the taxonomy and the journal of the probe campaign, readable here and linked to their source files at the deployed commit.">
        <Part request={method} what="the documents of the campaign">
          {(found) => <DocumentsSection method={found} />}
        </Part>
      </Section>
      <Section id="claims" summary="What the product never says, by design, and what it says in its place.">
        <Claims />
      </Section>
      <Section id="limits" summary="What the numbers of this page do not cover, and what the service allows.">
        <LimitsSection config={config} method={data} />
      </Section>
      <Section id="api" summary="One HTTP call stores a post and returns its scores and what surrounds it.">
        <ApiReference />
      </Section>
      <Section id="trace" summary="The exact version that is deployed, and the file behind every number of this page.">
        <Traceability method={data} reports={reports} />
      </Section>
    </>
  )
}
