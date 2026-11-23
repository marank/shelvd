import { describe, expect, it, vi } from 'vitest'
import type { ApiCall } from '@/test/utils'
import { mockApi, openMenu, pageText, renderApp, settle } from '@/test/utils'
import {
  layoutRoutes,
  makeItem,
  makeLibrary,
  makeOverview,
  makeRelease,
  makeWork,
} from '@/test/fixtures'
import { useUiStore } from '@/stores/ui'

const mk8 = makeItem({ id: 'item-mk8' })
const zelda = makeItem({
  id: 'item-zelda',
  release: makeRelease({ title: 'Zelda', publisher: null, year: null }),
  status: 'sold',
  location: {
    id: 'loc',
    name: 'Box A',
    path: 'Office › Box A',
    trail: [
      { name: 'Office', kind: 'room' },
      { name: 'Box A', kind: 'box' },
    ],
  },
})
const lent = makeItem({
  id: 'item-lent',
  release: makeRelease({ title: 'Pikmin 4' }),
  active_loan: {
    id: 'loan-1',
    borrower: { id: 'p1', name: 'Max' },
    lent_on: '2026-09-01',
    due_on: null,
  },
})

const tree = {
  total: 3,
  total_value: '120.00',
  group_by: ['platform.name', 'publisher.name'],
  nodes: [
    {
      field: 'platform.name',
      key: 'platform-switch',
      label: 'Nintendo Switch',
      count: 3,
      value: '120.00',
      children: [
        {
          field: 'publisher.name',
          key: 'company-nintendo',
          label: 'Nintendo',
          count: 2,
          value: '100.00',
          children: [],
        },
        { field: 'publisher.name', key: 'none', label: '', count: 1, value: '0', children: [] },
      ],
    },
  ],
}

function routes(overrides: Record<string, unknown> = {}) {
  const overviews = [
    makeOverview({ group_by: ['platform.name', 'publisher.name'] }),
    makeOverview({ id: 'overview-2', name: 'Alles', group_by: [] }),
  ]
  return {
    ...layoutRoutes(makeLibrary(), overviews),
    'GET /api/libraries/lib-1/tree': tree,
    'GET /api/libraries/lib-1/items': (call: ApiCall) => {
      const offset = Number(call.query.get('offset') ?? 0)
      return { count: 4, items: offset ? [lent] : [mk8, zelda, makeItem({ status: 'sold' })] }
    },
    'GET /api/libraries/lib-1/items/:id': mk8,
    'GET /api/libraries/lib-1/loans': [],
    ...overrides,
  }
}

