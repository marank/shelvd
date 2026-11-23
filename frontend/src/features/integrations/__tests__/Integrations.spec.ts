import { describe, expect, it, vi } from 'vitest'
import type { Integration, Provider } from '@/api/types'
import { layoutRoutes, makeItem, makeLibrary, makeRelease, makeWork } from '@/test/fixtures'
import { mockApi, pageText, plainUser, renderApp, settle, testUser } from '@/test/utils'

const staff = { ...testUser, is_staff: true }

function provider(name: string, kind: string, enabled = false): Provider {
  const labels: Record<string, string> = {
    igdb: 'IGDB', hltb: 'HowLongToBeat', opencritic: 'OpenCritic',
    thegamesdb: 'TheGamesDB', screenscraper: 'ScreenScraper',
  } // prettier-ignore
  return { name, label: labels[name]!, kind, enabled }
}

const providers = (on: string[] = []) => [
  provider('igdb', 'metadata', on.includes('igdb')),
  provider('hltb', 'facts', on.includes('hltb')),
  provider('opencritic', 'facts', on.includes('opencritic')),
  provider('thegamesdb', 'covers', on.includes('thegamesdb')),
  provider('screenscraper', 'covers', on.includes('screenscraper')),
]

function integration(key: string, overrides: Partial<Integration> = {}): Integration {
  const fields: Record<string, Integration['fields']> = {
    hltb: [
      { name: 'max_age_hours', type: 'number', secret: false, required: false, value: 720, has_value: true, masked: '' },
      { name: 'periodic', type: 'bool', secret: false, required: false, value: false, has_value: true, masked: '' },
      { name: 'periodic_hours', type: 'number', secret: false, required: false, value: 24, has_value: true, masked: '' },
      { name: 'batch', type: 'number', secret: false, required: false, value: 20, has_value: true, masked: '' },
    ],
    opencritic: [
      { name: 'rapidapi_key', type: 'text', secret: true, required: true, value: null, has_value: true, masked: '••••1234' },
    ],
    screenscraper: [
      { name: 'user', type: 'text', secret: false, required: true, value: 'me', has_value: true, masked: '' },
      { name: 'password', type: 'text', secret: true, required: true, value: null, has_value: false, masked: '' },
    ],
  } // prettier-ignore
  return {
    key,
    name: provider(key, 'facts').label,
    kind: 'facts',
    url: 'https://example.com/docs',
    unofficial: key === 'hltb',
    refreshes: key === 'hltb' || key === 'opencritic',
    enabled: false,
    active: false,
    fields: fields[key] ?? [],
    last_ok_at: null,
    last_error: '',
    last_error_at: null,
    last_run_at: null,
    ...overrides,
  }
}

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const input = async (selector: string, value: string) => {
  const el = q(selector) as HTMLInputElement | HTMLSelectElement
  el.value = value
  el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input'))
  await settle()
}

