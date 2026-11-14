/* Light or dark, remembered per browser. The canvas reads its colours from the same tokens. */

import { useCallback, useSyncExternalStore } from 'react'

export type Theme = 'light' | 'dark'
export type Rgb = readonly [number, number, number]

const STORAGE_KEY = 'noisemap.theme'
const listeners = new Set<() => void>()

function stored(): Theme {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'light' || value === 'dark') return value
  } catch {
    // Storage can be unavailable (private mode): the default applies.
  }
  return 'light'
}

let current: Theme = stored()

export function applyTheme(theme: Theme): void {
  current = theme
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Not remembered, still applied.
  }
  listeners.forEach((notify) => notify())
}

function subscribe(notify: () => void): () => void {
  listeners.add(notify)
  return () => listeners.delete(notify)
}

export function initTheme(): void {
  document.documentElement.dataset.theme = current
}

export function useTheme(): [Theme, () => void] {
  const theme = useSyncExternalStore(subscribe, () => current)
  const toggle = useCallback(() => applyTheme(current === 'light' ? 'dark' : 'light'), [])
  return [theme, toggle]
}

/** Reads a colour token as RGB bytes, for WebGL layers that cannot take a CSS variable. */
export function tokenRgb(name: string): Rgb {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  const hex = /^#([0-9a-f]{6})$/i.exec(raw)
  if (hex) {
    const value = Number.parseInt(hex[1], 16)
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
  }
  const rgb = /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(raw)
  if (rgb) return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])]
  return [128, 128, 128]
}
