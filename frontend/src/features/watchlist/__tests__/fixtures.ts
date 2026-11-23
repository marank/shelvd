import type { Library, Release, Tracking } from '@/api/types'
import { makeLibrary, makeRelease } from '@/test/fixtures'
import { settle } from '@/test/utils'

export const LIB = 'lib-1'
const OTHER_LIB = 'lib-2'

export const libraries: Library[] = [
  makeLibrary({ id: LIB, name: 'Games', role: 'owner' }),
  makeLibrary({ id: OTHER_LIB, name: 'Family', role: 'viewer' }),
  makeLibrary({ id: 'lib-3', name: 'Shared', role: 'editor' }),
]

export function upcoming(overrides: Partial<Release> = {}): Release {
  return makeRelease({
    release_date: '2026-11-22',
    release_precision: 'day',
    sort_date: '2026-11-22',
    is_released: false,
    year: 2026,
    ...overrides,
  })
}

export function tracking(overrides: Partial<Tracking> = {}): Tracking {
  return {
    id: 't-1',
    release: upcoming({ id: 'r-1', title: 'Metroid Prime 4', work_id: 'w-1' }),
    status: 'watching',
    library: null,
    user: 'alice',
    is_mine: true,
    owned_in: [],
    shop: '',
    price: null,
    ordered_on: null,
    notes: '',
    created_at: '2026-10-01T10:00:00Z',
    ...overrides,
  }
}

export const location = {
  id: 'loc-1',
  parent_id: null,
  name: 'Shelf',
  kind: 'shelf',
  notes: '',
  path: 'Living room / Shelf',
}
export const person = { id: 'per-1', name: 'Bob', email: '', notes: '' }

/** Teleported content lives in document.body. */
export function $(selector: string): HTMLElement {
  const el = document.body.querySelector<HTMLElement>(selector)
  if (!el) throw new Error(`not found: ${selector}`)
  return el
}

export function $$(selector: string): HTMLElement[] {
  return [...document.body.querySelectorAll<HTMLElement>(selector)]
}

export function type(selector: string, value: string) {
  const el = $(selector) as HTMLInputElement | HTMLSelectElement
  el.value = value
  el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
}

export function submitForm() {
  $('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
}

export async function openMenu(trigger: HTMLElement) {
  trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  await settle()
}
