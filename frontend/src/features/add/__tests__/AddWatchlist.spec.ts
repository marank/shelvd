import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { useUiStore } from '@/stores/ui'
import { mockApi, pageText, renderComponent, settle } from '@/test/utils'
import AddItemDialog from '../components/AddItemDialog.vue'
import { $, $$, baseRoutes, candidate, click, LIB, release, submit, type } from './fixtures'

const upcoming = release({
  id: 'r-up',
  title: 'Metroid Prime 4',
  release_date: '2026-12-01',
  release_precision: 'month',
  sort_date: '2026-12-01',
  is_released: false,
  year: 2026,
})

function tracking(overrides: Record<string, unknown> = {}) {
  return {
    id: 't-1',
    release: upcoming,
    status: 'preordered',
    library: { id: LIB, name: 'Games' },
    user: 'alice',
    is_mine: true,
    owned_in: [],
    shop: '',
    price: null,
    ordered_on: null,
    notes: '',
    created_at: '2026-11-01T10:00:00Z',
    ...overrides,
  }
}

async function chooseFromSearch(routes: Record<string, unknown>, libraryId = LIB) {
  const calls = mockApi({
    ...baseRoutes(false),
    'GET /api/catalog/releases': [upcoming],
    ...routes,
  })
  const ctx = await renderComponent(AddItemDialog, { url: '/' })
  useUiStore().openAdd(libraryId, 'search')
  await settle()
  type('[data-testid="search-input"]', 'metroid')
  await vi.waitFor(() => expect($$('[data-testid="release-row"]')).toHaveLength(1))
  click('[data-testid="release-row"]')
  await settle()
  return { ...ctx, calls }
}

describe('AddItemDialog: tracking', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 1, 12))
  })
  afterEach(() => vi.useRealTimers())

  it('preselects "Track" for an unreleased game and opens Upcoming', async () => {
    const { calls, router } = await chooseFromSearch({
      'POST /api/watchlist': { status: 201, body: tracking() },
    })
    // The search row shows the precision-aware date.
    const chosen = $('[data-testid="chosen-release"]').textContent
    expect(chosen).toContain('December 2026')
    expect(chosen).toContain('next month')
    expect(($('[data-testid="destination-track"]') as HTMLInputElement).checked).toBe(true)
    expect($$('[data-testid="more-details"]')).toHaveLength(0)
    expect($$('[data-testid="add-next"]')).toHaveLength(0)

    type('#track-status', 'preordered')
    await nextTick()
    submit('[data-testid="item-form"]')
    await settle()

    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      release_id: 'r-up',
      status: 'preordered',
      library_id: LIB,
      shop: '',
      notes: '',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('upcoming'))
    expect(useUiStore().addOpen).toBe(false)
  })

  it('shows tracking errors and can switch back to the library', async () => {
    const { calls } = await chooseFromSearch(
      { 'POST /api/watchlist': { status: 409, body: { detail: 'Already tracked.' } } },
      '',
    )
    submit('[data-testid="item-form"]')
    await settle()
    expect($('[data-testid="item-error"]').textContent).toContain('Already tracked.')
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({ library_id: null })

    click('[data-testid="destination-library"]')
    await settle()
    // Library errors are separate from tracking errors.
    expect($$('[data-testid="item-error"]')).toHaveLength(0)
    expect($$('[data-testid="add-next"]')).toHaveLength(1)
    expect($$('#track-status')).toHaveLength(0)
  })

  it('shows candidate dates with their precision', async () => {
    mockApi({
      ...baseRoutes(),
      'GET /api/catalog/releases': [],
      'GET /api/lookup/search': {
        query: 'x',
        platform_id: null,
        candidates: [
          candidate({ external_id: '1', release_date: '2027-07-01', release_precision: 'quarter' }),
          candidate({ external_id: '2', release_date: null, release_precision: 'tba' }),
          candidate({ external_id: '3', release_date: null, year: null }),
        ],
        errors: [],
      },
    })
    await renderComponent(AddItemDialog, { url: '/' })
    useUiStore().openAdd(LIB, 'search')
    await settle()
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(3))
    const rows = $$('[data-testid="candidate-row"]').map((r) => r.textContent)
    expect(rows[0]).toContain('Q3 2027')
    expect(rows[1]).toContain('TBA')
    expect(rows[2]).not.toMatch(/\d{4}/)
    expect(pageText()).toContain('Zelda')
  })
})