describe('integrations page', () => {
  it('shows status and credits to everyone, but no setting up', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/lookup/providers': providers(['igdb', 'hltb']),
    })
    await renderApp('/integrations', { user: plainUser })
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="integration-hltb"]')).not.toBeNull(),
    )
    expect(q('[data-testid="integration-hltb"] [data-testid="status"]').textContent).toContain(
      'Active',
    )
    expect(
      q('[data-testid="integration-opencritic"] [data-testid="status"]').textContent,
    ).toContain('Off')
    expect(pageText()).toContain('Only admins can set them up.')
    expect(document.querySelector('[data-testid="set-up-hltb"]')).toBeNull()
    expect(q('[data-testid="attribution"]').textContent).toContain(
      'Play times by HowLongToBeat.com',
    )
  })

  it('shows admins errors, incomplete setups and the way to set up', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/lookup/providers': providers(),
      'GET /api/integrations': [
        integration('opencritic', { enabled: true, last_error: 'Quota exceeded', last_error_at: '2026-11-01T10:00:00Z', last_ok_at: '2026-10-01T10:00:00Z' }),
        integration('hltb', { last_error: 'Old error', last_error_at: '2026-10-01T10:00:00Z', last_ok_at: '2026-11-01T10:00:00Z' }),
      ],
    }) // prettier-ignore
    await renderApp('/integrations', { user: staff })
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="last-error"]')).not.toBeNull(),
    )
    const card = q('[data-testid="integration-opencritic"]')
    expect(card.textContent).toContain('Incomplete')
    expect(card.textContent).toContain('Quota exceeded')
    expect(card.textContent).toContain('Last success')
    expect(q('[data-testid="integration-hltb"]').textContent).toContain('Unofficial')
    // An error followed by a success is over.
    expect(q('[data-testid="integration-hltb"]').textContent).not.toContain('Old error')
    expect(q('[data-testid="set-up-hltb"]').getAttribute('href')).toBe('/integrations/hltb')
  })

  it('sets up freshness in days and the background refresh', async () => {
    const calls = mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/lookup/providers': providers(),
      'GET /api/integrations': [integration('hltb')],
      'PATCH /api/integrations/:key': integration('hltb', { enabled: true }),
    })
    const { router } = await renderApp('/integrations/hltb', { user: staff })
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="field-max_age_hours"]')).not.toBeNull(),
    )
    expect(pageText()).toContain('No official API')
    // 720 hours read as 30 days.
    expect((q('[data-testid="field-max_age_hours"]') as HTMLInputElement).value).toBe('30')
    expect((q('[data-testid="unit-max_age_hours"]') as HTMLSelectElement).value).toBe('days')
    await input('[data-testid="field-max_age_hours"]', '2')
    q('[data-testid="enabled"]').click()
    q('[data-testid="field-periodic"]').click()
    await settle()
    await input('[data-testid="field-batch"]', '50')
    document.querySelector('form')!.dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toEqual({
      enabled: true,
      options: { max_age_hours: 48, periodic: true, periodic_hours: 24, batch: 50 },
      secrets: {},
    })
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('integrations'))
  })

  it('keeps secrets write-only, removes them and tests the connection', async () => {
    let tests = 0
    const calls = mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/lookup/providers': providers(),
      'GET /api/integrations': [integration('opencritic'), integration('screenscraper')],
      'PATCH /api/integrations/:key': integration('opencritic'),
      'POST /api/integrations/:key/test': () =>
        ++tests === 1 ? { ok: false, message: 'Bad key' } : { ok: true, message: '3 results' },
    })
    await renderApp('/integrations/opencritic', { user: staff })
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="field-rapidapi_key"]')).not.toBeNull(),
    )
    expect(pageText()).toContain('Saved (••••1234)')
    q('[data-testid="test-integration"]').click()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="test-result"]')).not.toBeNull(),
    )
    expect(q('[data-testid="test-result"]').textContent).toContain('Connection failed: Bad key')
    await input('[data-testid="field-rapidapi_key"]', 'new-key')
    q('[data-testid="test-integration"]').click()
    await vi.waitFor(() =>
      expect(q('[data-testid="test-result"]').textContent).toContain('Connection works'),
    )
    expect(calls.filter((c) => c.method === 'PATCH').at(-1)!.body).toMatchObject({
      secrets: { rapidapi_key: 'new-key' },
    })
    q('[data-testid="remove-rapidapi_key"]').click()
    await settle()
    expect(pageText()).toContain('Removed when you save')
    q('[data-testid="test-integration"]').click()
    await vi.waitFor(() => expect(calls.filter((c) => c.method === 'PATCH')).toHaveLength(3))
    expect(calls.filter((c) => c.method === 'PATCH').at(-1)!.body).toMatchObject({
      secrets: { rapidapi_key: '' },
    })
  })

  it('shows errors when saving fails or for non-admins', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/lookup/providers': providers(),
      'GET /api/integrations': [integration('screenscraper')],
      'PATCH /api/integrations/:key': { status: 400, body: { detail: 'Unknown setting: x' } },
    })
    await renderApp('/integrations/screenscraper', { user: staff })
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="field-user"]')).not.toBeNull(),
    )
    expect(pageText()).toContain('Not set yet')
    document.querySelector('form')!.dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(pageText()).toContain('Unknown setting: x'))
    q('[data-testid="test-integration"]').click()
    await settle()
    expect(document.querySelector('[data-testid="test-result"]')).toBeNull()

    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/integrations': {
        status: 403,
        body: { detail: 'Only admins can change integrations.' },
      },
    })
    await renderApp('/integrations/hltb')
    await vi.waitFor(() => expect(pageText()).toContain('Only admins can change integrations.'))
  })
})

