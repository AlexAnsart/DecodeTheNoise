/* One deck.gl instance inside a div, driven imperatively: React does not render per frame. */

import { Deck } from '@deck.gl/core'
import type { OrbitView, OrthographicView, PickingInfo, Viewport } from '@deck.gl/core'
import { useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { logger } from '../log/logger'
import type { Shape } from './geometry'
import type { Size, ViewState } from './views'
import { readView, viewFor } from './views'

const log = logger('map')
const MAX_LOGGED_ERRORS = 50
/** Names of the renderers that draw on the CPU: the browser has no hardware acceleration. */
const SOFTWARE_RENDERER = /swiftshader|basic render|llvmpipe|software/i

/** The map has one view at a time: flat or in depth. */
export type MapDeck = Deck<OrbitView | OrthographicView>

/** The viewport of the current frame. Null until WebGL has started: asking earlier throws. */
export function currentViewport(deck: MapDeck | null): Viewport | null {
  if (!deck || !deck.isInitialized) return null
  return deck.getViewports()[0] ?? null
}

export interface DeckEvents {
  onView(view: ViewState): void
  onHover(info: PickingInfo): void
  /** After each frame: the moment to place the HTML that follows a point. */
  onFrame(): void
  cursor(state: { isDragging: boolean; isHovering: boolean }): string
}

export interface DeckHost {
  deck: RefObject<MapDeck | null>
  size: Size | null
  /** True when WebGL could not start: the stage shows a sentence instead of a blank canvas. */
  failed: boolean
}

export function useDeck(host: RefObject<HTMLDivElement | null>, shape: Shape, events: DeckEvents): DeckHost {
  const deck = useRef<MapDeck | null>(null)
  const latest = useRef(events)
  const opening = useRef(shape)
  const [size, setSize] = useState<Size | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    latest.current = events
  })

  useEffect(() => {
    const parent = host.current
    if (!parent) return undefined
    const seen = new Set<string>()
    try {
      deck.current = new Deck<OrbitView | OrthographicView>({
        parent,
        // A view of the right kind from the first frame: the default one is a geographic map.
        views: viewFor(opening.current),
        viewState: { target: [0, 0, 0], zoom: 0 },
        style: { position: 'absolute', inset: '0' },
        layers: [],
        pickingRadius: 5,
        onViewStateChange: ({ viewState }) => latest.current.onView(readView(viewState)),
        onHover: (info) => latest.current.onHover(info),
        onAfterRender: () => latest.current.onFrame(),
        getCursor: (state) => latest.current.cursor(state),
        onResize: ({ width, height }) => setSize({ width, height }),
        // The styles adapt to a browser that composes the page on the CPU (theme/base.css).
        onDeviceInitialized: (device) =>
          document.documentElement.classList.toggle('is-software', SOFTWARE_RENDERER.test(device.info.renderer)),
        onError: (error) => {
          const message = error?.message ?? 'unknown rendering error'
          if (/webgl/i.test(message)) setFailed(true)
          if (!seen.has(message) && seen.size < MAX_LOGGED_ERRORS) {
            seen.add(message)
            log.error(message)
          }
        },
      })
    } catch (error) {
      log.error('the canvas could not start', error)
      setFailed(true)
      return undefined
    }
    return () => {
      deck.current?.finalize()
      deck.current = null
    }
  }, [host])

  return { deck, size, failed }
}
