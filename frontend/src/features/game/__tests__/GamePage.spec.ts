import { describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { useGroupLabel } from '@/lib/labels'
import { layoutRoutes, makeItem, makeLibrary, makeRelease, makeWork } from '@/test/fixtures'
import { mockApi, pageText, plainUser, renderApp, renderComponent, settle } from '@/test/utils'

const n64 = {
  ...makeRelease().platform,
  id: 'p-n64',
  name: 'Nintendo 64',
  short_name: 'N64',
  manufacturer: 'Nintendo',
}
const release = makeRelease({
  id: 'rel-1',
  work_id: 'work-1',
  work_title: 'Mario Kart 8 Deluxe',
  release_number: 129,
  edition: 'Booster Course Pack',
  age_rating: 'USK 0',
  players_offline: 4,
  players_online: 12,
  first_release_date: '1998-11-21',
  franchises: [{ id: 'fr-mario', name: 'Mario' }],
  series: [{ id: 'series-mk', name: 'Mario Kart' }],
  game_modes: ['Single player', 'Split screen', 'Hover racing'],
  perspectives: ['Third person'],
  languages: {
    German: ['audio', 'interface'],
    English: ['audio', 'subtitles', 'interface'],
    French: ['subtitles'],
    Italian: ['subtitles'],
    Japanese: ['audio'],
    Spanish: ['subtitles'],
    Klingon: ['interface'],
  },
  summary: 'Race karts. '.repeat(40),
  facts: {
    hltb: {
      source: 'hltb',
      title: 'MK8',
      url: 'https://howlongtobeat.com/game/1',
      values: { main: 12.5, complete: 40 },
      status: 'ok',
      pinned: false,
      fetched_at: null,
    },
  },
})
const original = makeRelease({
  id: 'rel-n64',
  work_id: 'work-1',
  platform: n64,
  region: 'jp',
  release_date: '1998-11-21',
  sort_date: '1998-11-21',
})
const item = makeItem({
  id: 'item-1',
  release,
  title: 'Mein MK8',
  status: 'sold',
  overrides: ['title'],
  purchase_price: '49.90',
  location: {
    id: 'loc-1',
    name: 'Box',
    path: 'Office › Box',
    trail: [
      { name: 'Office', kind: 'room' },
      { name: 'Box', kind: 'box' },
    ],
  },
  owner: { id: 'p1', name: 'Lena' },
  active_loan: {
    id: 'loan-1',
    borrower: { id: 'p2', name: 'Max' },
    lent_on: '2026-01-01',
    due_on: null,
  },
})
const other = makeItem({ id: 'item-2', release: original, cover_url: '/media/n64.jpg' })
const term = (id: string, name: string, image: string | null = null) => ({
  id,
  name,
  description: '',
  image_url: image,
  works: [],
  published: [],
  related: [],
  company: null,
})

function routes(role = 'owner', extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary({ role })),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/items/item-1': item,
    'GET /api/libraries/lib-1/items/item-1': item,
    'GET /api/catalog/releases/rel-1': release,
    'GET /api/catalog/works/work-1': makeWork({
      title: 'Mario Kart 8 Deluxe',
      releases: [release, original],
    }),
    'GET /api/libraries/lib-1/items': { count: 2, items: [item, other] },
    'GET /api/watchlist': [],
    'GET /api/lookup/providers': [
      { name: 'hltb', label: 'HowLongToBeat', kind: 'facts', enabled: false },
      { name: 'thegamesdb', label: 'TheGamesDB', kind: 'covers', enabled: true },
      { name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true },
    ],
    'GET /api/catalog/franchises/fr-mario': term('fr-mario', 'Mario'),
    'GET /api/catalog/series/series-mk': {
      ...term('series-mk', 'Mario Kart'),
      works: [
        { id: 'work-1', title: 'Mario Kart 8 Deluxe', year: 2017, platforms: [], cover_url: null },
        { id: 'work-64', title: 'Mario Kart 64', year: 1996, platforms: [], cover_url: null },
      ],
    },
    'GET /api/catalog/companies/company-epd': term('company-epd', 'Nintendo EPD', '/media/epd.svg'),
    'GET /api/catalog/companies/company-nintendo': term('company-nintendo', 'Nintendo'),
    ...extra,
  }
}

