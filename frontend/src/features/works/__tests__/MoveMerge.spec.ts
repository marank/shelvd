import { describe, expect, it, vi } from 'vitest'
import { layoutRoutes, makeLibrary, makeRelease, makeWork } from '@/test/fixtures'
import { mockApi, pageText, renderApp, settle } from '@/test/utils'

const release = makeRelease({
  id: 'rel-1',
  work_id: 'work-1',
  title: 'Dave',
  edition: 'Complete Edition',
})
const summary = {
  id: 'work-2',
  title: 'Dave the Diver',
  platforms: ['Switch'],
  releases: 1,
  cover_url: null,
}

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary()),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/libraries/lib-1/items': { count: 0, items: [] },
    'GET /api/watchlist': [],
    'GET /api/catalog/works/work-1': makeWork({ id: 'work-1', title: 'Dave: Complete Edition' }),
    'GET /api/catalog/works/work-2': makeWork({ id: 'work-2' }),
    'GET /api/catalog/releases/rel-1': release,
    'GET /api/catalog/works': [summary],
    ...extra,
  }
}

async function type(selector: string, value: string) {
  const input = document.querySelector(selector) as HTMLInputElement
  input.value = value
  input.dispatchEvent(new Event('input'))
  await settle()
}

const click = (selector: string) => (document.querySelector(selector) as HTMLElement).click()

async function submit() {
  await settle()
  document.querySelector('form')!.dispatchEvent(new Event('submit'))
  await settle()
}

describe('move release and merge game', () => {
  it('moves a release to another game and opens it in the library', async () => {
    const calls = mockApi(
      routes({ 'POST /api/catalog/releases/rel-1/move': { ...release, work_id: 'work-2' } }),
    )
    const { router } = await renderApp('/releases/rel-1/move?library=lib-1&back=/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid=work-search]')).not.toBeNull(),
    )
    await submit()
    expect(pageText()).toContain('Pick a game.')
    await type('[data-testid=work-search]', 'dave')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid=work-option]')).not.toBeNull(),
    )
    expect(calls.find((c) => c.path === '/api/catalog/works')!.query.get('exclude')).toBe('work-1')
    click('[data-testid=work-option]')
    await submit()
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({ work_id: 'work-2', title: '' })
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/works/work-2'))
  })

  it('splits a release off into a game of its own', async () => {
    const calls = mockApi(
      routes({ 'POST /api/catalog/releases/rel-1/move': { ...release, work_id: 'work-3' } }),
    )
    const { router } = await renderApp('/releases/rel-1/move?back=/l/lib-1')
    await vi.waitFor(() => expect(document.querySelector('[data-testid=mode-own]')).not.toBeNull())
    click('[data-testid=mode-own]')
    await settle()
    expect((document.querySelector('#m-title') as HTMLInputElement).value).toBe(
      'Dave Complete Edition',
    )
    await type('#m-title', 'Dave Remake')
    await submit()
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({
      work_id: null,
      title: 'Dave Remake',
    })
    // The release now belongs to its own new game: that game's page opens.
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/works/work-3'))
  })

  it('shows when nothing matches and when moving fails', async () => {
    mockApi(
      routes({
        'GET /api/catalog/works': [],
        'POST /api/catalog/releases/rel-1/move': {
          status: 400,
          body: { detail: 'The release already belongs to this game.' },
        },
      }),
    )
    await renderApp('/releases/rel-1/move')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid=work-search]')).not.toBeNull(),
    )
    await type('[data-testid=work-search]', 'zzz')
    await vi.waitFor(() => expect(document.querySelector('[data-testid=no-games]')).not.toBeNull())
    click('[data-testid=mode-own]')
    await submit()
    await vi.waitFor(() =>
      expect(pageText()).toContain('The release already belongs to this game.'),
    )
  })

  it('merges a game into another', async () => {
    const calls = mockApi(
      routes({
        'POST /api/catalog/works/work-1/merge': makeWork({ id: 'work-2', title: 'Dave the Diver' }),
      }),
    )
    const { router } = await renderApp('/works/work-1/merge?library=lib-1')
    // The search starts with the title minus its edition.
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid=work-option]')).not.toBeNull(),
    )
    expect(calls.find((c) => c.path === '/api/catalog/works')!.query.get('q')).toBe('Dave')
    expect(pageText()).toContain('Dave: Complete Edition')
    await submit()
    expect(pageText()).toContain('Pick a game.')
    click('[data-testid=work-option]')
    await submit()
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({ target_id: 'work-2' })
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/works/work-2'))
  })

  it('shows errors when merging fails', async () => {
    mockApi(
      routes({
        'POST /api/catalog/works/work-1/merge': {
          status: 400,
          body: { detail: "A game can't be merged into itself." },
        },
      }),
    )
    await renderApp('/works/work-1/merge')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid=work-option]')).not.toBeNull(),
    )
    click('[data-testid=work-option]')
    await submit()
    await vi.waitFor(() => expect(pageText()).toContain("A game can't be merged into itself."))
  })
})
