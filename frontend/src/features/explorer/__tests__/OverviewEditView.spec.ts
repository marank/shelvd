import { describe, expect, it, vi } from 'vitest'
import { layoutRoutes, makeLibrary, makeOverview } from '@/test/fixtures'
import { mockApi, pageText, renderApp, settle } from '@/test/utils'

async function type(selector: string, value: string) {
  const input = document.querySelector(selector) as HTMLInputElement
  input.value = value
  input.dispatchEvent(new Event('input'))
  await settle()
}

async function submit() {
  await settle()
  document.querySelector('form')!.dispatchEvent(new Event('submit'))
  await settle()
}

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary(), [
      makeOverview({ group_by: ['platform.name', 'release.year'], layout: 'list' }),
    ]),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/libraries/lib-1/items': { count: 0, items: [] },
    ...extra,
  }
}

describe('overview edit page', () => {
  it('creates a view prefilled from the explorer', async () => {
    const calls = mockApi(
      routes({
        'POST /api/libraries/lib-1/overviews': { status: 201, body: makeOverview({ id: 'new' }) },
      }),
    )
    const { router } = await renderApp(
      '/l/lib-1/views/new?g=platform.name,colour,release.year&sort=release.year&layout=table',
    )
    await vi.waitFor(() => expect(document.querySelector('#v-name')).not.toBeNull())
    expect(pageText()).toContain('New view')
    await submit()
    expect(pageText()).toContain('Give the view a name.')
    await type('#v-name', ' Jahre ')
    ;(document.querySelector('[data-testid="view-layout-grid"]') as HTMLElement).click()
    await submit()
    expect(calls.find((c) => c.method === 'POST')!.body).toMatchObject({
      name: 'Jahre',
      group_by: ['platform.name', 'release.year'],
      sort: 'release.year',
      layout: 'grid',
      filters: {},
    })
    await vi.waitFor(() => expect(router.currentRoute.value.query.v).toBe('new'))
  })

  it('edits an existing view and reports errors', async () => {
    const calls = mockApi(
      routes({
        'PATCH /api/libraries/lib-1/overviews/overview-1': () =>
          calls.filter((c) => c.method === 'PATCH').length > 1
            ? makeOverview()
            : { status: 400, body: { detail: 'Unknown sort order.' } },
      }),
    )
    const { router } = await renderApp('/l/lib-1/views/overview-1/edit')
    await vi.waitFor(() =>
      expect((document.querySelector('#v-name') as HTMLInputElement).value).toBe('Nach Plattform'),
    )
    ;(document.querySelector('[data-testid="edit-sort"]') as HTMLElement).click()
    await settle()
    ;(document.querySelector('[data-testid="field-copy.added"]') as HTMLElement).click()
    await settle()
    ;(document.querySelector('[data-testid="apply-sort"]') as HTMLElement).click()
    await settle()
    expect(document.querySelector('[data-testid="view-sort"]')!.textContent).toContain('Added')
    await submit()
    await vi.waitFor(() => expect(pageText()).toContain('Unknown sort order.'))
    await submit()
    expect(calls.filter((c) => c.method === 'PATCH')[0]!.body).toMatchObject({
      name: 'Nach Plattform',
      group_by: ['platform.name', 'release.year'],
      sort: 'copy.added',
      layout: 'list',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('explorer'))
  })

  it('reorders, removes and adds nesting levels', async () => {
    const calls = mockApi(
      routes({ 'PATCH /api/libraries/lib-1/overviews/overview-1': makeOverview() }),
    )
    await renderApp('/l/lib-1/views/overview-1/edit')
    const chips = () =>
      document.querySelectorAll('[data-testid="group-by-editor"] [draggable="true"]')
    await vi.waitFor(() => expect(chips()).toHaveLength(2))
    chips()[1]!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', altKey: true }))
    await settle()
    chips()[0]!.dispatchEvent(new Event('dragstart'))
    chips()[1]!.dispatchEvent(new Event('drop'))
    await settle()
    chips()[0]!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', altKey: true }))
    await settle()
    chips()[0]!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }))
    await settle()
    expect(chips()).toHaveLength(1)
    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      group_by: ['platform.name'],
    })
  })

  it('edits filter conditions with a live count', async () => {
    const calls = mockApi(
      routes({
        'GET /api/libraries/lib-1/tree': (call: { query: URLSearchParams }) =>
          call.query.get('group_by') === 'game.kind'
            ? {
                total: 3,
                group_by: ['game.kind'],
                nodes: [
                  {
                    field: 'game.kind',
                    key: 'game',
                    label: 'game',
                    count: 2,
                    value: '0',
                    children: [],
                  },
                  {
                    field: 'game.kind',
                    key: 'toy',
                    label: 'toy',
                    count: 1,
                    value: '0',
                    children: [],
                  },
                ],
              }
            : { total: 0, group_by: [], nodes: [] },
        'GET /api/libraries/lib-1/items': (call: { query: URLSearchParams }) => ({
          count: call.query.getAll('where').length ? 2 : 5,
          items: [],
        }),
        'GET /api/libraries/lib-1/overviews': [
          makeOverview({ filters: ['game.kind=toy', 'release.region!=jp', 'nonsense'] }),
        ],
        'PATCH /api/libraries/lib-1/overviews/overview-1': makeOverview(),
      }),
    )
    await renderApp('/l/lib-1/views/overview-1/edit')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="filter-value"]')).toHaveLength(2),
    )
    // Unknown conditions are dropped; the rest show as rows.
    expect(document.querySelector('[data-testid="filter-1"]')).not.toBeNull()
    expect(document.querySelector('[data-testid="filter-2"]')).toBeNull()
    await vi.waitFor(() => expect(pageText()).toContain('2 of 5 copies match'))
    const [game, toy] = document.querySelectorAll<HTMLElement>('[data-testid="filter-value"]')
    game!.click()
    await settle()
    toy!.click()
    await settle()

    // Second row: title matches a pattern.
    const row = (i: number) => document.querySelector(`[data-testid="filter-${i}"]`)!
    const select = (el: Element, value: string) => {
      const s = el as HTMLSelectElement
      s.value = value
      s.dispatchEvent(new Event('change'))
    }
    // Fields are picked by typing; paths work too ("place.box").
    const pick = async (i: number, query: string, key: string) => {
      const input = row(i).querySelector('[data-testid="filter-field"]') as HTMLInputElement
      input.dispatchEvent(new Event('focus'))
      input.value = query
      input.dispatchEvent(new Event('input'))
      await settle()
      const option = row(i).querySelector(`[data-testid="field-option-${key}"]`) as HTMLElement
      expect(option).not.toBeNull()
      option.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
      await settle()
    }
    await pick(1, 'title', 'game.title')
    const text = row(1).querySelector('[data-testid="filter-text"]') as HTMLInputElement
    text.value = 'A*'
    text.dispatchEvent(new Event('input'))
    await settle()

    // Third row: box has a value, then all → any.
    ;(document.querySelector('[data-testid="add-filter"]') as HTMLElement).click()
    await settle()
    await pick(2, 'place.bo', 'location.box')
    expect((row(2).querySelector('[data-testid="filter-field"]') as HTMLInputElement).value).toBe(
      'Place › Box',
    )
    select(row(2).querySelector('[data-testid="filter-op"]')!, 'set')
    await settle()
    // Fourth row: value between two numbers; fifth row stays unfinished and is dropped.
    ;(document.querySelector('[data-testid="add-filter"]') as HTMLElement).click()
    await settle()
    // Keyboard: type, arrow down to the first match, Enter.
    const input = row(3).querySelector('[data-testid="filter-field"]') as HTMLInputElement
    input.dispatchEvent(new Event('focus'))
    input.value = 'release.numb'
    input.dispatchEvent(new Event('input'))
    await settle()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    await settle()
    select(row(3).querySelector('[data-testid="filter-op"]')!, 'between')
    await settle()
    for (const [id, value] of [
      ['filter-text', '1'],
      ['filter-high', '100'],
    ] as const) {
      const input = row(3).querySelector(`[data-testid="${id}"]`) as HTMLInputElement
      input.value = value
      input.dispatchEvent(new Event('input'))
      await settle()
    }
    ;(document.querySelector('[data-testid="add-filter"]') as HTMLElement).click()
    await settle()
    ;(document.querySelector('[data-testid="match-any"]') as HTMLElement).click()
    await settle()

    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      filters: ['game.kind=game', 'game.title~A*', 'location.box?', 'release.number><1..100'],
      match: 'any',
    })
  })

  it('removes filters', async () => {
    const calls = mockApi(
      routes({
        'GET /api/libraries/lib-1/overviews': [
          makeOverview({ filters: ['location.box?', 'release.year>=2020'] }),
        ],
        'PATCH /api/libraries/lib-1/overviews/overview-1': makeOverview(),
      }),
    )
    await renderApp('/l/lib-1/views/overview-1/edit')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="filter-1"]')).not.toBeNull(),
    )
    expect(
      (
        document.querySelector(
          '[data-testid="filter-1"] [data-testid="filter-text"]',
        ) as HTMLInputElement
      ).value,
    ).toBe('2020')
    ;(
      document.querySelector(
        '[data-testid="filter-0"] [data-testid="remove-filter"]',
      ) as HTMLElement
    ).click()
    await settle()
    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      filters: ['release.year>=2020'],
    })
  })

  it('shows not found for unknown views', async () => {
    mockApi(routes())
    await renderApp('/l/lib-1/views/nope/edit')
    await vi.waitFor(() => expect(pageText()).toContain('Not found.'))
  })
})