describe('explorer', () => {
  it('shows folders, breadcrumbs and items and navigates into groups', async () => {
    const calls = mockApi(routes())
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="folder"]')).toHaveLength(1),
    )
    expect(pageText()).toContain('Nintendo Switch')
    expect(document.querySelectorAll('[data-testid="item-card"]')).toHaveLength(3)
    expect(document.querySelector('[data-testid="status-bar"]')?.textContent).toContain(
      'Platform · Publisher',
    )
    expect(document.querySelector('[data-testid="status-bar"]')?.textContent).toContain('€120.00')
    expect(document.querySelector('[data-testid="folder"]')?.textContent).toContain('€120.00')

    ;(document.querySelector('[data-testid="folder"]') as HTMLElement).click()
    await settle()
    expect(router.currentRoute.value.query.p).toEqual(['platform-switch'])
    const itemCalls = calls.filter((c) => c.path.endsWith('/items'))
    const itemCall = itemCalls[itemCalls.length - 1]!
    expect(itemCall.query.getAll('filter')).toEqual(['platform.name:platform-switch'])
    // Second level: the publisher folders incl. "not set".
    expect(pageText()).toContain('Not set')

    ;(document.querySelectorAll('[data-testid="folder"]')[0] as HTMLElement).click()
    await settle()
    expect(router.currentRoute.value.query.p).toEqual(['platform-switch', 'company-nintendo'])
    expect(document.querySelector('[data-testid="status-bar"]')?.textContent).toContain('€100.00')
    expect(document.querySelectorAll('[data-testid="folder"]')).toHaveLength(0)

    const middle = [...document.querySelectorAll('nav button')].find(
      (b) => b.textContent.trim() === 'Nintendo Switch',
    ) as HTMLElement
    middle.click()
    await settle()
    expect(router.currentRoute.value.query.p).toEqual(['platform-switch'])
    ;(document.querySelector('[data-testid="crumb-root"]') as HTMLElement).click()
    await settle()
    expect(router.currentRoute.value.query.p).toBeUndefined()
  })

  it('sorts the table by a column header while the page is open', async () => {
    mockApi(routes())
    const { router } = await renderApp('/l/lib-1?layout=table')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="item-table-row"]')).toHaveLength(3),
    )
    const titles = () =>
      [...document.querySelectorAll('[data-testid="item-table-row"] td:first-child')].map((td) =>
        td.textContent.trim(),
      )
    const header = (key: string) =>
      document.querySelector(`[data-testid="column-${key}"]`)!.getAttribute('aria-sort')
    const click = async (key: string) => {
      ;(document.querySelector(`[data-testid="sort-by-${key}"]`) as HTMLElement).click()
      await settle()
    }

    // Sorting needs every item: the second page is fetched by itself.
    await click('game.title')
    await vi.waitFor(() => expect(titles()).toHaveLength(4))
    expect(titles()).toEqual(['Mario Kart 8 Deluxe', 'Mario Kart 8 Deluxe', 'Pikmin 4', 'Zelda'])
    expect(header('game.title')).toBe('ascending')
    await click('game.title')
    expect(titles()[0]).toBe('Zelda')
    expect(header('game.title')).toBe('descending')

    // Empty values stay last in both directions.
    await click('release.year')
    expect(titles().at(-1)).toBe('Zelda')
    await click('release.year')
    expect(titles().at(-1)).toBe('Zelda')
    // Third click: back to the view's own order.
    await click('release.year')
    expect(header('release.year')).toBeNull()
    expect(titles()[1]).toBe('Zelda')
    // Nothing of this goes into the URL.
    expect(router.currentRoute.value.query).toEqual({ layout: 'table' })

    // Choosing a sort in the dialog ends the column sort.
    await click('game.title')
    ;(document.querySelector('[data-testid="sort-button"]') as HTMLElement).click()
    await settle()
    ;(document.querySelector('[data-testid="field-release.year"]') as HTMLElement).click()
    await settle()
    ;(document.querySelector('[data-testid="apply-sort"]') as HTMLElement).click()
    await settle()
    expect(header('game.title')).toBeNull()
    expect(router.currentRoute.value.query.sort).toBe('release.year')
  })

  it('loads more pages and switches layouts and sorting', async () => {
    const calls = mockApi(routes())
    const { router } = await renderApp('/l/lib-1?layout=list')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="item-row"]')).toHaveLength(3),
    )
    ;(document.querySelector('[data-testid="load-more"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="item-row"]')).toHaveLength(4),
    )
    expect(pageText()).toContain('Office › Box A')

    await router.replace({ query: { layout: 'table' } })
    await settle()
    const rows = document.querySelectorAll('[data-testid="item-table-row"]')
    expect(rows).toHaveLength(4)
    expect(pageText()).toContain('Sold')
    ;(rows[0] as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    // A copy opens its own page.
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('item'))
    expect(router.currentRoute.value.query).toEqual({})
    await router.push('/l/lib-1?layout=table')
    await settle()

    // The sort in the URL goes to the API as it is.
    await router.push('/l/lib-1?layout=table&sort=-release.year')
    await vi.waitFor(() =>
      expect(calls.some((c) => c.query.get('sort') === '-release.year')).toBe(true),
    )
    ;(document.querySelector('[data-testid="layout-grid"]') as HTMLElement).click()
    await settle()
    expect(router.currentRoute.value.query.layout).toBe('grid')
  })

  it('saves an unsaved nesting into the view', async () => {
    const calls = mockApi(routes({ 'PATCH /api/libraries/lib-1/overviews/:id': makeOverview() }))
    const { router } = await renderApp('/l/lib-1?g=platform.name')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="unsaved-dot"]')).not.toBeNull(),
    )
    await openMenu('view-menu')
    ;(document.querySelector('[data-testid="save-view"]') as HTMLElement).click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      group_by: ['platform.name'],
      sort: 'game.title',
      layout: 'grid',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.query.g).toBeUndefined())
  })

  it('renames and deletes views from the sidebar', async () => {
    const other = makeOverview({ id: 'overview-2', name: 'Timeline' })
    const calls = mockApi(
      routes({
        'GET /api/libraries/lib-1/overviews': [makeOverview(), other],
        'PATCH /api/libraries/lib-1/overviews/:id': other,
        'DELETE /api/libraries/lib-1/overviews/:id': { status: 204 },
      }),
    )
    const { router } = await renderApp('/l/lib-1?v=overview-2')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="view-actions-overview-2"]')).not.toBeNull(),
    )
    expect(document.querySelector('[data-testid="new-view"]')?.getAttribute('href')).toBe(
      '/l/lib-1/views/new',
    )
    await openMenu('view-actions-overview-2')
    expect(document.querySelector('[data-testid="sidebar-edit-view"]')?.getAttribute('href')).toBe(
      '/l/lib-1/views/overview-2/edit',
    )
    ;(document.querySelector('[data-testid="sidebar-rename-view"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="rename-view-input"]')).not.toBeNull(),
    )
    const input = document.querySelector('[data-testid="rename-view-input"]') as HTMLInputElement
    input.value = 'Zeitleiste'
    input.dispatchEvent(new Event('input'))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toEqual({ name: 'Zeitleiste' })

    await openMenu('view-actions-overview-2')
    ;(document.querySelector('[data-testid="sidebar-delete-view"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="sidebar-confirm-delete-view"]')).not.toBeNull(),
    )
    ;(document.querySelector('[data-testid="sidebar-confirm-delete-view"]') as HTMLElement).click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true))
    expect(calls.find((c) => c.method === 'DELETE')!.path).toContain('overview-2')
    await vi.waitFor(() => expect(router.currentRoute.value.query.v).toBeUndefined())
  })

  it('cancels renaming a view with Escape', async () => {
    const calls = mockApi(routes())
    await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="view-actions-overview-1"]')).not.toBeNull(),
    )
    await openMenu('view-actions-overview-1')
    ;(document.querySelector('[data-testid="sidebar-rename-view"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="rename-view-input"]')).not.toBeNull(),
    )
    const input = document.querySelector('[data-testid="rename-view-input"]') as HTMLInputElement
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await settle()
    expect(document.querySelector('[data-testid="rename-view-input"]')).toBeNull()
    // Leaving it blank or unchanged doesn't save either.
    for (const value of ['  ', 'Nach Plattform']) {
      await openMenu('view-actions-overview-1')
      ;(document.querySelector('[data-testid="sidebar-rename-view"]') as HTMLElement).click()
      await vi.waitFor(() =>
        expect(document.querySelector('[data-testid="rename-view-input"]')).not.toBeNull(),
      )
      const field = document.querySelector('[data-testid="rename-view-input"]') as HTMLInputElement
      field.value = value
      field.dispatchEvent(new Event('input'))
      field.dispatchEvent(new Event('blur'))
      await settle()
    }
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
  })

  it('deleting another view keeps the open one', async () => {
    const other = makeOverview({ id: 'overview-2', name: 'Timeline' })
    const calls = mockApi(
      routes({
        'GET /api/libraries/lib-1/overviews': [makeOverview(), other],
        'DELETE /api/libraries/lib-1/overviews/:id': { status: 204 },
      }),
    )
    const { router } = await renderApp('/l/lib-1?v=overview-1&layout=list')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="view-actions-overview-2"]')).not.toBeNull(),
    )
    await openMenu('view-actions-overview-2')
    ;(document.querySelector('[data-testid="sidebar-delete-view"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="sidebar-confirm-delete-view"]')).not.toBeNull(),
    )
    ;(document.querySelector('[data-testid="sidebar-confirm-delete-view"]') as HTMLElement).click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true))
    await settle()
    expect(router.currentRoute.value.query.v).toBe('overview-1')
  })

  it('without saved views, saving leads to the new-view page', async () => {
    mockApi({ ...routes(), 'GET /api/libraries/lib-1/overviews': [] })
    const { router } = await renderApp('/l/lib-1?g=release.year')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="unsaved-dot"]')).not.toBeNull(),
    )
    await openMenu('view-menu')
    ;(document.querySelector('[data-testid="save-view"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('overview-new'))
    expect(router.currentRoute.value.query.g).toBe('release.year')
  })

  it('shows empty states and opens the add dialog', async () => {
    mockApi(routes({ 'GET /api/libraries/lib-1/items': { count: 0, items: [] } }))
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="explorer-empty"]')).not.toBeNull(),
    )
    expect(pageText()).toContain('No games yet')
    const add = [
      ...document.querySelectorAll('[data-testid="explorer-empty"] button'),
    ][0] as HTMLElement
    add.click()
    expect(useUiStore().addOpen).toBe(true)
    expect(useUiStore().addMode).toBe('scan')

    await router.replace({ query: { q: 'nothing' } })
    await settle()
    expect(pageText()).toContain('No results')
  })

  it('duplicates and deletes a saved view from the view menu', async () => {
    const calls = mockApi(
      routes({
        'POST /api/libraries/lib-1/overviews': { status: 201, body: makeOverview({ id: 'copy' }) },
        'DELETE /api/libraries/lib-1/overviews/:id': { status: 204 },
      }),
    )
    const { router } = await renderApp('/l/lib-1?v=overview-2')
    await vi.waitFor(() => expect(pageText()).toContain('Alles'))
    const openMenu = async () => {
      document
        .querySelector('[data-testid="view-menu"]')!
        .dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
      await settle()
    }
    await openMenu()
    expect(document.querySelector('[data-testid="edit-view"]')?.getAttribute('href')).toBe(
      '/l/lib-1/views/overview-2/edit',
    )
    expect(document.querySelector('[data-testid="save-as-new"]')?.getAttribute('href')).toContain(
      '/l/lib-1/views/new?g=',
    )
    ;(document.querySelector('[data-testid="duplicate-view"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.v).toBe('copy'))
    expect(calls.find((c) => c.method === 'POST')!.body).toMatchObject({ name: 'Alles (copy)' })

    await router.replace('/l/lib-1?v=overview-2')
    await settle()
    await openMenu()
    ;(document.querySelector('[data-testid="delete-view"]') as HTMLElement).click()
    await settle()
    expect(pageText()).toContain('“Alles” will be deleted')
    ;(document.querySelector('[data-testid="sidebar-confirm-delete-view"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path.endsWith('overview-2'))).toBe(true),
    )
  })

  it('shows details in a third column and walks through items with the keyboard', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('min-width: 1024px'),
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    }))
    mockApi({
      ...routes(),
      'GET /api/libraries/lib-1/items/:id': (_: unknown, params: Record<string, string>) =>
        [mk8, zelda].find((i) => i.id === params.id) ?? mk8,
      'GET /api/catalog/works/:id': makeWork({
        id: 'w',
        title: 'Some game',
        summary: '',
        first_release_date: null,
        genres: [],
        developers: [],
        series: [],
        cover_url: null,
        releases: [zelda.release],
      }),
      'GET /api/watchlist': [],
    })
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="item-card"]')).toHaveLength(3),
    )
    ;(document.querySelector('[data-testid="toggle-detail-pane"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBe('item-mk8'))
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="detail-pane"]')).not.toBeNull(),
    )
    expect(useUiStore().detailPane).toBe(true)
    expect(document.querySelector('[data-item-id="item-mk8"]')?.getAttribute('aria-current')).toBe(
      'true',
    )

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBe('item-zelda'))
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }))
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBe('item-mk8'))
    // Clicking another card selects it instead of leaving the explorer.
    ;(document.querySelectorAll('[data-testid="item-card"]')[1] as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBe('item-zelda'))
    expect(router.currentRoute.value.name).toBe('explorer')
    // The column's "open" button leads to the selected copy's page; its game and
    // release blocks lead to theirs.
    const pane = () => document.querySelector('[data-testid="detail-pane"]')!
    await vi.waitFor(() =>
      expect(pane().querySelector('[data-testid="open-item"]')?.getAttribute('href')).toBe(
        '/items/item-zelda',
      ),
    )
    await vi.waitFor(() =>
      expect(
        pane().querySelector('[data-testid="level-card-work"] [data-testid="open-work"]'),
      ).not.toBeNull(),
    )
    expect(
      pane().querySelector('[data-testid="level-card-release"] [data-testid="open-release"]'),
    ).not.toBeNull()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBeUndefined())
    ;(document.querySelectorAll('[data-testid="item-card"]')[0] as HTMLElement).click()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="close-details"]')).not.toBeNull(),
    )
    ;(document.querySelector('[data-testid="close-details"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBeUndefined())
    ;(document.querySelector('[data-testid="toggle-detail-pane"]') as HTMLElement).click()
    await settle()
    expect(useUiStore().detailPane).toBe(false)
  })

  it('closes the detail column once its copy is deleted', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('min-width: 1024px'),
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    }))
    let answer!: () => void
    mockApi({
      ...routes(),
      'GET /api/catalog/works/:id': makeWork({
        id: 'w',
        title: 'Some game',
        summary: '',
        first_release_date: null,
        genres: [],
        developers: [],
        series: [],
        cover_url: null,
        releases: [mk8.release],
      }),
      'GET /api/watchlist': [],
      'DELETE /api/libraries/lib-1/items/item-mk8': () =>
        new Promise((resolve) => (answer = () => resolve({ status: 204 }))),
    })
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="item-card"]')).toHaveLength(3),
    )
    ;(document.querySelector('[data-testid="toggle-detail-pane"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBe('item-mk8'))
    await vi.waitFor(() =>
      expect(
        document.querySelector('[data-testid="detail-pane"] [aria-label="Actions for this copy"]'),
      ).not.toBeNull(),
    )
    document
      .querySelector('[data-testid="detail-pane"] [aria-label="Actions for this copy"]')!
      .dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    await settle()
    ;(document.querySelector('[data-testid="delete-copy"]') as HTMLElement).click()
    await settle()
    const confirm = document.querySelector('[data-testid="confirm-delete"]') as HTMLButtonElement
    confirm.click()
    // No second DELETE while the first one is on its way.
    await vi.waitFor(() => expect(confirm.disabled).toBe(true))
    answer()
    await vi.waitFor(() => expect(router.currentRoute.value.query.item).toBeUndefined())
    expect(document.querySelector('[data-testid="detail-pane"]')).toBeNull()
  })

  it('changes the cover size', async () => {
    mockApi(routes())
    await renderApp('/l/lib-1')
    await vi.waitFor(() => expect(document.querySelector('[data-testid="grid-l"]')).not.toBeNull())
    ;(document.querySelector('[data-testid="grid-l"]') as HTMLElement).click()
    await settle()
    expect(useUiStore().gridSize).toBe('l')
    // jsdom has no wide screen: the phone row heights (80 %) apply.
    expect(
      document.querySelector('[data-testid="item-grid"]')?.getAttribute('data-row-height'),
    ).toBe('216')
    const card = document.querySelector('[data-testid="item-card"]') as HTMLElement
    // Not measured in jsdom: laid out as one row at the target height (5:7 placeholders).
    expect(card.style.width).toBe(`${Math.floor((5 / 7) * 216 + 12)}px`)
    ;(document.querySelector('[data-testid="grid-s"]') as HTMLElement).click()
    await settle()
    expect(
      document.querySelector('[data-testid="item-grid"]')?.getAttribute('data-row-height'),
    ).toBe('112')
  })
  it('splits the list into collapsible sections and saves the choice', async () => {
    const sections = [
      { field: 'copy.added', key: '2026-03', label: '2026-03', count: 2, value: '50.00', start: 0 },
      { field: 'copy.added', key: 'none', label: '', count: 2, value: '0', start: 2 },
    ]
    const calls = mockApi(
      routes({
        'GET /api/libraries/lib-1/items': (call: ApiCall) => {
          const offset = Number(call.query.get('offset') ?? 0)
          const sectioned = call.query.get('section') === 'copy.added'
          return {
            count: 4,
            items: offset ? [lent] : [mk8, zelda, makeItem({ id: 'item-3' })],
            sections: sectioned ? sections : [],
          }
        },
        'PATCH /api/libraries/lib-1/overviews/:id': makeOverview(),
      }),
    )
    const { router } = await renderApp('/l/lib-1?v=overview-2&s=copy.added')
    const ui = useUiStore()
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="section-header"]')).toHaveLength(2),
    )
    expect(calls.some((c) => c.query.get('section') === 'copy.added')).toBe(true)
    const headers = () => document.querySelectorAll<HTMLElement>('[data-testid="section-header"]')
    expect(headers()[0]!.textContent).toContain('March 2026')
    expect(headers()[0]!.textContent).toContain('€50.00')
    expect(headers()[1]!.textContent).toContain('Not set')
    const cards = (i: number) =>
      document
        .querySelectorAll('[data-testid="item-section"]')
        [i]!.querySelectorAll('[data-testid="item-card"]').length
    expect(cards(0)).toBe(2)
    expect(cards(1)).toBe(1)
    expect(document.querySelector('[data-testid="status-bar"]')?.textContent).toContain(
      'Sections: Added',
    )

    // Folding in: remembered per library and field; nothing left to load for it.
    headers()[1]!.click()
    await settle()
    expect(headers()[1]!.getAttribute('aria-expanded')).toBe('false')
    expect(cards(1)).toBe(0)
    expect(ui.collapsed['lib-1|copy.added']).toEqual(['none'])
    expect(document.querySelector('[data-testid="load-more"]')).toBeNull()
    await openMenu('section-picker')
    ;(document.querySelector('[data-testid="toggle-all-sections"]') as HTMLElement).click()
    await settle()
    expect(ui.collapsed['lib-1|copy.added']).toEqual(['2026-03', 'none'])
    await openMenu('section-picker')
    ;(document.querySelector('[data-testid="toggle-all-sections"]') as HTMLElement).click()
    await settle()
    expect(ui.collapsed['lib-1|copy.added']).toBeUndefined()
    expect(document.querySelector('[data-testid="load-more"]')).not.toBeNull()

    await openMenu('view-menu')
    ;(document.querySelector('[data-testid="save-view"]') as HTMLElement).click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({ section: 'copy.added' })
    await vi.waitFor(() => expect(router.currentRoute.value.query.s).toBeUndefined())
  })
})
