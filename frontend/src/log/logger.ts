/* The one place that writes to the console. Each line carries the module that spoke. */

type Level = 'debug' | 'info' | 'warn' | 'error'

export interface Logger {
  debug(message: string, detail?: unknown): void
  info(message: string, detail?: unknown): void
  warn(message: string, detail?: unknown): void
  error(message: string, detail?: unknown): void
}

function write(level: Level, source: string, message: string, detail: unknown): void {
  const line = `[${source}] ${message}`
  // eslint-disable-next-line no-console
  const sink = console[level]
  if (detail === undefined) sink(line)
  else sink(line, detail)
}

export function logger(source: string): Logger {
  return {
    debug: (message, detail) => write('debug', source, message, detail),
    info: (message, detail) => write('info', source, message, detail),
    warn: (message, detail) => write('warn', source, message, detail),
    error: (message, detail) => write('error', source, message, detail),
  }
}
