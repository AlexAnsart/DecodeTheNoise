/* Where a link or an image of a document leads. A document of the repository refers to its
   neighbours by relative paths; here they become a place of the method page, a file at the
   deployed commit, or a figure served by the API. Pure. */

const WEB = /^https?:\/\//i
const SCHEME = /^[a-z][a-z0-9+.-]*:/i

export type Destination =
  /** Another site: opened in a new tab. */
  | { kind: 'web'; url: string }
  /** A heading of the same document. */
  | { kind: 'anchor'; id: string }
  /** A path of the repository, resolved from the folder of the document. */
  | { kind: 'path'; path: string }
  /** Nothing safe to follow (`javascript:`, `data:`): the words stay, the link does not. */
  | { kind: 'none' }

/** `docs/probes/report.md` + `guides/calls.md` gives `docs/probes/guides/calls.md`. */
export function resolvePath(base: string, relative: string): string {
  const parts = base.split('/').slice(0, -1)
  for (const part of relative.split('/')) {
    if (part === '..') parts.pop()
    else if (part !== '.' && part !== '') parts.push(part)
  }
  // A link to a folder keeps saying so.
  return parts.join('/') + (relative.endsWith('/') ? '/' : '')
}

export function destinationOf(base: string, href: string): Destination {
  const target = href.trim()
  if (WEB.test(target)) return { kind: 'web', url: target }
  if (target.startsWith('#')) return { kind: 'anchor', id: slug(target.slice(1)) }
  if (SCHEME.test(target) || target.startsWith('//')) return { kind: 'none' }
  const [path] = target.split('#')
  return path ? { kind: 'path', path: resolvePath(base, path) } : { kind: 'none' }
}

/** The name of a figure when a path points into a `figures/` folder; null otherwise. */
export function figureOf(path: string): string | null {
  const match = /(?:^|\/)figures\/([^/]+\.(?:png|jpe?g|svg|webp|gif))$/i.exec(path)
  return match ? match[1] : null
}

/** A heading as an element id: lower case, words joined by hyphens. */
export function slug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[`*_~]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
}

const ENTITIES: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' }

/** The few character references a document may hold, as the characters they stand for. */
export function decodeEntities(text: string): string {
  return text.replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (whole, name: string) => {
    if (name.startsWith('#')) {
      const code = name[1].toLowerCase() === 'x' ? Number.parseInt(name.slice(2), 16) : Number.parseInt(name.slice(1), 10)
      return Number.isFinite(code) && code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : whole
    }
    return ENTITIES[name.toLowerCase()] ?? whole
  })
}
