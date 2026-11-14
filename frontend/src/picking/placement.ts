/* Where the tooltip and the card of a point go, inside the part of the stage no drawer covers. */

export interface Box {
  width: number
  height: number
}

export interface Placed {
  left: number
  top: number
}

const TIP_OFFSET = 12
const TIP_EDGE_LEFT = 4
const TIP_EDGE_RIGHT = 8

/** 12px right of and below the pointer; kept inside the free width; above when it would pass the bottom. */
export function placeTip(x: number, y: number, tip: Box, stage: Box, freeWidth: number): Placed {
  const left = Math.min(Math.max(TIP_EDGE_LEFT, x + TIP_OFFSET), freeWidth - tip.width - TIP_EDGE_RIGHT)
  const below = y + TIP_OFFSET
  const top = below + tip.height > stage.height ? Math.max(0, y - TIP_OFFSET - tip.height) : below
  return { left, top }
}

const CARD_OFFSET_X = 18
const CARD_OFFSET_Y = 28
const CARD_EDGE = 8
const CARD_MAX_HEIGHT = 380
const CARD_MIN_ROOM = 220

export interface PlacedCard extends Placed {
  maxHeight: number
}

/** Beside the point, flipped to its left when the right edge is near, moved up to keep room
 *  below. Null while the point is outside the free part of the stage. */
export function placeCard(x: number, y: number, cardWidth: number, stage: Box, freeWidth: number): PlacedCard | null {
  if (x < 0 || y < 0 || x > freeWidth || y > stage.height) return null
  const right = x + CARD_OFFSET_X
  const fitsRight = right + cardWidth + CARD_EDGE <= freeWidth
  const left = fitsRight ? right : Math.max(CARD_EDGE, x - CARD_OFFSET_X - cardWidth)
  const room = stage.height - CARD_EDGE
  const top = Math.max(CARD_EDGE, Math.min(y - CARD_OFFSET_Y, room - CARD_MIN_ROOM))
  return { left, top, maxHeight: Math.min(CARD_MAX_HEIGHT, room - top) }
}
