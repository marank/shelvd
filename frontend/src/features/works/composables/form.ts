import type { RouteLocationRaw } from 'vue-router'

/** "a, b ,," → ["a", "b"] */
export function splitList(value: string): string[] {
  return value
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean)
}

/** The ?back= path of catalog edit pages (only same-app paths), else the home page. */
export function backTarget(back: unknown): RouteLocationRaw {
  return typeof back === 'string' && back.startsWith('/') && !back.startsWith('//')
    ? back
    : { name: 'home' }
}
