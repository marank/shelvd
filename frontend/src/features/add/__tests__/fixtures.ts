import type { Candidate, Item, Platform, Release } from '@/api/types'

export const LIB = '11111111-1111-1111-1111-111111111111'

const switchPlatform: Platform = {
  id: 'p-switch',
  name: 'Nintendo Switch',
  short_name: 'Switch',
  slug: 'switch',
  manufacturer: 'Nintendo',
  media_type: 'cartridge',
  release_year: 2017,
  color: '',
  icon: '',
  icon_url: null,
  icon_dark: false,
}
export const ps5: Platform = {
  id: 'p-ps5',
  name: 'PlayStation 5',
  short_name: 'PS5',
  slug: 'ps5',
  manufacturer: 'Sony',
  media_type: 'disc',
  release_year: 2020,
  color: '',
  icon: '',
  icon_url: null,
  icon_dark: false,
}

export function release(overrides: Partial<Release> = {}): Release {
  return {
    id: 'r-1',
    title: 'Mario Kart 8 Deluxe',
    work_id: 'w-1',
    work_title: 'Mario Kart 8',
    platform: switchPlatform,
    region: 'pal',
    edition: '',
    age_rating: '',
    product_code: '',
    release_number: null,
    series: [],
    first_release_date: null,
    facts: {},
    release_date: '2017-04-28',
    release_date_end: null,
    release_precision: 'day',
    sort_date: '2017-04-28',
    is_released: true,
    year: 2017,
    publisher: { id: 'c-1', name: 'Nintendo' },
    developers: [],
    release_developers: [],
    genres: [],
    summary: '',
    cover_url: null,
    cover_aspect: null,
    cover_source: '',
    cover_from_game: false,
    barcodes: ['0045496420055'],
    franchises: [],
    game_modes: [],
    perspectives: [],
    languages: {},
    players_offline: null,
    players_online: null,
    pending_barcodes: [],
    review_status: 'approved',
    can_edit: true,
    ...overrides,
  }
}

export function candidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    provider: 'igdb',
    external_id: '42',
    title: 'Zelda: Tears of the Kingdom',
    platform_id: switchPlatform.id,
    platform_name: 'Nintendo Switch',
    region: null,
    release_date: null,
    release_precision: 'day',
    year: 2023,
    publisher: 'Nintendo',
    developers: [],
    genres: [],
    summary: 'Sky islands.',
    cover_url: 'https://images.igdb.com/x.jpg',
    ...overrides,
  }
}

export function item(r: Release, id = 'i-1'): Item {
  return {
    id,
    library_id: 'lib-1',
    title: r.title,
    cover_url: r.cover_url,
    cover_aspect: null,
    title_override: '',
    current_value: null,
    tags: [],
    has_cover_override: false,
    edition_override: '',
    region_override: null,
    release_precision_override: null,
    release_date_override: null,
    release_date_end_override: null,
    overrides: [],
    release: r,
    format: 'physical',
    status: 'owned',
    condition: null,
    completeness: null,
    play_status: null,
    location: null,
    owner: null,
    acquired_on: null,
    purchase_price: null,
    notes: '',
    active_loan: null,
    created_at: '2026-11-01T10:00:00Z',
  }
}

export function lookup(overrides: Record<string, unknown> = {}) {
  return {
    code: '0045496420055',
    known: [],
    ...overrides,
  }
}

/** Reference data every dialog test needs. */
export function baseRoutes(igdb = true): Record<string, unknown> {
  return {
    'GET /api/catalog/platforms': [switchPlatform, ps5],
    'GET /api/lookup/providers': [{ name: 'igdb', kind: 'metadata', enabled: igdb }],
    'GET /api/libraries/:id/locations': [
      {
        id: 'loc-1',
        parent_id: null,
        name: 'Shelf',
        kind: 'shelf',
        notes: '',
        path: 'Living room / Shelf',
      },
    ],
    'GET /api/libraries/:id/people': [{ id: 'per-1', name: 'Alice', email: '', notes: '' }],
  }
}

/** Dialog content is teleported to document.body. */
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

export function click(selector: string | HTMLElement) {
  const el = typeof selector === 'string' ? $(selector) : selector
  el.click()
}

export function submit(selector: string) {
  $(selector).dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
}
