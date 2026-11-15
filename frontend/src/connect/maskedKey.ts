/* How an API key is written where it is only shown: enough of it to recognise, not to use. */

const HIDDEN_CHARS = 14

export function maskedKey(apiKey: string): string {
  return `${apiKey.slice(0, 3)}${'•'.repeat(HIDDEN_CHARS)}${apiKey.slice(-4)}`
}