describe('facts and covers', () => {
  const release = makeRelease({
    id: 'rel-1',
    work_id: 'work-1',
    facts: {
      hltb: { source: 'hltb', title: 'Mario Kart 8 Deluxe', url: 'https://howlongtobeat.com/game/1', values: { main: 12.5 }, status: 'ok', pinned: false, fetched_at: '2026-11-01T10:00:00Z' },
      opencritic: { source: 'opencritic', title: '', url: '', values: {}, status: 'missing', pinned: false, fetched_at: '2026-11-01T10:00:00Z' },
    },
  }) // prettier-ignore
  const routes = (extra: Record<string, unknown> = {}) => ({
    ...layoutRoutes(makeLibrary()),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/libraries/lib-1/items': { count: 0, items: [] },
    'GET /api/watchlist': [],
    'GET /api/catalog/works/work-1': makeWork({ releases: [release] }),
    'GET /api/catalog/releases/rel-1': release,
    'GET /api/lookup/providers': providers(['hltb', 'opencritic', 'thegamesdb']),
    ...extra,
  })

  it('shows play time on the game, refreshes it and links to the sources', async () => {
    const calls = mockApi(
      routes({ 'POST /api/catalog/works/:id/facts/refresh': { refreshed: true } }),
    )
    await renderApp('/works/work-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="fact-sources"]')).not.toBeNull(),
    )
    expect(q('[data-testid="hltb-bars"]').textContent).toContain('12.5 h')
    await vi.waitFor(() => expect(calls.some((c) => c.path.endsWith('/facts/refresh'))).toBe(true))
    const sources = q('[data-testid="fact-sources"]').textContent
    expect(sources).toContain('View on HowLongToBeat')
    expect(sources).toContain('Not found on OpenCritic')
    expect(q('[data-testid="match-opencritic"]').getAttribute('href')).toContain(
      '/works/work-1/facts/opencritic?back=',
    )
  })

  it('picks a match by hand or automatically', async () => {
    const calls = mockApi(
      routes({
        'GET /api/catalog/works/:id/facts/:source/candidates': (call: { query: URLSearchParams }) =>
          call.query.get('q') === 'nothing'
            ? []
            : [{ external_id: '9', title: 'Mario Kart 8', url: 'https://howlongtobeat.com/game/9', year: 2014, platforms: 'Wii U', values: { main: 10, extra: 20 } }],
        'PUT /api/catalog/works/:id/facts/:source': release.facts.hltb,
        'DELETE /api/catalog/works/:id/facts/:source': { status: 204 },
        'POST /api/catalog/works/:id/facts/refresh': { refreshed: true },
      }),
    ) // prettier-ignore
    const { router } = await renderApp('/works/work-1/facts/hltb?back=/works/work-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="fact-candidates"]')).not.toBeNull(),
    )
    expect(pageText()).toContain('Match: HowLongToBeat')
    expect(q('[data-testid="current-match"]').textContent).toContain('Play time (main): 12.5 h')
    expect(q('[data-testid="fact-candidates"]').textContent).toContain(
      'Wii U · Play time (main): 10 h · Play time (+ extras): 20 h',
    )
    await input('[data-testid="fact-query"]', 'nothing')
    q('[data-testid="fact-search"]').dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(pageText()).toContain('Nothing found.'))
    await input('[data-testid="fact-query"]', '')
    q('[data-testid="fact-search"]').dispatchEvent(new Event('submit'))
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="choose-9"]')).not.toBeNull(),
    )
    q('[data-testid="choose-9"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/works/work-1'))
    expect(calls.find((c) => c.method === 'PUT')!.body).toEqual({ external_id: '9' })

    await router.push('/works/work-1/facts/hltb?back=/works/work-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="auto-match"]')).not.toBeNull(),
    )
    q('[data-testid="auto-match"]').click()
    await vi.waitFor(() =>
      expect(
        calls.some((c) => c.path.endsWith('/facts/refresh') && c.query.get('force') === 'true'),
      ).toBe(true),
    )
    expect(calls.some((c) => c.method === 'DELETE')).toBe(true)
  })

  it('reports a failing source while matching', async () => {
    mockApi(
      routes({
        'GET /api/catalog/works/:id/facts/:source/candidates': {
          status: 502,
          body: { detail: 'HowLongToBeat changed its site' },
        },
      }),
    )
    await renderApp('/works/work-1/facts/hltb')
    await vi.waitFor(() => expect(pageText()).toContain('HowLongToBeat changed its site'))
  })

  it('finds and takes a cover', async () => {
    const calls = mockApi(
      routes({
        'GET /api/catalog/releases/:id/cover-candidates': [
          { source: 'thegamesdb', title: 'Mario Kart 8 Deluxe', region: 'pal', platform: 'switch', width: 600, height: 980, token: 'tok/1' },
        ],
        'POST /api/catalog/releases/:id/cover-from': release,
      }),
    ) // prettier-ignore
    const { router, queryClient } = await renderApp('/releases/rel-1/covers?back=/works/work-1')
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="cover-candidate"]')).not.toBeNull(),
    )
    expect(q('[data-testid="cover-candidate"] img').getAttribute('src')).toBe(
      '/api/catalog/cover-preview?token=tok%2F1',
    )
    expect(q('[data-testid="cover-candidate"]').textContent).toContain('TheGamesDB · switch · pal')
    // The source's size until the image is there, then the image's own.
    expect(q('[data-testid="cover-size"]').textContent.trim()).toBe('600×980')
    const img = q('[data-testid="cover-candidate"] img') as HTMLImageElement
    Object.defineProperty(img, 'naturalWidth', { value: 1200 })
    Object.defineProperty(img, 'naturalHeight', { value: 1960 })
    img.dispatchEvent(new Event('load'))
    await settle()
    expect(q('[data-testid="cover-size"]').textContent.trim()).toBe('1200×1960')
    q('[data-testid="cover-candidate"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/works/work-1'))
    expect(calls.find((c) => c.method === 'POST' && c.path.endsWith('cover-from'))!.body).toEqual({
      token: 'tok/1',
    })
    // The sidebar's group tree shows catalog data too.
    const invalidated = invalidate.mock.calls.map((c) => (c[0] as { queryKey: unknown }).queryKey)
    expect(invalidated).toEqual(expect.arrayContaining([['works'], ['items'], ['tree']]))
  })

  it('searches covers for another title', async () => {
    const calls = mockApi(routes({ 'GET /api/catalog/releases/:id/cover-candidates': [] }))
    await renderApp('/releases/rel-1/covers')
    await vi.waitFor(() => expect(pageText()).toContain('without the edition'))
    await input('[data-testid="cover-query"]', 'As Dusk Falls')
    q('[data-testid="cover-search"]').dispatchEvent(new Event('submit'))
    await vi.waitFor(() =>
      expect(calls.some((c) => c.query.get('q') === 'As Dusk Falls')).toBe(true),
    )
  })

  it('takes a cover for one copy only', async () => {
    // The copy says which library it is in.
    const copy = makeItem({ id: 'item-1', library_id: 'lib-1' })
    const calls = mockApi(
      routes({
        'GET /api/catalog/releases/:id/cover-candidates': [
          { source: 'thegamesdb', title: 'Mario Kart 8 Deluxe', region: 'pal', platform: 'switch', width: 600, height: 980, token: 'tok/1' },
        ],
        'GET /api/items/:id': copy,
        'GET /api/libraries/:id/items/:id': copy,
        'POST /api/libraries/:id/items/:id/cover-from': copy,
      }),
    ) // prettier-ignore
    const { router } = await renderApp('/releases/rel-1/covers?back=/works/work-1&item=item-1')
    await vi.waitFor(() => expect(pageText()).toContain('only for this copy'))
    q('[data-testid="cover-candidate"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/works/work-1'))
    const call = calls.find((c) => c.method === 'POST' && c.path.endsWith('cover-from'))!
    expect(call.path).toBe('/api/libraries/lib-1/items/item-1/cover-from')
    expect(call.body).toEqual({ token: 'tok/1' })
  })

  it('explains when no cover source is set up', async () => {
    mockApi(routes({ 'GET /api/lookup/providers': providers() }))
    await renderApp('/releases/rel-1/covers')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="no-cover-sources"]')).not.toBeNull(),
    )
  })
})
