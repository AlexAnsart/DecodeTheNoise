/* The buffers of a map, read as they arrive, so a long download can show how far it is. */

import type { BufferSpec, Manifest } from './schema'

const ELEMENT_BYTES: Record<BufferSpec['dtype'], number> = { float32: 4, float64: 8, uint8: 1, uint16: 2, uint32: 4 }

/** Called as the bytes arrive: how many so far, of how many the map holds. */
export type Progress = (received: number, total: number) => void

/** Bytes of the buffers a manifest describes: the end of its last buffer. */
export function bufferBytes(manifest: Manifest): number {
  let end = 0
  for (const spec of Object.values(manifest.buffers)) end = Math.max(end, spec.offset + spec.length * ELEMENT_BYTES[spec.dtype])
  return end
}

/** The body of a response, counted as it arrives. `total` is the size the manifest announces:
 *  a compressed answer reaches the page already decompressed, so its `Content-Length` says
 *  nothing of what is counted here. Where the browser gives no stream to read, the body is
 *  read whole and nothing is counted. */
export async function readCounted(response: Response, total: number, onProgress: Progress): Promise<ArrayBuffer> {
  const reader = response.body?.getReader?.()
  if (!reader) return response.arrayBuffer()
  let bytes = new Uint8Array(total)
  let received = 0
  onProgress(0, total)
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    if (received + value.length > bytes.length) {
      // More than announced: everything is kept, and the decoder says so if the map is wrong.
      const larger = new Uint8Array(Math.max(bytes.length * 2, received + value.length))
      larger.set(bytes.subarray(0, received))
      bytes = larger
    }
    bytes.set(value, received)
    received += value.length
    onProgress(Math.min(received, total), total)
  }
  return received === bytes.length ? bytes.buffer : bytes.buffer.slice(0, received)
}