const q = (selector: string) => document.querySelector(selector)
const all = (selector: string) => [...document.querySelectorAll(selector)]
const text = (selector: string) => q(selector)?.textContent ?? ''
async function openMenu() {
  q('[data-testid="game-menu"]')!.dispatchEvent(
    new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
  )
  await settle()
}
const shown = (...ids: string[]) => ids.filter((id) => q(`[data-testid="${id}"]`))

describe('the game page focused on a copy', () => {
  it('shows the copy, your copies, the release, the game and where to go', async () => {
    const calls = mockApi(
      routes('owner', {
        'POST /api/libraries/lib-1/loans/loan-1/return': {},
        'DELETE /api/libraries/lib-1/items/item-1': { status: 204 },
      }),
    )
    const { router } = await renderApp('/items/item-1')
    await vi.waitFor(() => expect(q('[data-testid="game-title"]')).not.toBeNull())
    // The head: the copy's title, the release number, no kicker; the game's text and figures.
    expect(text('[data-testid="game-title"]')).toContain('Mein MK8')
    expect(text('[data-testid="game-suffix"]')).toBe('#129')
    expect(q('[data-testid="game-kicker"]')).toBeNull()
    expect(q('[data-testid="level-trail"]')).toBeNull()
    expect(text('[data-testid="game-summary"]')).toContain('Race karts.')
    expect(text('[data-testid="hero-stats"]')).toContain('12.5 h')
    expect(text('[data-testid="hero-stats"]')).toContain('Max') // lent: a figure
    // Under the cover: franchise, series, developer (with logo) and publisher.
    await vi.waitFor(() =>
      expect(all('[data-testid="cover-column"] [data-testid="about-block"]')).toHaveLength(4),
    )
    const blocks = all('[data-testid="cover-column"] [data-testid="about-block"]')
    expect(blocks.map((b) => b.getAttribute('href'))).toEqual([
      '/franchises/fr-mario',
      '/series/series-mk',
      '/companies/company-epd',
      '/companies/company-nintendo',
    ])
    await vi.waitFor(() =>
      expect(blocks[2]!.querySelector('img')?.getAttribute('src')).toBe('/media/epd.svg'),
    )

    // This copy: its facts, its own values, its actions.
    const facts = text('[data-testid="copy-facts"]')
    for (const value of ['Office › Box', 'Lena', '49.90', 'Sold']) expect(facts).toContain(value)
    expect(q('[data-testid="own-values"]')).not.toBeNull()
    expect(q('[data-testid="edit-copy"]')!.getAttribute('href')).toBe('/items/item-1/edit')
    expect(q('[data-testid="lend-copy"]')).toBeNull() // it's lent

    // Your copies, this one outlined; the release's copies first.
    await vi.waitFor(() => expect(all('[data-testid="shelf-copy"]')).toHaveLength(2))
    const shelf = all('[data-testid="shelf-copy"]')
    expect(shelf.map((s) => s.getAttribute('href'))).toEqual(['/items/item-1', '/items/item-2'])
    expect(shelf[0]!.hasAttribute('data-current')).toBe(true)

    // This release and the game: every field with a value.
    const releaseFacts = text('[data-testid="release-section"]')
    for (const value of ['Booster Course Pack', 'USK 0', '4', '12', '0045496420253'])
      expect(releaseFacts).toContain(value)
    const game = q('[data-testid="game-section"]')!
    expect(game.querySelector('[data-field="game.first_release"]')!.textContent).toContain('(N64)')
    // Known names translated, unknown ones as IGDB gives them.
    expect(game.querySelector('[data-field="game.modes"]')!.textContent).toContain('Split screen')
    expect(game.querySelector('[data-field="game.modes"]')!.textContent).toContain('Hover racing')
    expect(text('[data-testid="hltb-bars"]')).toContain('40 h')

    // Languages: yours and English first, a few until opened.
    const languages = () => all('[data-language]').map((row) => row.getAttribute('data-language'))
    expect(languages()).toEqual(['English', 'French', 'German', 'Italian', 'Japanese', 'Klingon'])
    expect(q('[data-language="German"] svg')).not.toBeNull()
    ;(q('[data-testid="languages-more"]') as HTMLElement).click()
    await settle()
    expect(languages()).toHaveLength(7)

    // All releases are folded in on a copy's page; opening them is remembered.
    expect(q('[data-testid="release-list"]')).toBeNull()
    ;(q('[data-testid="releases-section-toggle"]') as HTMLElement).click()
    await vi.waitFor(() => expect(q('[data-testid="release-list"]')).not.toBeNull())
    const rows = all('[data-testid="release-row"]')
    expect(rows.map((r) => r.getAttribute('href'))).toEqual([
      '/releases/rel-n64',
      '/releases/rel-1',
    ])
    expect(rows[1]!.hasAttribute('data-current')).toBe(true)
    expect(rows[0]!.textContent).toContain('1 copy')
    expect(all('[data-testid="timeline-dot"]')).toHaveLength(2)
    expect(JSON.parse(localStorage.getItem('shelvd.game-sections')!)).toEqual({
      'item.releases': true,
    })

    // More of the series, without this game.
    await vi.waitFor(() =>
      expect(text('[data-testid="series-section"]')).toContain('Mario Kart 64'),
    )
    expect(text('[data-testid="series-section"]')).not.toContain('Mario Kart 8 Deluxe')
    expect(q('[data-testid="series-link"]')!.getAttribute('href')).toBe('/series/series-mk')

    // Further: the release and the game, the sources we know an address for.
    expect(q('[data-testid="link-work"]')!.getAttribute('href')).toBe('/works/work-1')
    expect(q('[data-testid="link-release"]')!.getAttribute('href')).toBe('/releases/rel-1')
    expect(q('[data-testid="link-external"]')!.getAttribute('href')).toBe(
      'https://howlongtobeat.com/game/1',
    )

    // The menu: copy, release and game together.
    await openMenu()
    expect(
      shown('return-copy', 'edit-release', 'find-cover', 'move-release', 'edit-work', 'merge-work'),
    ).toHaveLength(6)
    expect(q('[data-testid="match-metadata"]')!.getAttribute('href')).toContain(
      '/works/work-1/metadata/igdb',
    )
    ;(q('[data-testid="return-copy"]') as HTMLElement).click()
    await vi.waitFor(() => expect(calls.some((c) => c.path.endsWith('/return'))).toBe(true))
    await openMenu()
    ;(q('[data-testid="delete-copy"]') as HTMLElement).click()
    await settle()
    ;(q('[data-testid="confirm-delete"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/works/work-1'))
  })

  it('folds sections in and keeps them so', async () => {
    mockApi(routes())
    await renderApp('/items/item-1')
    await vi.waitFor(() => expect(q('[data-testid="copy-facts"]')).not.toBeNull())
    ;(q('[data-testid="game-section-toggle"]') as HTMLElement).click()
    await vi.waitFor(() => expect(q('[data-testid="language-table"]')).toBeNull())
    expect(JSON.parse(localStorage.getItem('shelvd.game-sections')!)).toEqual({
      'item.game': false,
    })
  })

  it('is read-only for viewers', async () => {
    const own = { ...item, active_loan: null, release: { ...release, can_edit: false } }
    mockApi(
      routes('viewer', {
        'GET /api/items/item-1': own,
        'GET /api/libraries/lib-1/items/item-1': own,
        'GET /api/catalog/works/work-1': makeWork({ can_edit: false, releases: [release] }),
      }),
    )
    await renderApp('/items/item-1', { user: plainUser })
    await vi.waitFor(() => expect(q('[data-testid="copy-facts"]')).not.toBeNull())
    expect(shown('edit-copy', 'lend-copy', 'add-copy')).toEqual([])
    await openMenu()
    expect(
      shown('edit-release', 'edit-work', 'find-cover', 'delete-copy', 'return-copy', 'merge-work'),
    ).toEqual([])
  })

  it('says when a copy is unknown or invisible', async () => {
    mockApi(routes('owner', { 'GET /api/items/:id': { status: 404, body: { detail: 'Gone.' } } }))
    await renderApp('/items/nope')
    await vi.waitFor(() => expect(pageText()).toContain('Not found'))
  })
})

