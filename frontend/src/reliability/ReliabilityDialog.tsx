import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { createPortal } from 'react-dom'
import { fetchMetrics } from '../api/client'
import type { DetectorMetrics } from '../api/schema'
import { logger } from '../log/logger'
import { DetectorReport } from './DetectorReport'
import './reliability.css'

const log = logger('reliability')

type Load = { status: 'loading' } | { status: 'ready'; detectors: DetectorMetrics[] } | { status: 'error' }

/** The Reliability view: what every detector of the product measured to be, read from the
 *  evaluation reports. Nothing here is typed by hand. */
export function ReliabilityDialog({ onClose }: { onClose(): void }): ReactElement {
  const [load, setLoad] = useState<Load>({ status: 'loading' })

  useEffect(() => {
    const abort = new AbortController()
    fetchMetrics(abort.signal)
      .then((detectors) => setLoad({ status: 'ready', detectors }))
      .catch((error: unknown) => {
        if (abort.signal.aborted) return
        log.error('the evaluation reports could not be read', error)
        setLoad({ status: 'error' })
      })
    return () => abort.abort()
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      onClose()
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [onClose])

  return createPortal(
    <div className="nm-reliability" onPointerDown={(event) => (event.target === event.currentTarget ? onClose() : undefined)}>
      <section className="nm-reliability__panel" role="dialog" aria-modal aria-label="Reliability">
        <header className="nm-reliability__head">
          <div>
            <h2>Reliability</h2>
            <p>What each detector measured to be, on data it was not tuned on. A layer is shown only with its report.</p>
          </div>
          <button type="button" className="nm-drawer__icon" onClick={onClose} title="Close" aria-label="Close">
            <X size={15} aria-hidden />
          </button>
        </header>
        <div className="nm-reliability__body">
          {load.status === 'loading' ? <p className="nm-item-state">Reading the reports…</p> : null}
          {load.status === 'error' ? <p className="nm-item-state nm-item-state--error">The reports could not be read.</p> : null}
          {load.status === 'ready' && load.detectors.length === 0 ? (
            <p className="nm-item-state">No detector is shown yet: a layer appears only once its evaluation report exists.</p>
          ) : null}
          {load.status === 'ready' ? load.detectors.map((metrics) => <DetectorReport key={metrics.detector} metrics={metrics} />) : null}
        </div>
      </section>
    </div>,
    document.body,
  )
}
