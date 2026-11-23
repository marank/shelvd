import { describe, expect, it, vi } from 'vitest'
import { FIELD_KEYS } from '@/lib/itemFields'
import { layoutRoutes, makeItem, makeLibrary, makeOverview, makeRelease } from '@/test/fixtures'
import { mockApi, openMenu, pageText, renderApp, settle } from '@/test/utils'

const item = makeItem({
  id: 'item-1',
  release: makeRelease({
    release_number: 17,
    product_code: 'LA-H-AAAAA-EUR',
    series: [{ id: 'series-zelda', name: 'Zelda' }],
    genres: [{ id: 'genre-adventure', name: 'Adventure' }],
    barcodes: ['0045496420277'],
    release_precision: 'quarter',
    release_date: '2099-07-01',
  }),
  condition: 'good',
  completeness: 'complete',
  play_status: 'finished',
  current_value: '89.90',
  purchase_price: '59.99',
  acquired_on: '2024-02-03',
  tags: ['Steelbook'],
  notes: 'Signed',
  owner: { id: 'p1', name: 'Lena' },
  location: {
    id: 'l1',
    name: 'Box NSW-01',
    path: 'Home › Left › Box NSW-01',
    trail: [
      { name: 'Home', kind: 'room' },
      { name: 'Left', kind: 'shelf' },
      { name: 'Box NSW-01', kind: 'box' },
    ],
  },
  active_loan: {
    id: 'loan',
    borrower: { id: 'p2', name: 'Max' },
    lent_on: '2026-01-01',
    due_on: null,
  },
})

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary(), [makeOverview({ group_by: [] })]),
    'GET /api/libraries/lib-1/tree': { total: 1, group_by: [], nodes: [] },
    'GET /api/libraries/lib-1/items': { count: 1, items: [item] },
    ...extra,
  }
}

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const tab = async (name: string) => {
  q(`[data-testid="fields-tab-${name}"]`).dispatchEvent(
    new MouseEvent('mousedown', { bubbles: true, button: 0 }),
  )
  await settle()
}
/** The picker of the open tab (inactive tabs aren't rendered). */
const inPicker = (selector: string) => q(`[data-testid="field-picker"] ${selector}`)

describe('item fields', () => {
  it('shows every known field in the table (unknown keys are skipped)', async () => {
    mockApi(routes())
    await renderApp(`/l/lib-1?layout=table&f_table=${[...FIELD_KEYS, 'gone'].join(',')}`)
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="item-table-row"]')).not.toBeNull(),
    )
    expect(document.querySelectorAll('thead th')).toHaveLength(FIELD_KEYS.length + 1)
    const text = pageText()
    for (const value of [
      '#17',
      'LA-H-AAAAA-EUR',
      'Box NSW-01',
      'Left',
      'Home',
      'Max',
      'Lena',
      '€89.90',
      '€59.99',
      'Q3 2099',
      '#Steelbook',
      'Signed',
      'Adventure',
      'Game',
      'Good',
      'Complete',
      'Finished',
    ]) {
      expect(text).toContain(value)
    }
  })

  it('picks, orders and saves the table fields in the dialog', async () => {
    const calls = mockApi(
      routes({ 'PATCH /api/libraries/lib-1/overviews/overview-1': makeOverview() }),
    )
    const { router } = await renderApp('/l/lib-1?layout=table')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="column-release.region"]')).not.toBeNull(),
    )

    q('[data-testid="fields-button"]').click()
    await settle()
    // Opens on the current layout's tab.
    expect(document.querySelectorAll('[data-testid="shown-fields"] li')).toHaveLength(8)
    const search = inPicker('[data-testid="field-search"]') as HTMLInputElement
    search.value = 'zzz'
    search.dispatchEvent(new Event('input'))
    await settle()
    expect(pageText()).toContain('No field found.')
    search.value = 'box'
    search.dispatchEvent(new Event('input'))
    await settle()
    inPicker('[data-testid="field-location.box"]').click()
    await settle()
    // Move "Platform" below "Region", then hide "Region".
    inPicker('[data-testid="move-down"]').click()
    await settle()
    const region = [...document.querySelectorAll('[data-testid="shown-fields"] li')].find((li) =>
      li.textContent.includes('Region'),
    )!
    ;(region.querySelector('[data-testid="hide-field"]') as HTMLElement).click()
    await settle()
    q('[data-testid="apply-fields"]').click()
    await settle()
    expect(router.currentRoute.value.query.f_table).toBe(
      'platform.name,release.year,publisher.name,location.path,owner.name,copy.value,copy.status,location.box',
    )
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="column-location.box"]')).not.toBeNull(),
    )
    expect(document.querySelector('[data-testid="column-release.region"]')).toBeNull()

    await openMenu('view-menu')
    q('[data-testid="save-view"]').click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      fields: {
        table: [
          'platform.name',
          'release.year',
          'publisher.name',
          'location.path',
          'owner.name',
          'copy.value',
          'copy.status',
          'location.box',
        ],
      },
    })
  })

  it('keeps fields per presentation and goes back to the defaults', async () => {
    mockApi(
      routes({
        'GET /api/libraries/lib-1/overviews': [
          makeOverview({
            fields: { list: ['location.box', 'release.number'], grid: ['location.box'] },
          }),
        ],
      }),
    )
    const { router } = await renderApp('/l/lib-1?layout=list')
    await vi.waitFor(() => expect(pageText()).toContain('Box NSW-01 · #17'))
    await router.replace({ query: { layout: 'grid' } })
    await settle()
    const card = () => document.querySelector('[data-testid="item-card"]')!.textContent
    expect(card()).toContain('Box NSW-01')
    expect(card()).not.toContain('#17')

    q('[data-testid="fields-button"]').click()
    await settle()
    q('[data-testid="reset-fields"]').click()
    await settle()
    // The detail column has its own tab; changing it doesn't touch the grid.
    await tab('detail')
    expect(pageText()).toContain('release block')
    inPicker('[data-testid="field-location.box"]').click()
    await settle()
    q('[data-testid="apply-fields"]').click()
    await settle()
    expect(router.currentRoute.value.query.f_grid).toBe(',')
    expect(router.currentRoute.value.query.f_detail).toContain('location.box')
    expect(router.currentRoute.value.query.f_list).toBeUndefined()
    expect(card()).not.toContain('Box NSW-01')
  })

  it('edits each presentation on the view edit page', async () => {
    const calls = mockApi(
      routes({ 'PATCH /api/libraries/lib-1/overviews/overview-1': makeOverview() }),
    )
    await renderApp('/l/lib-1/views/overview-1/edit')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="view-fields-detail"]')).not.toBeNull(),
    )
    expect(q('[data-testid="view-fields-list"]').textContent).toContain('Default')
    q('[data-testid="edit-fields-list"]').click()
    await settle()
    inPicker('[data-testid="field-release.number"]').click()
    await settle()
    q('[data-testid="apply-fields"]').click()
    await settle()
    expect(q('[data-testid="view-fields-list"]').textContent).toContain('Release number')
    document.querySelector('form')!.dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      fields: { list: ['release.year', 'publisher.name', 'location.path', 'release.number'] },
    })
    expect(
      Object.keys((calls.find((c) => c.method === 'PATCH')!.body as { fields: object }).fields),
    ).toEqual(['list'])
  })
})