describe('the game page focused on a release', () => {
  it('says whose release it is and adds or tracks copies of it', async () => {
    const calls = mockApi(
      routes('owner', {
        'GET /api/libraries/lib-1/items': { count: 1, items: [other] },
        'POST /api/libraries/lib-1/items': { status: 201, body: { ...item, id: 'item-new' } },
      }),
    )
    const { router } = await renderApp('/releases/rel-1')
    await vi.waitFor(() => expect(q('[data-testid="kicker-game"]')).not.toBeNull())
    expect(q('[data-testid="kicker-game"]')!.getAttribute('href')).toBe('/works/work-1')
    expect(text('[data-testid="game-title"]')).toContain('Mario Kart 8 Deluxe')
    expect(text('[data-testid="game-suffix"]')).toBe('#129')
    expect(q('[data-testid="copy-section"]')).toBeNull()
    // None of this release: watch it; your copy of another release is still shown.
    await vi.waitFor(() => expect(q('[data-testid="track-button"]')).not.toBeNull())
    expect(all('[data-testid="shelf-copy"]')).toHaveLength(1)
    expect(q('[data-testid="release-list"]')).not.toBeNull() // open here
    expect(q('[data-testid="release-row"][data-current]')!.getAttribute('href')).toBe(
      '/releases/rel-1',
    )
    expect(shown('link-work', 'link-release')).toEqual(['link-work'])
    ;(q('[data-testid="add-copy"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/items/item-new/edit'))
    expect(calls.find((c) => c.method === 'POST')!.body).toMatchObject({ release_id: 'rel-1' })
  })

  it('marks a release that waits for review', async () => {
    mockApi(
      routes('owner', {
        'GET /api/catalog/releases/rel-1': { ...release, review_status: 'pending' },
      }),
    )
    await renderApp('/releases/rel-1')
    await vi.waitFor(() =>
      expect(q('[data-testid="release-section"] [data-testid="unreviewed"]')).not.toBeNull(),
    )
  })
})

