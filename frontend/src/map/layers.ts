/* The WebGL layers of the map, rebuilt from typed arrays. Order: axes, edges, points, rings. */

import type { Layer } from '@deck.gl/core'
import { DataFilterExtension } from '@deck.gl/extensions'
import { LineLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers'
import type { Rgb } from '../theme/theme'

export type Vec3 = [number, number, number]

export interface Segment {
  from: Vec3
  to: Vec3
  /** The point at the far end. */
  index: number
}

export interface AxisLine {
  path: Vec3[]
  major: boolean
}

export interface Ring {
  position: Vec3
  /** Radius in pixels. */
  radius: number
  filled: boolean
}

export interface LayerInput {
  n: number
  positions: Float32Array
  colours: Uint8Array
  kept: Float32Array
  /** Typical distance between neighbours in this shape: the point radius derives from it. */
  gap: number
  flat: boolean
  segments: Segment[]
  rings: Ring[]
  axes: AxisLine[]
  accent: Rgb
  muted: Rgb
  highlight: Rgb
}

export const POINTS_LAYER = 'points'
export const EDGES_LAYER = 'edges'

const RADIUS_SHARE = 0.32
const RADIUS_MIN_PX = 1.6
const RADIUS_MAX_PX = 8

export function buildLayers(input: LayerInput): Layer[] {
  const { accent, muted, highlight } = input
  return [
    new PathLayer<AxisLine>({
      id: 'axes',
      data: input.axes,
      getPath: (line) => line.path,
      getColor: (line) => [muted[0], muted[1], muted[2], line.major ? 200 : 150],
      getWidth: (line) => (line.major ? 1.5 : 1),
      widthUnits: 'pixels',
      billboard: true,
    }),
    new LineLayer<Segment>({
      id: EDGES_LAYER,
      data: input.segments,
      getSourcePosition: (segment) => segment.from,
      getTargetPosition: (segment) => segment.to,
      getColor: [accent[0], accent[1], accent[2], 200],
      getWidth: 2,
      widthUnits: 'pixels',
      pickable: true,
    }),
    new ScatterplotLayer({
      id: POINTS_LAYER,
      data: {
        length: input.n,
        attributes: {
          getPosition: { value: input.positions, size: 3 },
          getFillColor: { value: input.colours, size: 4, normalized: true },
          getFilterValue: { value: input.kept, size: 1 },
        },
      },
      getRadius: 1,
      radiusUnits: 'common',
      radiusScale: input.gap * RADIUS_SHARE,
      radiusMinPixels: RADIUS_MIN_PX,
      radiusMaxPixels: RADIUS_MAX_PX,
      billboard: !input.flat,
      pickable: true,
      autoHighlight: true,
      highlightColor: [highlight[0], highlight[1], highlight[2], 200],
      // A filtered point is neither drawn nor pickable, and no buffer is rebuilt for it.
      extensions: [new DataFilterExtension({ filterSize: 1 })],
      filterRange: [0.5, 1],
    }),
    new ScatterplotLayer<Ring>({
      id: 'rings',
      data: input.rings,
      getPosition: (ring) => ring.position,
      getRadius: (ring) => ring.radius,
      radiusUnits: 'pixels',
      stroked: true,
      filled: true,
      getFillColor: (ring) => [accent[0], accent[1], accent[2], ring.filled ? 50 : 0],
      getLineColor: [accent[0], accent[1], accent[2], 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      billboard: !input.flat,
    }),
  ]
}
