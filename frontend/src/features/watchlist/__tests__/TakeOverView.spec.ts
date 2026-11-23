import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { keys } from '@/features/library/composables/queryKeys'
import { makeItem } from '@/test/fixtures'
import { mockApi, pageText, renderComponent, settle } from '@/test/utils'
import TakeOverView from '../views/TakeOverView.vue'
import {
  $,
  $$,
  LIB,
  libraries,
  location,
  person,
  submitForm,
  tracking,
  type,
  upcoming,
} from './fixtures'

const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string) => void>(),
  error: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

const release = upcoming({
  id: 'r-1',
  title: 'Mario Kart World',
  work_id: 'w-mkw',
  is_released: true,
})

function routes(entry = tracking(), extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries': libraries,
    'GET /api/watchlist/:id': entry,
    'GET /api/libraries/:id/locations': (_: unknown, p: Record<string, string>) =>
      p.id === LIB ? [location] : [],
    'GET /api/libraries/:id/people': (_: unknown, p: Record<string, string>) =>
      p.id === LIB ? [person] : [],
    ...extra,
  })
}

describe('TakeOverView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 1, 12))
  })
  afterEach(() => vi.useRealTimers())

  it('creates the copy and opens it on the work page', async () => {
    const entry = tracking({
      id: 't-7',
      release,
      status: 'bought',
      library: { id: LIB, name: 'Games' },
      shop: 'Media Markt',
      price: '49.99',
      ordered_on: '2026-10-15',
      notes: 'Launch edition',
    })
    const calls = routes(entry, {
      'POST /api/watchlist/:id/take-over': {
        status: 201,
        body: makeItem({ id: 'i-new', title: 'Mario Kart World', release }),
      },
    })
    const { router, queryClient } = await renderComponent(TakeOverView, {
      url: '/watchlist/t-7/take-over',
    })
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    await vi.waitFor(() => expect(($('#take-library') as HTMLSelectElement).value).toBe(LIB))
    // Only libraries the user can edit.
    expect($$('#take-library option').map((o) => o.textContent.trim())).toEqual(['Games', 'Shared'])
    expect(($('#take-acquired') as HTMLInputElement).value).toBe('2026-10-15')
    const carried = $('[data-testid="carried"]').textContent
    expect(carried).toContain('Media Markt')
    expect(carried).toContain('€49.99')
    expect(carried).toContain('10/15/2026')
    expect(carried).toContain('Launch edition')
    expect(carried).toContain('Bought')
    await vi.waitFor(() => expect($$('#take-location option')).toHaveLength(2))
    expect($('#take-location').textContent).toContain('Living room / Shelf')

    type('#take-format', 'digital')
    type('#take-condition', 'new')
    type('#take-completeness', 'sealed')
    type('#take-location', 'loc-1')
    type('#take-owner', 'per-1')
    type('#take-notes', ' gift ')
    await nextTick()
    submitForm()
    await settle()

    const post = calls.find((c) => c.method === 'POST')
    expect(post?.path).toBe('/api/watchlist/t-7/take-over')
    expect(post?.body).toEqual({
      library_id: LIB,
      format: 'digital',
      condition: 'new',
      completeness: 'sealed',
      location_id: 'loc-1',
      owner_id: 'per-1',
      acquired_on: '2026-10-15',
      notes: 'gift',
    })
    expect(toast.success).toHaveBeenCalledWith('“Mario Kart World” is now in Games')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/items/i-new'))
    const invalidated = invalidate.mock.calls.map((c) => (c[0] as { queryKey: unknown }).queryKey)
    expect(invalidated).toEqual(
      expect.arrayContaining([keys.trackings, keys.items(LIB), keys.tree(LIB), keys.libraries]),
    )
  })

  it('defaults to the first editable library and today, and resets places on switch', async () => {
    const calls = routes(tracking({ release, library: { id: 'lib-2', name: 'Family' } }), {
      'POST /api/watchlist/:id/take-over': { status: 400, body: { detail: 'Nope.' } },
    })
    await renderComponent(TakeOverView, { url: '/watchlist/t-1/take-over' })
    await vi.waitFor(() => expect(($('#take-library') as HTMLSelectElement).value).toBe(LIB))
    expect(($('#take-acquired') as HTMLInputElement).value).toBe('2026-11-01')
    expect(pageText()).toContain('No purchase details recorded.')
    await vi.waitFor(() => expect($$('#take-location option')).toHaveLength(2))
    type('#take-location', 'loc-1')
    await nextTick()
    type('#take-library', 'lib-3')
    await settle()
    expect(($('#take-location') as HTMLSelectElement).value).toBe('')
    type('#take-acquired', '')
    await nextTick()
    submitForm()
    await settle()
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      library_id: 'lib-3',
      format: 'physical',
      condition: null,
      completeness: null,
      location_id: null,
      owner_id: null,
      acquired_on: null,
      notes: '',
    })
    expect($('[data-testid="edit-error"]').textContent).toContain('Nope.')
  })

  it('refuses entries of others and users without editable libraries (German)', async () => {
    const calls = mockApi({
      'GET /api/libraries': [libraries[1]],
      'GET /api/watchlist/:id': tracking({ release, is_mine: false, user: 'bob' }),
    })
    await renderComponent(TakeOverView, { url: '/watchlist/t-1/take-over', locale: 'de' })
    await vi.waitFor(() => expect($$('[data-testid="not-mine"]')).toHaveLength(1))
    expect(pageText()).toContain('In Bibliothek übernehmen')
    submitForm()
    await settle()
    expect(calls.some((c) => c.method === 'POST')).toBe(false)

    mockApi({
      'GET /api/libraries': [libraries[1]],
      'GET /api/watchlist/:id': tracking({ release }),
    })
    await renderComponent(TakeOverView, { url: '/watchlist/t-1/take-over', locale: 'de' })
    await vi.waitFor(() =>
      expect($('[data-testid="no-libraries"]').textContent).toContain('in keiner Bibliothek'),
    )
  })

  it('shows load errors', async () => {
    mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': { status: 404, body: { detail: 'Gone.' } },
    })
    await renderComponent(TakeOverView, { url: '/watchlist/t-1/take-over' })
    await vi.waitFor(() => expect($('[data-testid="load-error"]').textContent).toContain('Gone.'))
  })
})
