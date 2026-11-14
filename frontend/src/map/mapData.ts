/* The map in memory: a struct of typed arrays, one index per point. */

import type { BufferSpec, Manifest, ProbeInfo } from '../api/schema'

export const NO_VALUE = 0xffff
export const NO_NEIGHBOUR = 0xffffffff

export interface MapColumn {
  key: string
  label: string
  names: string[]
  codes: Uint16Array
}

export interface MapZone {
  id: number
  name: string
  words: string[]
  size: number
  named: boolean
}

export interface MapData {
  build: string
  n: number
  /** Neighbours stored per point. */
  k: number
  pos3: Float32Array
  pos2: Float32Array
  /** Milliseconds since the epoch, 0 when undated. */
  ts: Float64Array
  neighbours: Uint32Array
  columns: MapColumn[]
  zones: MapZone[]
  embeddingKey: string
  /** A workspace map grows: `version` changes with every point, layout, name or review. */
  live: boolean
  version: number
  /** Probes that can be read on this map, shown or only feeding the review. */
  probes: ProbeInfo[]
}

type TypedArray = Float32Array | Float64Array | Uint8Array | Uint16Array | Uint32Array

function view(bytes: ArrayBuffer, spec: BufferSpec): TypedArray {
  switch (spec.dtype) {
    case 'float32':
      return new Float32Array(bytes, spec.offset, spec.length)
    case 'float64':
      return new Float64Array(bytes, spec.offset, spec.length)
    case 'uint8':
      return new Uint8Array(bytes, spec.offset, spec.length)
    case 'uint16':
      return new Uint16Array(bytes, spec.offset, spec.length)
    case 'uint32':
      return new Uint32Array(bytes, spec.offset, spec.length)
  }
}

function buffer<T extends TypedArray>(
  manifest: Manifest,
  bytes: ArrayBuffer,
  name: string,
  kind: new (...args: never[]) => T,
  length: number,
): T {
  const spec = manifest.buffers[name]
  if (!spec) throw new Error(`The map has no "${name}" buffer.`)
  const array = view(bytes, spec)
  if (!(array instanceof kind) || array.length !== length) {
    throw new Error(`The "${name}" buffer of the map has an unexpected type or size.`)
  }
  return array
}

function described(manifest: Manifest): Pick<MapData, 'build' | 'zones' | 'embeddingKey' | 'live' | 'version' | 'probes'> {
  return {
    build: manifest.build,
    zones: manifest.zones,
    embeddingKey: manifest.embedding_key,
    live: manifest.live,
    version: manifest.version,
    probes: manifest.probes,
  }
}

/** A map without a point: an empty workspace has no buffers to read. */
export function emptyMap(manifest: Manifest): MapData {
  return {
    ...described(manifest),
    n: 0,
    k: 0,
    pos3: new Float32Array(0),
    pos2: new Float32Array(0),
    ts: new Float64Array(0),
    neighbours: new Uint32Array(0),
    columns: [],
  }
}

export function decodeMap(manifest: Manifest, bytes: ArrayBuffer): MapData {
  const { n, k } = manifest
  return {
    ...described(manifest),
    n,
    k,
    pos3: buffer(manifest, bytes, 'pos3', Float32Array, n * 3),
    pos2: buffer(manifest, bytes, 'pos2', Float32Array, n * 2),
    ts: buffer(manifest, bytes, 'ts', Float64Array, n),
    neighbours: buffer(manifest, bytes, 'neighbours', Uint32Array, n * k),
    columns: manifest.columns.map((column) => ({
      key: column.key,
      label: column.label,
      names: column.names,
      codes: buffer(manifest, bytes, column.buffer, Uint16Array, n),
    })),
  }
}

export function columnOf(data: MapData, key: string): MapColumn | undefined {
  return data.columns.find((column) => column.key === key)
}

/** The stored neighbours of a point, nearest first. */
export function neighboursOf(data: MapData, index: number): number[] {
  const out: number[] = []
  for (let j = 0; j < data.k; j += 1) {
    const other = data.neighbours[index * data.k + j]
    if (other !== NO_NEIGHBOUR) out.push(other)
  }
  return out
}
