import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { keys } from '@/features/library/composables/queryKeys'
import { mockApi, pageText, renderComponent, settle } from '@/test/utils'
import WatchlistEditView from '../views/WatchlistEditView.vue'
import { $, $$, LIB, libraries, submitForm, tracking, type, upcoming } from './fixtures'

const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string) => void>(),
  error: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

const release = upcoming({
  id: 'r-9',
  title: 'Metroid Prime 4',
  edition: 'Steelbook',
  release_precision: 'quarter',
  release_date: '2027-01-01',
  sort_date: '2027-03-31',
})

describe('WatchlistEditView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('tracks a release with purchase details and goes back', async () => {
    const calls = mockApi({
      'GET /api/libraries': libraries,
      'GET /api/catalog/releases/:id': release,
      'POST /api/watchlist': (call: { body: unknown }) => ({
        status: 201,
        body: tracking({ release, ...(call.body as object) }),
      }),
    })
    const { router, queryClient } = await renderComponent(WatchlistEditView, {
      url: `/watchlist/new?release=r-9&library=${LIB}&back=/l/${LIB}/works/w-1`,
    })
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    await vi.waitFor(() => expect($$('[data-testid="release-header"]')).toHaveLength(1))
    expect(pageText()).toContain('Add to Upcoming')
    expect($('[data-testid="release-header"]').textContent).toContain('Q1 2027')
    expect(($('#tracking-library') as HTMLSelectElement).value).toBe(LIB)
    expect(($('[data-testid="status-watching"]') as HTMLInputElement).checked).toBe(true)
    expect(pageText()).toContain("Bought, but it hasn't arrived yet.")
    expect($('[data-testid="edit-back"]').getAttribute('href')).toBe(`/l/${LIB}/works/w-1`)

    $('[data-testid="status-preordered"]').click()
    type('#tracking-shop', ' Amazon ')
    type('#tracking-price', '59,99')
    type('#tracking-ordered', '2026-10-30')
    type('#tracking-library', '')
    type('#tracking-notes', ' Steelbook ')
    await nextTick()
    submitForm()
    await settle()

    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      release_id: 'r-9',
      status: 'preordered',
      library_id: null,
      shop: 'Amazon',
      price: '59.99',
      ordered_on: '2026-10-30',
      notes: 'Steelbook',
    })
    expect(toast.success).toHaveBeenCalledWith('“Metroid Prime 4” is now on Upcoming')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe(`/l/${LIB}/works/w-1`))
    expect(
      invalidate.mock.calls.map((c) => (c[0] as { queryKey: unknown }).queryKey),
    ).toContainEqual(keys.trackings)
  })

  it('shows the API error when the release is tracked already', async () => {
    mockApi({
      'GET /api/libraries': libraries,
      'GET /api/catalog/releases/:id': release,
      'POST /api/watchlist': { status: 409, body: { detail: 'You track this release already.' } },
    })
    const { router } = await renderComponent(WatchlistEditView, {
      url: '/watchlist/new?release=r-9',
    })
    await vi.waitFor(() => expect($$('[data-testid="release-header"]')).toHaveLength(1))
    expect(($('#tracking-library') as HTMLSelectElement).value).toBe('')
    expect($('[data-testid="edit-back"]').getAttribute('href')).toBe('/upcoming')
    submitForm()
    await settle()
    expect($('[data-testid="edit-error"]').textContent).toContain('already')
    expect(router.currentRoute.value.name).toBe('tracking-new')
  })

  it('needs a release', async () => {
    const calls = mockApi({ 'GET /api/libraries': libraries })
    await renderComponent(WatchlistEditView, { url: '/watchlist/new?back=//evil.example' })
    expect($('[data-testid="no-release"]').textContent).toContain('No release chosen.')
    expect($('[data-testid="edit-back"]').getAttribute('href')).toBe('/upcoming')
    submitForm()
    await settle()
    expect(calls.some((c) => c.method === 'POST')).toBe(false)

    mockApi({
      'GET /api/libraries': libraries,
      'GET /api/catalog/releases/:id': { status: 404, body: { detail: 'Release not found.' } },
    })
    await renderComponent(WatchlistEditView, { url: '/watchlist/new?release=nope' })
    await vi.waitFor(() =>
      expect($('[data-testid="load-error"]').textContent).toContain('Release not found.'),
    )
  })

  it('edits an entry', async () => {
    const entry = tracking({
      id: 't-5',
      status: 'preordered',
      library: { id: 'lib-3', name: 'Shared' },
      shop: 'Shop',
      price: '20.00',
      ordered_on: '2026-09-01',
      notes: 'note',
    })
    const calls = mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': entry,
      'PATCH /api/catalog/releases/:id': entry.release,
      'PATCH /api/watchlist/:id': (call: { body: unknown }) => ({
        ...entry,
        ...(call.body as object),
      }),
    })
    const { router } = await renderComponent(WatchlistEditView, { url: '/watchlist/t-5/edit' })
    await vi.waitFor(() => expect(($('#tracking-shop') as HTMLInputElement).value).toBe('Shop'))
    // The page is about the game; the date can be changed right here.
    expect($('h1').textContent).toContain('Metroid Prime 4')
    expect($$('[data-testid="released"]')).toHaveLength(0)
    $('[data-testid="precision-tba"]').click()
    await nextTick()
    expect(($('#tracking-library') as HTMLSelectElement).value).toBe('lib-3')
    expect(($('#tracking-price') as HTMLInputElement).value).toBe('20.00')
    expect(($('[data-testid="status-preordered"]') as HTMLInputElement).checked).toBe(true)

    $('[data-testid="status-bought"]').click()
    type('#tracking-price', '')
    type('#tracking-ordered', '')
    await nextTick()
    submitForm()
    await settle()
    expect(
      calls.find((c) => c.path === '/api/watchlist/t-5' && c.method === 'PATCH'),
    ).toMatchObject({
      body: {
        status: 'bought',
        library_id: 'lib-3',
        shop: 'Shop',
        price: null,
        ordered_on: null,
        notes: 'note',
      },
    })
    expect(calls.find((c) => c.path === '/api/catalog/releases/r-1')?.body).toMatchObject({
      release_precision: 'tba',
    })
    expect(toast.success).toHaveBeenCalledWith('Saved')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('upcoming'))
  })

  it('shows entries of others read-only (German)', async () => {
    const calls = mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': tracking({ id: 't-6', is_mine: false, user: 'bob' }),
    })
    await renderComponent(WatchlistEditView, { url: '/watchlist/t-6/edit', locale: 'de' })
    await vi.waitFor(() => expect($$('[data-testid="read-only"]')).toHaveLength(1))
    expect(pageText()).toContain('Dieser Eintrag gehört bob.')
    expect(($('#tracking-shop') as HTMLInputElement).disabled).toBe(true)
    // Others' entries: no date editing, no removing.
    expect($$('[data-testid="release-date"]')).toHaveLength(0)
    expect($$('[data-testid="remove-entry"]')).toHaveLength(0)
    submitForm()
    await settle()
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
  })

  it('leaves the date alone when it is unchanged', async () => {
    const calls = mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': tracking({ id: 't-7' }),
      'PATCH /api/watchlist/:id': tracking({ id: 't-7' }),
    })
    await renderComponent(WatchlistEditView, { url: '/watchlist/t-7/edit' })
    await vi.waitFor(() => expect($$('[data-testid="release-date"]')).toHaveLength(1))
    submitForm()
    await settle()
    expect(calls.some((c) => c.path.startsWith('/api/catalog/'))).toBe(false)
    expect(calls.some((c) => c.method === 'PATCH')).toBe(true)
  })

  it('offers taking over once released, the game, and removing', async () => {
    const out = tracking({
      id: 't-8',
      release: upcoming({ id: 'r-8', title: 'Out Now', work_id: 'w-8', is_released: true }),
    })
    const calls = mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': out,
      'DELETE /api/watchlist/:id': { status: 204 },
    })
    const { router } = await renderComponent(WatchlistEditView, { url: '/watchlist/t-8/edit' })
    await vi.waitFor(() => expect($$('[data-testid="released"]')).toHaveLength(1))
    expect($('[data-testid="released"] a').getAttribute('href')).toBe('/watchlist/t-8/take-over')
    expect($('[data-testid="take-over-button"]').className).toContain('no-underline!')
    $('[data-testid="remove-entry"]').click()
    await settle()
    expect($('[data-testid="confirm-dialog"]').textContent).toContain('“Out Now” is removed')
    $('[data-testid="confirm-button"]').click()
    await settle()
    expect(calls.find((c) => c.method === 'DELETE')?.path).toBe('/api/watchlist/t-8')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('upcoming'))
  })

  it('says where a released entry already sits instead of offering to take it over', async () => {
    const owned = tracking({
      id: 't-7',
      release: upcoming({ id: 'r-7', title: 'Wolverine', work_id: 'w-7', is_released: true }),
      owned_in: [{ id: LIB, name: 'Games' }],
    })
    const calls = mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': owned,
      'DELETE /api/watchlist/:id': { status: 204 },
    })
    const { router } = await renderComponent(WatchlistEditView, { url: '/watchlist/t-7/edit' })
    await vi.waitFor(() => expect($$('[data-testid="owned"]')).toHaveLength(1))
    expect($$('[data-testid="released"]')).toHaveLength(0)
    expect($('[data-testid="owned"]').textContent).toContain('“Wolverine” is already in Games.')
    expect($(`[data-testid="owned-${LIB}"]`).getAttribute('href')).toBe('/releases/r-7')
    $('[data-testid="owned-remove"]').click()
    await settle()
    $('[data-testid="confirm-button"]').click()
    await settle()
    expect(calls.find((c) => c.method === 'DELETE')?.path).toBe('/api/watchlist/t-7')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('upcoming'))
  })

  it('shows load errors of an entry', async () => {
    mockApi({
      'GET /api/libraries': libraries,
      'GET /api/watchlist/:id': { status: 404, body: { detail: 'Not found.' } },
    })
    await renderComponent(WatchlistEditView, { url: '/watchlist/t-x/edit' })
    await vi.waitFor(() =>
      expect($('[data-testid="load-error"]').textContent).toContain('Not found.'),
    )
  })
})
