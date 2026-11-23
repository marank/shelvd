import type { CustomList, ListEntry, Release } from '@/api/types'

function release(id: string, title: string, extra: Partial<Release> = {}): Release {
  return {
    id,
    title,
    work_id: `w-${id}`,
    work_title: title,
    platform: {
      id: 'p1',
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
    },
    region: 'pal',
    edition: '',
    age_rating: '',
    product_code: '',
    release_number: null,
    series: [],
    first_release_date: null,
    facts: {},
    release_date: '2017-03-03',
    release_date_end: null,
    release_precision: 'day',
    sort_date: '2017-03-03',
    is_released: true,
    year: 2017,
    publisher: null,
    developers: [],
    release_developers: [],
    genres: [],
    summary: '',
    cover_url: null,
    cover_aspect: null,
    cover_source: '',
    cover_from_game: false,
    barcodes: [],
    franchises: [],
    game_modes: [],
    perspectives: [],
    languages: {},
    players_offline: null,
    players_online: null,
    pending_barcodes: [],
    review_status: 'approved',
    can_edit: true,
    ...extra,
  }
}

export function list(id: string, name: string, extra: Partial<CustomList> = {}): CustomList {
  return {
    id,
    name,
    description: '',
    owner: 'alice',
    public_token: null,
    entry_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    ...extra,
  }
}

export function entry(id: string, title: string, position: number, note = ''): ListEntry {
  return { id, release: release(`r-${id}`, title), item_id: null, note, position }
}