describe('the game page focused on the game', () => {
  it('shows the game, your copies of any release and what others track', async () => {
    mockApi(
      routes('owner', {
        'GET /api/catalog/works/work-1': makeWork({
          releases: [release, original],
          review_status: 'pending',
        }),
        'GET /api/watchlist': [
          {
            id: 'tr-1',
            release: original,
            status: 'preordered',
            library: { id: 'lib-1', name: 'Meine Spiele' },
            user: 'bob',
            is_mine: false,
            owned_in: [],
            shop: '',
            price: null,
            ordered_on: null,
            notes: '',
            created_at: '2026-01-01T00:00:00Z',
          },
        ],
      }),
    )
    await renderApp('/works/work-1')
    await vi.waitFor(() => expect(text('[data-testid="game-kicker"]')).toContain('2 releases'))
    expect(q('[data-testid="game-suffix"]')).toBeNull()
    // A copy's cover while the game has none of its own.
    await vi.waitFor(() =>
      expect(q('[data-testid="cover-column"] img')?.getAttribute('src')).toBe('/media/n64.jpg'),
    )
    // No release in front: no release section, no publisher under the cover.
    expect(q('[data-testid="release-section"]')).toBeNull()
    expect(text('[data-testid="cover-column"]')).not.toContain('Publisher')
    expect(q('[data-testid="game-section"] [data-testid="unreviewed"]')).not.toBeNull()
    expect(q('[data-testid="release-row"][data-current]')).toBeNull()
    await vi.waitFor(() => expect(text('[data-testid="others-tracking"]')).toContain('bob'))
    expect(shown('link-work', 'link-release')).toEqual([])
    await openMenu()
    expect(shown('edit-work', 'merge-work', 'edit-release', 'delete-copy')).toEqual([
      'edit-work',
      'merge-work',
    ])
  })

  it('asks to pick a release when you have none', async () => {
    mockApi(routes('owner', { 'GET /api/libraries/lib-1/items': { count: 0, items: [] } }))
    await renderApp('/works/work-1')
    await vi.waitFor(() => expect(text('[data-testid="no-copies"]')).toContain('pick a release'))
    expect(q('[data-testid="add-copy"]')).toBeNull()
  })

  it('says when a game is unknown or has no release', async () => {
    mockApi(routes('owner', { 'GET /api/catalog/works/work-1': makeWork({ releases: [] }) }))
    await renderApp('/works/work-1')
    await vi.waitFor(() => expect(pageText()).toContain('Not found'))
  })
})

