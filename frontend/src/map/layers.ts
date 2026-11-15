/* The WebGL layers of the map, rebuilt from typed arrays. Order: axes, edges, points, rings. */

import type { Layer } from '@deck.gl/core'
import { DataFilterExtension } from '@deck.gl/extensions'
import { LineLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers'
import type { Rgb } from '../theme/theme'
import { gatherBytes, gatherFloats } from './sample'

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
  /** Fill: none, a tint of the accent, or the accent itself. */
  fill: 'none' | 'tint' | 'solid'
}

export interface ExtraPoint {
  position: Vec3
  colour: [number, number, number, number]
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
  /** The points drawn, in ascending order, where the browser draws in software; null draws
   *  every point. */
  sample: Uint32Array | null
  /** The GPU says which point is under the pointer and highlights it. False in software,
   *  where a picking pass costs as much as a frame: picking is then done on the CPU. */
  gpuPicking: boolean
  /** A point that is not part of the map data, drawn with the same size rule as the others. */
  extra: ExtraPoint | null
  axes: AxisLine[]
  accent: Rgb
  muted: Rgb
  highlight: Rgb
}

export const POINTS_LAYER = 'points'
export const EDGES_LAYER = 'edges'

interface Attribute {
  value: Float32Array | Uint8Array
  size: number
  normalized?: boolean
}

const attributes = new WeakMap<object, Attribute>()

/** The descriptor deck.gl reads an attribute from. It uploads an attribute again whenever its
 *  descriptor is another object, so one typed array always gets the same descriptor: a hover,
 *  a selection or a ring upload nothing, and a new colouring uploads the colours alone. On a
 *  map of half a million points that is 10 MB not sent to the GPU on every pointer move. */
function attribute(value: Float32Array | Uint8Array, size: number, normalized = false): Attribute {
  let kept = attributes.get(value)
  if (!kept || kept.size !== size) {
    kept = normalized ? { value, size, normalized } : { value, size }
    attributes.set(value, kept)
  }
  return kept
}

const gathered = new WeakMap<object, { sample: Uint32Array; rows: Float32Array | Uint8Array }>()

/** The rows of a per-point array for the sampled points, gathered once per array and sample. */
function sampled<T extends Float32Array | Uint8Array>(values: T, sample: Uint32Array | null, width: number): T {
  if (!sample) return values
  const kept = gathered.get(values)
  if (kept && kept.sample === sample) return kept.rows as T
  const rows = values instanceof Float32Array ? gatherFloats(values, sample, width) : gatherBytes(values, sample, width)
  gathered.set(values, { sample, rows })
  return rows as T
}

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
      pickable: input.gpuPicking,
    }),
    new ScatterplotLayer({
      id: POINTS_LAYER,
      data: {
        length: input.sample ? input.sample.length : input.n,
        attributes: {
          getPosition: attribute(sampled(input.positions, input.sample, 3), 3),
          getFillColor: attribute(sampled(input.colours, input.sample, 4), 4, true),
          getFilterValue: attribute(sampled(input.kept, input.sample, 1), 1),
        },
      },
      getRadius: 1,
      radiusUnits: 'common',
      radiusScale: input.gap * RADIUS_SHARE,
      radiusMinPixels: RADIUS_MIN_PX,
      radiusMaxPixels: RADIUS_MAX_PX,
      billboard: !input.flat,
      pickable: input.gpuPicking,
      autoHighlight: input.gpuPicking,
      highlightColor: [highlight[0], highlight[1], highlight[2], 200],
      // A filtered point is neither drawn nor pickable, and no buffer is rebuilt for it.
      extensions: [new DataFilterExtension({ filterSize: 1 })],
      filterRange: [0.5, 1],
    }),
    new ScatterplotLayer<ExtraPoint>({
      id: 'extra',
      data: input.extra ? [input.extra] : [],
      getPosition: (point) => point.position,
      getFillColor: (point) => point.colour,
      getRadius: 1,
      radiusUnits: 'common',
      radiusScale: input.gap * RADIUS_SHARE,
      radiusMinPixels: RADIUS_MIN_PX,
      radiusMaxPixels: RADIUS_MAX_PX,
      billboard: !input.flat,
    }),
    new ScatterplotLayer<Ring>({
      id: 'rings',
      data: input.rings,
      getPosition: (ring) => ring.position,
      getRadius: (ring) => ring.radius,
      radiusUnits: 'pixels',
      stroked: true,
      filled: true,
      getFillColor: (ring) => [accent[0], accent[1], accent[2], ring.fill === 'solid' ? 255 : ring.fill === 'tint' ? 50 : 0],
      getLineColor: (ring) => (ring.fill === 'solid' ? [highlight[0], highlight[1], highlight[2], 255] : [accent[0], accent[1], accent[2], 255]),
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      billboard: !input.flat,
    }),
  ]
}
