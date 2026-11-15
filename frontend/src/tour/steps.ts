/* The guided tour of the demo: a handful of short cards, each pointing at one control. */

export interface TourStep {
  id: string
  /** The element the card points at: its `data-tour` mark, then how to find it without one. */
  target: string
  title: string
  text: string
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: 'map',
    target: '[data-tour="map"], .nm-stage',
    title: 'Every point is a post',
    text: 'Posts that mean the same thing sit together, whatever words they use. Drag to turn the map, scroll to zoom, click a point to read it.',
  },
  {
    id: 'colour',
    target: '[data-tour="colour"], button[aria-label="Colour by"]',
    title: 'Colour the points',
    text: 'By zone, date or any other column. The legend names each colour: click a row to hide it.',
  },
  {
    id: 'axes',
    target: '[data-tour="axes"], button[aria-label="Axes"]',
    title: 'Add an axis',
    text: 'Put the date on an axis, or raise the points by the score of a probe.',
  },
  {
    id: 'lasso',
    target: '[data-tour="lasso"], button[aria-label="Lasso"]',
    title: 'Select a region',
    text: 'Draw around points to list them, colour them, or find what resembles them.',
  },
  {
    id: 'search',
    target: '[data-tour="search"], .nm-search',
    title: 'Search and paste',
    text: 'Find posts by word or by meaning. Paste a text or a link, and it lands among the posts it resembles.',
  },
  {
    id: 'mode',
    target: '[data-tour="mode"]',
    title: 'Now map your own posts',
    text: 'This is a demo dataset. Switch to My workspace to send your posts through the API and watch your own map build.',
  },
]

export function targetOf(step: TourStep): HTMLElement | null {
  const found = document.querySelector(step.target)
  return found instanceof HTMLElement ? found : null
}