describe('play info', () => {
  it("is named in the reader's language where we know the name", async () => {
    let label!: ReturnType<typeof useGroupLabel>
    mockApi({})
    await renderComponent(
      defineComponent({
        setup() {
          label = useGroupLabel()
          return () => null
        },
      }),
    )
    expect(label('game.perspectives', 'Bird view / Isometric')).toBe("Bird's-eye / isometric")
    expect(label('game.modes', 'Co-operative')).toBe('Co-op')
    expect(label('game.languages', 'Klingon')).toBe('Klingon')
  })

  it('goes without a first release, play times and known sources', async () => {
    const bare = {
      ...release,
      first_release_date: null,
      languages: {},
      facts: {
        opencritic: {
          source: 'opencritic',
          title: 'MK8',
          url: 'https://opencritic.com/game/1',
          values: {},
          status: 'ok',
          pinned: false,
          fetched_at: null,
        },
      },
    }
    mockApi(
      routes('owner', {
        'GET /api/catalog/works/work-1': makeWork({ releases: [bare] }),
        'GET /api/lookup/providers': [],
      }),
    )
    await renderApp('/works/work-1')
    await vi.waitFor(() => expect(q('[data-testid="game-section"]')).not.toBeNull())
    expect(q('[data-field="game.first_release"]')).toBeNull()
    expect(q('[data-testid="language-table"]')).toBeNull()
    expect(q('[data-testid="hltb-bars"]')).toBeNull()
    expect(text('[data-testid="link-external"]')).toContain('opencritic')
  })
})

describe('a crossover', () => {
  it('lists several franchises in the game section, not under the cover', async () => {
    const names = ['Ant-Man', 'Black Panther', 'Hulk', 'Iron Man', 'LEGO', 'Marvel', 'Thor']
    const crossover = {
      ...release,
      franchises: names.map((name, i) => ({ id: `fr-${i}`, name })),
    }
    mockApi(
      routes('owner', { 'GET /api/catalog/works/work-1': makeWork({ releases: [crossover] }) }),
    )
    await renderApp('/works/work-1')
    await vi.waitFor(() => expect(q('[data-testid="term-list-franchises"]')).not.toBeNull())
    expect(text('[data-testid="cover-column"]')).not.toContain('Franchise')
    const shownNames = () => all('[data-testid="term-list-franchises"] li a')
    expect(shownNames()).toHaveLength(6)
    expect(shownNames()[0]!.getAttribute('href')).toBe('/franchises/fr-0')
    ;(q('[data-testid="term-list-franchises-more"]') as HTMLElement).click()
    await settle()
    expect(shownNames()).toHaveLength(7)
    expect(text('[data-testid="term-list-franchises-more"]')).toContain('Fewer')
  })
})
