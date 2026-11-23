import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { mockApi, pageText, renderComponent, settle } from '@/test/utils'
import UpcomingView from '../views/UpcomingView.vue'
import { $, $$, LIB, libraries, openMenu, tracking, upcoming } from './fixtures'

const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string) => void>(),
  error: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

const entries = [
  tracking({
    id: 't-tba',
    release: upcoming({
      id: 'r-tba',
      title: 'Hollow Knight Silksong 2',
      release_date: null,
      release_precision: 'tba',
      sort_date: '9999-12-31',
    }),
  }),
  tracking({
    id: 't-dec',
    status: 'preordered',
    shop: 'Amazon',
    price: '59.99',
    release: upcoming({
      id: 'r-dec',
      title: 'Pokémon Winds',
      release_date: '2026-12-01',
      release_precision: 'month',
      sort_date: '2026-12-01',
    }),
  }),
  tracking({
    id: 't-nov',
    library: { id: 'lib-3', name: 'Shared' },
    release: upcoming({ id: 'r-nov', title: 'Metroid Prime 4', work_id: 'w-mp4' }),
  }),
  tracking({
    id: 't-2027',
    status: 'bought',
    release: upcoming({
      id: 'r-q',
      title: 'Zelda Next',
      release_date: '2027-04-01',
      release_precision: 'quarter',
      sort_date: '2027-06-30',
    }),
  }),
  tracking({
    id: 't-out',
    status: 'bought',
    release: upcoming({
      id: 'r-out',
      title: 'Mario Kart World',
      release_date: '2026-10-01',
      sort_date: '2026-10-01',
      is_released: true,
    }),
  }),
]
const foreign = tracking({
  id: 't-bob',
  user: 'bob',
  is_mine: false,
  library: { id: LIB, name: 'Games' },
  release: upcoming({ id: 'r-bob', title: 'Kirby Air Riders' }),
})

function routes(extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries': libraries,
    'GET /api/watchlist': (call: { query: URLSearchParams }) =>
      call.query.get('mine') === 'true' ? entries : [...entries, foreign],
    ...extra,
  })
}

const card = (id: string) => $(`[data-testid="tracking-card"][data-id="${id}"]`)

