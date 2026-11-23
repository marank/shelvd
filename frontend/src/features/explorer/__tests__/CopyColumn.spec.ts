import { describe, expect, it, vi } from 'vitest'
import { layoutRoutes, makeItem, makeLibrary, makeRelease, makeWork } from '@/test/fixtures'
import { mockApi, renderComponent } from '@/test/utils'

const release = makeRelease({
  id: 'rel-1',
  work_id: 'work-1',
  age_rating: 'USK 0',
  product_code: 'LA-H-AAAAA-EUR',
  release_number: 7,
})
const upcoming = makeRelease({
  id: 'rel-2',
  work_id: 'work-1',
  title: 'Mario Kart 9',
  release_date: '2099-07-01',
  release_precision: 'quarter',
  is_released: false,
  platform: { ...release.platform, id: 'sw2', name: 'Nintendo Switch 2', short_name: 'Switch 2' },
})
const copy = makeItem({
  id: 'item-1',
  release,
  location: {
    id: 'l1',
    name: 'Box',
    path: 'Office › Box',
    trail: [
      { name: 'Office', kind: 'room' },
      { name: 'Box', kind: 'box' },
    ],
  },
  owner: { id: 'p1', name: 'Lena' },
  condition: 'good',
  play_status: 'finished',
  status: 'sold',
  format: 'digital',
  notes: 'With DLC',
  current_value: '89.90',
  tags: ['Steelbook'],
  title: 'MK8 (mine)',
  active_loan: {
    id: 'loan-1',
    borrower: { id: 'p2', name: 'Max' },
    lent_on: '2026-01-01',
    due_on: '2000-01-01',
  },
})

function routes(role = 'owner', extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary({ role })),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/catalog/works/work-1': makeWork({
      summary: 'A'.repeat(400),
      series: [{ id: 'series-mk', name: 'Mario Kart' }],
      releases: [release, upcoming],
    }),
    'GET /api/libraries/lib-1/items': { count: 1, items: [copy] },
    'GET /api/watchlist': [
      {
        id: 'tr-1',
        release: upcoming,
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
    ...extra,
  }
}

describe('a copy opened from the explorer', () => {
  it("shows the copy's own card, not the game's sums", async () => {
    const sibling = makeItem({ id: 'item-0', release: upcoming, current_value: '10.00' })
    const { default: CopyColumn } = await import('@/features/explorer/components/CopyColumn.vue')
    const calls = mockApi(
      routes('owner', {
        'GET /api/libraries/lib-1/items': { count: 2, items: [sibling, copy] },
        'GET /api/lookup/providers': [
          { name: 'hltb', label: 'HowLongToBeat', kind: 'facts', enabled: true },
        ],
        'POST /api/catalog/works/:id/facts/refresh': { refreshed: false },
      }),
    )
    await renderComponent(CopyColumn, { props: { libraryId: 'lib-1', item: copy } })
    // Opening a copy refreshes its game's stale play times and scores.
    await vi.waitFor(() =>
      expect(calls.some((c) => c.path === '/api/catalog/works/work-1/facts/refresh')).toBe(true),
    )
    const stats = () => document.querySelector('[data-testid="hero-stats"]')?.textContent ?? ''
    expect(stats()).not.toContain('Total value')
    // No kicker, "edit" sits in the menu; place, value … in the copy's own card.
    expect(document.querySelector('[data-testid="item-kicker"]')).toBeNull()
    const own = document.querySelector('[data-testid="level-card-item"]')!.textContent
    expect(own).toContain('Office › Box')
    expect(own).toContain('89.90')
    // Lent: the loan shows (only then).
    expect(document.querySelector('[data-testid="active-loan"]')!.textContent).toContain('Max')
    // The library's copies of the game, the clicked one marked; another selects it.
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="column-copy"]')).toHaveLength(2),
    )
    const rows = [...document.querySelectorAll('[data-testid="column-copy"]')]
    expect(rows.find((r) => r.getAttribute('aria-current'))!.textContent).toContain('PAL')
    expect(rows.find((r) => !r.getAttribute('aria-current'))!.getAttribute('href')).toContain(
      'item=item-0',
    )
    // Release and game as rows, terms linked; releases one link away, no grid.
    const card = (level: string) =>
      document.querySelector(`[data-testid="level-card-${level}"]`)!.textContent
    expect(card('release')).toContain('USK 0')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="column-releases"]')!.textContent).toContain(
        'releases',
      ),
    )
    expect(document.querySelector('[data-testid="column-series"]')!.getAttribute('href')).toBe(
      '/series/series-mk',
    )
    expect(document.querySelector('[data-testid="release-grid"]')).toBeNull()
  })
})
