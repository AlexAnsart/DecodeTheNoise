/* What the renderer needs to know about the document it draws. */

export interface MarkdownEnv {
  /** Path of the document in the repository: its relative links start from there. */
  base: string
  /** Prefix of the ids given to headings, so two documents on one page do not collide. */
  ids: string
  /** How far headings are pushed down: 1 draws a document's `#` as a second-level heading. */
  shift: number
}