describe('UpcomingView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 1, 12))
  })
  afterEach(() => vi.useRealTimers())

  it('groups entries like a release calendar', async () => {
    const calls = routes()
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(5))
    expect(calls.find((c) => c.path === '/api/watchlist')?.query.get('mine')).toBe('true')

    const groups = $$('section[data-testid^="group-"]')
    expect(groups.map((g) => g.dataset.testid)).toEqual([
      'group-released',
      'group-month',
      'group-month',
      'group-year',
      'group-tba',
    ])
    expect(groups.map((g) => g.querySelector('h2')!.textContent)).toEqual([
      expect.stringContaining('Out now — ready to take over'),
      expect.stringContaining('November 2026'),
      expect.stringContaining('December 2026'),
      expect.stringContaining('2027'),
      expect.stringContaining('TBA — no date yet'),
    ])
    expect(groups[0]!.textContent).toContain('1 entry')

    // Released: primary take-over action.
    expect(card('t-out').querySelector('[data-testid="take-over"]')?.getAttribute('href')).toBe(
      '/watchlist/t-out/take-over',
    )
    expect(card('t-nov').querySelector('[data-testid="take-over"]')).toBeNull()
    // Date with relative hint; the whole row opens the entry.
    expect(card('t-nov').querySelector('[data-testid="tracking-date"]')?.textContent).toContain(
      'in 3 weeks',
    )
    expect(card('t-nov').querySelector('[data-testid="open-entry"]')?.getAttribute('href')).toBe(
      '/watchlist/t-nov/edit',
    )
    expect(card('t-nov').querySelector('[data-testid="library"]')?.textContent).toContain(
      'Library: Shared',
    )
    // The menu: "View game" opens the game, which shows the library you're in.
    await openMenu(card('t-nov').querySelector('[data-testid="entry-menu"]')!)
    await settle()
    expect($('[data-testid="work-link"]').getAttribute('href')).toBe('/works/w-mp4')
    expect($('[data-testid="change-date"]').getAttribute('href')).toBe(
      '/releases/r-nov/edit?back=/upcoming',
    )
    expect($('[data-testid="edit"]').getAttribute('href')).toBe('/watchlist/t-nov/edit')
    expect(card('t-dec').querySelector('[data-testid="purchase"]')?.textContent).toContain(
      'Amazon · €59.99',
    )
    expect(card('t-2027').textContent).toContain('Q2 2027')
    expect(card('t-tba').textContent).toContain('TBA')
    expect(
      card('t-dec').querySelector('[data-testid="status-badge"]')?.getAttribute('data-status'),
    ).toBe('preordered')
  })

  it('shows entries of other members read-only', async () => {
    const calls = routes()
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(5))
    $('[data-testid="scope-all"]').click()
    await settle()
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(6))
    expect(calls.at(-1)?.query.get('mine')).toBe('false')
    const bob = card('t-bob')
    expect(bob.querySelector('[data-testid="owner"]')?.textContent).toContain('by bob')
    expect(bob.textContent).toContain('Library: Games')
    // Read-only: the menu only opens and shows; no status, no removing.
    await openMenu(bob.querySelector('[data-testid="entry-menu"]')!)
    await settle()
    expect($$('[data-testid="set-watching"]')).toHaveLength(0)
    expect($$('[data-testid="delete"]')).toHaveLength(0)
    expect($('[data-testid="edit"]').getAttribute('href')).toBe('/watchlist/t-bob/edit')
    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await settle()

    // Deselecting the active toggle keeps the scope.
    $('[data-testid="scope-all"]').click()
    await settle()
    expect($$('[data-testid="tracking-card"]')).toHaveLength(6)
    $('[data-testid="scope-mine"]').click()
    await settle()
    expect($$('[data-testid="tracking-card"]')).toHaveLength(5)
  })

  it('marks released entries that already sit in a library instead of offering a take-over', async () => {
    const owned = tracking({
      id: 't-owned',
      owned_in: [{ id: LIB, name: 'Games' }],
      release: upcoming({ id: 'r-owned', title: 'Wolverine', is_released: true }),
    })
    mockApi({ 'GET /api/libraries': libraries, 'GET /api/watchlist': [owned] })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(1))
    expect(card('t-owned').querySelector('[data-testid="take-over"]')).toBeNull()
    expect(card('t-owned').querySelector('[data-testid="owned-in"]')?.textContent).toContain(
      'Already in Games',
    )
  })

  it('filters by status', async () => {
    routes()
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(5))
    expect($('[data-testid="filter-bought"]').textContent).toContain('2')

    $('[data-testid="filter-bought"]').click()
    await nextTick()
    expect($$('[data-testid="tracking-card"]').map((c) => c.dataset.id)).toEqual([
      't-out',
      't-2027',
    ])
    expect($('[data-testid="filter-bought"]').getAttribute('aria-pressed')).toBe('true')
    $('[data-testid="filter-preordered"]').click()
    await nextTick()
    expect($$('[data-testid="tracking-card"]')).toHaveLength(3)
    $('[data-testid="filter-bought"]').click()
    $('[data-testid="filter-preordered"]').click()
    await nextTick()
    expect($$('[data-testid="tracking-card"]')).toHaveLength(5)
  })

  it('says when no entry has the chosen status', async () => {
    mockApi({ 'GET /api/libraries': libraries, 'GET /api/watchlist': [tracking()] })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(1))
    $('[data-testid="filter-bought"]').click()
    await nextTick()
    expect($('[data-testid="no-match"]').textContent).toContain('No entries with this status.')
  })

  it('changes the status from the menu', async () => {
    const calls = routes({
      'PATCH /api/watchlist/:id': (call: { body: unknown }) => ({
        ...entries[2],
        ...(call.body as object),
      }),
    })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(5))
    // Same value: nothing happens.
    await openMenu(card('t-nov').querySelector('[data-testid="entry-menu"]')!)
    await settle()
    $('[data-testid="set-watching"]').click()
    await settle()
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)

    await openMenu(card('t-nov').querySelector('[data-testid="entry-menu"]')!)
    await settle()
    $('[data-testid="set-preordered"]').click()
    await settle()
    const patch = calls.find((c) => c.method === 'PATCH')
    expect(patch?.path).toBe('/api/watchlist/t-nov')
    expect(patch?.body).toEqual({ status: 'preordered' })
    expect(toast.success).toHaveBeenCalledWith('Status changed: Pre-ordered')
  })

  it('reports a failed status change', async () => {
    routes({ 'PATCH /api/watchlist/:id': { status: 403, body: { detail: 'Not yours.' } } })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(5))
    await openMenu(card('t-nov').querySelector('[data-testid="entry-menu"]')!)
    await settle()
    $('[data-testid="set-bought"]').click()
    await settle()
    expect(toast.error).toHaveBeenCalledWith('Not yours.')
  })

  it('deletes an entry after confirmation', async () => {
    let fail = true
    const calls = routes({
      'DELETE /api/watchlist/:id': () =>
        fail ? { status: 500, body: { detail: 'Boom' } } : { status: 204 },
    })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(5))
    await openMenu(card('t-dec').querySelector('[data-testid="entry-menu"]')!)
    await settle()
    $('[data-testid="delete"]').click()
    await settle()
    expect($('[data-testid="confirm-dialog"]').textContent).toContain(
      '“Pokémon Winds” is removed from Upcoming',
    )
    $('[data-testid="confirm-button"]').click()
    await settle()
    expect(toast.error).toHaveBeenCalledWith('Boom')
    fail = false
    $('[data-testid="confirm-button"]').click()
    await settle()
    expect(calls.filter((c) => c.method === 'DELETE').at(-1)?.path).toBe('/api/watchlist/t-dec')
    expect(toast.success).toHaveBeenCalledWith('Removed from Upcoming')
    await vi.waitFor(() => expect($$('[data-testid="confirm-dialog"]')).toHaveLength(0))

    // Cancel closes without deleting.
    await openMenu(card('t-nov').querySelector('[data-testid="entry-menu"]')!)
    await settle()
    $('[data-testid="delete"]').click()
    await settle()
    $$('[data-testid="confirm-dialog"] button')
      .find((b) => b.textContent.includes('Cancel'))!
      .click()
    await settle()
    await vi.waitFor(() => expect($$('[data-testid="confirm-dialog"]')).toHaveLength(0))
    expect(calls.filter((c) => c.method === 'DELETE')).toHaveLength(2)
  })

  it('explains tracking when there is nothing yet (German)', async () => {
    mockApi({ 'GET /api/libraries': [], 'GET /api/watchlist': [] })
    await renderComponent(UpcomingView, { url: '/upcoming', locale: 'de' })
    await vi.waitFor(() => expect($$('[data-testid="empty"]')).toHaveLength(1))
    expect(pageText()).toContain('Demnächst')
    expect(pageText()).toContain('Noch nichts auf Demnächst')
    expect(pageText()).toContain('„Beobachten“')
    expect($$('[data-testid^="filter-"]')).toHaveLength(0)
  })

  it('shows load errors and entries without any library context', async () => {
    mockApi({
      'GET /api/libraries': [],
      'GET /api/watchlist': { status: 500, body: { detail: 'Down' } },
    })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect(pageText()).toContain('Down'))

    mockApi({ 'GET /api/libraries': [], 'GET /api/watchlist': [tracking()] })
    await renderComponent(UpcomingView, { url: '/upcoming' })
    await vi.waitFor(() => expect($$('[data-testid="tracking-card"]')).toHaveLength(1))
    expect(pageText()).toContain('Metroid Prime 4')
    await openMenu($('[data-testid="entry-menu"]'))
    await settle()
    expect($$('[data-testid="work-link"]')).toHaveLength(0)
  })
})
