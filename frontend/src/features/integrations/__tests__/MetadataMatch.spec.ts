import { afterEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { layoutRoutes, makeLibrary, makeWork } from '@/test/fixtures'
import { mockApi, pageText, renderApp, settle } from '@/test/utils'

vi.mock('vue-sonner', () => ({
  toast: {
    success: vi.fn<(message: string) => void>(),
    error: vi.fn<(message: string) => void>(),
  },
}))

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const url = '/works/work-1/metadata/igdb?back=/works/work-1'
const odyssey = {
  external_id: '26758',
  title: 'Super Mario Odyssey',
  year: 2017,
  platforms: ['Nintendo Switch', 'Toaster'],
  summary: 'Cappy!',
  cover_url: 'https://images.igdb.com/igdb/image/upload/t_cover_big_2x/co1mxf.jpg',
}
const value = (v: Partial<Record<'text' | 'date' | 'precision' | 'image', string>> = {}) => ({
  text: '',
  date: null,
  precision: null,
  image: null,
  ...v,
})
const preview = {
  external_id: '26758',
  title: 'Super Mario Odyssey',
  changes: [
    { id: 'work.summary', field: 'summary', kind: 'fill', suggested: true, release_id: null, current: value(), proposed: value({ text: 'Cappy!' }) },
    { id: 'work.genres', field: 'genres', kind: 'differs', suggested: false, release_id: null, current: value({ text: 'Jump' }), proposed: value({ text: 'Platform, Adventure' }) },
    { id: 'rel-1.release_date', field: 'release_date', kind: 'precise', suggested: true, release_id: 'rel-1', current: value({ date: '2027-01-01', precision: 'half' }), proposed: value({ date: '2026-09-15', precision: 'day' }) },
    { id: 'rel-1.cover', field: 'cover', kind: 'differs', suggested: false, release_id: 'rel-1', current: value({ image: '/media/covers/rel-1.png' }), proposed: value({ image: 'https://images.igdb.com/igdb/image/upload/t_cover_big_2x/co1mxf.jpg' }) },
  ],
} // prettier-ignore
const routes = (extra: Record<string, unknown> = {}) => ({
  ...layoutRoutes(makeLibrary()),
  'GET /api/catalog/works/work-1': makeWork(),
  'GET /api/lookup/providers': [{ name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true }],
  'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
  'GET /api/libraries/lib-1/items': { count: 0, items: [] },
  'GET /api/watchlist': [],
  'GET /api/catalog/works/:id/metadata/:source/candidates': [odyssey],
  'GET /api/catalog/works/:id/metadata/:source/:externalId': preview,
  ...extra,
})

describe('matching a game with IGDB', () => {
  afterEach(() => vi.clearAllMocks())

  it('picks an entry, then reviews and applies the chosen changes', async () => {
    const calls = mockApi(
      routes({
        'POST /api/catalog/works/:id/metadata/:source': {
          applied: ['work.summary', 'work.genres', 'rel-1.release_date'],
        },
      }),
    )
    const { router } = await renderApp(url)
    await vi.waitFor(() => expect(q('[data-testid="metadata-candidates"]')).not.toBeNull())
    expect(pageText()).toContain('Match game data')
    // Just one source: no switch.
    expect(q('[data-testid="metadata-sources"]')).toBeNull()
    expect(q('[data-testid="current-link"]')).toBeNull()
    const row = q('[data-testid="metadata-candidates"]')
    expect(row.textContent).toContain('Nintendo Switch · Toaster')
    expect(row.querySelector('img')!.getAttribute('src')).toContain('/t_cover_small/co1mxf.jpg')

    q('[data-testid="choose-26758"]').click()
    await vi.waitFor(() =>
      expect(router.currentRoute.value.path).toBe('/works/work-1/metadata/igdb/26758'),
    )
    await vi.waitFor(() => expect(q('[data-testid="change-summary"]')).not.toBeNull())
    expect(q('[data-testid="metadata-entry"]').textContent).toContain('Super Mario Odyssey')
    // Grouped: the game, then the release.
    expect(pageText()).toContain('Release · Switch · PAL')
    expect(q('[data-testid="change-release_date"]').textContent).toContain('more precise')
    expect(q('[data-testid="change-release_date"]').textContent).toContain('H1 2027')
    expect(q('[data-testid="change-genres"]').textContent).toContain('Platform, Adventure')
    expect(q('[data-testid="change-cover"]').querySelectorAll('img')).toHaveLength(2)
    // Suggested ones are ticked, differences not.
    const checked = (field: string) =>
      q(`[data-testid="pick-${field}"]`).getAttribute('data-state') === 'checked'
    expect(['summary', 'genres', 'release_date', 'cover'].map(checked)).toEqual([
      true,
      false,
      true,
      false,
    ])
    expect(q('[data-testid="edit-save"]').textContent).toContain('Apply 2 changes')
    q('[data-testid="pick-genres"]').click()
    await settle()
    expect(q('[data-testid="edit-save"]').textContent).toContain('Apply 3 changes')

    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/works/work-1'))
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({
      external_id: '26758',
      changes: ['work.summary', 'rel-1.release_date', 'work.genres'],
    })
    expect(toast.success).toHaveBeenCalledWith('3 changes applied')
  })

  it('matches the linked entry again and searches by hand', async () => {
    const calls = mockApi(
      routes({
        'GET /api/catalog/works/work-1': makeWork({ external_ids: { igdb: 26758 } }),
        'GET /api/catalog/works/:id/metadata/:source/:externalId': { ...preview, changes: [] },
        'POST /api/catalog/works/:id/metadata/:source': { applied: [] },
      }),
    )
    const { router } = await renderApp(url)
    await vi.waitFor(() => expect(q('[data-testid="current-link"]')).not.toBeNull())
    expect(q('[data-testid="current-link"]').textContent).toContain('#26758')

    const field = q('[data-testid="metadata-query"]') as HTMLInputElement
    field.value = 'Odyssey'
    field.dispatchEvent(new Event('input'))
    await settle()
    q('[data-testid="metadata-search"]').dispatchEvent(new Event('submit'))
    await vi.waitFor(() =>
      expect(calls.some((c) => c.path.endsWith('/candidates') && c.query.get('q') === 'Odyssey'))
        .toBe(true),
    ) // prettier-ignore

    q('[data-testid="refill"]').click()
    await vi.waitFor(() => expect(q('[data-testid="no-changes"]')).not.toBeNull())
    expect(pageText()).toContain('Everything already matches IGDB.')
    expect(q('[data-testid="edit-save"]').textContent).toContain('Link with entry')
    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/works/work-1'))
    expect(toast.success).toHaveBeenCalledWith('Linked with IGDB, nothing changed')
  })

  it('shows a failing source and errors while applying', async () => {
    mockApi(
      routes({
        'GET /api/catalog/works/:id/metadata/:source/candidates': {
          status: 502,
          body: { detail: 'The source did not answer. Try again later.' },
        },
        'GET /api/catalog/works/:id/metadata/:source/:externalId': {
          status: 404,
          body: { detail: 'The source does not know this game.' },
        },
      }),
    )
    await renderApp(url)
    await vi.waitFor(() => expect(pageText()).toContain('The source did not answer.'))
    await renderApp('/works/work-1/metadata/igdb/1')
    await vi.waitFor(() => expect(pageText()).toContain('The source does not know this game.'))

    mockApi(
      routes({
        'POST /api/catalog/works/:id/metadata/:source': {
          status: 502,
          body: { detail: 'The source did not answer. Try again later.' },
        },
      }),
    )
    await renderApp('/works/work-1/metadata/igdb/26758')
    await vi.waitFor(() => expect(q('[data-testid="change-summary"]')).not.toBeNull())
    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('The source did not answer. Try again later.'),
    )
  })

  it('offers one match entry on the game page, starting with the first source', async () => {
    mockApi(routes())
    await renderApp('/works/work-1')
    await vi.waitFor(() => expect(q('[data-testid="game-menu"]')).not.toBeNull())
    q('[data-testid="game-menu"]').dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    )
    await vi.waitFor(() => expect(q('[data-testid="match-metadata"]')).not.toBeNull())
    expect(q('[data-testid="match-metadata"]').textContent).toContain('Match game data …')
    expect(q('[data-testid="match-metadata"]').getAttribute('href')).toContain(
      '/works/work-1/metadata/igdb?back=',
    )
  })

  it('switches between metadata sources', async () => {
    const calls = mockApi(
      routes({
        'GET /api/lookup/providers': [
          { name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true },
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
          { name: 'hltb', label: 'HowLongToBeat', kind: 'facts', enabled: true },
        ],
      }),
    )
    const { router } = await renderApp(url)
    await vi.waitFor(() => expect(q('[data-testid="source-wikipedia"]')).not.toBeNull())
    expect(q('[data-testid="source-igdb"]')).not.toBeNull()
    expect(q('[data-testid="source-hltb"]')).toBeNull()
    expect(q('[data-testid="source-offers"]').textContent).toContain('dates per platform')
    q('[data-testid="source-wikipedia"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.params.source).toBe('wikipedia'))
    expect(router.currentRoute.value.query.back).toBe('/works/work-1')
    await vi.waitFor(() =>
      expect(calls.some((c) => c.path.includes('/metadata/wikipedia/candidates'))).toBe(true),
    )
    expect(q('[data-testid="source-offers"]').textContent).toContain('in your language')
    // Clicking the active one again changes nothing.
    q('[data-testid="source-wikipedia"]').click()
    await settle()
    expect(router.currentRoute.value.params.source).toBe('wikipedia')
  })
})
