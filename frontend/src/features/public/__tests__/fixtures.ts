import type { ListEntry, PublicItem, Release } from '@/api/types'

function release(id: string, title: string, extra: Partial<Release> = {}): Release {
  return {
    id,
    title,
    work_id: `w-${id}`,
    work_title: title,
    platform: {
      id: 'p1',
      name: 'Nintendo DS',
      short_name: 'NDS',
      slug: 'nds',
      manufacturer: 'Nintendo',
      media_type: 'cartridge',
      release_year: 2004,
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
    release_date: '2006-05-15',
    release_date_end: null,
    release_precision: 'day',
    sort_date: '2006-05-15',
    is_released: true,
    year: 2006,
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

export function item(id: string, title: string, extra: Partial<Release> = {}): PublicItem {
  return {
    id,
    title,
    cover_url: null,
    cover_aspect: null,
    release: release(`r-${id}`, `Catalog ${title}`, extra),
    format: 'physical',
    status: 'owned',
    completeness: 'complete',
  }
}

export function entry(id: string, title: string, position: number, note = ''): ListEntry {
  return { id, release: release(`r-${id}`, title), item_id: null, note, position }
}
