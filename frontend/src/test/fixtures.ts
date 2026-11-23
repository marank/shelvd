/** Small factories for API objects in tests. */
import type { Item, Library, Overview, Platform, Release, Work } from '@/api/types'

let counter = 0
const id = (prefix: string) => `${prefix}-${++counter}`

export const switchPlatform: Platform = {
  id: 'platform-switch',
  name: 'Nintendo Switch',
  short_name: 'Switch',
  slug: 'switch',
  manufacturer: 'Nintendo',
  media_type: 'game',
  release_year: 2017,
  color: '',
  icon: '',
  icon_url: null,
  icon_dark: false,
}

export function makeLibrary(overrides: Partial<Library> = {}): Library {
  return {
    id: 'lib-1',
    name: 'Meine Spiele',
    description: '',
    owner: 'alice',
    role: 'owner',
    item_count: 2,
    public_token: null,
    viewer_loans: 'status',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeRelease(overrides: Partial<Release> = {}): Release {
  return {
    id: id('release'),
    title: 'Mario Kart 8 Deluxe',
    work_id: id('work'),
    work_title: 'Mario Kart 8 Deluxe',
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
    publisher: { id: 'company-nintendo', name: 'Nintendo' },
    developers: [{ id: 'company-epd', name: 'Nintendo EPD' }],
    release_developers: [],
    genres: [{ id: 'genre-racing', name: 'Racing' }],
    summary: 'Karts.',
    cover_url: null,
    cover_aspect: null,
    cover_source: '',
    cover_from_game: false,
    barcodes: ['0045496420253'],
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

export function makeItem(overrides: Partial<Item> = {}): Item {
  const release = overrides.release ?? makeRelease()
  return {
    id: id('item'),
    library_id: 'lib-1',
    title: release.title,
    cover_url: release.cover_url,
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
    release,
    format: 'physical',
    status: 'owned',
    condition: null,
    completeness: 'complete',
    play_status: null,
    location: null,
    owner: null,
    acquired_on: null,
    purchase_price: null,
    notes: '',
    active_loan: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeOverview(overrides: Partial<Overview> = {}): Overview {
  return {
    id: 'overview-1',
    name: 'Nach Plattform',
    group_by: ['platform'],
    section: '',
    filters: [],
    match: 'all',
    fields: {},
    sort: 'game.title',
    layout: 'grid',
    position: 0,
    ...overrides,
  }
}

/** The calls every page inside the app layout makes (sidebar, topbar). */
export function layoutRoutes(library = makeLibrary(), overviews = [makeOverview()]) {
  return {
    'GET /api/libraries': [library],
    [`GET /api/libraries/${library.id}`]: library,
    [`GET /api/libraries/${library.id}/overviews`]: overviews,
    'GET /api/catalog/platforms': [switchPlatform],
  }
}

export function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    id: 'work-1',
    title: 'Mario Kart 8 Deluxe',
    media_type: 'game',
    summary: 'Karts.',
    series: [{ id: 'series-mk', name: 'Mario Kart' }],
    franchises: [],
    first_release_date: '2014-05-30',
    genres: [{ id: 'genre-racing', name: 'Racing' }],
    developers: [{ id: 'company-epd', name: 'Nintendo EPD' }],
    cover_url: null,
    cover_aspect: null,
    has_cover: false,
    external_ids: {},
    releases: [makeRelease({ id: 'rel-1', work_id: 'work-1' })],
    review_status: 'approved',
    can_edit: true,
    ...overrides,
  }
}
